import re
from typing import Optional


RV32I_INSTRUCTIONS = {
    "add": {"type": "R", "opcode": 0b0110011, "funct3": 0b000, "funct7": 0b0000000},
    "sub": {"type": "R", "opcode": 0b0110011, "funct3": 0b000, "funct7": 0b0100000},
    "and": {"type": "R", "opcode": 0b0110011, "funct3": 0b111, "funct7": 0b0000000},
    "or": {"type": "R", "opcode": 0b0110011, "funct3": 0b110, "funct7": 0b0000000},
    "xor": {"type": "R", "opcode": 0b0110011, "funct3": 0b100, "funct7": 0b0000000},
    "sll": {"type": "R", "opcode": 0b0110011, "funct3": 0b001, "funct7": 0b0000000},
    "slt": {"type": "R", "opcode": 0b0110011, "funct3": 0b010, "funct7": 0b0000000},
    "sltu": {"type": "R", "opcode": 0b0110011, "funct3": 0b011, "funct7": 0b0000000},
    "srl": {"type": "R", "opcode": 0b0110011, "funct3": 0b101, "funct7": 0b0000000},
    "sra": {"type": "R", "opcode": 0b0110011, "funct3": 0b101, "funct7": 0b0100000},
    "addi": {"type": "I", "opcode": 0b0010011, "funct3": 0b000},
    "andi": {"type": "I", "opcode": 0b0010011, "funct3": 0b111},
    "ori": {"type": "I", "opcode": 0b0010011, "funct3": 0b110},
    "xori": {"type": "I", "opcode": 0b0010011, "funct3": 0b100},
    "slti": {"type": "I", "opcode": 0b0010011, "funct3": 0b010},
    "sltiu": {"type": "I", "opcode": 0b0010011, "funct3": 0b011},
    "slli": {"type": "I", "opcode": 0b0010011, "funct3": 0b001, "funct7": 0b0000000},
    "srli": {"type": "I", "opcode": 0b0010011, "funct3": 0b101, "funct7": 0b0000000},
    "srai": {"type": "I", "opcode": 0b0010011, "funct3": 0b101, "funct7": 0b0100000},
    "lb":  {"type": "I_LOAD", "opcode": 0b0000011, "funct3": 0b000},
    "lh":  {"type": "I_LOAD", "opcode": 0b0000011, "funct3": 0b001},
    "lw":  {"type": "I_LOAD", "opcode": 0b0000011, "funct3": 0b010},
    "lbu": {"type": "I_LOAD", "opcode": 0b0000011, "funct3": 0b100},
    "lhu": {"type": "I_LOAD", "opcode": 0b0000011, "funct3": 0b101},
    "sb":  {"type": "S", "opcode": 0b0100011, "funct3": 0b000},
    "sh":  {"type": "S", "opcode": 0b0100011, "funct3": 0b001},
    "sw":  {"type": "S", "opcode": 0b0100011, "funct3": 0b010},
    "beq": {"type": "B", "opcode": 0b1100011, "funct3": 0b000},
    "bne": {"type": "B", "opcode": 0b1100011, "funct3": 0b001},
    "blt": {"type": "B", "opcode": 0b1100011, "funct3": 0b100},
    "bge": {"type": "B", "opcode": 0b1100011, "funct3": 0b101},
    "bltu": {"type": "B", "opcode": 0b1100011, "funct3": 0b110},
    "bgeu": {"type": "B", "opcode": 0b1100011, "funct3": 0b111},
    "jal": {"type": "J", "opcode": 0b1101111},
    "jalr": {"type": "I_JALR", "opcode": 0b1100111, "funct3": 0b000},
    "lui": {"type": "U", "opcode": 0b0110111},
    "auipc": {"type": "U", "opcode": 0b0010111},
    # 系统指令
    "ecall":  {"type": "I_SYSTEM", "opcode": 0b1110011, "funct3": 0b000, "imm12": 0x000},
    "ebreak": {"type": "I_SYSTEM", "opcode": 0b1110011, "funct3": 0b000, "imm12": 0x001},
    # 内存屏障
    "fence":  {"type": "I_FENCE", "opcode": 0b0001111, "funct3": 0b000},
    # CSR 指令
    "csrrw":  {"type": "I_CSR", "opcode": 0b1110011, "funct3": 0b001},
    "csrrs":  {"type": "I_CSR", "opcode": 0b1110011, "funct3": 0b010},
    "csrrc":  {"type": "I_CSR", "opcode": 0b1110011, "funct3": 0b011},
    "csrrwi": {"type": "I_CSR", "opcode": 0b1110011, "funct3": 0b101},
    "csrrsi": {"type": "I_CSR", "opcode": 0b1110011, "funct3": 0b110},
    "csrrci": {"type": "I_CSR", "opcode": 0b1110011, "funct3": 0b111},
}

