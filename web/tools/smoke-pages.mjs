/**
 * 冒烟测试：用最小 DOM 桩把四个页面各挂载一遍，暴露真实的 TypeError。
 * 运行：node tools/smoke-pages.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));

class El {
  constructor(tag = 'div') {
    this.tagName = String(tag).toUpperCase();
    this.children = [];
    this.dataset = {};
    this.style = {};
    this.classList = {
      add() {}, remove() {}, toggle() {}, contains() { return false; },
    };
    this.value = '';
    this.textContent = '';
    this.hidden = false;
    this.scrollTop = 0;
    this.scrollLeft = 0;
    this.selectionStart = 0;
    this.selectionEnd = 0;
    this.htmlFor = '';
    this.type = '';
    this.id = '';
    this.spellcheck = false;
    this._innerHTML = '';
    this._byId = new Map();
  }

  set innerHTML(v) {
    this._innerHTML = String(v);
    this._byId = new Map();
    for (const m of this._innerHTML.matchAll(/\bid="([^"$]+)"/g)) {
      this._byId.set(m[1], new El('div'));
    }
  }

  get innerHTML() { return this._innerHTML; }

  querySelector(sel) {
    if (sel.startsWith('#')) {
      const found = this._byId.get(sel.slice(1));
      if (!found) throw new Error(`querySelector 未命中：${sel}`);
      return found;
    }
    return new El('div');
  }

  querySelectorAll() { return []; }
  matches() { return false; }
  appendChild(c) { this.children.push(c); return c; }
  append(...c) { this.children.push(...c); }
  replaceChildren(...c) { this.children = c; }
  addEventListener() {}
  removeEventListener() {}
  closest() { return null; }
  scrollIntoView() {}
  get offsetWidth() { return 0; }
}

const store = new Map();
globalThis.localStorage = {
  getItem: (k) => (store.has(k) ? store.get(k) : null),
  setItem: (k, v) => store.set(k, String(v)),
  removeItem: (k) => store.delete(k),
};
globalThis.requestAnimationFrame = (cb) => setTimeout(cb, 0);
globalThis.IntersectionObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};
globalThis.document = {
  createElement: (tag) => new El(tag),
  addEventListener() {},
  removeEventListener() {},
  querySelector: () => null,
  getElementById: () => null,
};

const DATA = {
  'instructions.json': path.join(here, '..', 'src', 'data', 'instructions.json'),
  'format-tables.json': path.join(here, '..', 'src', 'data', 'format-tables.json'),
};
globalThis.fetch = async (url) => {
  const key = [...Object.keys(DATA)].find((k) => String(url).endsWith(k));
  if (!key) throw new Error(`未预期的 fetch：${url}`);
  const text = fs.readFileSync(DATA[key], 'utf8');
  return { ok: true, json: async () => JSON.parse(text) };
};

const { loadState } = await import('../src/store.js');
const pages = [
  ['首页', (await import('../src/ui/home.js')).mountHome],
  ['转码页', (await import('../src/ui/convert.js')).mountConvert],
  ['学习页', (await import('../src/ui/learn.js')).mountLearn],
  ['帮助页', (await import('../src/ui/help.js')).mountHelp],
];

let failed = 0;
for (const [name, mount] of pages) {
  const root = new El('main');
  try {
    const cleanup = await mount(root, loadState());
    console.log(`✔ ${name} 挂载成功`);
    if (typeof cleanup === 'function') cleanup();
  } catch (err) {
    failed += 1;
    console.error(`✖ ${name} 挂载失败：${err.message}`);
    console.error(err.stack.split('\n').slice(0, 5).join('\n'));
  }
}

if (failed) process.exit(1);
console.log('\n四个页面均可挂载');
