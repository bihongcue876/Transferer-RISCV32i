"""RISC-V 32I 学习页面 — 完整实现"""
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from core.assembler import assemble_line, disassemble_bytes

# ── PIL 可选导入（用于 PNG 图片加载） ─────────────────────
_HAS_PIL = False
Image = None
ImageTk = None
try:
    from PIL import Image as _PIL_Image, ImageTk as _PIL_ImageTk
    Image = _PIL_Image
    ImageTk = _PIL_ImageTk
    _HAS_PIL = True
except ImportError:
    pass

# ── 资源路径 ─────────────────────────────────────────────────
_RESOURCE_DIR = Path(__file__).resolve().parent.parent / "resource"

# 图片文件名映射 (设计稿名称 -> 实际文件名)
_IMAGE_MAP = {
    "allcodes.png":     "picofalltype.png",
    "typesdivision.png": "useandalgorithm.png",
    "picoftype.png":    "picofsixtypes.png",
}


def _load_image(name: str, max_width: int = 700):
    """加载 resource 目录下的 PNG 图片，等比缩放至 max_width 以内。
    需要 Pillow 支持；若无则返回 None。"""
    if not _HAS_PIL:
        return None
    real_name = _IMAGE_MAP.get(name, name)
    path = _RESOURCE_DIR / real_name
    if not path.exists():
        return None
    img = Image.open(path)
    w, h = img.size
    if w > max_width:
        ratio = max_width / w
        new_w = max_width
        new_h = int(h * ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
    return ImageTk.PhotoImage(img)


# ── 指令数据（从 LEARNINGDOC.MD 整理） ────────────────────
# 每条指令：name, desc_short, fmt, fmt_type, example,
#            machine_table（列表[行]）, explanation, imm_desc（可选）

_INSTRUCTION_LIST = [
    # ── R-type ──
    {"name":"ADD","desc_short":"寄存器加法","fmt":"R","fmt_type":"R 型","example":"add x5, x6, x7",
     "machine_table":["funct7=0000000 | rs2 | rs1 | funct3=000 | rd | opcode=0110011"],
     "explanation":"opcode=0110011, funct3=000, funct7=0000000 指示加法运算。"},
    {"name":"SUB","desc_short":"寄存器减法","fmt":"R","fmt_type":"R 型","example":"sub x8, x9, x10",
     "machine_table":["funct7=0100000 | rs2 | rs1 | funct3=000 | rd | opcode=0110011"],
     "explanation":"opcode=0110011, funct3=000, funct7=0100000 区分减法。"},
    {"name":"XOR","desc_short":"按位异或","fmt":"R","fmt_type":"R 型","example":"xor x5, x6, x7",
     "machine_table":["funct7=0000000 | rs2 | rs1 | funct3=100 | rd | opcode=0110011"],
     "explanation":"funct3=100 选择异或。"},
    {"name":"OR","desc_short":"按位或","fmt":"R","fmt_type":"R 型","example":"or x10, x11, x12",
     "machine_table":["funct7=0000000 | rs2 | rs1 | funct3=110 | rd | opcode=0110011"],
     "explanation":"funct3=110 选择按位或。"},
    {"name":"AND","desc_short":"按位与","fmt":"R","fmt_type":"R 型","example":"and x13, x14, x15",
     "machine_table":["funct7=0000000 | rs2 | rs1 | funct3=111 | rd | opcode=0110011"],
     "explanation":"funct3=111 选择按位与。"},
    {"name":"SLL","desc_short":"逻辑左移","fmt":"R","fmt_type":"R 型","example":"sll x5, x6, x7",
     "machine_table":["funct7=0000000 | rs2 | rs1 | funct3=001 | rd | opcode=0110011"],
     "explanation":"移位量由 rs2 低5位决定。"},
    {"name":"SRL","desc_short":"逻辑右移","fmt":"R","fmt_type":"R 型","example":"srl x8, x9, x10",
     "machine_table":["funct7=0000000 | rs2 | rs1 | funct3=101 | rd | opcode=0110011"],
     "explanation":"高位补0。"},
    {"name":"SRA","desc_short":"算术右移","fmt":"R","fmt_type":"R 型","example":"sra x11, x12, x13",
     "machine_table":["funct7=0100000 | rs2 | rs1 | funct3=101 | rd | opcode=0110011"],
     "explanation":"高位按符号位填充。"},
    {"name":"SLT","desc_short":"有符号小于置位","fmt":"R","fmt_type":"R 型","example":"slt x5, x6, x7",
     "machine_table":["funct7=0000000 | rs2 | rs1 | funct3=010 | rd | opcode=0110011"],
     "explanation":"若 rs1<rs2(有符号), rd=1, 否则 rd=0。"},
    {"name":"SLTU","desc_short":"无符号小于置位","fmt":"R","fmt_type":"R 型","example":"sltu x8, x9, x10",
     "machine_table":["funct7=0000000 | rs2 | rs1 | funct3=011 | rd | opcode=0110011"],
     "explanation":"无符号比较。"},
    # ── I-type ──
    {"name":"ADDI","desc_short":"立即数加法","fmt":"I","fmt_type":"I 型","example":"addi x5, x6, 100",
     "machine_table":["imm[11:0] | rs1 | funct3=000 | rd | opcode=0010011"],
     "explanation":"opcode=0010011, 12位有符号立即数符号扩展后与 rs1 相加。"},
    {"name":"XORI","desc_short":"立即数异或","fmt":"I","fmt_type":"I 型","example":"xori x7, x8, -1",
     "machine_table":["imm[11:0] | rs1 | funct3=100 | rd | opcode=0010011"],
     "explanation":"立即数按位异或。"},
    {"name":"ORI","desc_short":"立即数或","fmt":"I","fmt_type":"I 型","example":"ori x9, x10, 0xff",
     "machine_table":["imm[11:0] | rs1 | funct3=110 | rd | opcode=0010011"],
     "explanation":"立即数按位或。"},
    {"name":"ANDI","desc_short":"立即数与","fmt":"I","fmt_type":"I 型","example":"andi x11, x12, 0xf",
     "machine_table":["imm[11:0] | rs1 | funct3=111 | rd | opcode=0010011"],
     "explanation":"立即数按位与。"},
    {"name":"SLLI","desc_short":"逻辑左移立即数","fmt":"I","fmt_type":"I 型","example":"slli x5, x6, 3",
     "machine_table":["0000000 shamt[4:0] | rs1 | funct3=001 | rd | opcode=0010011"],
     "explanation":"imm[11:5]=0000000, shamt 为移位量(0-31)。"},
    {"name":"SRLI","desc_short":"逻辑右移立即数","fmt":"I","fmt_type":"I 型","example":"srli x7, x8, 2",
     "machine_table":["0000000 shamt[4:0] | rs1 | funct3=101 | rd | opcode=0010011"],
     "explanation":"高位补0。"},
    {"name":"SRAI","desc_short":"算术右移立即数","fmt":"I","fmt_type":"I 型","example":"srai x9, x10, 4",
     "machine_table":["0100000 shamt[4:0] | rs1 | funct3=101 | rd | opcode=0010011"],
     "explanation":"imm[11:5]=0100000, 高位按符号填充。"},
    {"name":"SLTI","desc_short":"有符号小于立即数置位","fmt":"I","fmt_type":"I 型","example":"slti x11, x12, 5",
     "machine_table":["imm[11:0] | rs1 | funct3=010 | rd | opcode=0010011"],
     "explanation":"若 rs1 < 符号扩展(imm), rd=1。"},
    {"name":"SLTIU","desc_short":"无符号小于立即数置位","fmt":"I","fmt_type":"I 型","example":"sltiu x13, x14, 10",
     "machine_table":["imm[11:0] | rs1 | funct3=011 | rd | opcode=0010011"],
     "explanation":"无符号比较。"},
    {"name":"LB","desc_short":"字节加载(有符号扩展)","fmt":"I","fmt_type":"I 型(Load)","example":"lb x5, 0(x6)",
     "machine_table":["imm[11:0] | rs1 | funct3=000 | rd | opcode=0000011"],
     "explanation":"从地址 rs1+imm 读1字节，有符号扩展为32位。"},
    {"name":"LH","desc_short":"半字加载(有符号扩展)","fmt":"I","fmt_type":"I 型(Load)","example":"lh x7, 2(x8)",
     "machine_table":["imm[11:0] | rs1 | funct3=001 | rd | opcode=0000011"],
     "explanation":"读16位半字，有符号扩展。"},
    {"name":"LW","desc_short":"字加载","fmt":"I","fmt_type":"I 型(Load)","example":"lw x9, 4(x2)",
     "machine_table":["imm[11:0] | rs1 | funct3=010 | rd | opcode=0000011"],
     "explanation":"读32位字。"},
    {"name":"LBU","desc_short":"字节加载(无符号扩展)","fmt":"I","fmt_type":"I 型(Load)","example":"lbu x10, 1(x11)",
     "machine_table":["imm[11:0] | rs1 | funct3=100 | rd | opcode=0000011"],
     "explanation":"无符号扩展。"},
    {"name":"LHU","desc_short":"半字加载(无符号扩展)","fmt":"I","fmt_type":"I 型(Load)","example":"lhu x12, 6(x13)",
     "machine_table":["imm[11:0] | rs1 | funct3=101 | rd | opcode=0000011"],
     "explanation":"无符号扩展。"},
    {"name":"JALR","desc_short":"寄存器跳转并链接","fmt":"I","fmt_type":"I 型(JALR)","example":"jalr x1, 0(x5)",
     "machine_table":["imm[11:0] | rs1 | funct3=000 | rd | opcode=1100111"],
     "explanation":"pc+4 存 rd，跳转到 rs1+imm 且最低位清零。"},
    # ── S-type ──
    {"name":"SB","desc_short":"存储字节","fmt":"S","fmt_type":"S 型","example":"sb x5, 0(x6)",
     "machine_table":["imm[11:5] | rs2 | rs1 | funct3=000 | imm[4:0] | opcode=0100011"],
     "explanation":"将 rs2 低8位存入地址 rs1+imm。"},
    {"name":"SH","desc_short":"存储半字","fmt":"S","fmt_type":"S 型","example":"sh x7, 2(x8)",
     "machine_table":["imm[11:5] | rs2 | rs1 | funct3=001 | imm[4:0] | opcode=0100011"],
     "explanation":"存储16位半字。"},
    {"name":"SW","desc_short":"存储字","fmt":"S","fmt_type":"S 型","example":"sw x9, 4(x2)",
     "machine_table":["imm[11:5] | rs2 | rs1 | funct3=010 | imm[4:0] | opcode=0100011"],
     "explanation":"存储32位字。"},
    # ── B-type ──
    {"name":"BEQ","desc_short":"相等分支","fmt":"B","fmt_type":"B 型","example":"beq x5, x6, 8",
     "machine_table":["imm[12|10:5] | rs2 | rs1 | funct3=000 | imm[4:1|11] | opcode=1100011"],
     "explanation":"若 rs1==rs2, PC+=imm(字节)。"},
    {"name":"BNE","desc_short":"不等分支","fmt":"B","fmt_type":"B 型","example":"bne x7, x8, 8",
     "machine_table":["imm[12|10:5] | rs2 | rs1 | funct3=001 | imm[4:1|11] | opcode=1100011"],
     "explanation":"若 rs1!=rs2, 分支。"},
    {"name":"BLT","desc_short":"有符号小于分支","fmt":"B","fmt_type":"B 型","example":"blt x9, x10, 8",
     "machine_table":["imm[12|10:5] | rs2 | rs1 | funct3=100 | imm[4:1|11] | opcode=1100011"],
     "explanation":"有符号比较。"},
    {"name":"BGE","desc_short":"有符号大于等于分支","fmt":"B","fmt_type":"B 型","example":"bge x11, x12, 8",
     "machine_table":["imm[12|10:5] | rs2 | rs1 | funct3=101 | imm[4:1|11] | opcode=1100011"],
     "explanation":"有符号比较。"},
    {"name":"BLTU","desc_short":"无符号小于分支","fmt":"B","fmt_type":"B 型","example":"bltu x13, x14, 8",
     "machine_table":["imm[12|10:5] | rs2 | rs1 | funct3=110 | imm[4:1|11] | opcode=1100011"],
     "explanation":"无符号比较。"},
    {"name":"BGEU","desc_short":"无符号大于等于分支","fmt":"B","fmt_type":"B 型","example":"bgeu x15, x16, 8",
     "machine_table":["imm[12|10:5] | rs2 | rs1 | funct3=111 | imm[4:1|11] | opcode=1100011"],
     "explanation":"无符号比较。"},
    # ── U-type ──
    {"name":"LUI","desc_short":"高位立即数加载","fmt":"U","fmt_type":"U 型","example":"lui x10, 0x12345",
     "machine_table":["imm[31:12] | rd | opcode=0110111"],
     "explanation":"20位立即数左移12位(低12位填0)写入 rd。"},
    {"name":"AUIPC","desc_short":"PC 加立即数","fmt":"U","fmt_type":"U 型","example":"auipc x5, 0x1",
     "machine_table":["imm[31:12] | rd | opcode=0010111"],
     "explanation":"PC + imm<<12 写入 rd。"},
    # ── J-type ──
    {"name":"JAL","desc_short":"跳转并链接","fmt":"J","fmt_type":"J 型","example":"jal x1, 0",
     "machine_table":["imm[20|10:1|11|19:12] | rd | opcode=1101111"],
     "explanation":"pc+4 存入 rd, 跳转到 PC+offset(±1MiB)。"},
]

_CSR_INSTRUCTION_LIST = [
    {"name":"CSRRW","desc_short":"读后写 CSR","fmt":"I","fmt_type":"I 型(特权)","example":"csrrw x5, 0x300, x6",
     "machine_table":["csr[11:0] | rs1 | funct3=001 | rd | opcode=1110011"],
     "explanation":"原子读 CSR 到 rd, 写 rs1 到 CSR。若 rd=x0 只写不读。"},
    {"name":"CSRRS","desc_short":"读后置位 CSR","fmt":"I","fmt_type":"I 型(特权)","example":"csrrs x5, 0x300, x6",
     "machine_table":["csr[11:0] | rs1 | funct3=010 | rd | opcode=1110011"],
     "explanation":"读 CSR → rd, CSR 中 rs1 对应位为1的置位。"},
    {"name":"CSRRC","desc_short":"读后清零 CSR","fmt":"I","fmt_type":"I 型(特权)","example":"csrrc x5, 0x300, x6",
     "machine_table":["csr[11:0] | rs1 | funct3=011 | rd | opcode=1110011"],
     "explanation":"读 CSR → rd, CSR 中 rs1 对应位为1的清零。"},
    {"name":"CSRRWI","desc_short":"读后写 CSR(立即数)","fmt":"I","fmt_type":"I 型(特权)","example":"csrrwi x5, 0x300, 4",
     "machine_table":["csr[11:0] | zimm[4:0] | funct3=101 | rd | opcode=1110011"],
     "explanation":"5位无符号立即数 zimm 零扩展后写入 CSR。"},
    {"name":"CSRRSI","desc_short":"读后置位 CSR(立即数)","fmt":"I","fmt_type":"I 型(特权)","example":"csrrsi x5, 0x300, 8",
     "machine_table":["csr[11:0] | zimm[4:0] | funct3=110 | rd | opcode=1110011"],
     "explanation":"按 zimm 置位 CSR。"},
    {"name":"CSRRCI","desc_short":"读后清零 CSR(立即数)","fmt":"I","fmt_type":"I 型(特权)","example":"csrrci x5, 0x300, 1",
     "machine_table":["csr[11:0] | zimm[4:0] | funct3=111 | rd | opcode=1110011"],
     "explanation":"按 zimm 清零 CSR。"},
]

_PSEUDO_INSTRUCTION_LIST = [
    {"name":"LI","desc_short":"加载立即数","fmt":"Pseudo","fmt_type":"伪指令","example":"li x5, 0x12345678",
     "machine_table":["展开为 lui + addi (或仅为 addi)"],
     "explanation":"根据立即数范围选择最优展开序列。"},
    {"name":"LA","desc_short":"加载地址","fmt":"Pseudo","fmt_type":"伪指令","example":"la x10, array",
     "machine_table":["展开为 auipc + addi"],
     "explanation":"PC 相对寻址或绝对 lui 组合。"},
    {"name":"MV","desc_short":"寄存器复制","fmt":"Pseudo","fmt_type":"伪指令","example":"mv x8, x9",
     "machine_table":["addi rd, rs, 0 → 0010011"],
     "explanation":"展开为 addi rd, rs, 0。"},
    {"name":"NOP","desc_short":"空操作","fmt":"Pseudo","fmt_type":"伪指令","example":"nop",
     "machine_table":["addi x0, x0, 0 → 0x00000013"],
     "explanation":"不执行任何操作。"},
    {"name":"J","desc_short":"无条件跳转","fmt":"Pseudo","fmt_type":"伪指令","example":"j loop",
     "machine_table":["jal x0, label → 1101111"],
     "explanation":"rd=x0 不保存返回地址。"},
    {"name":"JR","desc_short":"寄存器跳转","fmt":"Pseudo","fmt_type":"伪指令","example":"jr x1",
     "machine_table":["jalr x0, 0(rs) → 1100111"],
     "explanation":"跳转到 rs 所存地址。"},
    {"name":"RET","desc_short":"函数返回","fmt":"Pseudo","fmt_type":"伪指令","example":"ret",
     "machine_table":["jalr x0, 0(x1) → 1100111"],
     "explanation":"跳转到 x1(ra) 中的地址。"},
    {"name":"CALL","desc_short":"远程函数调用","fmt":"Pseudo","fmt_type":"伪指令","example":"call func",
     "machine_table":["auipc x1, off + jalr x1, off(x1)"],
     "explanation":"返回地址存入 x1。"},
    {"name":"BEQZ","desc_short":"等于零分支","fmt":"Pseudo","fmt_type":"伪指令","example":"beqz rs, label",
     "machine_table":["beq rs, x0, label → 1100011"],
     "explanation":"展开为 beq rs, x0, label。"},
    {"name":"BNEZ","desc_short":"不等零分支","fmt":"Pseudo","fmt_type":"伪指令","example":"bnez rs, label",
     "machine_table":["bne rs, x0, label → 1100011"],
     "explanation":"展开为 bne rs, x0, label。"},
    {"name":"NEG","desc_short":"取负","fmt":"Pseudo","fmt_type":"伪指令","example":"neg x5, x6",
     "machine_table":["sub rd, x0, rs → 0110011"],
     "explanation":"rd = -rs(二进制补码)。"},
    {"name":"NOT","desc_short":"按位取反","fmt":"Pseudo","fmt_type":"伪指令","example":"not x7, x8",
     "machine_table":["xori rd, rs, -1 → 0010011"],
     "explanation":"rd = ~rs。"},
]


# ── 寄存器表数据 ────────────────────────────────────────────
_REGISTER_TABLE = [
    ("x0","00000","zero","硬连线常数 0",""),
    ("x1","00001","ra","返回地址","caller"),
    ("x2","00010","sp","栈指针","callee"),
    ("x3","00011","gp","全局指针",""),
    ("x4","00100","tp","线程指针",""),
    ("x5","00101","t0","临时寄存器","caller"),
    ("x6","00110","t1","临时寄存器","caller"),
    ("x7","00111","t2","临时寄存器","caller"),
    ("x8","01000","s0/fp","保存寄存器/帧指针","callee"),
    ("x9","01001","s1","保存寄存器","callee"),
    ("x10","01010","a0","函数参数/返回值0","caller"),
    ("x11","01011","a1","函数参数/返回值1","caller"),
    ("x12","01100","a2","函数参数2","caller"),
    ("x13","01101","a3","函数参数3","caller"),
    ("x14","01110","a4","函数参数4","caller"),
    ("x15","01111","a5","函数参数5","caller"),
    ("x16","10000","a6","函数参数6","caller"),
    ("x17","10001","a7","函数参数7","caller"),
    ("x18","10010","s2","保存寄存器","callee"),
    ("x19","10011","s3","保存寄存器","callee"),
    ("x20","10100","s4","保存寄存器","callee"),
    ("x21","10101","s5","保存寄存器","callee"),
    ("x22","10110","s6","保存寄存器","callee"),
    ("x23","10111","s7","保存寄存器","callee"),
    ("x24","11000","s8","保存寄存器","callee"),
    ("x25","11001","s9","保存寄存器","callee"),
    ("x26","11010","s10","保存寄存器","callee"),
    ("x27","11011","s11","保存寄存器","callee"),
    ("x28","11100","t3","临时寄存器","caller"),
    ("x29","11101","t4","临时寄存器","caller"),
    ("x30","11110","t5","临时寄存器","caller"),
    ("x31","11111","t6","临时寄存器","caller"),
]

# ── 六类编码格式总览表数据 ──────────────────────────────
_FORMAT_TABLES = {
    "R": [
        ("ADD","0000000","rs2","rs1","000","rd","0110011","加法"),
        ("SUB","0100000","rs2","rs1","000","rd","0110011","减法"),
        ("XOR","0000000","rs2","rs1","100","rd","0110011","异或"),
        ("OR","0000000","rs2","rs1","110","rd","0110011","或"),
        ("AND","0000000","rs2","rs1","111","rd","0110011","与"),
        ("SLL","0000000","rs2","rs1","001","rd","0110011","逻辑左移"),
        ("SRL","0000000","rs2","rs1","101","rd","0110011","逻辑右移"),
        ("SRA","0100000","rs2","rs1","101","rd","0110011","算术右移"),
        ("SLT","0000000","rs2","rs1","010","rd","0110011","有符号小于置位"),
        ("SLTU","0000000","rs2","rs1","011","rd","0110011","无符号小于置位"),
    ],
    "I": [
        ("ADDI","imm[11:0]","rs1","000","rd","0010011","立即数加法"),
        ("XORI","imm[11:0]","rs1","100","rd","0010011","立即数异或"),
        ("ORI","imm[11:0]","rs1","110","rd","0010011","立即数或"),
        ("ANDI","imm[11:0]","rs1","111","rd","0010011","立即数与"),
        ("SLLI","0000000 shamt","rs1","001","rd","0010011","逻辑左移立即数"),
        ("SRLI","0000000 shamt","rs1","101","rd","0010011","逻辑右移立即数"),
        ("SRAI","0100000 shamt","rs1","101","rd","0010011","算术右移立即数"),
        ("SLTI","imm[11:0]","rs1","010","rd","0010011","有符号小于立即数"),
        ("SLTIU","imm[11:0]","rs1","011","rd","0010011","无符号小于立即数"),
        ("LW","imm[11:0]","rs1","010","rd","0000011","字加载"),
    ],
    "S": [
        ("SB","imm[11:5]","rs2","rs1","000","imm[4:0]","0100011","存储字节"),
        ("SH","imm[11:5]","rs2","rs1","001","imm[4:0]","0100011","存储半字"),
        ("SW","imm[11:5]","rs2","rs1","010","imm[4:0]","0100011","存储字"),
    ],
    "B": [
        ("BEQ","imm[12|10:5]","rs2","rs1","000","imm[4:1|11]","1100011","相等跳转"),
        ("BNE","imm[12|10:5]","rs2","rs1","001","imm[4:1|11]","1100011","不等跳转"),
        ("BLT","imm[12|10:5]","rs2","rs1","100","imm[4:1|11]","1100011","有符号小于跳转"),
        ("BGE","imm[12|10:5]","rs2","rs1","101","imm[4:1|11]","1100011","有符号≥跳转"),
        ("BLTU","imm[12|10:5]","rs2","rs1","110","imm[4:1|11]","1100011","无符号小于跳转"),
        ("BGEU","imm[12|10:5]","rs2","rs1","111","imm[4:1|11]","1100011","无符号≥跳转"),
    ],
    "U": [
        ("LUI","imm[31:12]","rd","0110111","高位立即数加载"),
        ("AUIPC","imm[31:12]","rd","0010111","PC加立即数"),
    ],
    "J": [
        ("JAL","imm[20|10:1|11|19:12]","rd","1101111","跳转并链接"),
    ],
}

# ── 具体指令到格式的映射，用于导航树分组 ──────────────────
_INST_FORMAT_MAP = {}
for inst in _INSTRUCTION_LIST:
    _INST_FORMAT_MAP[inst["name"]] = inst["fmt"]


class LearnPage(ttk.Frame):
    """RISC-V 学习页面：左侧导航树 + 右侧滚动文档"""

    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self._last_selected = "intro-intro"
        self._content_widgets: dict[str, tk.Widget] = {}
        self._images: list[ImageTk.PhotoImage] = []
        self._tree_map: dict[str, str] = {}  # tag -> tree item
        self.setup_ui()

    # ── UI 搭建 ──────────────────────────────────────────────
    def setup_ui(self):
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # ── 左侧导航 ──
        left = ttk.Frame(self, width=220)
        left.grid(row=0, column=0, sticky="ns", padx=(5, 0), pady=5)
        left.grid_propagate(False)

        ttk.Label(left, text="指令导航", font=("", 12, "bold")).pack(
            anchor="w", padx=5, pady=(5, 5))

        self.tree = ttk.Treeview(left, show="tree", selectmode="browse")
        self.tree.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        self._build_nav_tree()

        # ── 右侧内容 ──
        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(right, highlightthickness=0)
        scrollbar = ttk.Scrollbar(right, orient="vertical", command=self.canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.content_frame = ttk.Frame(self.canvas)
        self.content_window = self.canvas.create_window(
            (0, 0), window=self.content_frame, anchor="nw", width=10)

        self.content_frame.bind("<Configure>", self._on_content_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # ── 鼠标滚轮滚动（全局绑定，确保子控件也能响应） ──
        self.canvas.bind("<Enter>", self._enable_scroll)
        self.content_frame.bind("<Enter>", self._enable_scroll)
        self.canvas.bind("<Leave>", self._disable_scroll)

        # 此外对 Treeview 左侧导航直接绑定，避免与右侧冲突
        self.tree.bind("<Enter>", self._disable_scroll)

        self._build_content()

    # ── 滚动事件 ────────────────────────────────────────────
    def _on_content_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.content_window, width=event.width - 20)

    def _enable_scroll(self, event=None):
        """鼠标进入内容区域：全局绑定滚轮 + 设焦点"""
        self.canvas.focus_set()
        self.bind_all("<MouseWheel>", self._on_mousewheel)
        self.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))

    def _disable_scroll(self, event=None):
        """鼠标离开内容区域：解除全局绑定，不影响左侧 Treeview"""
        self.unbind_all("<MouseWheel>")
        self.unbind_all("<Button-4>")
        self.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ══════════════════════════════════════════════════════════
    #  导航树
    # ══════════════════════════════════════════════════════════
    def _build_nav_tree(self):
        # 总述
        intro = self.tree.insert("", "end", text="总述", open=True)
        self._add_nav_node(intro, "RISC-V 介绍", "intro-intro")
        self._add_nav_node(intro, "寄存器一览表", "intro-regs")
        self._add_nav_node(intro, "汇编与机器码总览表", "intro-overview")

        # 基本语句
        detail = self.tree.insert("", "end", text="基本语句说明", open=True)
        fmt_groups = [
            ("R","R-type 指令"), ("I","I-type 指令"),
            ("S","S-type 指令"), ("B","B-type 指令"),
            ("U","U-type 指令"), ("J","J-type 指令"),
        ]
        for fmt_key, fmt_name in fmt_groups:
            fmt_node = self.tree.insert(detail, "end", text=fmt_name, open=True)
            for inst in _INSTRUCTION_LIST:
                if inst["fmt"] == fmt_key:
                    self._add_nav_node(
                        fmt_node,
                        f"{inst['name']} – {inst['desc_short']}",
                        f"inst-{inst['name'].lower()}")

        # 特权指令
        priv = self.tree.insert("", "end", text="特权指令 (Zicsr)", open=True)
        for inst in _CSR_INSTRUCTION_LIST:
            self._add_nav_node(
                priv,
                f"{inst['name']} – {inst['desc_short']}",
                f"inst-{inst['name'].lower()}")

        # 伪指令
        pseudo = self.tree.insert("", "end", text="常用伪指令", open=True)
        for inst in _PSEUDO_INSTRUCTION_LIST:
            self._add_nav_node(
                pseudo,
                f"{inst['name']} – {inst['desc_short']}",
                f"inst-{inst['name'].lower()}")

    def _add_nav_node(self, parent, text, tag):
        item = self.tree.insert(parent, "end", text=text, tags=(tag,))
        self._tree_map[tag] = item

    # ══════════════════════════════════════════════════════════
    #  内容构建
    # ══════════════════════════════════════════════════════════
    def _build_content(self):
        self.content_frame.columnconfigure(0, weight=1)
        sec = ttk.Frame(self.content_frame)
        sec.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        sec.columnconfigure(0, weight=1)

        # ── 总述 ──
        self._build_overview(sec)

        # ── 基本语句说明 ──
        self._h1(sec, "基本语句说明")
        for inst in _INSTRUCTION_LIST:
            self._build_inst_card(sec, inst)

        # ── 特权指令 ──
        self._h1(sec, "特权指令（Zicsr 扩展）")
        for inst in _CSR_INSTRUCTION_LIST:
            self._build_inst_card(sec, inst)

        # ── 伪指令 ──
        self._h1(sec, "常用伪指令")
        for inst in _PSEUDO_INSTRUCTION_LIST:
            self._build_inst_card(sec, inst)

    # ── 总述部分 ──────────────────────────────────────────
    def _build_overview(self, parent):
        self._h1(parent, "总述", "intro-intro")

        # RISC-V 介绍
        self._h2(parent, "RISC-V 介绍", "intro-intro")
        self._p(parent,
            "RISC-V（Reduced Instruction Set Computer V）是一种开源的指令集架构（ISA）。"
            "它采用精简指令集计算原则，设计简洁、高效且模块化，支持多种数据宽度（如32位、64位、128位）。"
            "RISC-V 开放性和灵活性使其广泛应用于学术研究、工业和嵌入式系统等领域，"
            "并且能够满足从微控制器到超级计算机的各种需求。")
        self._p(parent,
            "RISC-V 由加州大学伯克利分校的研究团队于2010年首次发布，基于精简指令集计算（RISC）原则。"
            "作为一个开源标准，RISC-V 允许任何个人或组织自由使用、修改和扩展，无需支付专利费用。"
            "其设计目标是提供一个简单、可扩展且灵活的指令集。")
        self._ref(parent, "更多信息参考官网和诸多百科网站。")

        # 寄存器一览表
        self._h2(parent, "寄存器意义编码一览表", "intro-regs")
        self._p(parent,
            "RISC-V32i 的寄存器编码占据5位，从编码顺序上来看，可以命名为 x0 到 x31，"
            "从功能上命名各有不同，一般直接使用后者，对应前者编码。")
        self._build_register_table(parent)

        # 汇编与机器码总览表
        self._h2(parent, "汇编指令对照机器码总览表", "intro-overview")
        self._p(parent,
            "RV32I 是32位基础整数指令集，它支持32位寻址空间，支持字节地址访问，"
            "仅支持小端格式（little-endian），寄存器也是32位整数寄存器。"
            "RV32I 指令集的目的是尽量简化硬件的实施设计，所以它只有40条指令。")
        self._p(parent,
            "这40条指令几乎能够模拟其它任何扩展指令。实际上要实现机器模式的 RISC-V 特权架构，"
            "还需要6条 csr 指令，它们被放在扩展指令集 Zicsr 中。"
            "所以说要实现一个完整的 RISC-V 系统，至少要实现 RV32I+Zicsr 指令集。")
        self._ref(parent, "参考文章：RISC-V RV32I Base Instruction Set")

        # 三张图片
        for img_name in ("allcodes.png", "typesdivision.png", "picoftype.png"):
            self._image(parent, img_name)

        self._p(parent, "图像来自参考文章: 从零开始写 riscv 处理器（一）指令集")
        self._ref(parent, "在 RV32I 体系内一般在特权指令之外，机器码划分为 R-type, I-type, S-type, B-type, U-type, J-type 六种基本格式。")

        # 六类编码格式总览表
        self._build_format_tables(parent)

    # ── 寄存器表格 ─────────────────────────────────────────
    def _build_register_table(self, parent):
        frame = ttk.LabelFrame(parent, text="寄存器编码表", padding=5)
        frame.grid(sticky="ew", pady=5)
        cols = ("编号", "二进制", "ABI名称", "作用", "调用约定")
        tree = ttk.Treeview(frame, columns=cols, show="headings",
                            height=15, displaycolumns=cols)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=80)
        tree.column("编号", width=50)
        tree.column("二进制", width=70)
        tree.column("ABI名称", width=80)
        tree.column("作用", width=200)
        tree.column("调用约定", width=70)
        for row in _REGISTER_TABLE:
            tree.insert("", "end", values=row)
        tree.grid(sticky="ew")
        # 添加 pc 行
        ttk.Label(frame, text="pc — 程序计数器，不可直接读写",
                  font=("", 9), foreground="#666").grid(sticky="w", pady=(2, 0))
        self._content_widgets["intro-regs"] = tree

    # ── 六类编码格式总览表 ────────────────────────────────
    def _build_format_tables(self, parent):
        format_info = {
            "R": ("R型", ["31-25","24-20","19-15","14-12","11-7","6-0","功能"]),
            "I": ("I型", ["31-20","19-15","14-12","11-7","6-0","功能"]),
            "S": ("S型", ["31-25","24-20","19-15","14-12","11-7","6-0","功能"]),
            "B": ("B型", ["31-25","24-20","19-15","14-12","11-7","6-0","功能"]),
            "U": ("U型", ["31-12","11-7","6-0","功能"]),
            "J": ("J型", ["31-12","11-7","6-0","功能"]),
        }
        for fmt_key, (title, cols) in format_info.items():
            data = _FORMAT_TABLES[fmt_key]
            if not data:
                continue
            frame = ttk.LabelFrame(parent, text=f"{title} 编码表格", padding=5)
            frame.grid(sticky="ew", pady=5)
            # 表头行
            hdr = ttk.Frame(frame)
            hdr.pack(fill="x")
            for c in cols:
                ttk.Label(hdr, text=c, font=("", 9, "bold"),
                          borderwidth=1, relief="solid", padding=2).pack(side="left", fill="x", expand=True)
            for row in data:
                r = ttk.Frame(frame)
                r.pack(fill="x")
                for val in row:
                    ttk.Label(r, text=str(val), font=("Consolas", 9),
                              borderwidth=1, relief="solid", padding=2).pack(side="left", fill="x", expand=True)

    # ── 指令卡片 ─────────────────────────────────────────────
    def _build_inst_card(self, parent, inst):
        tag = f"inst-{inst['name'].lower()}"

        # 三级标题
        self._h3(parent, f"{inst['name']} – {inst['desc_short']}", tag)

        # 类型 + 作用
        self._p(parent, f"类型：{inst['fmt_type']}  作用：{inst.get('desc','')}")

        # 示例 (等宽)
        self._code(parent, f"示例：{inst['example']}")

        # 机器码
        self._p(parent, "机器码格式：")
        for line in inst["machine_table"]:
            self._code(parent, f"  {line}")

        # 说明
        self._p(parent, inst["explanation"])

        # 测试块
        self._build_test_block(parent, inst["name"], inst["example"])

    # ══════════════════════════════════════════════════════════
    #  排版辅助
    # ══════════════════════════════════════════════════════════
    def _h1(self, parent, text, tag=None):
        """一级标题：15pt bold"""
        lbl = ttk.Label(parent, text=text, font=("", 15, "bold"))
        lbl.grid(sticky="w", pady=(20, 5))
        if tag:
            self._content_widgets[tag] = lbl

    def _h2(self, parent, text, tag=None):
        """二级标题：13pt bold"""
        lbl = ttk.Label(parent, text=text, font=("", 13, "bold"))
        lbl.grid(sticky="w", pady=(12, 3))
        if tag:
            self._content_widgets[tag] = lbl

    def _h3(self, parent, text, tag=None):
        """三级标题：12pt bold"""
        lbl = ttk.Label(parent, text=text, font=("", 12, "bold"))
        lbl.grid(sticky="w", pady=(10, 2))
        if tag:
            self._content_widgets[tag] = lbl

    def _p(self, parent, text):
        """正文：11pt"""
        lbl = ttk.Label(parent, text=text, justify="left",
                        anchor="w", wraplength=700)
        lbl.grid(sticky="w", pady=2)
        return lbl

    def _code(self, parent, text):
        """等宽代码行：10pt"""
        lbl = ttk.Label(parent, text=text, font=("Consolas", 10),
                        justify="left", anchor="w")
        lbl.grid(sticky="w", pady=1)

    def _ref(self, parent, text):
        """参考文字：9pt 灰色"""
        lbl = ttk.Label(parent, text=text, foreground="#888888",
                        font=("", 9))
        lbl.grid(sticky="w", pady=(0, 4))

    def _image(self, parent, name):
        """插入图片"""
        try:
            img = _load_image(name)
            if img is None:
                raise FileNotFoundError(name)
            self._images.append(img)
            ttk.Label(parent, image=img).grid(sticky="w", pady=5)
        except Exception:
            # 图片缺省占位
            placeholder = ttk.Label(
                parent, text=f"[图片：{name} 未加载]",
                foreground="#999", background="#f0f0f0",
                font=("", 9), padding=40)
            placeholder.grid(sticky="ew", pady=5)

    # ══════════════════════════════════════════════════════════
    #  测试块
    # ══════════════════════════════════════════════════════════
    def _build_test_block(self, parent, inst_name, example):
        test_frame = ttk.LabelFrame(parent, text="试试看", padding=5)
        test_frame.grid(sticky="ew", pady=(8, 5))
        test_frame.columnconfigure(1, weight=1)

        asm_var = tk.StringVar(value=example if example.startswith(inst_name.lower())
                               else f"{inst_name.lower()} {example.split(' ', 1)[-1]}" if " " in example
                               else f"{inst_name.lower()} {example}")
        hex_var = tk.StringVar()
        bin_var = tk.StringVar()
        status_label = ttk.Label(test_frame, text="", foreground="#666")

        # 行1：汇编
        ttk.Label(test_frame, text="汇编:", font=("Consolas", 10)).grid(
            row=0, column=0, sticky="w")
        asm_entry = ttk.Entry(test_frame, textvariable=asm_var, font=("Consolas", 10))
        asm_entry.grid(row=0, column=1, sticky="ew", padx=(0, 4))
        ttk.Button(test_frame, text="转换→", width=8,
                   command=lambda: self._test_asm(asm_var, hex_var, bin_var, status_label)
                   ).grid(row=0, column=2)

        # 行2：十六进制
        ttk.Label(test_frame, text="十六进制:", font=("Consolas", 10)).grid(
            row=1, column=0, sticky="w", pady=(3, 0))
        hex_entry = ttk.Entry(test_frame, textvariable=hex_var, font=("Consolas", 10))
        hex_entry.grid(row=1, column=1, sticky="ew", padx=(0, 4), pady=(3, 0))
        ttk.Button(test_frame, text="转换→", width=8,
                   command=lambda: self._test_hex(hex_var, asm_var, bin_var, status_label)
                   ).grid(row=1, column=2, pady=(3, 0))

        # 行3：二进制
        ttk.Label(test_frame, text="二进制:", font=("Consolas", 10)).grid(
            row=2, column=0, sticky="w", pady=(3, 0))
        bin_entry = ttk.Entry(test_frame, textvariable=bin_var, font=("Consolas", 10))
        bin_entry.grid(row=2, column=1, sticky="ew", padx=(0, 4), pady=(3, 0))
        ttk.Button(test_frame, text="转换→", width=8,
                   command=lambda: self._test_bin(bin_var, asm_var, hex_var, status_label)
                   ).grid(row=2, column=2, pady=(3, 0))

        # 状态
        status_label.grid(row=3, column=0, columnspan=3, sticky="w", pady=(2, 0))

        # 自动执行一次汇编→机器码转换
        self._test_asm(asm_var, hex_var, bin_var, status_label)

    # ── 转换逻辑 ──────────────────────────────────────────
    def _test_asm(self, asm_var, hex_var, bin_var, status_label):
        text = asm_var.get().strip()
        if not text:
            return
        data = assemble_line(text)
        if data:
            hex_var.set(data.hex())
            bin_var.set(" ".join(f"{b:08b}" for b in data))
            status_label.config(text="✅ 转换成功", foreground="green")
        else:
            hex_var.set("")
            bin_var.set("")
            status_label.config(text="❌ 转换失败", foreground="red")

    def _test_hex(self, hex_var, asm_var, bin_var, status_label):
        text = hex_var.get().strip()
        if len(text) != 8:
            status_label.config(text="需要8位十六进制字符", foreground="red")
            return
        try:
            data = bytes.fromhex(text)
            result = disassemble_bytes(data)
            if result:
                asm_var.set(result)
                bin_var.set(" ".join(f"{b:08b}" for b in data))
                status_label.config(text="✅ 转换成功", foreground="green")
            else:
                status_label.config(text="❌ 无效指令编码", foreground="red")
        except Exception as e:
            status_label.config(text=str(e), foreground="red")

    def _test_bin(self, bin_var, asm_var, hex_var, status_label):
        text = bin_var.get().strip().replace(" ", "")
        if len(text) != 32:
            status_label.config(text="需要32位二进制(含空格)", foreground="red")
            return
        try:
            data = bytes(int(text[i:i+8], 2) for i in range(0, 32, 8))
            result = disassemble_bytes(data)
            if result:
                asm_var.set(result)
                hex_var.set(data.hex())
                status_label.config(text="✅ 转换成功", foreground="green")
            else:
                status_label.config(text="❌ 无效指令编码", foreground="red")
        except Exception as e:
            status_label.config(text=str(e), foreground="red")

    # ══════════════════════════════════════════════════════════
    #  导航跳转
    # ══════════════════════════════════════════════════════════
    def _on_tree_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        tags = self.tree.item(item, "tags")
        if tags:
            tag = tags[0]
            self._last_selected = tag
            self._scroll_to_tag(tag)

    def _scroll_to_tag(self, tag):
        if tag in self._content_widgets:
            widget = self._content_widgets[tag]
            self.canvas.update_idletasks()
            bbox = self.canvas.bbox("all")
            if bbox and bbox[3] > 0:
                # 用绝对坐标计算相对于 content_frame 的位置
                content_y = self.content_frame.winfo_rooty()
                widget_y = widget.winfo_rooty()
                y = widget_y - content_y
                frac = y / bbox[3] if bbox[3] > 0 else 0
                self.canvas.yview_moveto(max(0.0, frac - 0.05))
            # 高亮效果：临时变蓝
            orig_fg = widget.cget("foreground")
            if orig_fg != "#3498db" and orig_fg != "blue":
                widget.configure(foreground="#3498db")
                self.after(500, lambda w=widget, fg=orig_fg: w.configure(foreground=fg))

    # ══════════════════════════════════════════════════════════
    #  状态管理
    # ══════════════════════════════════════════════════════════
    def load_state(self, state_data: dict):
        last = state_data.get("last_selected_instruction", "intro-intro")
        self._last_selected = last
        self.after(100, lambda: self._scroll_to_tag(self._last_selected))

    def save_state(self) -> dict:
        return {"last_selected_instruction": self._last_selected}

    def reset(self):
        self._last_selected = "intro-intro"