PSEUDO_INSTRUCTIONS = {
    "li": "li",
    "mv": "mv",
    "not": "not",
    "neg": "neg",
    "la": "la",
    "nop": "nop",
    "unimp": "unimp",
    "ret": "ret",
    "call": "call",
    "tail": "tail",
    "j": "j",
    "jr": "jr",
    "jalr": "jalr_pseudo",
    "beqz": "beqz",
    "bnez": "bnez",
    "blez": "blez",
    "bgez": "bgez",
    "bltz": "bltz",
    "bgtz": "bgtz",
    "seqz": "seqz",
    "snez": "snez",
    "sltz": "sltz",
    "sgtz": "sgtz",
    "bgt": "bgt",
    "ble": "ble",
    "bgtu": "bgtu",
    "bleu": "bleu",
}

# ABI 别名 → 寄存器编号
REG_ALIASES = {
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

_MEM_RE = re.compile(r"^(.+?)\s*\(\s*([A-Za-z]\w*)\s*\)$")
_FENCE_BITS = {"i": 1, "o": 2, "r": 4, "w": 8}
_FENCE_ORDER = (("i", 1), ("o", 2), ("r", 4), ("w", 8))


def parse_register(reg_str: str) -> int:
    t = reg_str.strip().lower()
    if t.startswith("x") and t[1:].isdigit():
        n = int(t[1:])
        if 0 <= n <= 31:
            return n
        raise ValueError(f"无效寄存器: {reg_str} (范围 x0-x31)")
    if t in REG_ALIASES:
        return REG_ALIASES[t]
    raise ValueError(f"无效寄存器: {reg_str}")


def parse_int(imm_str: str) -> int:
    """解析整数字面量，支持十进制 / 0x 十六进制 / 0b 二进制，可带正负号与下划线分隔。"""
    t = str(imm_str).strip().lower().replace("_", "")
    neg = False
    if t.startswith("+"):
        t = t[1:]
    elif t.startswith("-"):
        neg = True
        t = t[1:]
    try:
        if t.startswith("0x"):
            v = int(t, 16)
        elif t.startswith("0b"):
            v = int(t, 2)
        else:
            v = int(t, 10)
    except ValueError:
        raise ValueError(f"无效立即数: {imm_str}")
    return -v if neg else v


def parse_immediate(imm_str: str, bits: int = 12) -> int:
    return parse_int(imm_str) & ((1 << bits) - 1)


def _imm_checked(imm_str: str, lo: int, hi: int, what: str) -> int:
    v = parse_int(imm_str)
    if not (lo <= v <= hi):
        raise ValueError(f"立即数 {imm_str} 超出{what}范围 [{lo}, {hi}]")
    return v


def _parse_mem(operand: str) -> tuple[str, str]:
    """解析 imm(rs) 形式的内存操作数，返回 (imm_str, reg_str)。"""
    m = _MEM_RE.match(operand.strip())
    if not m:
        raise ValueError(f"无效的内存操作数: {operand} (应为 imm(rs) 格式)")
    return m.group(1), m.group(2)


def _parse_fence_bits(tok: str) -> int:
    t = tok.strip().lower()
    if t and all(c in "iorw" for c in t):
        return sum(_FENCE_BITS[c] for c in t)
    v = parse_int(tok)
    if not (0 <= v <= 15):
        raise ValueError(f"fence 掩码 {tok} 超出范围 [0, 15]")
    return v


def _fence_bits_to_str(bits: int) -> str:
    if bits == 0:
        return "0"
    return "".join(c for c, b in _FENCE_ORDER if bits & b)


def _need(operands: list, n: int, usage: str):
    if len(operands) < n:
        raise ValueError(f"操作数不足，用法: {usage}")


def encode(name: str, operands: list[str]) -> int:
    name = name.lower()

    if name not in RV32I_INSTRUCTIONS:
        raise ValueError(f"未知指令: {name}")

    inst_info = RV32I_INSTRUCTIONS[name]
    inst_type = inst_info["type"]
    opcode = inst_info["opcode"]

    if inst_type == "R":
        _need(operands, 3, "add rd, rs1, rs2")
        rd = parse_register(operands[0])
        rs1 = parse_register(operands[1])
        rs2 = parse_register(operands[2])
        funct3 = inst_info["funct3"]
        funct7 = inst_info["funct7"]
        return (funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode

    elif inst_type == "I":
        _need(operands, 3, "addi rd, rs1, imm")
        rd = parse_register(operands[0])
        rs1 = parse_register(operands[1])
        funct3 = inst_info["funct3"]
        if name in ("slli", "srli", "srai"):
            shamt = _imm_checked(operands[2], 0, 31, "移位量")
            funct7 = inst_info["funct7"]
            return (funct7 << 25) | (shamt << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode
        imm = _imm_checked(operands[2], -2048, 2047, "I型立即数")
        return ((imm & 0xFFF) << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode

    elif inst_type == "I_LOAD":
        _need(operands, 2, "lw rd, imm(rs1)")
        rd = parse_register(operands[0])
        imm_str, rs1_str = _parse_mem(operands[1])
        rs1 = parse_register(rs1_str)
        imm = _imm_checked(imm_str, -2048, 2047, "访存偏移")
        funct3 = inst_info["funct3"]
        return ((imm & 0xFFF) << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode

    elif inst_type == "I_JALR":
        _need(operands, 2, "jalr rd, imm(rs1)")
        rd = parse_register(operands[0])
        # 支持两种格式：
        # 1. jalr rd, imm(rs1)    — 用户输入格式
        # 2. jalr rd, rs1, imm    — 伪指令展开格式（如 ret → jalr x0, x1, 0）
        if len(operands) >= 3:
            rs1 = parse_register(operands[1])
            imm = _imm_checked(operands[2], -2048, 2047, "jalr偏移")
        else:
            imm_str, rs1_str = _parse_mem(operands[1])
            rs1 = parse_register(rs1_str)
            imm = _imm_checked(imm_str, -2048, 2047, "jalr偏移")
        funct3 = inst_info["funct3"]
        return ((imm & 0xFFF) << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode

    elif inst_type == "S":
        _need(operands, 2, "sw rs2, imm(rs1)")
        rs2 = parse_register(operands[0])
        imm_str, rs1_str = _parse_mem(operands[1])
        rs1 = parse_register(rs1_str)
        imm = _imm_checked(imm_str, -2048, 2047, "访存偏移")
        funct3 = inst_info["funct3"]

        imm &= 0xFFF
        imm_11_5 = (imm >> 5) & 0x7F
        imm_4_0 = imm & 0x1F
        return (imm_11_5 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (imm_4_0 << 7) | opcode

    elif inst_type == "B":
        _need(operands, 3, "beq rs1, rs2, offset")
        rs1 = parse_register(operands[0])
        rs2 = parse_register(operands[1])
        off = _imm_checked(operands[2], -4096, 4094, "分支偏移")
        if off & 1:
            raise ValueError(f"分支偏移 {operands[2]} 必须是 2 的倍数")
        funct3 = inst_info["funct3"]

        imm = off & 0x1FFF
        imm_12 = (imm >> 12) & 0x1
        imm_10_5 = (imm >> 5) & 0x3F
        imm_4_1 = (imm >> 1) & 0xF
        imm_11 = (imm >> 11) & 0x1

        return (
            (imm_12 << 31)
            | (imm_10_5 << 25)
            | (rs2 << 20)
            | (rs1 << 15)
            | (funct3 << 12)
            | (imm_4_1 << 8)
            | (imm_11 << 7)
            | opcode
        )

    elif inst_type == "U":
        _need(operands, 2, "lui rd, imm20")
        rd = parse_register(operands[0])
        # U 型立即数是 20 位：lui x10, 0x12345 → rd = 0x12345000
        v = _imm_checked(operands[1], -524288, 1048575, "U型立即数(20位)")
        imm_31_12 = v & 0xFFFFF
        return (imm_31_12 << 12) | (rd << 7) | opcode

    elif inst_type == "J":
        _need(operands, 2, "jal rd, offset")
        rd = parse_register(operands[0])
        off = _imm_checked(operands[1], -1048576, 1048574, "跳转偏移")
        if off & 1:
            raise ValueError(f"跳转偏移 {operands[1]} 必须是 2 的倍数")

        imm = off & 0x1FFFFF
        imm_20 = (imm >> 20) & 0x1
        imm_10_1 = (imm >> 1) & 0x3FF
        imm_11 = (imm >> 11) & 0x1
        imm_19_12 = (imm >> 12) & 0xFF

        return (
            (imm_20 << 31)
            | (imm_10_1 << 21)
            | (imm_11 << 20)
            | (imm_19_12 << 12)
            | (rd << 7)
            | opcode
        )

    elif inst_type == "I_SYSTEM":
        imm12 = inst_info.get("imm12", 0)
        return (imm12 << 20) | opcode

    elif inst_type == "I_CSR":
        _need(operands, 3, "csrrw rd, csr, rs1")
        rd = parse_register(operands[0])
        csr = _imm_checked(operands[1], 0, 4095, "CSR地址")
        csr_funct3 = inst_info["funct3"]
        if csr_funct3 in (0b101, 0b110, 0b111):
            # csrrwi/csrrsi/csrrci: 使用 5 位无符号立即数 (zimm)
            zimm = _imm_checked(operands[2], 0, 31, "zimm")
            rs1_or_zimm = zimm & 0x1F
        else:
            rs1_or_zimm = parse_register(operands[2])
        return (csr << 20) | (rs1_or_zimm << 15) | (csr_funct3 << 12) | (rd << 7) | opcode

    elif inst_type == "I_FENCE":
        if not operands or all(not o.strip() for o in operands):
            pred = succ = 0xF  # fence 等价于 fence iorw, iorw
        else:
            _need(operands, 2, "fence pred, succ")
            pred = _parse_fence_bits(operands[0])
            succ = _parse_fence_bits(operands[1])
        fence_imm = ((pred & 0xF) << 4) | (succ & 0xF)
        return (fence_imm << 20) | (inst_info["funct3"] << 12) | opcode

    raise ValueError(f"未知指令类型: {inst_type}")


def decode(machine_code: int) -> tuple[Optional[str], list[str]]:
    opcode = machine_code & 0x7F
    funct3 = (machine_code >> 12) & 0x7
    funct7 = (machine_code >> 25) & 0x7F
    rd = (machine_code >> 7) & 0x1F
    rs1 = (machine_code >> 15) & 0x1F
    rs2 = (machine_code >> 20) & 0x1F

    # 精确匹配指令：opcode + funct3(若有) + funct7(R型/移位I型) + imm12(SYSTEM)
    matched_name = None
    matched_info = None
    for inst_name, inst_info in RV32I_INSTRUCTIONS.items():
        if inst_info["opcode"] != opcode:
            continue
        if "funct3" in inst_info and inst_info["funct3"] != funct3:
            continue
        inst_type = inst_info["type"]
        if inst_type == "I_SYSTEM":
            # ecall/ebreak 通过 imm12 区分，未知 SYSTEM 编码不应误判
            if inst_info.get("imm12", 0) != ((machine_code >> 20) & 0xFFF):
                continue
        if inst_type == "R" or (inst_type == "I" and "funct7" in inst_info):
            if inst_info.get("funct7", -1) != funct7:
                continue
        matched_name = inst_name
        matched_info = inst_info
        break

    if matched_name is None:
        return (None, [])

    inst_type = matched_info["type"]
    operands = []

    if inst_type == "R":
        operands = [f"x{rd}", f"x{rs1}", f"x{rs2}"]
    elif inst_type in ("I", "I_JALR"):
        imm = (machine_code >> 20) & 0xFFF
        if matched_info is not None and "funct7" in matched_info:
            # 移位指令（slli/srli/srai）：输出 5 位 shamt 而非原始 imm12
            imm = imm & 0x1F
        elif imm & 0x800:
            imm = imm - 0x1000
        operands = [f"x{rd}", f"x{rs1}", str(imm)]
    elif inst_type == "I_LOAD":
        imm = (machine_code >> 20) & 0xFFF
        if imm & 0x800:
            imm = imm - 0x1000
        operands = [f"x{rd}", f"{imm}(x{rs1})"]
    elif inst_type == "S":
        imm_4_0 = (machine_code >> 7) & 0x1F
        imm_11_5 = (machine_code >> 25) & 0x7F
        imm = (imm_11_5 << 5) | imm_4_0
        if imm & 0x800:
            imm = imm - 0x1000
        operands = [f"x{rs2}", f"{imm}(x{rs1})"]
    elif inst_type == "B":
        imm_12 = (machine_code >> 31) & 0x1
        imm_10_5 = (machine_code >> 25) & 0x3F
        imm_4_1 = (machine_code >> 8) & 0xF
        imm_11 = (machine_code >> 7) & 0x1
        imm = (imm_12 << 12) | (imm_11 << 11) | (imm_10_5 << 5) | (imm_4_1 << 1)
        if imm & 0x1000:
            imm = imm - 0x2000
        operands = [f"x{rs1}", f"x{rs2}", str(imm)]
    elif inst_type == "U":
        # 反汇编输出 20 位立即数（与汇编输入约定一致），如 lui x10, 0x12345
        imm_31_12 = (machine_code >> 12) & 0xFFFFF
        operands = [f"x{rd}", f"0x{imm_31_12:x}"]
    elif inst_type == "J":
        imm_20 = (machine_code >> 31) & 0x1
        imm_10_1 = (machine_code >> 21) & 0x3FF
        imm_11 = (machine_code >> 20) & 0x1
        imm_19_12 = (machine_code >> 12) & 0xFF
        imm = (imm_20 << 20) | (imm_19_12 << 12) | (imm_11 << 11) | (imm_10_1 << 1)
        if imm & 0x100000:
            imm = imm - 0x200000
        operands = [f"x{rd}", str(imm)]

    elif inst_type == "I_SYSTEM":
        operands = []

    elif inst_type == "I_CSR":
        csr = (machine_code >> 20) & 0xFFF
        csr_funct3 = matched_info["funct3"]
        if csr_funct3 in (0b101, 0b110, 0b111):
            zimm = rs1 & 0x1F
            operands = [f"x{rd}", str(csr), str(zimm)]
        else:
            operands = [f"x{rd}", str(csr), f"x{rs1}"]

    elif inst_type == "I_FENCE":
        imm_val = (machine_code >> 20) & 0xFFF
        pred = (imm_val >> 4) & 0xF
        succ = imm_val & 0xF
        operands = [_fence_bits_to_str(pred), _fence_bits_to_str(succ)]

    return (matched_name, operands)


def is_pseudo(name: str) -> bool:
    return name.lower() in PSEUDO_INSTRUCTIONS


def expand_pseudo(name: str, operands: list[str]) -> list[tuple[str, list[str]]]:
    name = name.lower()

    if name == "mv":
        return [("addi", [operands[0], operands[1], "0"])]

    elif name == "not":
        return [("xori", [operands[0], operands[1], "-1"])]

    elif name == "neg":
        return [("sub", [operands[0], "x0", operands[1]])]

    elif name == "nop":
        return [("addi", ["x0", "x0", "0"])]

    elif name == "unimp":
        return [("addi", ["x0", "x0", "0"])]

    elif name == "ret":
        return [("jalr", ["x0", "x1", "0"])]

    elif name == "jr":
        return [("jalr", ["x0", operands[0], "0"])]

    elif name == "jalr_pseudo":
        if len(operands) == 1:
            return [("jalr", ["x1", operands[0], "0"])]
        elif len(operands) == 2:
            return [("jalr", [operands[0], operands[1], "0"])]
        return [("jalr", operands)]

    elif name == "j":
        return [("jal", ["x0", operands[0]])]

    elif name == "call":
        # 数值偏移的近距离调用；标签形式由转码页两遍汇编展开为 auipc + jalr
        return [("jal", ["x1", operands[0]])]

    elif name == "tail":
        return [("jal", ["x0", operands[0]])]

    elif name == "beqz":
        return [("beq", [operands[0], "x0", operands[1]])]

    elif name == "bnez":
        return [("bne", [operands[0], "x0", operands[1]])]

    elif name == "blez":
        return [("bge", ["x0", operands[0], operands[1]])]

    elif name == "bgez":
        return [("bge", [operands[0], "x0", operands[1]])]

    elif name == "bltz":
        return [("blt", [operands[0], "x0", operands[1]])]

    elif name == "bgtz":
        return [("blt", ["x0", operands[0], operands[1]])]

    elif name == "bgt":
        return [("blt", [operands[1], operands[0], operands[2]])]

    elif name == "ble":
        return [("bge", [operands[1], operands[0], operands[2]])]

    elif name == "bgtu":
        return [("bltu", [operands[1], operands[0], operands[2]])]

    elif name == "bleu":
        return [("bgeu", [operands[1], operands[0], operands[2]])]

    elif name == "seqz":
        return [("sltiu", [operands[0], operands[1], "1"])]

    elif name == "snez":
        return [("sltu", [operands[0], "x0", operands[1]])]

    elif name == "sltz":
        return [("slt", [operands[0], operands[1], "x0"])]

    elif name == "sgtz":
        return [("slt", [operands[0], "x0", operands[1]])]

    elif name == "li":
        return _expand_li(operands[0], operands[1])

    elif name == "la":
        # 数值地址：等价于 li；标签地址由转码页两遍汇编展开为 auipc + addi
        try:
            parse_int(operands[1])
        except ValueError:
            raise ValueError(
                f"la 需要标签支持（标签: {operands[1]}），请在转码页中使用；此处请使用数值地址"
            )
        return _expand_li(operands[0], operands[1])

    return [(name, operands)]


def _expand_li(rd: str, imm_str: str) -> list[tuple[str, list[str]]]:
    imm = parse_int(imm_str)
    if -2048 <= imm <= 2047:
        return [("addi", [rd, "x0", str(imm)])]

    v = imm & 0xFFFFFFFF
    upper = (v >> 12) & 0xFFFFF
    lower = v & 0xFFF
    if lower >= 0x800:
        upper = (upper + 1) & 0xFFFFF
        lower -= 0x1000

    seq = []
    if upper:
        seq.append(("lui", [rd, str(upper)]))
        base = rd
    else:
        base = "x0"
    if lower or not seq:
        seq.append(("addi", [rd, base, str(lower)]))
    return seq


TYPE_FRIENDLY = {
    "R": "R-type",
    "I": "I-type",
    "I_LOAD": "I-type (Load)",
    "I_JALR": "I-type (JALR)",
    "S": "S-type",
    "B": "B-type",
    "U": "U-type",
    "J": "J-type",
    "I_SYSTEM": "System",
    "I_CSR": "CSR",
    "I_FENCE": "Fence",
}


def get_format(name: str) -> str:
    name = name.lower()
    if name in PSEUDO_INSTRUCTIONS:
        return "Pseudo"
    if name not in RV32I_INSTRUCTIONS:
        return "Unknown"
    raw_type = RV32I_INSTRUCTIONS[name]["type"]
    return TYPE_FRIENDLY.get(raw_type, raw_type)
