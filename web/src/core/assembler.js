/**
 * 两遍汇编器 —— core/assembler.py 的 JavaScript 移植。
 *
 * 包含：行解析、标签符号表、地址锚点、PC 相对展开（la/call/tail）、
 * 行级错误模型、机器码格式化。行为与 Python 版逐位一致。
 */

import {
  RV32I_INSTRUCTIONS,
  encode,
  decode,
  isPseudo,
  expandPseudo,
  getFormat,
  parseIntLiteral,
} from './isa.js';

const LABEL_RE = /^\s*([A-Za-z_.$][A-Za-z0-9_.$]*)\s*:/;
const LABEL_TOKEN_RE = /^[A-Za-z_.$][A-Za-z0-9_.$]*$/;
const LABEL_PSEUDOS = new Set(['la', 'call', 'tail']);
const OFFSET_TAIL = new Set(['beq', 'bne', 'blt', 'bge', 'bltu', 'bgeu', 'jal']);

// ── 字节与格式化 ─────────────────────────────────────────────

/**
 * @param {number} machineCode
 * @returns {Uint8Array}
 */
export function machineCodeToBytes(machineCode) {
  const c = machineCode >>> 0;
  return new Uint8Array([c & 0xFF, (c >>> 8) & 0xFF, (c >>> 16) & 0xFF, (c >>> 24) & 0xFF]);
}

/**
 * @param {Uint8Array} data
 * @returns {string}
 */
export function bytesToHexStr(data) {
  return Array.from(data, (b) => b.toString(16).padStart(2, '0')).join('');
}

/**
 * @param {Uint8Array} data
 * @returns {string}
 */
export function bytesToBinStr(data) {
  return Array.from(data, (b) => b.toString(2).padStart(8, '0')).join(' ');
}

/**
 * @param {Uint8Array} data
 * @param {'hex'|'bin'} mode
 * @returns {string}
 */
export function formatMachineBytes(data, mode) {
  if (mode === 'bin') return bytesToBinStr(data);
  return bytesToHexStr(data);
}

/**
 * @param {Uint8Array} data
 * @param {'hex'|'bin'} mode
 * @param {'little'|'big'} endian
 * @returns {string}
 */
export function formatMachineBytesEndian(data, mode, endian = 'little') {
  if (endian === 'big') return formatMachineBytes(Uint8Array.from(data).reverse(), mode);
  return formatMachineBytes(data, mode);
}

/**
 * 解析地址字面量，失败返回 null。
 * @param {string} addrStr
 * @returns {number|null}
 */
export function parseAddress(addrStr) {
  const t = String(addrStr).trim().toLowerCase();
  if (t.startsWith('0x')) {
    const body = t.slice(2);
    return /^[0-9a-f]+$/.test(body) ? Number.parseInt(body, 16) : null;
  }
  if (t.startsWith('-0x')) {
    const body = t.slice(1);
    return /^-0x[0-9a-f]+$/.test(body) ? -Number.parseInt(body, 16) : null;
  }
  if (/^-?\d+$/.test(t)) return Number.parseInt(t, 10);
  return null;
}

// ── 行解析 ───────────────────────────────────────────────────

/**
 * 去掉注释（# 与 //）并去除首尾空白。
 * @param {string} line
 * @returns {string}
 */
export function stripComment(line) {
  let s = line;
  for (const marker of ['#', '//']) {
    const idx = s.indexOf(marker);
    if (idx !== -1) s = s.slice(0, idx);
  }
  return s.trim();
}

/**
 * 提取行首的所有标签定义。
 * @param {string} line
 * @returns {[string[], string]}
 */
export function splitLabels(line) {
  const labels = [];
  let rest = line;
  for (;;) {
    const m = LABEL_RE.exec(rest);
    if (!m) break;
    labels.push(m[1]);
    rest = rest.slice(m.index + m[0].length);
  }
  return [labels, rest.trim()];
}

function instructionText(mnem, ops) {
  return ops.length ? `${mnem} ${ops.join(', ')}` : mnem;
}

/**
 * 把末位操作数里的标签替换为相对 pc 的数值偏移。
 * @param {string} mnem
 * @param {string[]} ops
 * @param {number} pc
 * @param {Map<string, number>} symbols
 * @returns {string[]}
 */
