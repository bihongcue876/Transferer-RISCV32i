/**
 * 学习页 —— 桌面版 ui/learn_page.py 的 Web 重构。
 *
 * 与桌面版相比的 Web 化处理：
 *   · 指令卡片改为自适应网格，宽屏一屏看多条
 *   · 左侧导航带实时搜索，输入即过滤
 *   · 滚动时导航自动高亮当前卡片
 *   · 「试试看」三个框即时互转，不用逐个点按钮
 *   · 格式表表头粘性固定
 */

import {
  RV32I_INSTRUCTIONS,
  PSEUDO_INSTRUCTIONS,
  expandPseudo,
} from '../core/isa.js';
import {
  assembleLine,
  bytesToHexStr,
  bytesToBinStr,
  disassembleBytes,
  disassembleHex,
  analyzeAssemblyLine,
} from '../core/assembler.js';
import { escapeHtml } from './bits.js';
import { highlightAsmLine } from './highlight.js';

const FMT_TITLE = { R: 'R 型', I: 'I 型', S: 'S 型', B: 'B 型', U: 'U 型', J: 'J 型' };

const PSEUDO_EXAMPLES = {
  li: 'x1, 0x12345', mv: 'x1, x2', not: 'x1, x2', neg: 'x1, x2',
  la: 'x1, 0x1000', nop: '', unimp: '', ret: '', call: '0x100', tail: '0x100',
  j: '0x20', jr: 'x1', jalr: 'x1', beqz: 'x1, 8', bnez: 'x1, 8',
  blez: 'x1, 8', bgez: 'x1, 8', bltz: 'x1, 8', bgtz: 'x1, 8',
  seqz: 'x1, x2', snez: 'x1, x2', sltz: 'x1, x2', sgtz: 'x1, x2',
  bgt: 'x1, x2, 8', ble: 'x1, x2, 8', bgtu: 'x1, x2, 8', bleu: 'x1, x2, 8',
};

function setStatus(el, kind, text) {
  el.className = `try-status${kind ? ` ${kind}` : ''}`;
  el.textContent = text;
}

function runTry(card, act) {
  const asmInput = card.querySelector('.try-asm');
  const hexInput = card.querySelector('.try-hex');
  const binInput = card.querySelector('.try-bin');
  const status = card.querySelector('.try-status');

  if (act === 'asm') {
    const text = asmInput.value.trim();
    if (!text) return setStatus(status, '', '');
    const data = assembleLine(text);
    if (data.length) {
      hexInput.value = bytesToHexStr(data);
      binInput.value = bytesToBinStr(data);
      setStatus(status, 'ok', `✅ ${data.length} 字节 · 0x${bytesToHexStr(data)}`);
    } else {
      const info = analyzeAssemblyLine(text);
      setStatus(status, 'err', `❌ ${info.error || '无法转换'}`);
    }
    return undefined;
  }

  if (act === 'hex') {
    const text = hexInput.value.trim().toLowerCase().replace(/\s/g, '');
    if (text.length !== 8) return setStatus(status, 'err', '❌ 需要 8 位十六进制');
    const asm = disassembleHex(text);
    if (!asm) return setStatus(status, 'err', '❌ 无效指令编码');
    asmInput.value = asm;
    const bytes = new Uint8Array(4);
    for (let i = 0; i < 4; i += 1) bytes[i] = Number.parseInt(text.slice(i * 2, i * 2 + 2), 16);
    binInput.value = bytesToBinStr(bytes);
    return setStatus(status, 'ok', '✅ 转换成功');
  }

  const bits = binInput.value.trim().replace(/ /g, '');
  if (bits.length !== 32 || !/^[01]+$/.test(bits)) return setStatus(status, 'err', '❌ 需要 32 位二进制');
  const bytes = new Uint8Array(4);
  for (let i = 0; i < 4; i += 1) bytes[i] = Number.parseInt(bits.slice(i * 8, i * 8 + 8), 2);
  const asm = disassembleBytes(bytes);
  if (!asm) return setStatus(status, 'err', '❌ 无效指令编码');
  asmInput.value = asm;
  hexInput.value = bytesToHexStr(bytes);
  return setStatus(status, 'ok', '✅ 转换成功');
}

