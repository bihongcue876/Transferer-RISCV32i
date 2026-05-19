import tkinter as tk
from tkinter import ttk


class HomePage(ttk.Frame):
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self.setup_ui()

    def setup_ui(self):
        outer_frame = ttk.Frame(self)
        outer_frame.place(relx=0.5, rely=0.5, anchor="center")

        title_label = ttk.Label(
            outer_frame,
            text="RISC-V 机器码学习助手",
            font=("", 20, "bold"),
            foreground="#333333",
        )
        title_label.pack(pady=(0, 30))

        self.enter_btn = ttk.Button(
            outer_frame,
            text="进入转码器",
            width=20,
            command=self.on_enter_converter,
        )
        self.enter_btn.pack(pady=8)

        self.learn_btn = ttk.Button(
            outer_frame,
            text="进入学习",
            width=20,
            command=self.on_enter_learn,
        )
        self.learn_btn.pack(pady=8)

        self.clear_cache_btn = ttk.Button(
            outer_frame,
            text="清除缓存",
            width=20,
            command=self.on_clear_cache,
        )
        self.clear_cache_btn.pack(pady=8)

        self.exit_btn = ttk.Button(
            outer_frame,
            text="退出",
            width=20,
            command=self.on_exit,
        )
        self.exit_btn.pack(pady=8)

    def on_enter_converter(self):
        self.main_window.show_page("convert")

    def on_enter_learn(self):
        self.main_window.show_page("learn")

    def on_clear_cache(self):
        self.main_window.clear_cache()

    def on_exit(self):
        self.main_window.on_close()

    def save_state(self):
        return {}

    def load_state(self, data: dict):
        pass
