/**
 * 首页 —— 按桌面版 ui/home_page.py 的样式复现：
 * 居中标题 + 一列等宽按钮，不放说明文字。
 *
 * 与桌面版的差异只有一处：桌面版有「退出」，网页没有退出的概念，
 * 换成「使用说明」。
 */

import { resetState } from '../store.js';

export function mountHome(root) {
  root.innerHTML = `
    <div class="page home">
      <div class="home-center">
        <h1 class="home-title">RISC-V 机器码学习助手</h1>
        <a class="home-btn" href="#/convert">进入转码器</a>
        <a class="home-btn" href="#/learn">进入学习</a>
        <button class="home-btn" id="home-clear" type="button">清除缓存</button>
        <a class="home-btn" href="#/help">使用说明</a>
        <p class="home-hint" id="home-hint"></p>
      </div>
    </div>
  `;

  const hint = root.querySelector('#home-hint');
  root.querySelector('#home-clear').addEventListener('click', () => {
    resetState();
    hint.textContent = '缓存已清除';
    setTimeout(() => {
      hint.textContent = '';
    }, 1600);
  });
}
