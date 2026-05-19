import re
from typing import Optional


RV32I_INSTRUCTIONS = {
    "add": {"type": "R", "opcode": 0b0110011, "funct3": 0b000, "funct7": 0b0000000},
    "sub": {"type": "R", "opcode": 0b0110011, "funct3": 0b000, "funct7": 0b0100000},
    "and": {"type": "R", "opcode": 0b0110011, "funct3": 0b111, "funct7": 0b0000000},
    "or": {"type": "R", "opcode": 0b0110011, "funct3": 0b110, "funct7": 0b0000000},
    "xor": {"type": "R", "opcode": 0b0110011, "funct3": 0b100, "funct7": 0b0000000},
    "sll": {"type": "R", "opcode": 0b0110011, "funct3": 0b001, "funct7": 0b0000000},
    "srl": {"type": "R", "opcode": 0b0110011, "funct3": 0b101, "funct7": 0b0000000},
    "sra": {"type": "R", "opcode": 0b0110011, "funct3": 0b101, "funct7": 0b0100000},
    "addi": {"type": "I", "opcode": 0b0010011, "funct3": 0b000},
    "andi": {"type": "I", "opcode": 0b0010011, "funct3": 0b111},
    "ori": {"type": "I", "opcode": 0b0010011, "funct3": 0b110},
    "xori": {"type": "I", "opcode": 0b0010011, "funct3": 0b100},
    "slli": {"type": "I", "opcode": 0b0010011, "funct3": 0b001, "funct7": 0b0000000},
    "srli": {"type": "I", "opcode": 0b0010011, "funct3": 0b101, "funct7": 0b0000000},
    "srai": {"type": "I", "opcode": 0b0010011, "funct3": 0b101, "funct7": 0b0100000},
    "lw": {"type": "I_LOAD", "opcode": 0b0000011, "funct3": 0b010},
    "sw": {"type": "S", "opcode": 0b0100011, "funct3": 0b010},
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
}


def parse_register(reg_str: str) -> int:
    reg_str = reg_str.strip().lower()
    if reg_str.startswith("x"):
        return int(reg_str[1:])
    elif reg_str == "zero":
        return 0
    elif reg_str == "ra":
        return 1
    elif reg_str == "sp":
        return 2
    elif reg_str == "gp":
        return 3
    elif reg_str == "tp":
        return 4
    elif reg_str.startswith("t") and reg_str[1:].isdigit():
        num = int(reg_str[1:])
        if num <= 2:
            return 5 + num
        elif num <= 6:
            return 25 + (num - 3)
        else:
            raise ValueError(f"Invalid register: {reg_str}")
    elif reg_str.startswith("s") and reg_str[1:].isdigit():
        num = int(reg_str[1:])
        if num == 0:
            return 8
        elif num <= 11:
            return 8 + num
        else:
            raise ValueError(f"Invalid register: {reg_str}")
    elif reg_str.startswith("a") and reg_str[1:].isdigit():
        num = int(reg_str[1:])
        if num <= 7:
            return 10 + num
        else:
            raise ValueError(f"Invalid register: {reg_str}")
    else:
        raise ValueError(f"Unknown register: {reg_str}")


def parse_immediate(imm_str: str, bits: int = 12) -> int:
    imm_str = imm_str.strip().lower()
    if imm_str.startswith("0x"):
        value = int(imm_str, 16)
    elif imm_str.startswith("-0x"):
        value = -int(imm_str[1:], 16)
    else:
        value = int(imm_str)

    if value < 0:
        value = (1 << bits) + value

    return value & ((1 << bits) - 1)


