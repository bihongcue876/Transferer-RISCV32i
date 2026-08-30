"""两遍汇编器测试：标签解析、地址推进、错误上报、反汇编。"""
import unittest

from core.assembler import (
    assemble_program,
    assemble_line,
    assemble_line_hex,
    compute_addresses,
    disassemble_bytes,
    disassemble_hex,
    strip_comment,
    split_labels,
    analyze_assembly_line,
)


def _chunk_data(row):
    return [c["data"] for c in row["chunks"] if c["data"]]


class LineParsingTests(unittest.TestCase):
    def test_strip_comment(self):
        self.assertEqual(strip_comment("add x1, x2, x3 # comment"), "add x1, x2, x3")
        self.assertEqual(strip_comment("# whole line"), "")
        self.assertEqual(strip_comment("nop // c++ style"), "nop")

    def test_split_labels(self):
        labels, rest = split_labels("loop: addi x1, x0, 1")
        self.assertEqual(labels, ["loop"])
        self.assertEqual(rest, "addi x1, x0, 1")

        labels, rest = split_labels("a: b: nop")
        self.assertEqual(labels, ["a", "b"])
        self.assertEqual(rest, "nop")

        labels, rest = split_labels("end:")
        self.assertEqual(labels, ["end"])
        self.assertEqual(rest, "")

        labels, rest = split_labels("add x1, x2, x3")
        self.assertEqual(labels, [])
        self.assertEqual(rest, "add x1, x2, x3")


class SingleLineTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(assemble_line("addi x1, x0, 10"), bytes.fromhex("9300a000"))

    def test_empty_and_comment(self):
        self.assertEqual(assemble_line(""), b"")
        self.assertEqual(assemble_line("# comment"), b"")
        self.assertEqual(assemble_line("   "), b"")

    def test_multi_instruction_line(self):
        data = assemble_line("li x5, 0x12345678")
        self.assertEqual(len(data), 8)

    def test_error_returns_empty(self):
        self.assertEqual(assemble_line("bad x1"), b"")
        self.assertEqual(assemble_line("addi x1, x0, 99999"), b"")

    def test_fence_default(self):
        self.assertEqual(assemble_line("fence"), bytes.fromhex("0f00f00f"))

    def test_disassemble_hex(self):
        self.assertEqual(disassemble_hex("9300a000"), "addi x1, x0, 10")
        self.assertIsNone(disassemble_hex("1234"))  # 长度不对
        self.assertIsNone(disassemble_hex("ffffffff"))