function buildCard(inst, idx) {
  const name = inst.name.toLowerCase();
  const card = document.createElement('div');
  card.className = 'inst-card';
  card.id = `inst-${name}`;
  card.dataset.name = name;
  card.dataset.desc = inst.desc_short;

  const asmValue = inst.example.startsWith(name) ? inst.example : `${name} ${inst.example}`;

  card.innerHTML = `
    <div class="inst-head">
      <h3>${escapeHtml(inst.name)}</h3>
      <span class="desc">${escapeHtml(inst.desc_short)}</span>
      <span class="badge-fmt">${escapeHtml(inst.fmt)}</span>
    </div>
    <div class="inst-example">${highlightAsmLine(inst.example)}</div>
    <div class="inst-meta">
      ${inst.machine_table.map((l) => `<code>${escapeHtml(l.trim())}</code>`).join(' ')}<br>
      ${escapeHtml(inst.explanation)}
    </div>
    <div class="try">
      <div class="try-row">
        <span>汇编</span>
        <input class="try-asm" type="text" value="${escapeHtml(asmValue)}" spellcheck="false">
        <button type="button" data-act="asm" data-i="${idx}">转换</button>
      </div>
      <div class="try-row">
        <span>十六进制</span>
        <input class="try-hex" type="text" spellcheck="false" placeholder="8 位十六进制">
        <button type="button" data-act="hex" data-i="${idx}">转换</button>
      </div>
      <div class="try-row">
        <span>二进制</span>
        <input class="try-bin" type="text" spellcheck="false" placeholder="32 位二进制">
        <button type="button" data-act="bin" data-i="${idx}">转换</button>
      </div>
      <div class="try-status"></div>
    </div>
  `;
  return card;
}

/**
 * 每种格式的字段数不同，表头必须按格式取。
 * 与桌面版 ui/learn_page.py 的 _build_format_tables_treeview 一致。
 */
const FMT_HEADERS = {
  R: ['指令', 'funct7', 'rs2', 'rs1', 'funct3', 'rd', 'opcode', '功能'],
  I: ['指令', 'imm[11:0]', 'rs1', 'funct3', 'rd', 'opcode', '功能'],
  S: ['指令', 'imm[11:5]', 'rs2', 'rs1', 'funct3', 'imm[4:0]', 'opcode', '功能'],
  B: ['指令', 'imm[12|10:5]', 'rs2', 'rs1', 'funct3', 'imm[4:1|11]', 'opcode', '功能'],
  U: ['指令', 'imm[31:12]', 'rd', 'opcode', '功能'],
  J: ['指令', 'imm[20|10:1|11|19:12]', 'rd', 'opcode', '功能'],
};

function buildFormatTable(fmt, rows) {
  const head = FMT_HEADERS[fmt] ?? FMT_HEADERS.R;
  const last = head.length - 1;
  const wrap = document.createElement('div');
  wrap.className = 'table-wrap';
  wrap.innerHTML = `
    <table class="matrix">
      <thead><tr>${head.map((h) => `<th>${h}</th>`).join('')}</tr></thead>
      <tbody>${rows
        .map(
          (r) => `<tr>${r
            .map((cell, i) => `<td class="${i === last ? 'fn' : 'mono'}">${escapeHtml(cell)}</td>`)
            .join('')}</tr>`,
        )
        .join('')}</tbody>
    </table>
  `;
  return wrap;
}

function buildPseudoSection() {
  const sec = document.createElement('section');
  sec.id = 'pseudo-table';
  sec.innerHTML = '<h2>伪指令展开表</h2><p class="muted small">伪指令在汇编时展开为一条或多条基础指令，展开结果与桌面版一致。</p>';

  const rows = Object.keys(PSEUDO_INSTRUCTIONS).map((name) => {
    const sample = PSEUDO_EXAMPLES[name] ?? '';
    let expandText = '';
    try {
      const ops = sample ? sample.split(',').map((s) => s.trim()) : [];
      expandText = expandPseudo(name, ops)
        .map(([m, o]) => (o.length ? `${m} ${o.join(', ')}` : m))
        .join(' ; ');
    } catch {
      expandText = '（需要操作数）';
    }
    return (
      `<tr><td class="mono">${name}${sample ? ` ${escapeHtml(sample)}` : ''}</td>` +
      `<td class="mono">${escapeHtml(expandText)}</td></tr>`
    );
  });

  const wrap = document.createElement('div');
  wrap.className = 'table-wrap';
  wrap.innerHTML =
    `<table class="matrix"><thead><tr><th>伪指令写法</th><th>展开结果</th></tr></thead>` +
    `<tbody>${rows.join('')}</tbody></table>`;
  sec.appendChild(wrap);
  return sec;
}

