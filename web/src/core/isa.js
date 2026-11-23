/**
 * RV32I 指令编码/译码 —— core/isa_rv32i.py 的 JavaScript 移植。
 *
 * 行为必须与 Python 版逐位一致，包括错误文案。一致性由
 * web/tests/parity.test.js 读取 tools/export_golden.py 生成的
 * golden.json 逐条比对来保证。
 */

/** 46 条基础指令（含 6 条 Zicsr、2 条系统、1 条 fence）。顺序与 Python 版一致。 */
export const RV32I_INSTRUCTIONS = {
  add: { type: 'R', opcode: 0b0110011, funct3: 0b000, funct7: 0b0000000 },
  sub: { type: 'R', opcode: 0b0110011, funct3: 0b000, funct7: 0b0100000 },
  and: { type: 'R', opcode: 0b0110011, funct3: 0b111, funct7: 0b0000000 },
  or: { type: 'R', opcode: 0b0110011, funct3: 0b110, funct7: 0b0000000 },
  xor: { type: 'R', opcode: 0b0110011, funct3: 0b100, funct7: 0b0000000 },
  sll: { type: 'R', opcode: 0b0110011, funct3: 0b001, funct7: 0b0000000 },
  slt: { type: 'R', opcode: 0b0110011, funct3: 0b010, funct7: 0b0000000 },
  sltu: { type: 'R', opcode: 0b0110011, funct3: 0b011, funct7: 0b0000000 },
  srl: { type: 'R', opcode: 0b0110011, funct3: 0b101, funct7: 0b0000000 },
  sra: { type: 'R', opcode: 0b0110011, funct3: 0b101, funct7: 0b0100000 },
  addi: { type: 'I', opcode: 0b0010011, funct3: 0b000 },
  andi: { type: 'I', opcode: 0b0010011, funct3: 0b111 },
  ori: { type: 'I', opcode: 0b0010011, funct3: 0b110 },
  xori: { type: 'I', opcode: 0b0010011, funct3: 0b100 },
  slti: { type: 'I', opcode: 0b0010011, funct3: 0b010 },
  sltiu: { type: 'I', opcode: 0b0010011, funct3: 0b011 },
  slli: { type: 'I', opcode: 0b0010011, funct3: 0b001, funct7: 0b0000000 },
  srli: { type: 'I', opcode: 0b0010011, funct3: 0b101, funct7: 0b0000000 },
  srai: { type: 'I', opcode: 0b0010011, funct3: 0b101, funct7: 0b0100000 },
  lb: { type: 'I_LOAD', opcode: 0b0000011, funct3: 0b000 },
  lh: { type: 'I_LOAD', opcode: 0b0000011, funct3: 0b001 },
  lw: { type: 'I_LOAD', opcode: 0b0000011, funct3: 0b010 },
  lbu: { type: 'I_LOAD', opcode: 0b0000011, funct3: 0b100 },
  lhu: { type: 'I_LOAD', opcode: 0b0000011, funct3: 0b101 },
  sb: { type: 'S', opcode: 0b0100011, funct3: 0b000 },
  sh: { type: 'S', opcode: 0b0100011, funct3: 0b001 },
  sw: { type: 'S', opcode: 0b0100011, funct3: 0b010 },
  beq: { type: 'B', opcode: 0b1100011, funct3: 0b000 },
  bne: { type: 'B', opcode: 0b1100011, funct3: 0b001 },
  blt: { type: 'B', opcode: 0b1100011, funct3: 0b100 },
  bge: { type: 'B', opcode: 0b1100011, funct3: 0b101 },
  bltu: { type: 'B', opcode: 0b1100011, funct3: 0b110 },
  bgeu: { type: 'B', opcode: 0b1100011, funct3: 0b111 },
  jal: { type: 'J', opcode: 0b1101111 },
  jalr: { type: 'I_JALR', opcode: 0b1100111, funct3: 0b000 },
  lui: { type: 'U', opcode: 0b0110111 },
  auipc: { type: 'U', opcode: 0b0010111 },
  ecall: { type: 'I_SYSTEM', opcode: 0b1110011, funct3: 0b000, imm12: 0x000 },
  ebreak: { type: 'I_SYSTEM', opcode: 0b1110011, funct3: 0b000, imm12: 0x001 },
  fence: { type: 'I_FENCE', opcode: 0b0001111, funct3: 0b000 },
  csrrw: { type: 'I_CSR', opcode: 0b1110011, funct3: 0b001 },
  csrrs: { type: 'I_CSR', opcode: 0b1110011, funct3: 0b010 },
  csrrc: { type: 'I_CSR', opcode: 0b1110011, funct3: 0b011 },
  csrrwi: { type: 'I_CSR', opcode: 0b1110011, funct3: 0b101 },
  csrrsi: { type: 'I_CSR', opcode: 0b1110011, funct3: 0b110 },
  csrrci: { type: 'I_CSR', opcode: 0b1110011, funct3: 0b111 },
};

