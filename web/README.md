# RISC-V 32I 转码学习助手 · 前端演示

桌面版（Python + Tkinter）的纯前端演示。零构建、零依赖：浏览器直接加载 ES module，
不需要 npm install，不需要打包工具。

## 跑起来

```bash
cd web
python -m http.server 8000
# 打开 http://127.0.0.1:8000/
```

必须用 HTTP 打开，不能双击 `index.html`：ES module 与 `fetch` 在 `file://` 下会被浏览器拦截。

## 目录

```
web/
├── index.html                 单页入口
├── assets/style.css           全部样式（无内联样式，适配 script-src 'self'）
├── src/
│   ├── main.js                hash 路由
│   ├── store.js               localStorage 状态缓存（替代 pickle）
│   ├── core/
│   │   ├── isa.js             core/isa_rv32i.py 的移植：46 条基础 + 27 条伪指令
│   │   └── assembler.js       core/assembler.py 的移植：两遍汇编、锚点、行级错误
│   ├── data/
│   │   ├── instructions.json  37 张指令卡片（从 ui/learn_page.py 导出）
│   │   └── format-tables.json 六张格式表（同上）
│   └── ui/
│       ├── home.js            首页
│       ├── convert.js         转码页：三列联动、防抖、错误高亮
│       ├── bits.js            32 位位段可视化
│       ├── learn.js           学习页：格式表、指令卡片、试试看
│       └── help.js            帮助页
├── tests/
│   ├── golden.json            金标准向量（由 tools/export_golden.py 生成）
│   └── parity.test.js         对拍测试
└── tools/check-dom-ids.mjs    id 引用静态检查
```

## 正确性

JavaScript 引擎不是重新设计，而是 `core/` 的逐行移植。为了证明两者一致，
`tools/export_golden.py` 调用 Python 原实现生成金标准向量，`tests/parity.test.js`
读取同一份向量逐条比对：

```bash
python tools/export_golden.py   # 在仓库根目录运行，重新生成向量
cd web && node tests/parity.test.js
```

覆盖范围：

- 163 条编码向量：46 条基础指令 × 多组操作数，比对机器码、反汇编结果
- 14 条错误向量：错误文案逐字一致
- 33 条伪指令向量：展开序列与每块编码一致
- 7 个多行程序样本：标签、la/call/tail 的 PC 相对展开、地址锚点、错误行，逐行逐块比对
- 指令表、伪指令集合、寄存器别名逐项一致

改过 `core/` 之后重跑导出脚本，测试变红就说明两套实现分叉了。

## 部署

整个 `web/` 目录就是产物，复制到 nginx 的静态目录即可，例如 `/var/www/example.com/demo/riscv32i/`。

站点需要三处配合：

1. 给演示目录加一个 location，关闭缓存，便于更新：

```nginx
location ^~ /demo/riscv32i/ {
    include /etc/nginx/snippets/example.com-security.conf;
    add_header Cache-Control "no-cache" always;
    types { application/javascript js mjs; text/css css; application/json json; }
    try_files $uri $uri/ =404;
}
```

2. 现有 CSP 不用改。页面没有内联脚本、没有内联样式、没有 wasm、没有 eval，
   `script-src 'self'` 与 `style-src 'self'` 都能直接通过。

3. 如果以后换成打包产物（例如引入构建工具），记得关掉内联的 modulepreload polyfill，
   否则会注入内联脚本被 CSP 拦下。

## 与桌面版的差异

- 状态缓存从 pickle 文件改为 localStorage，只存在本机
- 新增 32 位位段可视化：点击转码页任意行，按字段拆开 32 个比特
- 地址列、汇编列、机器码列的行高固定为 24px，三列滚动同步
