/**
 * 转码页 —— 桌面版 ui/convert_page.py 的 Web 重构。
 *
 * 与桌面版相比的 Web 化处理：
 *   · 汇编列带词法着色（助记符 / 伪指令 / 寄存器 / 立即数 / 标签 / 注释）
 *   · 左侧 gutter 显示行号与地址，行号与错误状态同时可见
 *   · 选中行在 gutter、两个面板、位段面板之间联动
 *   · 位段面板跟随选中行，点字段可看位区间
 *   · 一键复制机器码
 */

import {
  assembleProgram,
  formatMachineBytesEndian,
  disassembleBytes,
} from '../core/assembler.js';
import { renderBits, renderBitsEmpty, escapeHtml } from './bits.js';
import { highlightAsmLine } from './highlight.js';
import { saveState, SAMPLE_ASM, DEFAULT_MEMORY } from '../store.js';

const DEBOUNCE_MS = 100;

function fmt8(n) {
  return (n >>> 0).toString(16).padStart(8, '0');
}

function splitLines(text) {
  const lines = String(text).split('\n');
  while (lines.length > 1 && lines[lines.length - 1] === '') lines.pop();
  return lines.length ? lines : [''];
}

function concatBytes(parts) {
  const total = parts.reduce((s, d) => s + d.length, 0);
  const out = new Uint8Array(total);
  let off = 0;
  for (const d of parts) {
    out.set(d, off);
    off += d.length;
  }
  return out;
}

function validContent(text, mode) {
  if (mode === 'hex') return /^[0-9a-fA-F]+$/.test(text);
  return /^[01 ]+$/.test(text);
}

function parseData(text, mode) {
  if (mode === 'hex') {
    if (text.length % 2 !== 0) throw new Error('十六进制长度必须是偶数');
    const out = new Uint8Array(text.length / 2);
    for (let i = 0; i < out.length; i += 1) {
      out[i] = Number.parseInt(text.slice(i * 2, i * 2 + 2), 16);
    }
    return out;
  }
  const bits = text.replace(/ /g, '');
  if (bits.length % 8 !== 0) throw new Error('二进制长度必须是 8 的倍数');
  const out = new Uint8Array(bits.length / 8);
  for (let i = 0; i < out.length; i += 1) {
    out[i] = Number.parseInt(bits.slice(i * 8, i * 8 + 8), 2);
  }
  return out;
}

/**
 * 挂载转码页。
 * @param {HTMLElement} root
 * @param {object} state
 */
