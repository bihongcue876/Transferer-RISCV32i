/** 明暗主题：自动（跟随系统）/ 浅色 / 深色 三态循环，选择存 localStorage。 */

const KEY = 'rv32i.theme';
const ORDER = ['auto', 'light', 'dark'];
const LABEL = { auto: '自动', light: '浅色', dark: '深色' };

export function currentTheme() {
  const v = document.documentElement.dataset.theme;
  return v === 'light' || v === 'dark' ? v : 'auto';
}

export function applyTheme(mode) {
  if (mode === 'auto') {
    delete document.documentElement.dataset.theme;
  } else {
    document.documentElement.dataset.theme = mode;
  }
  try {
    if (mode === 'auto') localStorage.removeItem(KEY);
    else localStorage.setItem(KEY, mode);
  } catch {
    /* 存储不可用时只影响记忆，不影响本次切换 */
  }
  return mode;
}

export function initTheme() {
  let saved = null;
  try {
    saved = localStorage.getItem(KEY);
  } catch {
    saved = null;
  }
  if (saved === 'light' || saved === 'dark') applyTheme(saved);
  return currentTheme();
}

export function cycleTheme() {
  const next = ORDER[(ORDER.indexOf(currentTheme()) + 1) % ORDER.length];
  return applyTheme(next);
}

export function themeLabel(mode) {
  return LABEL[mode] ?? LABEL.auto;
}
