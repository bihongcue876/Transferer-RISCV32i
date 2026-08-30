import tkinter as tk
from tkinter import ttk
from core.assembler import (
    assemble_program,
    format_machine_bytes_endian,
    disassemble_bytes,
    analyze_assembly_line,
)


class ConvertPage(ttk.Frame):
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self._display_mode = "hex"
        self._endian = "little"
        self._syncing_scroll = False
        self._updating = False
        self._convert_after_id = None
        self._memory_entries = {}
        self._last_results = []          # 最近一次两遍汇编结果（与汇编行一一对应）
        self._symbol_addrs = {}          # 标签 → 地址
        self._symbols = set()            # 标签名集合
        self._memory_config = {
            "rom_start": "00000000",
            "rom_size": "00010000",
            "ram_start": "10000000",
            "ram_size": "00100000",
            "stack_size": "00001000",
        }
        self.setup_ui()

    def setup_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        tool_bar = ttk.Frame(self)
        tool_bar.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 0))

        self.format_label = ttk.Label(tool_bar, text="", foreground="#666666")
        self.format_label.pack(side="left")

        tool_bar_right = ttk.Frame(tool_bar)
        tool_bar_right.pack(side="right")

        self.mode_combo = ttk.Combobox(
            tool_bar_right,
            values=["十六进制", "二进制"],
            state="readonly",
            width=12,
        )
        self.mode_combo.current(0)
        self.mode_combo.pack(side="right", padx=(5, 0))
        self.mode_combo.bind("<<ComboboxSelected>>", self.on_mode_change)

        self.endian_combo = ttk.Combobox(
            tool_bar_right,
            values=["小端", "大端"],
            state="readonly",
            width=8,
        )
        self.endian_combo.current(0)
        self.endian_combo.pack(side="right", padx=(5, 0))
        self.endian_combo.bind("<<ComboboxSelected>>", self.on_endian_change)

        self.clear_btn = ttk.Button(
            tool_bar_right, text="清空", command=self.clear_editor
        )
        self.clear_btn.pack(side="right")

        main_frame = ttk.Frame(self)
        main_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, columnspan=4, sticky="ew", padx=2)
        ttk.Label(header_frame, text="地址", foreground="#666666", width=12).pack(side="left")
        ttk.Label(header_frame, text="汇编代码", foreground="#666666").pack(side="left", padx=(10, 0))
        ttk.Label(header_frame, text="机器码", foreground="#666666").pack(side="right")

        input_frame = ttk.Frame(main_frame)
        input_frame.grid(row=1, column=0, sticky="nsew")
        input_frame.columnconfigure(1, weight=1)
        input_frame.columnconfigure(2, weight=1)
        input_frame.rowconfigure(0, weight=1)

        self.addr_text = tk.Text(
            input_frame,
            font=("Consolas", 11),
            wrap="none",
            width=12,
            height=1,
        )
        self.addr_text.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(input_frame, orient="vertical")
        vsb.grid(row=0, column=3, sticky="ns")

        self.assembly_text = tk.Text(
            input_frame,
            font=("Consolas", 11),
            wrap="none",
            undo=False,
        )
        self.assembly_text.grid(row=0, column=1, sticky="nsew")

        self.machine_text = tk.Text(
            input_frame,
            font=("Consolas", 11),
            wrap="word",
            undo=False,
        )
        self.machine_text.grid(row=0, column=2, sticky="nsew")

        self._vsb = vsb
        vsb.config(command=self._all_yview)

        self.addr_text.config(yscrollcommand=self._on_addr_scroll)
        self.assembly_text.config(yscrollcommand=self._on_asm_scroll)
        self.machine_text.config(yscrollcommand=self._on_machine_scroll)

        self.assembly_text.tag_configure("error", background="#ffcccc")
        self.machine_text.tag_configure("error", background="#ffcccc")

        self.assembly_text.bind("<<Modified>>", self._on_assembly_modified)
        self.assembly_text.bind("<KeyRelease>", self._on_cursor_move)
        self.assembly_text.bind("<ButtonRelease-1>", self._on_cursor_move)

        self.machine_text.bind("<<Modified>>", self._on_machine_modified)
        self.machine_text.bind("<Return>", self._on_machine_return)
        self.machine_text.bind("<FocusOut>", self._do_reverse_conversion)
        self.machine_text.bind("<KeyRelease>", self._on_machine_key)
        self.machine_text.bind("<ButtonRelease-1>", self._on_machine_click)

        self.addr_text.bind("<KeyRelease>", self._on_addr_change)

        self._bind_mousewheel(self.addr_text)
        self._bind_mousewheel(self.assembly_text)
        self._bind_mousewheel(self.machine_text)

        # ── 底部状态栏（总览 / 本行 / 覆写） ─────────────────
        self._build_bottom_panel()

    def _build_bottom_panel(self):
        """构建底部 Notebook 状态栏"""
        bottom_frame = ttk.Frame(self, height=150)
        bottom_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=(0, 5))
        bottom_frame.grid_propagate(False)
        bottom_frame.columnconfigure(0, weight=1)
        bottom_frame.rowconfigure(0, weight=1)

        self.bottom_notebook = ttk.Notebook(bottom_frame)
        self.bottom_notebook.pack(fill="both", expand=True)

        # ── 总览标签 ──
        self.overview_tab = ttk.Frame(self.bottom_notebook)
        self.bottom_notebook.add(self.overview_tab, text="  总览  ")
        self._build_overview_tab()

        # ── 本行标签 ──
        self.line_tab = ttk.Frame(self.bottom_notebook)
        self.bottom_notebook.add(self.line_tab, text="  本行  ")
        self._build_line_tab()

    def _build_overview_tab(self):
        """总览标签：全局统计 + 内存布局配置"""
        panes = ttk.PanedWindow(self.overview_tab, orient="horizontal")
        panes.pack(fill="both", expand=True, padx=5, pady=5)

        # 左侧：全局统计
        stats_frame = ttk.LabelFrame(panes, text="全局统计", padding=8)
        self._stats_labels = {}
        for i, (key, text) in enumerate([
            ("lines", "总行数"),
            ("bytes", "总字节数"),
            ("errors", "错误行数"),
        ]):
            ttk.Label(stats_frame, text=f"{text}：", font=("", 10)).grid(row=i, column=0, sticky="w", pady=1)
            lbl = ttk.Label(stats_frame, text="0", font=("", 10))
            lbl.grid(row=i, column=1, sticky="w", padx=(5, 0), pady=1)
            self._stats_labels[key] = lbl
        panes.add(stats_frame, weight=1)

        # 右侧：内存布局配置
        mem_frame = ttk.LabelFrame(panes, text="内存布局配置", padding=8)
        self._memory_entries = {}
        fields = [
            ("ROM 起始地址", "rom_start", "00000000"),
            ("ROM 大小",      "rom_size",  "00010000"),
            ("RAM 起始地址",  "ram_start", "10000000"),
            ("RAM 大小",      "ram_size",  "00100000"),
            ("栈大小",        "stack_size","00001000"),
        ]
        for i, (label, key, default) in enumerate(fields):
            ttk.Label(mem_frame, text=label, font=("", 10)).grid(row=i, column=0, sticky="w", padx=5, pady=2)
            entry = ttk.Entry(mem_frame, font=("Consolas", 10), width=12)
            entry.insert(0, self._memory_config.get(key, default))
            entry.grid(row=i, column=1, padx=5, pady=2)
            entry.bind("<FocusOut>", lambda e, k=key: self._validate_memory_field(k, e.widget))
            self._memory_entries[key] = entry

        reset_btn = ttk.Button(mem_frame, text="恢复默认", command=self._reset_memory_config)
        reset_btn.grid(row=len(fields), column=0, columnspan=2, pady=(5, 0))
        panes.add(mem_frame, weight=1)

    def _build_line_tab(self):
        """本行标签：当前行详细信息"""
        self.line_info_var = tk.StringVar(value="选择一行查看详细信息")
        ttk.Label(self.line_tab, textvariable=self.line_info_var, font=("", 10),
                  wraplength=900, justify="left").pack(anchor="w", padx=10, pady=10)

    def _validate_memory_field(self, key: str, widget: ttk.Entry):
        """验证内存配置字段是否为有效十六进制"""
        val = widget.get().strip()
        try:
            int(val, 16)
            widget.config(foreground="black")
            self._memory_config[key] = val
            self.main_window.auto_cache()
        except ValueError:
            widget.config(foreground="red")

    def _reset_memory_config(self):
        """恢复默认内存配置"""
        defaults = {
            "rom_start": "00000000",
            "rom_size": "00010000",
            "ram_start": "10000000",
            "ram_size": "00100000",
            "stack_size": "00001000",
        }
        for key, val in defaults.items():
            self._memory_config[key] = val
            if key in self._memory_entries:
                self._memory_entries[key].delete(0, "end")
                self._memory_entries[key].insert(0, val)
                self._memory_entries[key].config(foreground="black")
        self.main_window.auto_cache()

    def _bind_mousewheel(self, widget):
        widget.bind("<MouseWheel>", self._on_mousewheel)
        widget.bind("<Button-4>", self._on_mousewheel_linux)
        widget.bind("<Button-5>", self._on_mousewheel_linux)

    def _on_addr_scroll(self, first, last):
        if self._syncing_scroll:
            return
        self._syncing_scroll = True
        self._vsb.set(first, last)
        self.assembly_text.yview_moveto(first)
        self.machine_text.yview_moveto(first)
        self._syncing_scroll = False

    def _on_asm_scroll(self, first, last):
        if self._syncing_scroll:
            return
        self._syncing_scroll = True
        self._vsb.set(first, last)
        self.addr_text.yview_moveto(first)
        self.machine_text.yview_moveto(first)
        self._syncing_scroll = False

    def _on_machine_scroll(self, first, last):
        if self._syncing_scroll:
            return
        self._syncing_scroll = True
        self._vsb.set(first, last)
        self.addr_text.yview_moveto(first)
        self.assembly_text.yview_moveto(first)
        self._syncing_scroll = False

    def _all_yview(self, *args):
        if self._syncing_scroll:
            return
        self._syncing_scroll = True
        self.addr_text.yview(*args)
        self.assembly_text.yview(*args)
        self.machine_text.yview(*args)
        self._syncing_scroll = False

    def _on_mousewheel(self, event):
        delta = -1 if event.delta > 0 else 1
        self.addr_text.yview_scroll(delta, "units")
        self.assembly_text.yview_scroll(delta, "units")
        self.machine_text.yview_scroll(delta, "units")
        return "break"

    def _on_mousewheel_linux(self, event):
        delta = -1 if event.num == 4 else 1
        self.addr_text.yview_scroll(delta, "units")
        self.assembly_text.yview_scroll(delta, "units")
        self.machine_text.yview_scroll(delta, "units")
        return "break"

    def _on_addr_change(self, event=None):
        self.main_window.auto_cache()

    def _on_assembly_modified(self, event=None):
        if self.assembly_text.edit_modified():
            self.assembly_text.edit_modified(False)
            if not self._updating:
                self._schedule_conversion()

    def _schedule_conversion(self):
        if self._convert_after_id:
            self.after_cancel(self._convert_after_id)
        self._convert_after_id = self.after(100, self._do_assembly_conversion)

    def _split_asm_lines(self) -> list[str]:
        content = self.assembly_text.get("1.0", "end-1c")
        lines = content.split("\n")
        # 去掉末尾多余的单个空行，保留用户意图
        while lines and lines[-1] == "" and len(lines) > 1:
            lines.pop()
        if not lines:
            lines = [""]
        return lines

    def _do_assembly_conversion(self):
        if self._updating:
            return
        self._convert_after_id = None

        lines = self._split_asm_lines()
        addr_content = self.addr_text.get("1.0", "end-1c")
        addr_lines = addr_content.split("\n") if addr_content else []

        results = assemble_program(lines, addr_lines)
        self._last_results = results
        self._symbol_addrs = {}
        for r in results:
            for lab in r["labels"]:
                self._symbol_addrs[lab] = r["address"]
        self._symbols = set(self._symbol_addrs)

        machine_rows = []
        addr_rows = []
        for r in results:
            datas = [c["data"] for c in r["chunks"] if c["data"]]
            if datas:
                blob = b"".join(datas)
                machine_rows.append(format_machine_bytes_endian(blob, self._display_mode, self._endian))
            else:
                machine_rows.append("")
            addr_rows.append(f"{r['address']:08x}")

        self._updating = True
        self.addr_text.delete("1.0", "end")
        self.addr_text.insert("1.0", "\n".join(addr_rows))
        self.machine_text.delete("1.0", "end")
        self.machine_text.insert("1.0", "\n".join(machine_rows))
        self._apply_error_tags(results)
        self.after_idle(lambda: setattr(self, '_updating', False))
        self._update_overview_stats()
        self.main_window.auto_cache()

    def _apply_error_tags(self, results):
        """错误行在汇编列与机器码列同时红色高亮。"""
        self.assembly_text.tag_remove("error", "1.0", "end")
        self.machine_text.tag_remove("error", "1.0", "end")
        for i, r in enumerate(results):
            if r["error"]:
                ln = f"{i + 1}.0"
                self.assembly_text.tag_add("error", ln, f"{i + 1}.end")
                self.machine_text.tag_add("error", ln, f"{i + 1}.end")

    def _on_machine_modified(self, event=None):
        if self.machine_text.edit_modified():
            self.machine_text.edit_modified(False)
            if not self._updating:
                self._schedule_reverse_conversion()

    def _schedule_reverse_conversion(self):
        if self._convert_after_id:
            self.after_cancel(self._convert_after_id)
        self._convert_after_id = self.after(100, self._do_reverse_conversion)

    def _on_machine_return(self, event):
        self._do_reverse_conversion()
        # 允许 Enter 插入新行

    def _do_reverse_conversion(self, event=None):
        if self._updating:
            return
        self._convert_after_id = None
        try:
            content = self.machine_text.get("1.0", "end-1c")
            lines = content.split("\n")
            while lines and lines[-1] == "" and len(lines) > 1:
                lines.pop()
            if not lines:
                lines = [""]

            new_asm_lines = []
            new_machine_lines = []
            new_addr_lines = []
            error_rows = set()
            index = 0

            for line_content in lines:
                stripped = line_content.strip()
                if stripped and self._is_valid_mode_content(stripped):
                    try:
                        if self._display_mode == "hex":
                            data = bytes.fromhex(stripped)
                        else:
                            parts = stripped.replace(" ", "")
                            data = bytes(
                                int(parts[j: j + 8], 2)
                                for j in range(0, len(parts), 8)
                            )
                        if self._endian == "big":
                            data = bytes(reversed(data))
                        if len(data) == 0 or len(data) % 4 != 0:
                            raise ValueError("length")
                        # 一行可能包含多条指令（如 li 展开后的 8 字节），按 4 字节分组
                        for k in range(0, len(data), 4):
                            word = data[k: k + 4]
                            text = disassemble_bytes(word)
                            if text is None:
                                new_asm_lines.append("")
                                error_rows.add(index)
                            else:
                                new_asm_lines.append(text)
                            new_machine_lines.append(
                                format_machine_bytes_endian(word, self._display_mode, self._endian)
                            )
                            new_addr_lines.append(f"{index * 4:08x}")
                            index += 1
                    except Exception:
                        new_asm_lines.append("")
                        new_machine_lines.append("")
                        new_addr_lines.append(f"{index * 4:08x}")
                        error_rows.add(index)
                        index += 1
                else:
                    # 空行/无效字符行：原样保留汇编列文本，便于用户继续编辑
                    new_asm_lines.append(stripped)
                    new_machine_lines.append("")
                    new_addr_lines.append(f"{index * 4:08x}")
                    index += 1

            self._updating = True
            self.assembly_text.delete("1.0", "end")
            self.assembly_text.insert("1.0", "\n".join(new_asm_lines))
            self.addr_text.delete("1.0", "end")
            self.addr_text.insert("1.0", "\n".join(new_addr_lines))
            self.machine_text.delete("1.0", "end")
            self.machine_text.insert("1.0", "\n".join(new_machine_lines))
            # 高亮无法反汇编的行
            self.assembly_text.tag_remove("error", "1.0", "end")
            self.machine_text.tag_remove("error", "1.0", "end")
            for i in error_rows:
                self.assembly_text.tag_add("error", f"{i + 1}.0", f"{i + 1}.end")
                self.machine_text.tag_add("error", f"{i + 1}.0", f"{i + 1}.end")
            self._last_results = []
            self._symbol_addrs = {}
            self._symbols = set()
            self.after_idle(lambda: setattr(self, '_updating', False))
            self._update_overview_stats()
            self.main_window.auto_cache()
        except Exception:
            pass

    def _is_valid_mode_content(self, text: str) -> bool:
        if self._display_mode == "hex":
            allowed = set("0123456789abcdefABCDEF")
            return all(c in allowed for c in text)
        else:
            allowed = set("01 ")
            return all(c in allowed for c in text)

    def _on_machine_key(self, event):
        self._update_format_label()

    def _on_machine_click(self, event):
        self._update_format_label()

    def _on_cursor_move(self, event=None):
        self._update_format_label()

    def _update_format_label(self):
        if self._updating:
            return
        try:
            cursor_pos = self.assembly_text.index("insert")
            line_num = int(cursor_pos.split(".")[0])
            line_content = self.assembly_text.get(
                f"{line_num}.0", f"{line_num}.end"
            ).strip()
            if line_content:
                analysis = analyze_assembly_line(
                    line_content, self._symbols, self._symbol_addrs
                )
                if analysis["valid"]:
                    fmt = analysis["format"]
                    expanded = analysis.get("expanded_count", 1)
                    self.format_label.config(text=fmt)
                    # 更新本行标签页信息
                    extra = f" (展开为 {expanded} 条指令)" if expanded > 1 else ""
                    detail = analysis.get("detail", "")
                    info = f"类型：{fmt} | 指令：{analysis['name']}{extra}"
                    if detail:
                        info += f" | {detail}"
                    self.line_info_var.set(info)
                    status = f"{fmt} | {analysis['name']}"
                    if expanded > 1:
                        status += f" (展开为 {expanded} 条指令)"
                    if detail:
                        status += f" | {detail}"
                    self.main_window.set_status(status)
                else:
                    err = analysis.get("error", "")
                    self.format_label.config(text="")
                    if err:
                        self.line_info_var.set(f"错误：{err}")
                        self.main_window.set_status(f"错误: {err}")
                    else:
                        self.line_info_var.set("空行或注释")
                        self.main_window.set_status("")
            else:
                self.format_label.config(text="")
                self.line_info_var.set("空行或注释")
        except Exception:
            self.format_label.config(text="")

    def _update_overview_stats(self):
        """更新总览标签中的全局统计（基于最近一次两遍汇编结果）。"""
        try:
            lines = self._split_asm_lines()
            addr_content = self.addr_text.get("1.0", "end-1c")
            addr_lines = addr_content.split("\n") if addr_content else []
            results = assemble_program(lines, addr_lines)

            total_lines = len(lines)
            total_bytes = sum(r["size"] for r in results)
            error_lines = sum(1 for r in results if r["error"])

            if hasattr(self, "_stats_labels"):
                self._stats_labels["lines"].config(text=str(total_lines))
                self._stats_labels["bytes"].config(text=str(total_bytes))
                self._stats_labels["errors"].config(text=str(error_lines))
        except Exception:
            pass

    def clear_editor(self):
        self._updating = True
        self.addr_text.delete("1.0", "end")
        self.assembly_text.delete("1.0", "end")
        self.machine_text.delete("1.0", "end")
        self.assembly_text.tag_remove("error", "1.0", "end")
        self.machine_text.tag_remove("error", "1.0", "end")
        self._last_results = []
        self._symbol_addrs = {}
        self._symbols = set()
        self.after_idle(lambda: setattr(self, '_updating', False))
        self.format_label.config(text="")
        self._update_overview_stats()
        self.main_window.auto_cache()

    def on_mode_change(self, event=None):
        new_mode = "bin" if self.mode_combo.get() == "二进制" else "hex"
        if new_mode != self._display_mode:
            self._display_mode = new_mode
            self.main_window.state["convert"]["display_mode"] = new_mode
            self._reformat_machine_column()
            self.main_window.auto_cache()

    def on_endian_change(self, event=None):
        new_endian = "big" if self.endian_combo.get() == "大端" else "little"
        if new_endian != self._endian:
            self._endian = new_endian
            self.main_window.state["convert"]["endian"] = new_endian
            self._reformat_machine_column()
            self.main_window.auto_cache()

    def set_display_mode(self, mode: str):
        if mode != self._display_mode:
            self._display_mode = mode
            self.mode_combo.current(1 if mode == "bin" else 0)
            self._reformat_machine_column()

    def set_endian(self, endian: str):
        if endian != self._endian:
            self._endian = endian
            self.endian_combo.current(1 if endian == "big" else 0)
            self._reformat_machine_column()

    def _reformat_machine_column(self):
        """显示模式/字节序切换后，从汇编列重新生成机器码列。"""
        if self._updating:
            return
        self._do_assembly_conversion()

    def load_state(self, state_data: dict):
        self._updating = True
        self._display_mode = state_data.get("display_mode", "hex")
        self.mode_combo.current(1 if self._display_mode == "bin" else 0)

        self._endian = state_data.get("endian", "little")
        self.endian_combo.current(1 if self._endian == "big" else 0)

        # 恢复内存配置
        mem_config = state_data.get("memory_config", {})
        if mem_config:
            self._memory_config.update(mem_config)
            # 刷新 Entry 显示
            for key, entry in self._memory_entries.items():
                if key in self._memory_config:
                    entry.delete(0, "end")
                    entry.insert(0, self._memory_config[key])

        addr_text = state_data.get("addresses", "")
        asm_text = state_data.get("assembly", "")
        mach_text = state_data.get("machine", "")

        self.addr_text.delete("1.0", "end")
        if addr_text:
            self.addr_text.insert("1.0", addr_text)
        else:
            lines = asm_text.split("\n") if asm_text else [""]
            addr_lines = [f"{i * 4:08x}" for i in range(max(1, len(lines)))]
            self.addr_text.insert("1.0", "\n".join(addr_lines))

        self.assembly_text.delete("1.0", "end")
        self.assembly_text.insert("1.0", asm_text)

        self.machine_text.delete("1.0", "end")
        if mach_text:
            self.machine_text.insert("1.0", mach_text)

        # 恢复后立即做一次两遍汇编，刷新地址/机器码/错误高亮/符号表
        self.after_idle(lambda: setattr(self, '_updating', False))
        self.after_idle(self._do_assembly_conversion)

    def save_state(self) -> dict:
        return {
            "addresses": self.addr_text.get("1.0", "end-1c"),
            "assembly": self.assembly_text.get("1.0", "end-1c"),
            "machine": self.machine_text.get("1.0", "end-1c"),
            "display_mode": self._display_mode,
            "endian": self._endian,
            "memory_config": dict(self._memory_config),
        }