function resolveTailLabel(mnem, ops, pc, symbols) {
  if (OFFSET_TAIL.has(mnem) && ops.length) {
    const tok = ops[ops.length - 1];
    try {
      parseIntLiteral(tok);
      return ops;
    } catch (err) {
      if (symbols.has(tok)) {
        return [...ops.slice(0, -1), String(symbols.get(tok) - pc)];
      }
      if (LABEL_TOKEN_RE.test(tok)) {
        throw new Error(`未知标签: ${tok}`);
      }
      throw err;
    }
  }
  return ops;
}

/**
 * PC 相对偏移拆成 auipc 的 20 位与 addi/jalr 的 12 位。
 * @param {number} off
 * @returns {[number, number]}
 */
export function pcrelParts(off) {
  const hi = ((off + 0x800) >> 12) & 0xFFFFF;
  const hiSigned = (hi & 0x80000) ? hi - 0x100000 : hi;
  const lo = off - (hiSigned * 0x1000);
  return [hi, lo];
}

function expandLabelPseudo(name, ops, off) {
  const [hi, lo] = pcrelParts(off);
  const hiStr = String((hi << 12) >>> 0);
  if (name === 'la') {
    const rd = ops[0];
    return [['auipc', [rd, hiStr]], ['addi', [rd, rd, String(lo)]]];
  }
  if (name === 'call') {
    return [['auipc', ['x1', hiStr]], ['jalr', ['x1', 'x1', String(lo)]]];
  }
  return [['auipc', ['x6', hiStr]], ['jalr', ['x0', 'x6', String(lo)]]];
}

function encodeChunk(mnem, ops, pc, symbols) {
  const text = instructionText(mnem, ops);
  try {
    const ops2 = resolveTailLabel(mnem, ops, pc, symbols);
    const code = encode(mnem, ops2);
    return { mnemonic: mnem, text: instructionText(mnem, ops2), data: machineCodeToBytes(code), error: null };
  } catch (err) {
    return { mnemonic: mnem, text, data: null, error: String(err.message ?? err) };
  }
}

// ── 两遍汇编 ─────────────────────────────────────────────────

function planLine(line) {
  const text = stripComment(line);
  const [labels, rest] = splitLabels(text);
  const plan = { labels, name: null, operands: [], count: 0, error: null };
  if (!rest) return plan;
  const parts = rest.replace(/,/g, ' ').split(/\s+/).filter(Boolean);
  if (!parts.length) return plan;
  const name = parts[0].toLowerCase();
  const operands = parts.slice(1);
  plan.name = name;
  plan.operands = operands;
  if (LABEL_PSEUDOS.has(name)) {
    plan.count = 2;
    return plan;
  }
  if (isPseudo(name)) {
    try {
      plan.count = expandPseudo(name, operands).length;
    } catch (err) {
      plan.count = 1;
      plan.error = String(err.message ?? err);
    }
    return plan;
  }
  if (Object.prototype.hasOwnProperty.call(RV32I_INSTRUCTIONS, name)) {
    plan.count = 1;
    return plan;
  }
  plan.count = 1;
  plan.error = `未知指令: ${name}`;
  return plan;
}

/**
 * 按每行占用字节数与手动地址锚点计算显示地址。
 * @param {string[]} addrLines
 * @param {number[]} sizes
 * @returns {string[]}
 */
export function computeAddresses(addrLines, sizes) {
  const anchors = new Map();
  (addrLines ?? []).forEach((line, i) => {
    const stripped = String(line).trim();
    if (!stripped) return;
    const v = parseAddressHex(stripped);
    if (v !== null) anchors.set(i, v);
  });
  const anchorKeys = [...anchors.keys()].sort((a, b) => a - b);

  const result = [];
  let currentAddr = 0;
  for (let i = 0; i < sizes.length; i += 1) {
    const size = sizes[i];
    if (anchors.has(i)) {
      result.push(fmtAddr(anchors.get(i)));
      currentAddr = anchors.get(i) + size;
      continue;
    }
    const nextAnchor = anchorKeys.find((k) => k > i);
    if (size === 0) {
      result.push(fmtAddr(currentAddr));
    } else if (nextAnchor !== undefined && currentAddr >= anchors.get(nextAnchor)) {
      result.push('');
    } else {
      result.push(fmtAddr(currentAddr));
      currentAddr += size;
    }
  }
  return result;
}

function parseAddressHex(s) {
  // 对应 Python 的 int(s, 16)：只接受十六进制数字
  if (!/^[0-9a-fA-F]+$/.test(s)) return null;
  return Number.parseInt(s, 16);
}

function fmtAddr(n) {
  return (n >>> 0).toString(16).padStart(8, '0');
}