/** 27 条伪指令。值仅用于集合判断。 */
export const PSEUDO_INSTRUCTIONS = {
  li: 'li',
  mv: 'mv',
  not: 'not',
  neg: 'neg',
  la: 'la',
  nop: 'nop',
  unimp: 'unimp',
  ret: 'ret',
  call: 'call',
  tail: 'tail',
  j: 'j',
  jr: 'jr',
  jalr: 'jalr_pseudo',
  beqz: 'beqz',
  bnez: 'bnez',
  blez: 'blez',
  bgez: 'bgez',
  bltz: 'bltz',
  bgtz: 'bgtz',
  seqz: 'seqz',
  snez: 'snez',
  sltz: 'sltz',
  sgtz: 'sgtz',
  bgt: 'bgt',
  ble: 'ble',
  bgtu: 'bgtu',
  bleu: 'bleu',
};

/** ABI 别名 → 寄存器编号。 */
export const REG_ALIASES = {
  zero: 0, ra: 1, sp: 2, gp: 3, tp: 4,
  t0: 5, t1: 6, t2: 7,
  s0: 8, fp: 8, s1: 9,
  a0: 10, a1: 11, a2: 12, a3: 13,
  a4: 14, a5: 15, a6: 16, a7: 17,
  s2: 18, s3: 19, s4: 20, s5: 21,
  s6: 22, s7: 23, s8: 24, s9: 25,
  s10: 26, s11: 27,
  t3: 28, t4: 29, t5: 30, t6: 31,
};

export const TYPE_FRIENDLY = {
  R: 'R-type',
  I: 'I-type',
  I_LOAD: 'I-type (Load)',
  I_JALR: 'I-type (JALR)',
  S: 'S-type',
  B: 'B-type',
  U: 'U-type',
  J: 'J-type',
  I_SYSTEM: 'System',
  I_CSR: 'CSR',
  I_FENCE: 'Fence',
};

const MEM_RE = /^(.+?)\s*\(\s*([A-Za-z][A-Za-z0-9_]*)\s*\)$/;
// fence 的 pred/succ 是 4 位掩码，按 RISC-V 规范 I=8、O=4、R=2、W=1
const FENCE_BITS = { i: 8, o: 4, r: 2, w: 1 };
const FENCE_ORDER = [['i', 8], ['o', 4], ['r', 2], ['w', 1]];

/**
 * 解析寄存器名，返回 0–31。
 * @param {string} regStr
 * @returns {number}
 */
export function parseRegister(regStr) {
  const t = String(regStr).trim().toLowerCase();
  if (/^x\d+$/.test(t)) {
    const n = Number.parseInt(t.slice(1), 10);
    if (n >= 0 && n <= 31) return n;
    throw new Error(`无效寄存器: ${regStr} (范围 x0-x31)`);
  }
  if (Object.prototype.hasOwnProperty.call(REG_ALIASES, t)) {
    return REG_ALIASES[t];
  }
  throw new Error(`无效寄存器: ${regStr}`);
}

/**
 * 解析整数字面量：十进制 / 0x 十六进制 / 0b 二进制，可带正负号与下划线。
 * @param {string} immStr
 * @returns {number}
 */
export function parseIntLiteral(immStr) {
  let t = String(immStr).trim().toLowerCase().replace(/_/g, '');
  let neg = false;
  if (t.startsWith('+')) {
    t = t.slice(1);
  } else if (t.startsWith('-')) {
    neg = true;
    t = t.slice(1);
  }
  let v;
  if (t.startsWith('0x')) {
    const body = t.slice(2);
    if (!/^[0-9a-f]+$/.test(body)) throw new Error(`无效立即数: ${immStr}`);
    v = Number.parseInt(body, 16);
  } else if (t.startsWith('0b')) {
    const body = t.slice(2);
    if (!/^[01]+$/.test(body)) throw new Error(`无效立即数: ${immStr}`);
    v = Number.parseInt(body, 2);
  } else {
    if (!/^\d+$/.test(t)) throw new Error(`无效立即数: ${immStr}`);
    v = Number.parseInt(t, 10);
  }
  return neg ? -v : v;
}