function buildSystemSection() {
  const sec = document.createElement('section');
  sec.id = 'system-table';
  sec.innerHTML = '<h2>CSR 与系统指令</h2><p class="muted small">6 条 Zicsr 特权指令、2 条系统指令与 1 条内存屏障。</p>';

  const rows = Object.entries(RV32I_INSTRUCTIONS)
    .filter(([, info]) => ['I_CSR', 'I_SYSTEM', 'I_FENCE'].includes(info.type))
    .map(([name, info]) => {
      const funct3 = info.funct3 === undefined ? '—' : info.funct3.toString(2).padStart(3, '0');
      const imm12 = info.imm12 === undefined ? '—' : `0x${info.imm12.toString(16).padStart(3, '0')}`;
      return (
        `<tr><td class="mono">${name}</td>` +
        `<td class="mono">${info.opcode.toString(2).padStart(7, '0')}</td>` +
        `<td class="mono">${funct3}</td><td class="mono">${imm12}</td></tr>`
      );
    });

  const wrap = document.createElement('div');
  wrap.className = 'table-wrap';
  wrap.innerHTML =
    `<table class="matrix"><thead><tr><th>指令</th><th>opcode</th><th>funct3</th><th>imm12</th></tr></thead>` +
    `<tbody>${rows.join('')}</tbody></table>`;
  sec.appendChild(wrap);
  return sec;
}

/**
 * 挂载学习页。
 * @param {HTMLElement} root
 * @returns {Promise<() => void>}
 */
