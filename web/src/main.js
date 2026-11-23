/** 入口：hash 路由 + 页面挂载。 */

import { loadState, saveState } from './store.js';
import { initTheme, cycleTheme, currentTheme, themeLabel } from './theme.js';
import { mountHome } from './ui/home.js';
import { mountConvert } from './ui/convert.js';
import { mountLearn } from './ui/learn.js';
import { mountHelp } from './ui/help.js';
import { escapeHtml } from './ui/bits.js';

const app = document.getElementById('app');
const navLinks = [...document.querySelectorAll('#nav a')];
const badge = document.getElementById('engine-badge');
const footerNote = document.getElementById('footer-note');

const ROUTES = {
  '': mountHome,
  home: mountHome,
  convert: mountConvert,
  learn: mountLearn,
  help: mountHelp,
};

let cleanup = null;

function currentKey() {
  const raw = location.hash.replace(/^#\/?/, '').split('?')[0];
  return raw || 'home';
}

async function render() {
  if (typeof cleanup === 'function') {
    try {
      cleanup();
    } catch {
      /* 忽略清理失败 */
    }
    cleanup = null;
  }

  const key = currentKey();
  const mount = ROUTES[key] ?? mountHome;
  app.replaceChildren();

  for (const a of navLinks) {
    a.classList.toggle('active', a.dataset.nav === (ROUTES[key] ? key : 'home'));
  }

  const state = loadState();
  saveState({ page: key });

  try {
    const result = await mount(app, state);
    cleanup = typeof result === 'function' ? result : null;
    badge.textContent = '引擎就绪';
    badge.className = 'badge ok';
    footerNote.textContent = key === 'convert' ? '改动自动保存到本机' : '纯前端 · 无后端';
    if (location.search.includes('diag')) requestAnimationFrame(renderDiag);
  } catch (err) {
    badge.textContent = '引擎异常';
    badge.className = 'badge err';
    app.innerHTML =
      `<div class="page"><h1>页面加载失败</h1>` +
      `<pre>${escapeHtml(String(err?.stack ?? err))}</pre></div>`;
  }
}

/**
 * 诊断模式（URL 带 ?diag）：把关键容器的实测尺寸写进页脚，
 * 用来定位「某几页顶栏看起来不一样」这类问题。
 */
function renderDiag() {
  const rect = (el) => {
    if (!el) return 'none';
    const r = el.getBoundingClientRect();
    return `${Math.round(r.width)}x${Math.round(r.height)}@${Math.round(r.top)}`;
  };
  const sc = document.scrollingElement;
  const inner = app.firstElementChild;
  const parts = [
    `topbar ${rect(document.querySelector('.topbar'))}`,
    `app ${rect(app)}`,
    `inner ${inner ? inner.className.split(' ')[0] : 'none'} ${rect(inner)}`,
    `footer ${rect(document.querySelector('.footer'))}`,
    `body ${sc.scrollHeight}/${sc.clientHeight}`,
    `win ${window.innerWidth}x${window.innerHeight}`,
  ];
  footerNote.textContent = parts.join(' · ');
  footerNote.style.fontFamily = 'ui-monospace, monospace';
}

// 明暗主题：三态循环，选择存本机
const themeBtn = document.getElementById('theme-btn');
initTheme();
themeBtn.textContent = themeLabel(currentTheme());
themeBtn.addEventListener('click', () => {
  themeBtn.textContent = themeLabel(cycleTheme());
});

window.addEventListener('hashchange', render);
render();