export function mountConvert(root, state) {
  root.innerHTML = `
    <div class="convert">
      <div class="toolbar">
        <div class="seg" id="cv-mode">
          <button type="button" data-v="hex">十六进制</button>
          <button type="button" data-v="bin">二进制</button>
        </div>
        <div class="seg" id="cv-endian">
          <button type="button" data-v="little">小端</button>
          <button type="button" data-v="big">大端</button>
        </div>
        <label class="field">起始地址 <input id="cv-base" value="00000000" spellcheck="false"></label>
        <span class="spacer"></span>
        <button type="button" class="ghost" id="cv-sample">载入示例</button>
        <button type="button" class="ghost" id="cv-clear">清空</button>
        <button type="button" class="ghost" id="cv-copy">复制机器码</button>
      </div>

      <div class="editor-grid">
        <div class="gutter">
          <div class="gutter-head">偏移</div>
          <div class="gutter-body"><div class="gutter-rows" id="cv-gutter"></div></div>
        </div>

        <div class="pane">
          <div class="pane-head"><span>汇编</span><span class="note" id="cv-asm-note"></span></div>
          <div class="pane-body">
            <div class="hl-layer" id="cv-asm-hl"></div>
            <textarea class="editor hl" id="cv-asm" wrap="off" spellcheck="false"
              placeholder="addi x1, x2, 100"></textarea>
          </div>
        </div>

        <div class="pane">
          <div class="pane-head"><span>机器码</span><span class="note" id="cv-mc-note"></span></div>
          <div class="pane-body">
            <div class="hl-layer" id="cv-mc-hl"></div>
            <textarea class="editor" id="cv-mc" wrap="off" spellcheck="false"
              placeholder="93004106（小端字节序，不带 0x）"></textarea>
          </div>
        </div>
      </div>

      <div class="err-note" id="cv-err"></div>

      <div class="bits-panel">
        <div class="bits-bar">
          <span class="bits-title" id="cv-bits-title">位段</span>
          <span class="bits-sub" id="cv-bits-sub">点击任意行查看字段拆分</span>
        </div>
        <div id="cv-bits"></div>
      </div>

      <div class="statusbar">
        <span><b id="cv-st-lines">0</b> 行</span>
        <span><b id="cv-st-bytes">0</b> 字节</span>
        <span><b id="cv-st-errs">0</b> 错误</span>
        <span class="spacer"></span>
        <button type="button" class="ghost small" id="cv-mem-toggle">内存布局</button>
      </div>

      <div class="mem-panel" id="cv-mem-panel" hidden>
        <div class="mem-grid" id="cv-mem"></div>
      </div>
    </div>
  `;

  const $ = (sel) => root.querySelector(sel);
  const gutter = $('#cv-gutter');
  const asm = $('#cv-asm');
  const mc = $('#cv-mc');
  const asmHl = $('#cv-asm-hl');
  const mcHl = $('#cv-mc-hl');
  const errNote = $('#cv-err');
  const bitsBody = $('#cv-bits');
  const bitsTitle = $('#cv-bits-title');
  const bitsSub = $('#cv-bits-sub');
  const baseInput = $('#cv-base');
  const stLines = $('#cv-st-lines');
  const stBytes = $('#cv-st-bytes');
  const stErrs = $('#cv-st-errs');

  let mode = state.mode ?? 'hex';
  let endian = state.endian ?? 'little';
  let baseAddr = 0;
  let results = [];
  let updating = false;
  let asmTimer = null;
  let revTimer = null;
  let scrolling = false;
  let curLine = 0;

  asm.value = state.asm ?? SAMPLE_ASM;
  mc.value = state.mc ?? '';
  baseInput.value = (state.baseAddr ?? '00000000').toString();

  // ── 分段控件 ─────────────────────────────────────────────
  function bindSeg(segId, value, onPick) {
    const seg = $(segId);
    const paint = (v) => {
      for (const b of seg.querySelectorAll('button')) {
        b.classList.toggle('on', b.dataset.v === v);
      }
    };
    paint(value);
    seg.addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-v]');
      if (!btn) return;
      paint(btn.dataset.v);
      onPick(btn.dataset.v);
    });
    return paint;
  }

  bindSeg('#cv-mode', mode, (v) => {
    mode = v;
    doAssembly();
  });
  bindSeg('#cv-endian', endian, (v) => {
    endian = v;
    doAssembly();
  });

  // ── 内存布局 ─────────────────────────────────────────────
  const memory = { ...DEFAULT_MEMORY, ...(state.memory ?? {}) };
  const memGrid = $('#cv-mem');
  for (const [key, label] of [
    ['rom_start', 'ROM 起始'],
    ['rom_size', 'ROM 大小'],
    ['ram_start', 'RAM 起始'],
    ['ram_size', 'RAM 大小'],
    ['stack_size', '栈大小'],
  ]) {
    const lb = document.createElement('label');
    lb.textContent = label;
    const input = document.createElement('input');
    input.type = 'text';
    input.value = memory[key] ?? '';
    input.spellcheck = false;
    input.addEventListener('change', () => {
      memory[key] = input.value.trim();
      saveState({ memory: { ...memory } });
    });
    lb.appendChild(input);
    memGrid.appendChild(lb);
  }
  $('#cv-mem-toggle').addEventListener('click', () => {
    const panel = $('#cv-mem-panel');
    panel.hidden = !panel.hidden;
  });

  // ── 渲染 ─────────────────────────────────────────────────
  function renderAll(lines) {
    const gutterRows = [];
    const asmRows = [];
    const mcRows = [];

    for (let i = 0; i < lines.length; i += 1) {
      const r = results[i];
      const err = Boolean(r && r.error);
      const cur = i === curLine ? ' cur' : '';
      // gutter 显示相对起始地址的偏移，绝对地址放在 title 里
      const offset = r ? r.address - baseAddr : 0;
      const addr = r ? offset.toString(16).padStart(4, '0') : '';
      const abs = r ? `0x${fmt8(r.address)}` : '';

      gutterRows.push(
        `<div class="g-row${err ? ' err' : ''}${cur}" title="${abs}">` +
          `<span class="g-no">${i + 1}</span><span class="g-addr">${addr}</span></div>`,
      );
      asmRows.push(`<div class="hl-row${err ? ' err' : ''}${cur}">${highlightAsmLine(lines[i])}</div>`);
      mcRows.push(`<div class="hl-row${err ? ' err' : ''}${cur}"></div>`);
    }

    gutter.innerHTML = gutterRows.join('');
    asmHl.innerHTML = asmRows.join('');
    mcHl.innerHTML = mcRows.join('');
    syncLayers();
  }

  function syncLayers() {
    asmHl.style.transform = `translateY(${-asm.scrollTop}px)`;
    mcHl.style.transform = `translateY(${-mc.scrollTop}px)`;
    gutter.style.transform = `translateY(${-asm.scrollTop}px)`;
  }

  function renderErrors() {
    const errs = results
      .map((r, i) => (r.error ? { line: i + 1, msg: r.error } : null))
      .filter(Boolean);
    errNote.innerHTML = errs
      .map((e) => `<div><span class="ln">第 ${e.line} 行</span>${escapeHtml(e.msg)}</div>`)
      .join('');
    return errs.length;
  }

  function renderStats(lineCount) {
    const bytes = results.reduce((s, r) => s + r.size, 0);
    const errs = results.filter((r) => r.error).length;
    stLines.textContent = String(lineCount);
    stBytes.textContent = String(bytes);
    stErrs.textContent = String(errs);
    stErrs.classList.toggle('err', errs > 0);
    $('#cv-asm-note').textContent = `${lineCount} 行`;
    $('#cv-mc-note').textContent = `${bytes} 字节`;
  }

  // ── 位段 ─────────────────────────────────────────────────
  function showBits(idx) {
    const row = results[idx];
    if (!row || !row.chunks.length) {
      bitsTitle.textContent = '位段';
      bitsSub.textContent = '这一行没有可解码的机器码';
      renderBitsEmpty(bitsBody, '');
      return;
    }
    const chunks = row.chunks.filter((c) => c.data);
    if (!chunks.length) {
      bitsTitle.textContent = `第 ${idx + 1} 行`;
      bitsSub.textContent = row.error ?? '无法编码';
      renderBitsEmpty(bitsBody, '');
      return;
    }

    bitsBody.replaceChildren();
    chunks.forEach((chunk, i) => {
      const word =
        (chunk.data[0] | (chunk.data[1] << 8) | (chunk.data[2] << 16) | (chunk.data[3] << 24)) >>> 0;
      const box = document.createElement('div');
      if (chunks.length > 1) box.classList.add('bits-group');
      const note = chunks.length > 1 ? `展开第 ${i + 1}/${chunks.length} 条` : `第 ${idx + 1} 行`;
      renderBits(box, word, { asm: chunk.text, note });
      bitsBody.appendChild(box);
    });

    bitsTitle.innerHTML = `第 ${idx + 1} 行`;
    bitsSub.textContent = chunks.length > 1 ? `该行展开为 ${chunks.length} 条指令` : '';
  }

  // ── 汇编 → 机器码 ────────────────────────────────────────
  function doAssembly() {
    if (updating) return;
    updating = true;
    try {
      const lines = splitLines(asm.value);
      const parsed = Number.parseInt(String(baseInput.value).replace(/^0x/i, ''), 16);
      baseAddr = Number.isFinite(parsed) ? parsed >>> 0 : 0;

      results = assembleProgram(lines, null, baseAddr);

      mc.value = results
        .map((r) => {
          const parts = r.chunks.filter((c) => c.data).map((c) => c.data);
          return parts.length ? formatMachineBytesEndian(concatBytes(parts), mode, endian) : '';
        })
        .join('\n');

      if (curLine >= lines.length) curLine = Math.max(0, lines.length - 1);
      renderAll(lines);
      renderErrors();
      renderStats(lines.length);
      showBits(curLine);

      saveState({ asm: asm.value, mc: mc.value, mode, endian, baseAddr: baseInput.value, memory: { ...memory } });
    } finally {
      updating = false;
    }
  }

  // ── 机器码 → 汇编 ────────────────────────────────────────
  function doReverse() {
    if (updating) return;
    updating = true;
    try {
      const lines = splitLines(mc.value);
      const newAsm = [];
      const errRows = [];
      let index = 0;

      for (const line of lines) {
        const stripped = line.trim();
        if (stripped && validContent(stripped, mode)) {
          try {
            let data = parseData(stripped, mode);
            if (!data.length || data.length % 4 !== 0) throw new Error('length');
            if (endian === 'big') data = Uint8Array.from(data).reverse();
            for (let k = 0; k < data.length; k += 4) {
              const word = data.slice(k, k + 4);
              const text = disassembleBytes(word);
              newAsm.push(text ?? '');
              errRows.push(text === null);
              index += 1;
            }
          } catch {
            newAsm.push('');
            errRows.push(true);
            index += 1;
          }
        } else {
          newAsm.push(stripped);
          errRows.push(false);
          index += 1;
        }
      }

      asm.value = newAsm.join('\n');
      results = assembleProgram(newAsm, null, baseAddr);
      mc.value = newAsm
        .map((_, i) => {
          const r = results[i];
          if (!r) return '';
          const parts = r.chunks.filter((c) => c.data).map((c) => c.data);
          return parts.length ? formatMachineBytesEndian(concatBytes(parts), mode, endian) : '';
        })
        .join('\n');

      const bad = errRows.filter(Boolean).length;
      if (curLine >= newAsm.length) curLine = Math.max(0, newAsm.length - 1);
      renderAll(newAsm);
      errNote.innerHTML = bad
        ? `<div><span class="ln">共 ${bad} 行</span>无法反汇编为有效指令</div>`
        : '';
      renderStats(newAsm.length);
      showBits(curLine);

      saveState({ asm: asm.value, mc: mc.value, mode, endian, baseAddr: baseInput.value, memory: { ...memory } });
    } finally {
      updating = false;
    }
  }

  function scheduleAssembly() {
    if (asmTimer) clearTimeout(asmTimer);
    asmTimer = setTimeout(doAssembly, DEBOUNCE_MS);
  }

  function scheduleReverse() {
    if (revTimer) clearTimeout(revTimer);
    revTimer = setTimeout(doReverse, DEBOUNCE_MS);
  }

  // ── 行选中 ───────────────────────────────────────────────
  function lineIndexAt(ta) {
    const before = ta.value.slice(0, ta.selectionStart);
    return before.split('\n').length - 1;
  }

  function selectLine(idx) {
    const total = splitLines(asm.value).length;
    const next = Math.max(0, Math.min(total - 1, idx));
    if (next === curLine && bitsBody.childElementCount) return;
    curLine = next;
    renderAll(splitLines(asm.value));
    showBits(curLine);
  }

  // ── 事件 ─────────────────────────────────────────────────
  asm.addEventListener('input', () => {
    if (updating) return;
    scheduleAssembly();
  });
  asm.addEventListener('click', () => selectLine(lineIndexAt(asm)));
  asm.addEventListener('keyup', (e) => {
    if (e.key.startsWith('Arrow') || e.key === 'Home' || e.key === 'End') {
      selectLine(lineIndexAt(asm));
    }
  });

  mc.addEventListener('input', () => {
    if (updating) return;
    scheduleReverse();
  });
  mc.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') setTimeout(doReverse, 0);
  });
  mc.addEventListener('click', () => {
    if (results.length) selectLine(lineIndexAt(mc));
  });

  baseInput.addEventListener('change', doAssembly);

  $('#cv-sample').addEventListener('click', () => {
    asm.value = SAMPLE_ASM;
    curLine = 0;
    doAssembly();
  });

  $('#cv-clear').addEventListener('click', () => {
    updating = true;
    asm.value = '';
    mc.value = '';
    updating = false;
    results = [];
    curLine = 0;
    renderAll(['']);
    errNote.innerHTML = '';
    renderStats(0);
    bitsTitle.textContent = '位段';
    bitsSub.textContent = '点击任意行查看字段拆分';
    renderBitsEmpty(bitsBody, '');
    saveState({ asm: '', mc: '' });
  });

  $('#cv-copy').addEventListener('click', async () => {
    const btn = $('#cv-copy');
    const text = mc.value;
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      btn.textContent = '已复制';
    } catch {
      btn.textContent = '复制失败';
    }
    setTimeout(() => {
      btn.textContent = '复制机器码';
    }, 1400);
  });

  // 滚动同步
  for (const ta of [asm, mc]) {
    ta.addEventListener('scroll', () => {
      syncLayers();
      if (scrolling) return;
      scrolling = true;
      const other = ta === asm ? mc : asm;
      if (other.scrollTop !== ta.scrollTop) other.scrollTop = ta.scrollTop;
      requestAnimationFrame(() => {
        scrolling = false;
      });
    });
  }

  const onKeydown = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
      e.preventDefault();
      saveState({ asm: asm.value, mc: mc.value, mode, endian, baseAddr: baseInput.value, memory: { ...memory } });
      const note = $('#cv-asm-note');
      note.textContent = '已保存到本机';
      setTimeout(() => {
        note.textContent = `${splitLines(asm.value).length} 行`;
      }, 1400);
    }
  };
  document.addEventListener('keydown', onKeydown);

  // ── 首次渲染 ─────────────────────────────────────────────
  doAssembly();

  return () => {
    document.removeEventListener('keydown', onKeydown);
    if (asmTimer) clearTimeout(asmTimer);
    if (revTimer) clearTimeout(revTimer);
  };
}