function immChecked(immStr, lo, hi, what) {
  const v = parseIntLiteral(immStr);
  if (!(v >= lo && v <= hi)) {
    throw new Error(`立即数 ${immStr} 超出${what}范围 [${lo}, ${hi}]`);
  }
  return v;
}

function parseMem(operand) {
  const m = MEM_RE.exec(String(operand).trim());
  if (!m) {
    throw new Error(`无效的内存操作数: ${operand} (应为 imm(rs) 格式)`);
  }
  return [m[1], m[2]];
}

function parseFenceBits(tok) {
  const t = String(tok).trim().toLowerCase();
  if (t && /^[iorw]+$/.test(t)) {
    let sum = 0;
    for (const c of t) sum += FENCE_BITS[c];
    return sum;
  }
  const v = parseIntLiteral(tok);
  if (!(v >= 0 && v <= 15)) {
    throw new Error(`fence 掩码 ${tok} 超出范围 [0, 15]`);
  }
  return v;
}

function fenceBitsToStr(bits) {
  if (bits === 0) return '0';
  return FENCE_ORDER.filter(([, b]) => bits & b).map(([c]) => c).join('');
}

function need(operands, n, usage) {
  if (operands.length < n) {
    throw new Error(`操作数不足，用法: ${usage}`);
  }
}

/**
 * 编码一条指令，返回 32 位无符号整数。
 * @param {string} name
 * @param {string[]} operands
 * @returns {number}
 */
