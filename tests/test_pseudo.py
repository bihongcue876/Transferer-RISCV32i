"""伪指令展开测试：li 全区间、比较分支族、寄存器/跳转族。"""
import unittest

from core.isa_rv32i import expand_pseudo, encode, parse_int


def _li_value(seq) -> int:
    """模拟 li 展开序列的最终寄存器值（模 2^32）。"""
    val = 0
    for mnem, ops in seq:
        if mnem == "lui":
            val = (parse_int(ops[1]) & 0xFFFFF) << 12
        elif mnem == "addi":
            base = 0 if ops[1] == "x0" else val
            val = (base + parse_int(ops[2])) & 0xFFFFFFFF
        else:
            raise AssertionError(f"li 展开不应包含 {mnem}")
    return val


class SimplePseudoTests(unittest.TestCase):
    def test_mv(self):
        self.assertEqual(expand_pseudo("mv", ["x1", "x2"]), [("addi", ["x1", "x2", "0"])])

    def test_nop(self):
        self.assertEqual(expand_pseudo("nop", []), [("addi", ["x0", "x0", "0"])])

    def test_ret(self):
        self.assertEqual(expand_pseudo("ret", []), [("jalr", ["x0", "x1", "0"])])

    def test_not(self):
        self.assertEqual(expand_pseudo("not", ["x1", "x2"]), [("xori", ["x1", "x2", "-1"])])

    def test_neg(self):
        self.assertEqual(expand_pseudo("neg", ["x1", "x2"]), [("sub", ["x1", "x0", "x2"])])

    def test_j(self):
        self.assertEqual(expand_pseudo("j", ["8"]), [("jal", ["x0", "8"])])

    def test_jr(self):
        self.assertEqual(expand_pseudo("jr", ["x1"]), [("jalr", ["x0", "x1", "0"])])

    def test_call_numeric_near(self):
        self.assertEqual(expand_pseudo("call", ["256"]), [("jal", ["x1", "256"])])

    def test_seqz_snez(self):
        self.assertEqual(expand_pseudo("seqz", ["x1", "x2"]), [("sltiu", ["x1", "x2", "1"])])
        self.assertEqual(expand_pseudo("snez", ["x1", "x2"]), [("sltu", ["x1", "x0", "x2"])])


class BranchComparePseudoTests(unittest.TestCase):
    """bgt/ble/bgtu/bleu：交换操作数后复用基础分支。"""

    def test_bgt(self):
        self.assertEqual(expand_pseudo("bgt", ["x1", "x2", "8"]), [("blt", ["x2", "x1", "8"])])

    def test_ble(self):
        self.assertEqual(expand_pseudo("ble", ["x1", "x2", "8"]), [("bge", ["x2", "x1", "8"])])

    def test_bgtu(self):
        self.assertEqual(expand_pseudo("bgtu", ["x1", "x2", "8"]), [("bltu", ["x2", "x1", "8"])])

    def test_bleu(self):
        self.assertEqual(expand_pseudo("bleu", ["x1", "x2", "8"]), [("bgeu", ["x2", "x1", "8"])])

    def test_zero_compare_family(self):
        self.assertEqual(expand_pseudo("beqz", ["x1", "8"]), [("beq", ["x1", "x0", "8"])])
        self.assertEqual(expand_pseudo("bnez", ["x1", "8"]), [("bne", ["x1", "x0", "8"])])
        self.assertEqual(expand_pseudo("blez", ["x1", "8"]), [("bge", ["x0", "x1", "8"])])
        self.assertEqual(expand_pseudo("bgez", ["x1", "8"]), [("bge", ["x1", "x0", "8"])])
        self.assertEqual(expand_pseudo("bltz", ["x1", "8"]), [("blt", ["x1", "x0", "8"])])
        self.assertEqual(expand_pseudo("bgtz", ["x1", "8"]), [("blt", ["x0", "x1", "8"])])

    def test_expanded_encodes(self):
        seq = expand_pseudo("bgt", ["x1", "x2", "8"])
        code = encode(seq[0][0], seq[0][1])
        name, ops = __import__("core.isa_rv32i", fromlist=["decode"]).decode(code)
        self.assertEqual((name, ops), ("blt", ["x2", "x1", "8"]))


class LiTests(unittest.TestCase):
    def test_li_small(self):
        self.assertEqual(expand_pseudo("li", ["x5", "10"]), [("addi", ["x5", "x0", "10"])])

    def test_li_negative_small(self):
        self.assertEqual(expand_pseudo("li", ["x5", "-1"]), [("addi", ["x5", "x0", "-1"])])

    def test_li_large_positive(self):
        seq = expand_pseudo("li", ["x5", "0x12345678"])
        self.assertEqual(len(seq), 2)
        self.assertEqual(seq[0][0], "lui")
        self.assertEqual(seq[1][0], "addi")

    def test_li_composed_value(self):
        """展开序列模拟执行后必须还原原始立即数。"""
        cases = [
            0, 1, -1, 10, -10, 2047, 2048, -2048, -2049,
            0x12345678, 0x7FFFFFFF, -0x80000000, -70000, 0xFFFFF000, 1 << 31,
        ]
        for imm in cases:
            with self.subTest(imm=imm):
                seq = expand_pseudo("li", ["x5", str(imm)])
                self.assertEqual(_li_value(seq), imm & 0xFFFFFFFF, f"li x5, {imm}")

    def test_li_hex_lower_overflow(self):
        # 低 12 位 >= 0x800 时需要进位修正
        seq = expand_pseudo("li", ["x5", "0x12345F78"])
        self.assertEqual(len(seq), 2)
        lui_imm = parse_int(seq[0][1][1])
        addi_imm = parse_int(seq[1][1][2])
        self.assertEqual(lui_imm, 0x12346)   # 0x12345 + 1
        self.assertEqual(addi_imm, -136)     # 0xF78 - 0x1000


class LaTests(unittest.TestCase):
    def test_la_numeric_small(self):
        self.assertEqual(expand_pseudo("la", ["x5", "0x100"]), [("addi", ["x5", "x0", "256"])])

    def test_la_numeric_large(self):
        seq = expand_pseudo("la", ["x5", "0x12345678"])
        self.assertEqual([m for m, _ in seq], ["lui", "addi"])

    def test_la_label_rejected_outside_convert_page(self):
        with self.assertRaises(ValueError):
            expand_pseudo("la", ["x5", "array"])


if __name__ == "__main__":
    unittest.main()
