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

        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)

        content = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=content, anchor="nw", width=900)

        ttk.Label(content, text="帮助", font=("", 16, "bold")).pack(pady=(20, 10))

        help_items = [
            ("快速入门", "在「转码」页面左侧输入汇编代码，右侧会自动显示对应机器码。\n修改机器码后按 Enter 也会自动反汇编为汇编代码。"),
            ("转码页操作", "支持三列编辑器：地址、汇编、机器码。\n地址可手动双击修改，修改后下方地址自动更新。\n机器码支持十六进制和二进制两种显示模式。"),
            ("学习页", "左侧导航树选择指令类型，右侧显示指令文档和交互式测试块。\n每个测试块有三个输入框，点击转换按钮即可双向转换。"),
            ("伪指令支持", "支持常用伪指令：li, mv, not, neg, nop, ret, j, jr, call, tail 等。"),
            ("缓存与持久化", "切换页面时自动保存当前编辑内容，下次启动恢复。\n首页「清除缓存」可重置所有状态。"),
        ]

        for title, desc in help_items:
            ttk.Label(content, text=title, font=("", 12, "bold")).pack(anchor="w", padx=20, pady=(10, 2))
            ttk.Label(content, text=desc, justify="left", wraplength=800).pack(anchor="w", padx=30, pady=(0, 8))

        content.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.bind("<Enter>", lambda e: canvas.focus_set())
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        canvas.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

    def load_state(self, state_data: dict):
        pass

    def save_state(self) -> dict:
        return {}

    def reset(self):
        pass