/**
 * 两遍汇编。
 * @param {string[]} lines
 * @param {string[]|null} addrLines
 * @param {number} baseAddr
 * @returns {Array<{labels: string[], address: number, size: number,
 *   chunks: Array<{mnemonic: string, text: string, data: Uint8Array|null, error: string|null}>,
 *   error: string|null}>}
 */
export function assembleProgram(lines, addrLines = null, baseAddr = 0) {
  const plans = lines.map(planLine);
  const sizes = plans.map((p) => 4 * p.count);

  let addrs;
  if (addrLines === null) {
    addrs = [];
    let cur = baseAddr;
    for (const s of sizes) {
      addrs.push(fmtAddr(cur));
      cur += s;
    }
  } else {
    addrs = computeAddresses(addrLines, sizes);
  }

  // 第一遍：符号表
  const symbols = new Map();
  const dupErrors = new Map();
  let lastAddr = 0;
  plans.forEach((plan, i) => {
    const rowAddr = addrs[i] ? Number.parseInt(addrs[i], 16) : lastAddr;
    lastAddr = rowAddr;
    for (const lab of plan.labels) {
      if (symbols.has(lab)) {
        if (!dupErrors.has(i)) dupErrors.set(i, `重复定义标签: ${lab}`);
      } else {
        symbols.set(lab, rowAddr);
      }
    }
  });

  // 第二遍：逐块编码
  const results = [];
  plans.forEach((plan, i) => {
    const pc = addrs[i] ? Number.parseInt(addrs[i], 16) : 0;
    const chunks = [];
    let lineErr = dupErrors.get(i) ?? plan.error ?? null;
    const name = plan.name;
    const operands = plan.operands;

    if (name === null) {
      // 空行或纯标签行
    } else if (LABEL_PSEUDOS.has(name) && operands.length && symbols.has(operands[operands.length - 1])) {
      const target = symbols.get(operands[operands.length - 1]);
      const off = target - pc;
      const seq = expandLabelPseudo(name, operands, off);
      seq.forEach(([mnem, ops2], j) => {
        chunks.push(encodeChunk(mnem, ops2, pc + 4 * j, symbols));
      });
    } else if (isPseudo(name)) {
      let seq = [];
      try {
        seq = expandPseudo(name, operands);
      } catch (err) {
        lineErr = lineErr ?? String(err.message ?? err);
        seq = [];
      }
      seq.forEach(([mnem, ops2], j) => {
        chunks.push(encodeChunk(mnem, ops2, pc + 4 * j, symbols));
      });
    } else {
      chunks.push(encodeChunk(name, operands, pc, symbols));
    }

    const chunkErr = chunks.find((c) => c.error)?.error ?? null;
    results.push({
      labels: plan.labels,
      address: pc,
      size: chunks.reduce((s, c) => s + (c.data ? c.data.length : 0), 0),
      chunks,
      error: lineErr ?? chunkErr,
    });
  });

  return results;
}

/**
 * 单行汇编（无标签上下文）。
 * @param {string} line
 * @param {number} currentAddress
 * @returns {Uint8Array}
 */
export function assembleLine(line, currentAddress = 0) {
  const results = assembleProgram([line], null, currentAddress);
  const parts = results[0].chunks.filter((c) => c.data).map((c) => c.data);
  const total = parts.reduce((s, d) => s + d.length, 0);
  const out = new Uint8Array(total);
  let off = 0;
  for (const d of parts) {
    out.set(d, off);
    off += d.length;
  }
  return out;
}

/**
 * @param {string} line
 * @param {number} currentAddress
 * @returns {string}
 */
export function assembleLineHex(line, currentAddress = 0) {
  const data = assembleLine(line, currentAddress);
  return data.length ? bytesToHexStr(data) : '';
}

/**
 * @param {Uint8Array} data
 * @returns {string|null}
 */
export function disassembleBytes(data) {
  if (data.length !== 4) return null;
  try {
    const word = (data[0] | (data[1] << 8) | (data[2] << 16) | (data[3] << 24)) >>> 0;
    const [name, operands] = decode(word);
    if (name === null) return null;
    return operands.length ? `${name} ${operands.join(', ')}` : name;
  } catch {
    return null;
  }
}

/**
 * @param {string} hexStr
 * @returns {string|null}
 */
export function disassembleHex(hexStr) {
  const t = String(hexStr).trim().toLowerCase();
  if (t.length !== 8) return null;
  if (!/^[0-9a-f]{8}$/.test(t)) return null;
  const data = new Uint8Array(4);
  for (let i = 0; i < 4; i += 1) data[i] = Number.parseInt(t.slice(i * 2, i * 2 + 2), 16);
  return disassembleBytes(data);
}