def encode(name: str, operands: list[str]) -> int:
    name = name.lower()

    if name not in RV32I_INSTRUCTIONS:
        raise ValueError(f"Unknown instruction: {name}")

    inst_info = RV32I_INSTRUCTIONS[name]
    inst_type = inst_info["type"]
    opcode = inst_info["opcode"]

    if inst_type == "R":
        rd = parse_register(operands[0])
        rs1 = parse_register(operands[1])
        rs2 = parse_register(operands[2])
        funct3 = inst_info["funct3"]
        funct7 = inst_info["funct7"]
        return (funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode

    elif inst_type == "I":
        rd = parse_register(operands[0])
        rs1 = parse_register(operands[1])
        imm = parse_immediate(operands[2], 12)
        funct3 = inst_info["funct3"]
        if name in ("slli", "srli", "srai"):
            funct7 = inst_info.get("funct7", 0)
            shamt = imm & 0x1F
            return (funct7 << 25) | (shamt << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode
        return (imm << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode

    elif inst_type == "I_LOAD":
        match = re.match(r"(-?\d+|0x[0-9a-fA-F]+|-0x[0-9a-fA-F]+)\s*\(\s*(\w+)\s*\)", operands[1])
        if match:
            imm_str = match.group(1)
            rs1_str = match.group(2)
        else:
            raise ValueError(f"Invalid load format: {operands[1]}")

        rd = parse_register(operands[0])
        rs1 = parse_register(rs1_str)
        imm = parse_immediate(imm_str, 12)
        funct3 = inst_info["funct3"]
        return (imm << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode

    elif inst_type == "I_JALR":
        rd = parse_register(operands[0])
        match = re.match(r"(-?\d+|0x[0-9a-fA-F]+|-0x[0-9a-fA-F]+)\s*\(\s*(\w+)\s*\)", operands[1])
        if match:
            imm_str = match.group(1)
            rs1_str = match.group(2)
        else:
            parts = operands[1].split("(")
            imm_str = parts[0].strip()
            rs1_str = parts[1].rstrip(")").strip()

        rs1 = parse_register(rs1_str)
        imm = parse_immediate(imm_str, 12)
        funct3 = inst_info["funct3"]
        return (imm << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode

    elif inst_type == "S":
        match = re.match(r"(\w+)\s*,\s*(-?\d+|0x[0-9a-fA-F]+|-0x[0-9a-fA-F]+)\s*\(\s*(\w+)\s*\)", f"{operands[0]}, {operands[1]}")
        if match:
            rs2_str = match.group(1)
            imm_str = match.group(2)
            rs1_str = match.group(3)
        else:
            raise ValueError(f"Invalid store format")

        rs2 = parse_register(rs2_str)
        rs1 = parse_register(rs1_str)
        imm = parse_immediate(imm_str, 12)
        funct3 = inst_info["funct3"]

        imm_11_5 = (imm >> 5) & 0x7F
        imm_4_0 = imm & 0x1F
        return (imm_11_5 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (imm_4_0 << 7) | opcode

    elif inst_type == "B":
        rs1 = parse_register(operands[0])
        rs2 = parse_register(operands[1])
        imm = parse_immediate(operands[2], 13)
        funct3 = inst_info["funct3"]

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
        rd = parse_register(operands[0])
        imm = parse_immediate(operands[1], 32)
        imm_31_12 = (imm >> 12) & 0xFFFFF
        return (imm_31_12 << 12) | (rd << 7) | opcode

    elif inst_type == "J":
        rd = parse_register(operands[0])
        imm = parse_immediate(operands[1], 21)

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

    raise ValueError(f"Unknown instruction type: {inst_type}")


def decode(machine_code: int) -> tuple[Optional[str], list[str]]:
    opcode = machine_code & 0x7F

    name = None
    for inst_name, inst_info in RV32I_INSTRUCTIONS.items():
        if inst_info["opcode"] == opcode:
            name = inst_name
            break

    if name is None:
        return (None, [])

    inst_info = RV32I_INSTRUCTIONS[name]
    inst_type = inst_info["type"]

    rd = (machine_code >> 7) & 0x1F
    funct3 = (machine_code >> 12) & 0x7
    rs1 = (machine_code >> 15) & 0x1F
    rs2 = (machine_code >> 20) & 0x1F

    operands = []

    if inst_type == "R":
        funct7 = (machine_code >> 25) & 0x7F
        for inst_name, inst in RV32I_INSTRUCTIONS.items():
            if inst["type"] == "R" and inst["opcode"] == opcode and inst["funct3"] == funct3:
                if inst["funct7"] == funct7:
                    name = inst_name
                    break
        operands = [f"x{rd}", f"x{rs1}", f"x{rs2}"]

    elif inst_type in ("I", "I_JALR"):
        imm = (machine_code >> 20) & 0xFFF
        if imm & 0x800:
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
        imm_31_12 = (machine_code >> 12) & 0xFFFFF
        imm = imm_31_12 << 12
        operands = [f"x{rd}", str(imm)]

    elif inst_type == "J":
        imm_20 = (machine_code >> 31) & 0x1
        imm_10_1 = (machine_code >> 21) & 0x3FF
        imm_11 = (machine_code >> 20) & 0x1
        imm_19_12 = (machine_code >> 12) & 0xFF

        imm = (imm_20 << 20) | (imm_19_12 << 12) | (imm_11 << 11) | (imm_10_1 << 1)
        if imm & 0x100000:
            imm = imm - 0x200000
        operands = [f"x{rd}", str(imm)]

    return (name, operands)


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

    elif name == "seqz":
        return [("sltiu", [operands[0], operands[1], "1"])]

    elif name == "snez":
        return [("sltu", [operands[0], "x0", operands[1]])]

    elif name == "sltz":
        return [("slt", [operands[0], operands[1], "x0"])]

    elif name == "sgtz":
        return [("slt", [operands[0], "x0", operands[1]])]

    elif name == "li":
        rd = operands[0]
        imm_str = operands[1].strip().lower()

        if imm_str.startswith("0x"):
            imm = int(imm_str, 16)
        elif imm_str.startswith("-0x"):
            imm = -int(imm_str[1:], 16)
        else:
            imm = int(imm_str)

        if -2048 <= imm <= 2047:
            return [("addi", [rd, "x0", str(imm)])]
        elif 0 <= imm <= 0xFFFFF:
            upper = (imm >> 12) & 0xFFFFF
            lower = imm & 0xFFF
            if lower == 0:
                return [("lui", [rd, str(upper)])]
            else:
                result = [("lui", [rd, str(upper)])]
                if lower & 0x800:
                    lower = lower - 0x1000
                result.append(("addi", [rd, rd, str(lower)]))
                return result
        else:
            upper = (imm >> 12) & 0xFFFFF
            lower = imm & 0xFFF
            result = [("lui", [rd, str(upper)])]
            if lower & 0x800:
                lower = lower - 0x1000
            result.append(("addi", [rd, rd, str(lower)]))
            return result

    elif name == "la":
        rd = operands[0]
        return [("lui", [rd, "0"]), ("addi", [rd, rd, "0"])]

    return [(name, operands)]


TYPE_FRIENDLY = {
    "R": "R-type",
    "I": "I-type",
    "I_LOAD": "I-type (Load)",
    "I_JALR": "I-type (JALR)",
    "S": "S-type",
    "B": "B-type",
    "U": "U-type",
    "J": "J-type",
}


def get_format(name: str) -> str:
    name = name.lower()
    if name in PSEUDO_INSTRUCTIONS:
        return "Pseudo"
    if name not in RV32I_INSTRUCTIONS:
        return "Unknown"
    raw_type = RV32I_INSTRUCTIONS[name]["type"]
    return TYPE_FRIENDLY.get(raw_type, raw_type)
