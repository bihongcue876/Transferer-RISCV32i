/** 帮助页 —— 对应桌面版 ui/help_page.py。 */

export function mountHelp(root) {
  root.innerHTML = `
    <div class="page">
      <h1>使用说明</h1>

      <h2>快捷键</h2>
      <table class="kbd-table">
        <tbody>
          <tr><td><kbd>Ctrl</kbd> + <kbd>S</kbd></td><td>把当前内容保存到本机（localStorage）</td></tr>
          <tr><td><kbd>Enter</kbd>（机器码列）</td><td>插入新行并立即反汇编</td></tr>
          <tr><td>点击任意行</td><td>在下方展开该行的 32 位位段</td></tr>
        </tbody>
      </table>

      <h2>标签与两遍汇编</h2>
      <p>行首写 <code>名字:</code> 即可定义标签，分支与跳转的末位操作数可以直接写标签名，
         汇编时替换为「目标地址 − 当前 pc」的相对偏移。</p>
      <pre>main:
    li   x1, 0x12345
    la   x2, data        # la 展开为 auipc + addi
    beq  x1, x2, done
done:
    ret
data:
    addi x3, x0, 100</pre>
      <p><code>la</code>、<code>call</code>、<code>tail</code> 的目标可达任意 32 位地址，
         超出单条指令立即数范围，因此拆成高低两段：高 20 位进 <code>auipc</code>，
         低 12 位进 <code>addi</code> 或 <code>jalr</code>，加 <code>0x800</code> 的修正把进位折入高位。</p>

      <h2>起始地址</h2>
      <p>工具栏的「起始地址」决定第一行的地址，其余行按每行实际占用的字节数递增：
         基础指令每条 4 字节，<code>li</code>、<code>la</code>、<code>call</code>、<code>tail</code>
         展开后占 8 字节。行号与地址显示在左侧 gutter。</p>

      <h2>字节序</h2>
      <p>切换「小端 / 大端」只改变机器码的显示顺序，不影响编码结果。
         小端下 <code>0x06410093</code> 显示为 <code>93004106</code>。</p>

      <h2>错误提示</h2>
      <p>错误粒度定在「行」：未知指令、无效寄存器、立即数越界、未知标签、重复标签，
         都会让该行在汇编列与机器码列同时标红，并在下方给出具体原因。汇编过程照常推进，
         不会因为一行出错而中断。</p>

      <h2>状态缓存</h2>
      <p>桌面版用 pickle 文件保存状态，这里换成浏览器 localStorage，
         只存在本机，不上传。清除浏览器数据会一并清除。</p>
    </div>
  `;
}
