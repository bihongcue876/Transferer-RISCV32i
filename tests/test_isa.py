"""RV32I 编码/解码核心测试：寄存器映射、已知向量、立即数校验、往返一致性。"""
import unittest

from core.isa_rv32i import (
    parse_register,
    parse_int,
    parse_immediate,
    encode,
    decode,
    get_format,
)


class RegisterTests(unittest.TestCase):
    def test_numeric_all_32(self):
        for i in range(32):
            self.assertEqual(parse_register(f"x{i}"), i)

    def test_abi_names(self):
        abi = {
            "zero": 0, "ra": 1, "sp": 2, "gp": 3, "tp": 4,
            "t0": 5, "t1": 6, "t2": 7,
            "s0": 8, "fp": 8, "s1": 9,
            "a0": 10, "a1": 11, "a2": 12, "a3": 13,
            "a4": 14, "a5": 15, "a6": 16, "a7": 17,
            "s2": 18, "s3": 19, "s4": 20, "s5": 21,
            "s6": 22, "s7": 23, "s8": 24, "s9": 25,
            "s10": 26, "s11": 27,
            "t3": 28, "t4": 29, "t5": 30, "t6": 31,
        }
        for name, num in abi.items():
            self.assertEqual(parse_register(name), num, f"寄存器 {name} 应为 x{num}")

    def test_case_insensitive(self):
        self.assertEqual(parse_register("RA"), 1)
        self.assertEqual(parse_register(" ZERO "), 0)

    def test_invalid(self):
        for bad in ("x32", "x-1", "t7", "s12", "a8", "foo", "x"):
            with self.assertRaises(ValueError, msg=bad):
                parse_register(bad)


class ParseIntTests(unittest.TestCase):
    def test_decimal(self):
        self.assertEqual(parse_int("10"), 10)
        self.assertEqual(parse_int("-2048"), -2048)
        self.assertEqual(parse_int("+5"), 5)

    def test_hex(self):
        self.assertEqual(parse_int("0x1F"), 31)
        self.assertEqual(parse_int("-0x10"), -16)

    def test_binary(self):
        self.assertEqual(parse_int("0b101"), 5)
        self.assertEqual(parse_int("-0b101"), -5)

    def test_underscore(self):
        self.assertEqual(parse_int("0x12_34"), 0x1234)

    def test_invalid(self):
        for bad in ("abc", "0x", "1x", ""):
            with self.assertRaises(ValueError, msg=bad):
                parse_int(bad)

    def test_parse_immediate_masks(self):
        self.assertEqual(parse_immediate("-1", 12), 0xFFF)
        self.assertEqual(parse_immediate("0xFFF", 12), 0xFFF)


class KnownVectorTests(unittest.TestCase):
    """教科书标准编码向量。"""

    def test_addi(self):
        self.assertEqual(encode("addi", ["x1", "x0", "10"]), 0x00A00093)

    def test_addi_negative(self):
        self.assertEqual(encode("addi", ["x1", "x0", "-1"]), 0xFFF00093)

    def test_add(self):
        self.assertEqual(encode("add", ["x1", "x2", "x3"]), 0x003100B3)

    def test_sub(self):
        self.assertEqual(encode("sub", ["x1", "x2", "x3"]), 0x403100B3)

    def test_lw(self):
        self.assertEqual(encode("lw", ["x5", "8(x6)"]), 0x00832283)

    def test_sw(self):
        self.assertEqual(encode("sw", ["x5", "8(x6)"]), 0x00532423)

    def test_beq(self):
        self.assertEqual(encode("beq", ["x1", "x2", "8"]), 0x00208463)

    def test_jal(self):
        self.assertEqual(encode("jal", ["x1", "8"]), 0x008000EF)

    def test_lui(self):
        # 20 位立即数语义：lui x10, 0x12345 → rd = 0x12345000
        self.assertEqual(encode("lui", ["x10", "0x12345"]), 0x12345537)

    def test_auipc(self):
        self.assertEqual(encode("auipc", ["x5", "1"]), 0x00001297)

    def test_slli(self):
        self.assertEqual(encode("slli", ["x1", "x2", "3"]), 0x00311093)

    def test_ecall_ebreak(self):
        self.assertEqual(encode("ecall", []), 0x00000073)
        self.assertEqual(encode("ebreak", []), 0x00100073)

    def test_fence_default_and_iorw(self):
        self.assertEqual(encode("fence", []), 0x0FF0000F)
        self.assertEqual(encode("fence", ["iorw", "iorw"]), 0x0FF0000F)
        # pred=i(1), succ=i(1) → imm = 0x11
        self.assertEqual(encode("fence", ["i", "i"]), 0x0110000F)

    def test_csr(self):
        self.assertEqual(encode("csrrw", ["x5", "0x300", "x6"]), 0x300312F3)
        self.assertEqual(encode("csrrwi", ["x5", "0x300", "4"]), 0x300252F3)

    def test_abi_register_encoding(self):
        # add s2, s3, s4 → rd=18, rs1=19, rs2=20
        code = encode("add", ["s2", "s3", "s4"])
        self.assertEqual(code, (20 << 20) | (19 << 15) | (18 << 7) | 0x33)
        # add t3, t4, t5 → rd=28, rs1=29, rs2=30
        code = encode("add", ["t3", "t4", "t5"])
        self.assertEqual(code, (30 << 20) | (29 << 15) | (28 << 7) | 0x33)


