/**
 * 32 位位段可视化 —— 桌面版没有的组件。
 *
 * 把一条指令的 32 个比特按字段拆成格子，从高位到低位排列，
 * 每格显示字段名与字段值，颜色区分 opcode / rd / rs1 / rs2 / funct3 / funct7 / imm。
 */

import { RV32I_INSTRUCTIONS, decode } from '../core/isa.js';

/** 字段布局：从左（bit31）到右（bit0）。 */
const LAYOUTS = {
  R: [
    ['funct7', 31, 25], ['rs2', 24, 20], ['rs1', 19, 15],
    ['funct3', 14, 12], ['rd', 11, 7], ['opcode', 6, 0],
  ],
  I: [
    ['imm[31:20]', 31, 20], ['rs1', 19, 15],
    ['funct3', 14, 12], ['rd', 11, 7], ['opcode', 6, 0],
  ],
  S: [
    ['imm[11:5]', 31, 25], ['rs2', 24, 20], ['rs1', 19, 15],
    ['funct3', 14, 12], ['imm[4:0]', 11, 7], ['opcode', 6, 0],
  ],
  B: [
    ['imm[12|10:5]', 31, 25], ['rs2', 24, 20], ['rs1', 19, 15],
    ['funct3', 14, 12], ['imm[4:1|11]', 11, 7], ['opcode', 6, 0],
  ],
  U: [
    ['imm[31:12]', 31, 12], ['rd', 11, 7], ['opcode', 6, 0],
  ],
  J: [
    ['imm[20|10:1]', 31, 21], ['imm[19:12]', 19, 12],
    ['rd', 11, 7], ['opcode', 6, 0],
  ],
  I_SYSTEM: [
    ['imm12', 31, 20], ['rs1', 19, 15],
    ['funct3', 14, 12], ['rd', 11, 7], ['opcode', 6, 0],
  ],
  I_CSR: [
    ['csr', 31, 20], ['rs1/zimm', 19, 15],
    ['funct3', 14, 12], ['rd', 11, 7], ['opcode', 6, 0],
  ],
  I_FENCE: [
    ['pred/succ', 31, 20], ['rs1', 19, 15],
    ['funct3', 14, 12], ['rd', 11, 7], ['opcode', 6, 0],
  ],
};

LAYOUTS.I_LOAD = LAYOUTS.I;
LAYOUTS.I_JALR = LAYOUTS.I;

function fieldValue(word, from, to) {
  const width = from - to + 1;
  const mask = width >= 32 ? 0xFFFFFFFF : (1 << width) - 1;
  return (word >>> to) & mask;
}

function fieldText(value, width) {
  if (width > 7) return `0x${value.toString(16).toUpperCase()}`;
  return value.toString(2).padStart(width, '0');
}

function colorKey(name) {
  if (name.startsWith('imm')) return 'imm';
  if (name.startsWith('rs1')) return 'rs1';
  if (name === 'csr' || name === 'pred/succ') return 'imm';
  return name;
}

/**
 * 渲染一条指令的位段。
 * @param {HTMLElement} container
 * @param {number} word 32 位无符号机器码
 * @param {{ asm?: string, note?: string }} [opts]
 */
export function renderBits(container, word, opts = {}) {
  const [name, operands] = decode(word);
  const type = name && RV32I_INSTRUCTIONS[name] ? RV32I_INSTRUCTIONS[name].type : 'R';
  const layout = LAYOUTS[type] ?? LAYOUTS.R;
  const asmText = opts.asm ?? (name ? (operands.length ? `${name} ${operands.join(', ')}` : name) : '无法解码');

  const head = document.createElement('div');
  head.className = 'bits-head';
  head.innerHTML =
    `<span class="asm">${escapeHtml(asmText)}</span>` +
    `<span class="hex">0x${word.toString(16).padStart(8, '0').toUpperCase()}</span>` +
    `<span class="faint small">${escapeHtml(type)} 型 · ${escapeHtml(name ?? '未知')}</span>` +
    (opts.note ? `<span class="faint small">${escapeHtml(opts.note)}</span>` : '');

  const row = document.createElement('div');
  row.className = 'bit-row';

  for (const [label, from, to] of layout) {
    const width = from - to + 1;
    const value = fieldValue(word, from, to);
    const cell = document.createElement('div');
    cell.className = 'bit-field';
    cell.dataset.w = String(width);
    cell.dataset.name = colorKey(label);
    cell.title = `bit ${from}..${to}（${width} 位）= ${fieldText(value, width)}`;
    cell.innerHTML =
      `<span class="name">${escapeHtml(label)}</span>` +
      `<span class="val">${fieldText(value, width)}</span>`;
    row.appendChild(cell);
  }

  container.replaceChildren(head, row);
}

/**
 * 清空位段区。
 * @param {HTMLElement} container
 * @param {string} message
 */
export function renderBitsEmpty(container, message) {
  if (!message) {
    container.replaceChildren();
    return;
  }
  const div = document.createElement('div');
  div.className = 'bit-empty';
  div.textContent = message;
  container.replaceChildren(div);
}

export function escapeHtml(text) {
  return String(text)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}