class AssembleProgramTests(unittest.TestCase):
    def test_single_instruction(self):
        rows = assemble_program(["addi x1, x0, 10"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["address"], 0)
        self.assertEqual(rows[0]["error"], None)
        self.assertEqual(rows[0]["size"], 4)
        self.assertEqual(_chunk_data(rows[0]), [bytes.fromhex("9300a000")])

    def test_sequential_addresses(self):
        rows = assemble_program(["nop", "nop", "nop"])
        self.assertEqual([r["address"] for r in rows], [0, 4, 8])

    def test_unknown_instruction_error(self):
        rows = assemble_program(["bad x1"])
        self.assertIn("未知指令", rows[0]["error"])
        self.assertEqual(rows[0]["size"], 0)

    def test_range_error_reported(self):
        rows = assemble_program(["addi x1, x0, 99999"])
        self.assertIn("超出", rows[0]["error"])

    def test_label_only_row(self):
        rows = assemble_program(["loop:", "nop"])
        self.assertEqual(rows[0]["labels"], ["loop"])
        self.assertEqual(rows[0]["size"], 0)
        self.assertEqual(rows[0]["address"], 0)
        self.assertEqual(rows[1]["address"], 0)

    def test_inline_label(self):
        rows = assemble_program(["start: addi x1, x0, 1"])
        self.assertEqual(rows[0]["labels"], ["start"])
        self.assertEqual(rows[0]["size"], 4)
        self.assertEqual(len(rows[0]["chunks"]), 1)

    def test_backward_branch_label(self):
        rows = assemble_program(["loop:", "addi x5, x5, 1", "beq x5, x6, loop"])
        # beq 位于地址 4，loop=0 → 偏移 -4
        self.assertEqual(rows[2]["chunks"][0]["text"], "beq x5, x6, -4")
        self.assertEqual(rows[2]["error"], None)

    def test_forward_branch_label(self):
        rows = assemble_program(["beq x1, x2, end", "nop", "end: nop"])
        self.assertEqual(rows[0]["chunks"][0]["text"], "beq x1, x2, 8")
        self.assertEqual(rows[0]["error"], None)

    def test_j_label(self):
        rows = assemble_program(["j skip", "nop", "skip: nop"])
        self.assertEqual(rows[0]["chunks"][0]["text"], "jal x0, 8")

    def test_undefined_label(self):
        rows = assemble_program(["beq x1, x2, nowhere"])
        self.assertIn("未知标签", rows[0]["error"])

    def test_duplicate_label(self):
        rows = assemble_program(["a:", "a: nop"])
        self.assertIn("重复定义标签", rows[1]["error"])

    def test_call_expansion(self):
        rows = assemble_program(["call func", "func: ret"])
        self.assertEqual(rows[0]["size"], 8)
        self.assertEqual(len(rows[0]["chunks"]), 2)
        self.assertEqual(rows[0]["chunks"][0]["mnemonic"], "auipc")
        self.assertEqual(rows[0]["chunks"][1]["mnemonic"], "jalr")
        # off = 8 - 0 = 8 → hi=0, lo=8
        self.assertEqual(rows[0]["chunks"][0]["text"], "auipc x1, 0")
        self.assertEqual(rows[0]["chunks"][1]["text"], "jalr x1, x1, 8")
        self.assertEqual(rows[1]["address"], 8)

    def test_la_expansion(self):
        rows = assemble_program(["la x5, val", "val: nop", "nop"])
        # la 占 2 条指令(8字节)，val 位于地址 8 → off = 8 → hi=0, lo=8
        self.assertEqual(rows[0]["chunks"][0]["mnemonic"], "auipc")
        self.assertEqual(rows[0]["chunks"][1]["text"], "addi x5, x5, 8")
        self.assertEqual(rows[1]["address"], 8)

    def test_tail_expansion(self):
        rows = assemble_program(["tail func", "func: nop"])
        self.assertEqual(rows[0]["chunks"][0]["mnemonic"], "auipc")
        self.assertEqual(rows[0]["chunks"][1]["mnemonic"], "jalr")
        self.assertEqual(rows[0]["chunks"][1]["text"], "jalr x0, x6, 8")

    def test_pcrel_negative_offset(self):
        rows = assemble_program(["func: nop", "la x5, func"])
        # la 在地址 4，func 在 0 → off = -4
        # hi = ((-4 + 0x800) >> 12) & 0xFFFFF = 0 → lo = -4
        self.assertEqual(rows[1]["chunks"][0]["text"], "auipc x5, 0")
        self.assertEqual(rows[1]["chunks"][1]["text"], "addi x5, x5, -4")

    def test_pseudo_expansion_multi_chunk_addressing(self):
        rows = assemble_program(["li x5, 0x12345678", "nop"])
        self.assertEqual(rows[0]["size"], 8)
        self.assertEqual(rows[1]["address"], 8)

    def test_case_insensitive_mnemonics(self):
        rows = assemble_program(["ADDI x1, x0, 5"])
        self.assertEqual(rows[0]["error"], None)
        self.assertEqual(len(_chunk_data(rows[0])), 1)

    def test_comment_lines(self):
        rows = assemble_program(["# 注释", "nop", "// c++ 注释"])
        self.assertEqual(rows[0]["size"], 0)
        self.assertEqual(rows[1]["size"], 4)
        self.assertEqual(rows[2]["size"], 0)

    def test_empty_program(self):
        self.assertEqual(assemble_program([]), [])


class AddressAnchorTests(unittest.TestCase):
    def test_compute_addresses_by_size(self):
        addrs = compute_addresses(["", ""], [4, 8])
        self.assertEqual(addrs, ["00000000", "00000004"])

    def test_anchor(self):
        addrs = compute_addresses(["", "", "00000100"], [4, 4, 4])
        self.assertEqual(addrs, ["00000000", "00000004", "00000100"])

    def test_anchor_gap_blank(self):
        # 锚点 0x100，第二行自动地址 0x04 < 0x100 → 正常；之后 0x08 仍 < 0x100
        addrs = compute_addresses(["", "", "", "00000010"], [4, 4, 4, 4])
        self.assertEqual(addrs, ["00000000", "00000004", "00000008", "00000010"])

    def test_zero_size_rows(self):
        addrs = compute_addresses(["", "", ""], [0, 4, 4])
        self.assertEqual(addrs, ["00000000", "00000000", "00000004"])

    def test_invalid_anchor_ignored(self):
        addrs = compute_addresses(["xyz", ""], [4, 4])
        self.assertEqual(addrs, ["00000000", "00000004"])

    def test_anchor_resumed_after(self):
        addrs = compute_addresses(["000000c0", ""], [4, 4])
        self.assertEqual(addrs, ["000000c0", "000000c4"])

    def test_program_with_anchor(self):
        rows = assemble_program(["nop", "nop"], addr_lines=["", "00000040"])
        self.assertEqual(rows[0]["address"], 0)
        self.assertEqual(rows[1]["address"], 0x40)


class AnalyzeTests(unittest.TestCase):
    def test_valid_instruction(self):
        info = analyze_assembly_line("add x1, x2, x3")
        self.assertTrue(info["valid"])
        self.assertEqual(info["format"], "R-type")

    def test_unknown_instruction(self):
        info = analyze_assembly_line("mul x1, x2, x3")
        self.assertFalse(info["valid"])
        self.assertIn("未知指令", info["error"])

    def test_label_line(self):
        info = analyze_assembly_line("loop: addi x1, x0, 1", {}, {})
        self.assertTrue(info["valid"])
        # 标签+指令混合行
        self.assertEqual(info["name"], "addi")

    def test_label_only_with_addr(self):
        info = analyze_assembly_line("loop:", {}, {"loop": 8})
        self.assertTrue(info["valid"])
        self.assertIn("0x00000008", info["detail"])

    def test_label_operand_with_symbols(self):
        info = analyze_assembly_line("beq x1, x2, loop", {"loop"}, {"loop": 8})
        self.assertTrue(info["valid"])

    def test_label_operand_without_symbols(self):
        info = analyze_assembly_line("beq x1, x2, loop")
        self.assertFalse(info["valid"])
        self.assertIn("未知标签", info["error"])

    def test_range_error_message(self):
        info = analyze_assembly_line("addi x1, x0, 99999")
        self.assertFalse(info["valid"])
        self.assertIn("超出", info["error"])


if __name__ == "__main__":
    unittest.main()