class ImmediateRangeTests(unittest.TestCase):
    def assert_range_error(self, name, operands):
        with self.assertRaises(ValueError, msg=f"{name} {operands} 应报错"):
            encode(name, operands)

    def test_branch_range(self):
        self.assert_range_error("beq", ["x1", "x2", "4096"])
        self.assert_range_error("beq", ["x1", "x2", "-4098"])
        self.assert_range_error("beq", ["x1", "x2", "3"])  # 奇数偏移

    def test_branch_boundary_ok(self):
        encode("beq", ["x1", "x2", "4094"])
        encode("beq", ["x1", "x2", "-4096"])

    def test_jump_range(self):
        self.assert_range_error("jal", ["x1", "1048576"])
        self.assert_range_error("jal", ["x1", "-1048578"])
        self.assert_range_error("jal", ["x1", "7"])  # 奇数

    def test_jump_boundary_ok(self):
        encode("jal", ["x1", "1048574"])
        encode("jal", ["x1", "-1048576"])

    def test_i_type_range(self):
        self.assert_range_error("addi", ["x1", "x2", "2048"])
        self.assert_range_error("addi", ["x1", "x2", "-2049"])
        encode("addi", ["x1", "x2", "2047"])
        encode("addi", ["x1", "x2", "-2048"])

    def test_load_store_range(self):
        self.assert_range_error("lw", ["x1", "2048(x2)"])
        self.assert_range_error("sw", ["x1", "-2049(x2)"])

    def test_shamt_range(self):
        self.assert_range_error("slli", ["x1", "x2", "32"])
        self.assert_range_error("srai", ["x1", "x2", "-1"])
        encode("slli", ["x1", "x2", "31"])

    def test_u_type_range(self):
        self.assert_range_error("lui", ["x1", "1048576"])
        encode("lui", ["x1", "1048575"])
        encode("lui", ["x1", "-524288"])

    def test_mem_format(self):
        self.assert_range_error("lw", ["x1", "x2"])       # 缺 imm(rs)
        self.assert_range_error("sw", ["x1", "8(x32)"])   # 无效寄存器

    def test_operand_count(self):
        self.assert_range_error("add", ["x1", "x2"])
        self.assert_range_error("beq", ["x1", "x2"])
        self.assert_range_error("csrrw", ["x1", "0x300"])

    def test_unknown_instruction(self):
        self.assert_range_error("mul", ["x1", "x2", "x3"])  # 不支持 M 扩展


