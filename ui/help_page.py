import tkinter as tk
from tkinter import ttk


class HelpPage(ttk.Frame):
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self.setup_ui()

    def setup_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        content = ttk.Frame(self.canvas)
        self._content_window = self.canvas.create_window((0, 0), window=content, anchor="nw")

        # 内层居中容器
        inner = ttk.Frame(content)
        inner.pack(fill="x", padx=60, pady=(20, 40))

        # 内容宽度随 canvas 自适应，同时更新文字换行宽度
        self._desc_labels = []

        def _resize_content(event):
            w = event.width - 20
            if w > 600:
                self.canvas.itemconfig(self._content_window, width=w)
                wrap_w = w - 120 - 10  # inner padx 60*2 + 余量
                for lbl in self._desc_labels:
                    lbl.configure(wraplength=wrap_w)
        self.canvas.bind("<Configure>", _resize_content)

        ttk.Label(inner, text="帮助", font=("", 19, "bold")).pack(anchor="w")

        help_items = [
            ("快速入门", "在「转码」页面左侧输入汇编代码，右侧会自动显示对应机器码。\n修改机器码后按 Enter 也会自动反汇编为汇编代码。"),
            ("转码页操作", "支持三列编辑器：地址、汇编、机器码。\n地址可手动双击修改，修改后下方地址自动更新。\n机器码支持十六进制和二进制两种显示模式。"),
            ("大小端显示", "转码页工具栏提供大小端切换下拉框。\n小端（默认）：最低有效字节在前，如「9300a00a」\n大端：最高有效字节在前，如「0a00a093」\n反向转换时自动适配当前大小端模式。"),
            ("内存布局配置", "在转码页底部状态栏的「总览」标签中，可设置 ROM 起始地址、ROM 大小、RAM 起始地址、RAM 大小和栈大小。\n这些设置会影响地址列的默认起始地址，并用于统计信息比对。"),
            ("学习页", "左侧导航树选择指令类型，右侧显示指令文档和交互式测试块。\n每个测试块有三个输入框，点击转换按钮即可双向转换。\n页面中的表格可以手动拖动表头调整各列宽度。"),
            ("伪指令支持", "支持常用伪指令：li, mv, not, neg, nop, ret, j, jr, call, tail 等。\n汇编器会自动将伪指令展开为真实指令序列。"),
            ("快捷键", "Ctrl+S — 保存当前状态到缓存\nCtrl+Q — 退出程序\nCtrl+Shift+N — 清空转码页内容"),
            ("缓存与持久化", "切换页面时自动保存当前编辑内容，下次启动恢复。\n首页「清除缓存」可重置所有状态。"),
        ]

        for title, desc in help_items:
            ttk.Label(inner, text=title, font=("", 15, "bold")).pack(anchor="w", pady=(18, 4))
            lbl = ttk.Label(inner, text=desc, justify="left", font=("", 13), wraplength=900)
            lbl.pack(anchor="w", pady=(0, 6))
            self._desc_labels.append(lbl)

        content.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        # 滚轮事件：递归绑定到所有子控件
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_mousewheel_linux_up(event):
            self.canvas.yview_scroll(-1, "units")

        def _on_mousewheel_linux_dn(event):
            self.canvas.yview_scroll(1, "units")

        self._bind_mousewheel_to_tree(content, _on_mousewheel, _on_mousewheel_linux_up, _on_mousewheel_linux_dn)
        self.canvas.bind("<Enter>", lambda e: self.canvas.focus_set())
        self.canvas.bind("<MouseWheel>", _on_mousewheel)
        self.canvas.bind("<Button-4>", _on_mousewheel_linux_up)
        self.canvas.bind("<Button-5>", _on_mousewheel_linux_dn)

    def _bind_mousewheel_to_tree(self, parent, wheel_fn, btn4_fn, btn5_fn):
        """递归绑定滚轮事件到 parent 及其所有子控件"""
        for child in parent.winfo_children():
            child.bind("<MouseWheel>", wheel_fn, add="+")
            child.bind("<Button-4>", btn4_fn, add="+")
            child.bind("<Button-5>", btn5_fn, add="+")
            self._bind_mousewheel_to_tree(child, wheel_fn, btn4_fn, btn5_fn)

    def load_state(self, state_data: dict):
        pass

    def save_state(self) -> dict:
        return {}

    def reset(self):
        pass
