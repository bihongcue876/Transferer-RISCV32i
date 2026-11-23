/* 主题引导：在样式生效前把已保存的选择写到 <html>，避免明暗闪烁。
   普通脚本（非 module），放在 head 里同步执行。 */
(function () {
  try {
    var t = localStorage.getItem('rv32i.theme');
    if (t === 'light' || t === 'dark') {
      document.documentElement.dataset.theme = t;
    }
  } catch (e) {
    /* 存储不可用时保持跟随系统 */
  }
})();
