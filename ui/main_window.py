import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from ui.home_page import HomePage
from ui.convert_page import ConvertPage
from ui.learn_page import LearnPage
from ui.help_page import HelpPage
from core.assembler import save_state, load_state as core_load_state, clear_cache as core_clear_cache


DEFAULT_STATE = {
    "convert": {
        "addresses": "",
        "assembly": "",
        "machine": "",
        "display_mode": "hex",
    },
    "learn": {
        "last_selected_instruction": "add",
    },
    "global": {
        "font_size": 11,
    },
}


class MainWindow(tk.Tk):
    def __init__(self, cached_data: dict):
        super().__init__()
        self.title("RISC-V 机器码学习助手")
        self.geometry("1350x800")
        self.minsize(800, 500)

        # 设置应用图标
        icon_path = Path(__file__).resolve().parent.parent / "resource" / "picture.ico"
        if icon_path.exists():
            self.iconbitmap(default=str(icon_path))

        self.state = DEFAULT_STATE.copy()
        self.state["convert"] = DEFAULT_STATE["convert"].copy()
        self.state["learn"] = DEFAULT_STATE["learn"].copy()
        self.state["global"] = DEFAULT_STATE["global"].copy()

        if cached_data:
            self._merge_state(cached_data)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self._nav_labels = {}
        self._current_nav = None

        self.setup_ui()
        self.bind_shortcuts()

        self.current_page = None
        self.current_page_name = None
        self.show_page("home")

    def _merge_state(self, cached):
        for section in ("convert", "learn", "global"):
            if section in cached and isinstance(cached[section], dict):
                self.state[section].update(cached[section])

    def setup_ui(self):
        self.nav_frame = tk.Frame(self, bg="#ffffff", height=45, highlightbackground="#e0e0e0", highlightthickness=1)
        self.nav_frame.pack(side="top", fill="x")
        self.nav_frame.pack_propagate(False)

        nav_items = [
            ("home", "首页"),
            ("learn", "学习"),
            ("convert", "转码"),
            ("help", "帮助"),
        ]

        for page_name, label in nav_items:
            nav_label = tk.Label(
                self.nav_frame,
                text=label,
                bg="#ffffff",
                fg="#333333",
                font=("Microsoft YaHei UI", 12),
                padx=25,
                pady=10,
                cursor="hand2",
            )
            nav_label.pack(side="left")
            nav_label.bind("<Button-1>", lambda e, p=page_name: self.show_page(p))
            nav_label.bind("<Enter>", lambda e, l=nav_label: self._on_nav_hover(l))
            nav_label.bind("<Leave>", lambda e, l=nav_label, p=page_name: self._on_nav_leave(l, p))
            self._nav_labels[page_name] = nav_label

        exit_label = tk.Label(
            self.nav_frame,
            text="退出",
            bg="#ffffff",
            fg="#333333",
            font=("Microsoft YaHei UI", 12),
            padx=25,
            pady=10,
            cursor="hand2",
        )
        exit_label.pack(side="right")
        exit_label.bind("<Button-1>", lambda e: self.on_close())
        exit_label.bind("<Enter>", lambda e: exit_label.config(fg="#e74c3c"))
        exit_label.bind("<Leave>", lambda e: exit_label.config(fg="#333333"))

        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self.status_var = tk.StringVar(value="就绪")
        self.status_bar = ttk.Label(
            self,
            textvariable=self.status_var,
            relief="sunken",
            anchor="w",
            padding=(4, 2),
        )
        self.status_bar.pack(side="bottom", fill="x")

        self.home_page = HomePage(self.container, self)
        self.convert_page = ConvertPage(self.container, self)
        self.learn_page = LearnPage(self.container, self)
        self.help_page = HelpPage(self.container, self)

    def _on_nav_hover(self, label):
        if label != self._current_nav:
            label.config(fg="#3498db")

    def _on_nav_leave(self, label, page_name):
        if label != self._current_nav:
            label.config(fg="#333333")

    def bind_shortcuts(self):
        self.bind_all("<Control-q>", lambda e: self.on_close())
        self.bind_all("<Control-Q>", lambda e: self.on_close())
        self.bind_all("<Control-Shift-N>", lambda e: self.on_clear_all())
        self.bind_all("<Control-Shift-n>", lambda e: self.on_clear_all())

    def show_page(self, page_name: str):
        if self.current_page and self.current_page_name:
            self._save_current_page_state(self.current_page_name)
        if self.current_page:
            self.current_page.pack_forget()

        for name, label in self._nav_labels.items():
            label.config(bg="#ffffff", fg="#333333")

        if page_name in self._nav_labels:
            self._nav_labels[page_name].config(fg="#3498db", font=("Microsoft YaHei UI", 11, "bold"))
            self._current_nav = self._nav_labels[page_name]

        if page_name == "home":
            self.home_page.pack(fill="both", expand=True)
            self.current_page = self.home_page
        elif page_name == "convert":
            self.convert_page.load_state(self.state["convert"])
            self.convert_page.pack(fill="both", expand=True)
            self.current_page = self.convert_page
        elif page_name == "learn":
            self.learn_page.load_state(self.state["learn"])
            self.learn_page.pack(fill="both", expand=True)
            self.current_page = self.learn_page
        elif page_name == "help":
            self.help_page.pack(fill="both", expand=True)
            self.current_page = self.help_page

        self.current_page_name = page_name
        self.status_var.set("就绪")

    def _save_current_page_state(self, page_name: str):
        if page_name == "convert":
            self.state["convert"] = self.convert_page.save_state()
        elif page_name == "learn":
            self.state["learn"] = self.learn_page.save_state()

    def set_status(self, text: str):
        self.status_var.set(text)

    def auto_cache(self):
        if self.current_page_name:
            self._save_current_page_state(self.current_page_name)
        save_state(self.state)

    def on_clear_all(self):
        if self.current_page_name == "convert":
            self.convert_page.clear_editor()
        self.set_status("已清空")

    def on_close(self):
        if self.current_page_name:
            self._save_current_page_state(self.current_page_name)
        save_state(self.state)
        self.destroy()

    def clear_cache(self):
        core_clear_cache()
        self.state["convert"] = DEFAULT_STATE["convert"].copy()
        self.state["learn"] = DEFAULT_STATE["learn"].copy()
        if hasattr(self, "convert_page"):
            self.convert_page.clear_editor()
        if hasattr(self, "learn_page"):
            self.learn_page.reset()
        messagebox.showinfo("提示", "缓存已清除，下次启动将恢复初始状态。")
        self.set_status("缓存已清除")