export function encode(name, operands) {
  const lname = name.toLowerCase();

  if (!Object.prototype.hasOwnProperty.call(RV32I_INSTRUCTIONS, lname)) {
    throw new Error(`未知指令: ${lname}`);
  }

  const info = RV32I_INSTRUCTIONS[lname];
  const type = info.type;
  const opcode = info.opcode;

  if (type === 'R') {
    need(operands, 3, 'add rd, rs1, rs2');
    const rd = parseRegister(operands[0]);
    const rs1 = parseRegister(operands[1]);
    const rs2 = parseRegister(operands[2]);
    const funct3 = info.funct3;
    const funct7 = info.funct7;
    return ((funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode) >>> 0;
  }

  if (type === 'I') {
    need(operands, 3, 'addi rd, rs1, imm');
    const rd = parseRegister(operands[0]);
    const rs1 = parseRegister(operands[1]);
    const funct3 = info.funct3;
    if (lname === 'slli' || lname === 'srli' || lname === 'srai') {
      const shamt = immChecked(operands[2], 0, 31, '移位量');
      const funct7 = info.funct7;
      return ((funct7 << 25) | (shamt << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode) >>> 0;
    }
    const imm = immChecked(operands[2], -2048, 2047, 'I型立即数');
    return (((imm & 0xFFF) << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode) >>> 0;
  }

  if (type === 'I_LOAD') {
    need(operands, 2, 'lw rd, imm(rs1)');
    const rd = parseRegister(operands[0]);
    const [immStr, rs1Str] = parseMem(operands[1]);
    const rs1 = parseRegister(rs1Str);
    const imm = immChecked(immStr, -2048, 2047, '访存偏移');
    const funct3 = info.funct3;
    return (((imm & 0xFFF) << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode) >>> 0;
  }

  if (type === 'I_JALR') {
    need(operands, 2, 'jalr rd, imm(rs1)');
    const rd = parseRegister(operands[0]);
    let rs1;
    let imm;
    if (operands.length >= 3) {
      rs1 = parseRegister(operands[1]);
      imm = immChecked(operands[2], -2048, 2047, 'jalr偏移');
    } else {
      const [immStr, rs1Str] = parseMem(operands[1]);
      rs1 = parseRegister(rs1Str);
      imm = immChecked(immStr, -2048, 2047, 'jalr偏移');
    }
    const funct3 = info.funct3;
    return (((imm & 0xFFF) << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode) >>> 0;
  }

  if (type === 'S') {
    need(operands, 2, 'sw rs2, imm(rs1)');
    const rs2 = parseRegister(operands[0]);
    const [immStr, rs1Str] = parseMem(operands[1]);
    const rs1 = parseRegister(rs1Str);
    let imm = immChecked(immStr, -2048, 2047, '访存偏移');
    const funct3 = info.funct3;
    imm &= 0xFFF;
    const imm115 = (imm >>> 5) & 0x7F;
    const imm40 = imm & 0x1F;
    return ((imm115 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (imm40 << 7) | opcode) >>> 0;
  }

  if (type === 'B') {
    need(operands, 3, 'beq rs1, rs2, offset');
    const rs1 = parseRegister(operands[0]);
    const rs2 = parseRegister(operands[1]);
    const off = immChecked(operands[2], -4096, 4094, '分支偏移');
    if (off & 1) {
      throw new Error(`分支偏移 ${operands[2]} 必须是 2 的倍数`);
    }
    const funct3 = info.funct3;
    const imm = off & 0x1FFF;
    const imm12 = (imm >>> 12) & 0x1;
    const imm105 = (imm >>> 5) & 0x3F;
    const imm41 = (imm >>> 1) & 0xF;
    const imm11 = (imm >>> 11) & 0x1;
    return (
      (imm12 << 31) | (imm105 << 25) | (rs2 << 20) | (rs1 << 15) |
      (funct3 << 12) | (imm41 << 8) | (imm11 << 7) | opcode
    ) >>> 0;
  }

  if (type === 'U') {
    need(operands, 2, 'lui rd, imm20');
    const rd = parseRegister(operands[0]);
    const v = immChecked(operands[1], -524288, 1048575, 'U型立即数(20位)');
    const imm3112 = v & 0xFFFFF;
    return ((imm3112 << 12) | (rd << 7) | opcode) >>> 0;
  }

  if (type === 'J') {
    need(operands, 2, 'jal rd, offset');
    const rd = parseRegister(operands[0]);
    const off = immChecked(operands[1], -1048576, 1048574, '跳转偏移');
    if (off & 1) {
      throw new Error(`跳转偏移 ${operands[1]} 必须是 2 的倍数`);
    }
    const imm = off & 0x1FFFFF;
    const imm20 = (imm >>> 20) & 0x1;
    const imm101 = (imm >>> 1) & 0x3FF;
    const imm11 = (imm >>> 11) & 0x1;
    const imm1912 = (imm >>> 12) & 0xFF;
    return (
      (imm20 << 31) | (imm101 << 21) | (imm11 << 20) | (imm1912 << 12) |
      (rd << 7) | opcode
    ) >>> 0;
  }

  if (type === 'I_SYSTEM') {
    const imm12 = info.imm12 ?? 0;
    return ((imm12 << 20) | opcode) >>> 0;
  }

  if (type === 'I_CSR') {
    need(operands, 3, 'csrrw rd, csr, rs1');
    const rd = parseRegister(operands[0]);
    const csr = immChecked(operands[1], 0, 4095, 'CSR地址');
    const csrFunct3 = info.funct3;
    let rs1OrZimm;
    if (csrFunct3 === 0b101 || csrFunct3 === 0b110 || csrFunct3 === 0b111) {
      const zimm = immChecked(operands[2], 0, 31, 'zimm');
      rs1OrZimm = zimm & 0x1F;
    } else {
      rs1OrZimm = parseRegister(operands[2]);
    }
    return ((csr << 20) | (rs1OrZimm << 15) | (csrFunct3 << 12) | (rd << 7) | opcode) >>> 0;
  }

  if (type === 'I_FENCE') {
    let pred;
    let succ;
    if (operands.length === 0 || operands.every((o) => !String(o).trim())) {
      pred = 0xF;
      succ = 0xF;
    } else {
      need(operands, 2, 'fence pred, succ');
      pred = parseFenceBits(operands[0]);
      succ = parseFenceBits(operands[1]);
    }
    const fenceImm = ((pred & 0xF) << 4) | (succ & 0xF);
    return ((fenceImm << 20) | (info.funct3 << 12) | opcode) >>> 0;
  }

  throw new Error(`未知指令类型: ${type}`);
}

/**
 * 译码 32 位机器码。
 * @param {number} word
 * @returns {[string|null, string[]]}
 */
export function decode(word) {
  const code = word >>> 0;
  const opcode = code & 0x7F;
  const funct3 = (code >>> 12) & 0x7;
  const funct7 = (code >>> 25) & 0x7F;
  const rd = (code >>> 7) & 0x1F;
  const rs1 = (code >>> 15) & 0x1F;
  const rs2 = (code >>> 20) & 0x1F;

  let matchedName = null;
  let matchedInfo = null;
  for (const instName of Object.keys(RV32I_INSTRUCTIONS)) {
    const info = RV32I_INSTRUCTIONS[instName];
    if (info.opcode !== opcode) continue;
    if ('funct3' in info && info.funct3 !== funct3) continue;
    const type = info.type;
    if (type === 'I_SYSTEM') {
      if ((info.imm12 ?? 0) !== ((code >>> 20) & 0xFFF)) continue;
    }
    if (type === 'R' || (type === 'I' && 'funct7' in info)) {
      if ((info.funct7 ?? -1) !== funct7) continue;
    }
    matchedName = instName;
    matchedInfo = info;
    break;
  }

  if (matchedName === null) return [null, []];

  const type = matchedInfo.type;
  let operands = [];

  if (type === 'R') {
    operands = [`x${rd}`, `x${rs1}`, `x${rs2}`];
  } else if (type === 'I' || type === 'I_JALR') {
    let imm = (code >>> 20) & 0xFFF;
    if ('funct7' in matchedInfo) {
      imm &= 0x1F;
    } else if (imm & 0x800) {
      imm -= 0x1000;
    }
    operands = [`x${rd}`, `x${rs1}`, String(imm)];
  } else if (type === 'I_LOAD') {
    let imm = (code >>> 20) & 0xFFF;
    if (imm & 0x800) imm -= 0x1000;
    operands = [`x${rd}`, `${imm}(x${rs1})`];
  } else if (type === 'S') {
    const imm40 = (code >>> 7) & 0x1F;
    const imm115 = (code >>> 25) & 0x7F;
    let imm = (imm115 << 5) | imm40;
    if (imm & 0x800) imm -= 0x1000;
    operands = [`x${rs2}`, `${imm}(x${rs1})`];
  } else if (type === 'B') {
    const imm12 = (code >>> 31) & 0x1;
    const imm105 = (code >>> 25) & 0x3F;
    const imm41 = (code >>> 8) & 0xF;
    const imm11 = (code >>> 7) & 0x1;
    let imm = (imm12 << 12) | (imm11 << 11) | (imm105 << 5) | (imm41 << 1);
    if (imm & 0x1000) imm -= 0x2000;
    operands = [`x${rs1}`, `x${rs2}`, String(imm)];
  } else if (type === 'U') {
    const imm3112 = (code >>> 12) & 0xFFFFF;
    operands = [`x${rd}`, `0x${imm3112.toString(16)}`];
  } else if (type === 'J') {
    const imm20 = (code >>> 31) & 0x1;
    const imm101 = (code >>> 21) & 0x3FF;
    const imm11 = (code >>> 20) & 0x1;
    const imm1912 = (code >>> 12) & 0xFF;
    let imm = (imm20 << 20) | (imm1912 << 12) | (imm11 << 11) | (imm101 << 1);
    if (imm & 0x100000) imm -= 0x200000;
    operands = [`x${rd}`, String(imm)];
  } else if (type === 'I_SYSTEM') {
    operands = [];
  } else if (type === 'I_CSR') {
    const csr = (code >>> 20) & 0xFFF;
    const csrFunct3 = matchedInfo.funct3;
    if (csrFunct3 === 0b101 || csrFunct3 === 0b110 || csrFunct3 === 0b111) {
      const zimm = rs1 & 0x1F;
      operands = [`x${rd}`, String(csr), String(zimm)];
    } else {
      operands = [`x${rd}`, String(csr), `x${rs1}`];
    }
  } else if (type === 'I_FENCE') {
    const immVal = (code >>> 20) & 0xFFF;
    const pred = (immVal >>> 4) & 0xF;
    const succ = immVal & 0xF;
    operands = [fenceBitsToStr(pred), fenceBitsToStr(succ)];
  }

  return [matchedName, operands];
}

/**
 * @param {string} name
 * @returns {boolean}
 */
export function isPseudo(name) {
  return Object.prototype.hasOwnProperty.call(PSEUDO_INSTRUCTIONS, name.toLowerCase());
}

/**
 * 展开伪指令为「助记符 + 操作数」序列。
 * @param {string} name
 * @param {string[]} operands
 * @returns {Array<[string, string[]]>}
 */
export function expandPseudo(name, operands) {
  const lname = name.toLowerCase();

  switch (lname) {
    case 'mv':
      return [['addi', [operands[0], operands[1], '0']]];
    case 'not':
      return [['xori', [operands[0], operands[1], '-1']]];
    case 'neg':
      return [['sub', [operands[0], 'x0', operands[1]]]];
    case 'nop':
      return [['addi', ['x0', 'x0', '0']]];
    case 'unimp':
      return [['addi', ['x0', 'x0', '0']]];
    case 'ret':
      return [['jalr', ['x0', 'x1', '0']]];
    case 'jr':
      return [['jalr', ['x0', operands[0], '0']]];
    // Python 版判断的是 "jalr_pseudo"，而实际传入的是 "jalr"，
    // 因此该分支不可达，"jalr" 落到默认分支原样返回。这里保持一致。
    case 'jalr_pseudo':
      if (operands.length === 1) return [['jalr', ['x1', operands[0], '0']]];
      if (operands.length === 2) return [['jalr', [operands[0], operands[1], '0']]];
      return [['jalr', operands]];
    case 'j':
      return [['jal', ['x0', operands[0]]]];
    case 'call':
      return [['jal', ['x1', operands[0]]]];
    case 'tail':
      return [['jal', ['x0', operands[0]]]];
    case 'beqz':
      return [['beq', [operands[0], 'x0', operands[1]]]];
    case 'bnez':
      return [['bne', [operands[0], 'x0', operands[1]]]];
    case 'blez':
      return [['bge', ['x0', operands[0], operands[1]]]];
    case 'bgez':
      return [['bge', [operands[0], 'x0', operands[1]]]];
    case 'bltz':
      return [['blt', [operands[0], 'x0', operands[1]]]];
    case 'bgtz':
      return [['blt', ['x0', operands[0], operands[1]]]];
    case 'bgt':
      return [['blt', [operands[1], operands[0], operands[2]]]];
    case 'ble':
      return [['bge', [operands[1], operands[0], operands[2]]]];
    case 'bgtu':
      return [['bltu', [operands[1], operands[0], operands[2]]]];
    case 'bleu':
      return [['bgeu', [operands[1], operands[0], operands[2]]]];
    case 'seqz':
      return [['sltiu', [operands[0], operands[1], '1']]];
    case 'snez':
      return [['sltu', [operands[0], 'x0', operands[1]]]];
    case 'sltz':
      return [['slt', [operands[0], operands[1], 'x0']]];
    case 'sgtz':
      return [['slt', [operands[0], 'x0', operands[1]]]];
    case 'li':
      return expandLi(operands[0], operands[1]);
    case 'la':
      try {
        parseIntLiteral(operands[1]);
      } catch {
        throw new Error(
          `la 需要标签支持（标签: ${operands[1]}），请在转码页中使用；此处请使用数值地址`,
        );
      }
      return expandLi(operands[0], operands[1]);
    default:
      return [[lname, operands]];
  }
}

/**
 * li 展开：小立即数用 addi，大立即数拆成 lui + addi。
 * @param {string} rd
 * @param {string} immStr
 * @returns {Array<[string, string[]]>}
 */
function expandLi(rd, immStr) {
  const imm = parseIntLiteral(immStr);
  if (imm >= -2048 && imm <= 2047) {
    return [['addi', [rd, 'x0', String(imm)]]];
  }

  const v = imm >>> 0;
  let upper = (v >>> 12) & 0xFFFFF;
  let lower = v & 0xFFF;
  if (lower >= 0x800) {
    upper = (upper + 1) & 0xFFFFF;
    lower -= 0x1000;
  }

  const seq = [];
  let base;
  if (upper) {
    seq.push(['lui', [rd, String(upper)]]);
    base = rd;
  } else {
    base = 'x0';
  }
  if (lower || seq.length === 0) {
    seq.push(['addi', [rd, base, String(lower)]]);
  }
  return seq;
}

/**
 * @param {string} name
 * @returns {string}
 */
export function getFormat(name) {
  const lname = name.toLowerCase();
  if (Object.prototype.hasOwnProperty.call(PSEUDO_INSTRUCTIONS, lname)) return 'Pseudo';
  if (!Object.prototype.hasOwnProperty.call(RV32I_INSTRUCTIONS, lname)) return 'Unknown';
  const rawType = RV32I_INSTRUCTIONS[lname].type;
  return TYPE_FRIENDLY[rawType] ?? rawType;
}