/**
 * 单行浅析：不生成机器码，只判断合法性并给出提示。
 * @param {string} line
 * @param {Set<string>|Map<string, number>|null} symbols
 * @param {Map<string, number>|null} symbolAddrs
 * @returns {{valid: boolean, format: string, name: string, operands: string[],
 *   labels: string[], detail: string, error: string, expandedCount: number}}
 */
export function analyzeAssemblyLine(line, symbols = null, symbolAddrs = null) {
  const result = {
    valid: false,
    format: '',
    name: '',
    operands: [],
    labels: [],
    detail: '',
    error: '',
    expandedCount: 1,
  };
  const text = stripComment(line);
  const [labels, rest] = splitLabels(text);
  result.labels = labels;

  if (!rest) {
    if (labels.length) {
      result.valid = true;
      result.format = 'Label';
      result.name = labels[0];
      if (symbolAddrs && symbolAddrs.has(labels[0])) {
        result.detail = `标签 ${labels[0]} → 地址 0x${fmtAddr(symbolAddrs.get(labels[0]))}`;
      }
    }
    return result;
  }

  const parts = rest.replace(/,/g, ' ').split(/\s+/).filter(Boolean);
  if (!parts.length) return result;
  const name = parts[0].toLowerCase();
  const operands = parts.slice(1);
  result.name = name;
  result.operands = operands;

  let sym;
  if (symbolAddrs && symbolAddrs.size) {
    sym = symbolAddrs;
  } else if (symbols instanceof Map) {
    sym = symbols;
  } else if (symbols) {
    sym = new Map([...symbols].map((s) => [s, 0]));
  } else {
    sym = new Map();
  }

  try {
    if (LABEL_PSEUDOS.has(name) && symbols && operands.length &&
        hasSym(symbols, operands[operands.length - 1])) {
      result.format = 'Pseudo';
      result.valid = true;
      result.expandedCount = 2;
      const last = operands[operands.length - 1];
      if (symbolAddrs && symbolAddrs.has(last)) {
        result.detail =
          `${name} ${last} → 目标地址 0x${fmtAddr(symbolAddrs.get(last))} ` +
          `(展开为 auipc + ${name !== 'la' ? 'jalr' : 'addi'})`;
      }
      return result;
    }

    if (isPseudo(name)) {
      result.format = 'Pseudo';
      const expanded = expandPseudo(name, operands);
      result.expandedCount = expanded.length;
      let ok = 0;
      let firstErr = '';
      for (const [mn, mo] of expanded) {
        try {
          const mo2 = resolveTailLabel(mn, mo, 0, sym);
          encode(mn, mo2);
          ok += 1;
        } catch (err) {
          if (!firstErr) firstErr = String(err.message ?? err);
        }
      }
      if (expanded.length && ok === expanded.length) {
        result.valid = true;
        const inner = expanded.length === 1 ? getFormat(expanded[0][0]) : 'Pseudo';
        result.format = expanded.length === 1 ? inner : `Pseudo (展开 ${expanded.length} 条)`;
      } else {
        result.error = firstErr || '操作数无效';
      }
      return result;
    }

    if (Object.prototype.hasOwnProperty.call(RV32I_INSTRUCTIONS, name)) {
      const ops2 = resolveTailLabel(name, operands, 0, sym);
      encode(name, ops2);
      result.valid = true;
      result.format = getFormat(name);
    } else {
      result.error = `未知指令: ${name}`;
    }
  } catch (err) {
    result.error = String(err.message ?? err);
  }
  return result;
}

function hasSym(symbols, key) {
  if (symbols instanceof Map) return symbols.has(key);
  if (symbols instanceof Set) return symbols.has(key);
  return false;
}

/**
 * 从汇编结果中收集标签地址。
 * @param {Array<{labels: string[], address: number}>} results
 * @returns {Map<string, number>}
 */
export function collectSymbols(results) {
  const map = new Map();
  for (const r of results) {
    for (const lab of r.labels) map.set(lab, r.address);
  }
  return map;
}

/**
 * 全局统计：总行数、总字节数、错误行数。
 * @param {string[]} lines
 * @param {Array} results
 * @returns {{lines: number, bytes: number, errors: number}}
 */
export function summarize(lines, results) {
  return {
    lines: lines.length,
    bytes: results.reduce((s, r) => s + r.size, 0),
    errors: results.filter((r) => r.error).length,
  };
}