class DecodeTests(unittest.TestCase):
    def test_decode_addi(self):
        self.assertEqual(decode(0x00A00093), ("addi", ["x1", "x0", "10"]))

    def test_decode_r(self):
        self.assertEqual(decode(0x003100B3), ("add", ["x1", "x2", "x3"]))

    def test_decode_load_store(self):
        self.assertEqual(decode(0x00832283), ("lw", ["x5", "8(x6)"]))
        self.assertEqual(decode(0x00532423), ("sw", ["x5", "8(x6)"]))

    def test_decode_u_type(self):
        # U 型没有 funct3 字段，任何 imm 位组合都应能反汇编
        self.assertEqual(decode(0x12345537), ("lui", ["x10", "0x12345"]))
        self.assertEqual(decode(0x00001297), ("auipc", ["x5", "0x1"]))

    def test_decode_j_type(self):
        self.assertEqual(decode(0x008000EF), ("jal", ["x1", "8"]))

    def test_decode_branch(self):
        self.assertEqual(decode(0x00208463), ("beq", ["x1", "x2", "8"]))

    def test_decode_system(self):
        self.assertEqual(decode(0x00000073), ("ecall", []))
        self.assertEqual(decode(0x00100073), ("ebreak", []))
        # mret (0x302) 不在 RV32I 基础集内，不应误判为 ecall
        name, ops = decode(0x30200073)
        self.assertIsNone(name)

    def test_decode_fence(self):
        name, ops = decode(0x0FF0000F)
        self.assertEqual(name, "fence")
        self.assertEqual(ops, ["iorw", "iorw"])

    def test_decode_unknown(self):
        self.assertEqual(decode(0xFFFFFFFF), (None, []))
        self.assertEqual(decode(0x00000000), (None, []))


class RoundTripTests(unittest.TestCase):
    """encode → decode → re-encode 必须一致。"""

    CASES = [
        ("add", ["x3", "x4", "x5"]),
        ("sub", ["x8", "x9", "x10"]),
        ("and", ["x31", "x1", "x2"]),
        ("addi", ["x1", "x2", "-2048"]),
        ("addi", ["x1", "x2", "2047"]),
        ("sltiu", ["x5", "x6", "-1"]),
        ("srai", ["x1", "x2", "31"]),
        ("slli", ["x7", "x8", "0"]),
        ("lw", ["x5", "-2048(x6)"]),
        ("sw", ["x5", "2047(x6)"]),
        ("lbu", ["x1", "0(x31)"]),
        ("beq", ["x1", "x2", "-4096"]),
        ("beq", ["x1", "x2", "4094"]),
        ("bgeu", ["x8", "x9", "-4"]),
        ("bltu", ["x10", "x11", "2"]),
        ("jal", ["x1", "-1048576"]),
        ("jal", ["x0", "1048574"]),
        ("jalr", ["x1", "-2048(x5)"]),
        ("jalr", ["x0", "x1", "2047"]),
        ("lui", ["x10", "1048575"]),
        ("lui", ["x10", "0x12345"]),
        ("auipc", ["x5", "0x1"]),
        ("csrrs", ["x1", "0x300", "x2"]),
        ("csrrwi", ["x1", "0x300", "31"]),
    ]

    def test_roundtrip(self):
        for name, ops in self.CASES:
            with self.subTest(inst=name, ops=ops):
                code = encode(name, ops)
                name2, ops2 = decode(code)
                self.assertEqual(name2, name)
                code2 = encode(name2, ops2)
                self.assertEqual(code2, code)


class FormatTests(unittest.TestCase):
    def test_get_format(self):
        self.assertEqual(get_format("add"), "R-type")
        self.assertEqual(get_format("addi"), "I-type")
        self.assertEqual(get_format("lw"), "I-type (Load)")
        self.assertEqual(get_format("sw"), "S-type")
        self.assertEqual(get_format("beq"), "B-type")
        self.assertEqual(get_format("lui"), "U-type")
        self.assertEqual(get_format("jal"), "J-type")
        self.assertEqual(get_format("ecall"), "System")
        self.assertEqual(get_format("csrrw"), "CSR")
        self.assertEqual(get_format("fence"), "Fence")
        self.assertEqual(get_format("mv"), "Pseudo")
        self.assertEqual(get_format("xxx"), "Unknown")


if __name__ == "__main__":
    unittest.main()
