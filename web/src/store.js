/**
 * 状态缓存 —— 替代桌面版的 pickle 文件（core/assembler.py 的 load_state/save_state）。
 * 浏览器里改用 localStorage，键名带版本号，结构变化时旧数据自动作废。
 */

const KEY = 'rv32i.demo.v1';

export const SAMPLE_ASM = [
  '# 两遍汇编示例：标签、伪指令、PC 相对寻址',
  'main:',
  '    li   x1, 0x12345',
  '    la   x2, data',
  '    beq  x1, x2, done',
  '    addi x1, x1, 1',
  '    j    main',
  'done:',
  '    ret',
  'data:',
  '    addi x3, x0, 100',
  '    sw   x3, -8(sp)',
].join('\n');

const DEFAULT_MEMORY = {
  rom_start: '00000000',
  rom_size: '00010000',
  ram_start: '10000000',
  ram_size: '00100000',
  stack_size: '00001000',
};

const DEFAULTS = {
  asm: SAMPLE_ASM,
  addr: '',
  mc: '',
  mode: 'hex',
  endian: 'little',
  memory: { ...DEFAULT_MEMORY },
  page: 'home',
};

/** @returns {typeof DEFAULTS} */
export function loadState() {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return { ...DEFAULTS, memory: { ...DEFAULT_MEMORY } };
    const parsed = JSON.parse(raw);
    return {
      ...DEFAULTS,
      ...parsed,
      memory: { ...DEFAULT_MEMORY, ...(parsed.memory ?? {}) },
    };
  } catch {
    return { ...DEFAULTS, memory: { ...DEFAULT_MEMORY } };
  }
}

/** @param {object} patch */
export function saveState(patch) {
  try {
    const current = loadState();
    localStorage.setItem(KEY, JSON.stringify({ ...current, ...patch }));
  } catch {
    /* 存储被禁用时静默降级 */
  }
}

export function resetState() {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* 忽略 */
  }
  return { ...DEFAULTS, memory: { ...DEFAULT_MEMORY } };
}

export { DEFAULT_MEMORY };