export async function mountLearn(root) {
  root.innerHTML = `
    <div class="learn">
      <aside class="learn-nav">
        <div class="nav-search">
          <input id="learn-search" type="text" placeholder="搜索指令…" spellcheck="false">
        </div>
        <div class="nav-scroll" id="learn-nav"></div>
      </aside>
      <div class="learn-body" id="learn-body">
        <p class="muted">正在加载指令数据…</p>
      </div>
    </div>
  `;

  const nav = root.querySelector('#learn-nav');
  const body = root.querySelector('#learn-body');
  const search = root.querySelector('#learn-search');

  let instructions = [];
  let formatTables = {};
  try {
    const [a, b] = await Promise.all([
      fetch(new URL('../data/instructions.json', import.meta.url)).then((r) => r.json()),
      fetch(new URL('../data/format-tables.json', import.meta.url)).then((r) => r.json()),
    ]);
    instructions = a;
    formatTables = b;
  } catch (err) {
    body.innerHTML = `<p class="try-status err">指令数据加载失败：${escapeHtml(err.message)}</p>`;
    return () => {};
  }

  body.replaceChildren();

  // 概述
  const intro = document.createElement('section');
  intro.className = 'section-intro';
  intro.id = 'learn-intro';
  intro.innerHTML = `
    <h1>RV32I 指令速查</h1>
    <p class="lead">${Object.keys(RV32I_INSTRUCTIONS).length} 条基础指令与 ${Object.keys(PSEUDO_INSTRUCTIONS).length} 条伪指令。
    每张卡片下方的三个框可以即时互转，失败时给出具体原因。</p>
  `;
  body.appendChild(intro);

  // 格式表
  const fmtSec = document.createElement('section');
  fmtSec.id = 'format-tables';
  fmtSec.innerHTML = '<h2>六种指令格式</h2>';
  for (const [fmt, rows] of Object.entries(formatTables)) {
    const h = document.createElement('h3');
    h.textContent = FMT_TITLE[fmt] ?? fmt;
    fmtSec.appendChild(h);
    fmtSec.appendChild(buildFormatTable(fmt, rows));
  }
  body.appendChild(fmtSec);

  // 指令卡片
  const listSec = document.createElement('section');
  listSec.id = 'inst-list';
  listSec.innerHTML = '<h2>指令卡片</h2>';

  const grid = document.createElement('div');
  grid.className = 'inst-grid';
  instructions.forEach((inst, i) => grid.appendChild(buildCard(inst, i)));
  listSec.appendChild(grid);
  body.appendChild(listSec);

  body.appendChild(buildPseudoSection());
  body.appendChild(buildSystemSection());

  // 导航
  const groups = [
    { title: '目录', items: [
      { label: '概述', target: 'learn-intro' },
      { label: '六种格式', target: 'format-tables' },
      { label: '伪指令', target: 'pseudo-table' },
      { label: 'CSR 与系统', target: 'system-table' },
    ] },
    { title: '指令', items: instructions.map((inst) => ({
      label: inst.name,
      target: `inst-${inst.name.toLowerCase()}`,
      fmt: inst.fmt,
      name: inst.name.toLowerCase(),
      desc: inst.desc_short,
      inst: true,
    })) },
  ];

  nav.replaceChildren();
  for (const g of groups) {
    const box = document.createElement('div');
    box.className = 'nav-group';
    box.innerHTML = `<h4>${g.title}</h4>`;
    for (const item of g.items) {
      const a = document.createElement('a');
      a.href = '#';
      a.dataset.target = item.target;
      if (item.inst) {
        a.dataset.name = item.name;
        a.dataset.desc = item.desc;
      }
      a.innerHTML = `${escapeHtml(item.label)}${item.fmt ? `<span class="fmt">${escapeHtml(item.fmt)}</span>` : ''}`;
      box.appendChild(a);
    }
    nav.appendChild(box);
  }

  // 卡片按钮
  body.addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-act]');
    if (!btn) return;
    const card = btn.closest('.inst-card');
    if (card) runTry(card, btn.dataset.act);
  });

  // 输入即时互转
  let tryTimer = null;
  body.addEventListener('input', (e) => {
    const input = e.target;
    if (!input.matches('.try-asm, .try-hex, .try-bin')) return;
    const card = input.closest('.inst-card');
    if (!card) return;
    const act = input.classList.contains('try-asm')
      ? 'asm'
      : input.classList.contains('try-hex') ? 'hex' : 'bin';
    if (tryTimer) clearTimeout(tryTimer);
    tryTimer = setTimeout(() => runTry(card, act), 160);
  });

  // 首次跑一遍
  for (const card of grid.querySelectorAll('.inst-card')) runTry(card, 'asm');

  // 搜索过滤
  search.addEventListener('input', () => {
    const q = search.value.trim().toLowerCase();
    for (const card of grid.querySelectorAll('.inst-card')) {
      card.hidden = Boolean(q) && !card.dataset.name.includes(q) && !card.dataset.desc.includes(q);
    }
    for (const a of nav.querySelectorAll('a[data-name]')) {
      a.hidden = Boolean(q) && !a.dataset.name.includes(q) && !a.dataset.desc.includes(q);
    }
  });

  // 导航点击
  nav.addEventListener('click', (e) => {
    const a = e.target.closest('a[data-target]');
    if (!a) return;
    e.preventDefault();
    const target = document.getElementById(a.dataset.target);
    if (!target) return;
    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    target.classList.remove('flash');
    void target.offsetWidth;
    target.classList.add('flash');
    setTimeout(() => target.classList.remove('flash'), 1200);
  });

  // 滚动高亮
  const links = new Map(
    [...nav.querySelectorAll('a[data-name]')].map((a) => [a.dataset.target, a]),
  );
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const link = links.get(entry.target.id);
        if (!link) continue;
        for (const other of links.values()) other.classList.remove('cur');
        link.classList.add('cur');
      }
    },
    { root: body, rootMargin: '-8% 0px -75% 0px', threshold: 0 },
  );
  for (const card of grid.querySelectorAll('.inst-card')) observer.observe(card);

  return () => {
    observer.disconnect();
    if (tryTimer) clearTimeout(tryTimer);
  };
}
