"""RISC-V 32I 学习页面 — 分块渲染 + 测试块始终可见 + 无 PIL"""
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from core.assembler import assemble_line, disassemble_bytes

# ── 资源路径 ─────────────────────────────────────────────────
_RESOURCE_DIR = Path(__file__).resolve().parent.parent / "resource"
_IMAGE_MAP = {
    "allcodes.png":      "picofalltype.gif",
    "typesdivision.png": "useandalgorithm.gif",
    "picoftype.png":     "picofsixtypes.gif",
}


def _load_gif(name: str):
    """加载 resource 目录下的 GIF（Tkinter 原生支持）"""
    real_name = _IMAGE_MAP.get(name, name)
    path = _RESOURCE_DIR / real_name
    if not path.exists():
        return None
    return tk.PhotoImage(file=str(path))


# ══════════════════════════════════════════════════════════════
#  指令数据
# ══════════════════════════════════════════════════════════════
_INSTRUCTION_LIST = [
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
    {"name":"ADDI","desc_short":"立即数加法","fmt":"I","fmt_type":"I 型","example":"addi x5, x6, 100",
     "machine_table":["imm[11:0] | rs1 | funct3=000 | rd | opcode=0010011"],
     "explanation":"opcode=0010011, 12位立即数符号扩展后与 rs1 相加。"},
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
     "explanation":"从地址 rs1+imm 读1字节，有符号扩展。"},
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
    {"name":"SB","desc_short":"存储字节","fmt":"S","fmt_type":"S 型","example":"sb x5, 0(x6)",
     "machine_table":["imm[11:5] | rs2 | rs1 | funct3=000 | imm[4:0] | opcode=0100011"],
     "explanation":"将 rs2 低8位存入地址 rs1+imm。"},
    {"name":"SH","desc_short":"存储半字","fmt":"S","fmt_type":"S 型","example":"sh x7, 2(x8)",
     "machine_table":["imm[11:5] | rs2 | rs1 | funct3=001 | imm[4:0] | opcode=0100011"],
     "explanation":"存储16位半字。"},
    {"name":"SW","desc_short":"存储字","fmt":"S","fmt_type":"S 型","example":"sw x9, 4(x2)",
     "machine_table":["imm[11:5] | rs2 | rs1 | funct3=010 | imm[4:0] | opcode=0100011"],
     "explanation":"存储32位字。"},
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
    {"name":"LUI","desc_short":"高位立即数加载","fmt":"U","fmt_type":"U 型","example":"lui x10, 0x12345",
     "machine_table":["imm[31:12] | rd | opcode=0110111"],
     "explanation":"20位立即数左移12位(低12位填0)写入 rd。"},
    {"name":"AUIPC","desc_short":"PC 加立即数","fmt":"U","fmt_type":"U 型","example":"auipc x5, 0x1",
     "machine_table":["imm[31:12] | rd | opcode=0010111"],
     "explanation":"PC + imm<<12 写入 rd。"},
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

# ── 寄存器表 ─────────────────────────────────────────────────
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

# ── 格式总览表 ──────────────────────────────────────────────
_FORMAT_TABLES = {
    "R": [("ADD","0000000","rs2","rs1","000","rd","0110011","加法"),("SUB","0100000","rs2","rs1","000","rd","0110011","减法"),
          ("XOR","0000000","rs2","rs1","100","rd","0110011","异或"),("OR","0000000","rs2","rs1","110","rd","0110011","或"),
          ("AND","0000000","rs2","rs1","111","rd","0110011","与"),("SLL","0000000","rs2","rs1","001","rd","0110011","逻辑左移"),
          ("SRL","0000000","rs2","rs1","101","rd","0110011","逻辑右移"),("SRA","0100000","rs2","rs1","101","rd","0110011","算术右移"),
          ("SLT","0000000","rs2","rs1","010","rd","0110011","有符号小于置位"),("SLTU","0000000","rs2","rs1","011","rd","0110011","无符号小于置位")],
    "I": [("ADDI","imm[11:0]","rs1","000","rd","0010011","立即数加法"),("XORI","imm[11:0]","rs1","100","rd","0010011","立即数异或"),
          ("ORI","imm[11:0]","rs1","110","rd","0010011","立即数或"),("ANDI","imm[11:0]","rs1","111","rd","0010011","立即数与"),
          ("SLLI","0000000 shamt","rs1","001","rd","0010011","逻辑左移立即数"),("SRLI","0000000 shamt","rs1","101","rd","0010011","逻辑右移立即数"),
          ("SRAI","0100000 shamt","rs1","101","rd","0010011","算术右移立即数"),("SLTI","imm[11:0]","rs1","010","rd","0010011","有符号小于立即数"),
          ("SLTIU","imm[11:0]","rs1","011","rd","0010011","无符号小于立即数"),("LW","imm[11:0]","rs1","010","rd","0000011","字加载")],
    "S": [("SB","imm[11:5]","rs2","rs1","000","imm[4:0]","0100011","存储字节"),("SH","imm[11:5]","rs2","rs1","001","imm[4:0]","0100011","存储半字"),
          ("SW","imm[11:5]","rs2","rs1","010","imm[4:0]","0100011","存储字")],
    "B": [("BEQ","imm[12|10:5]","rs2","rs1","000","imm[4:1|11]","1100011","相等跳转"),("BNE","imm[12|10:5]","rs2","rs1","001","imm[4:1|11]","1100011","不等跳转"),
          ("BLT","imm[12|10:5]","rs2","rs1","100","imm[4:1|11]","1100011","有符号小于跳转"),("BGE","imm[12|10:5]","rs2","rs1","101","imm[4:1|11]","1100011","有符号≥跳转"),
          ("BLTU","imm[12|10:5]","rs2","rs1","110","imm[4:1|11]","1100011","无符号小于跳转"),("BGEU","imm[12|10:5]","rs2","rs1","111","imm[4:1|11]","1100011","无符号≥跳转")],
    "U": [("LUI","imm[31:12]","rd","0110111","高位立即数加载"),("AUIPC","imm[31:12]","rd","0010111","PC加立即数")],
    "J": [("JAL","imm[20|10:1|11|19:12]","rd","1101111","跳转并链接")],
}

# ── 标签→区块映射 ──────────────────────────────────────────
_TAG_TO_SECTION = {"intro-intro":"intro","intro-regs":"intro","intro-overview":"intro"}
for _i in _INSTRUCTION_LIST:       _TAG_TO_SECTION[f"inst-{_i['name'].lower()}"] = _i["fmt"]
for _i in _CSR_INSTRUCTION_LIST:   _TAG_TO_SECTION[f"inst-{_i['name'].lower()}"] = "csr"
for _i in _PSEUDO_INSTRUCTION_LIST:_TAG_TO_SECTION[f"inst-{_i['name'].lower()}"] = "pseudo"


class LearnPage(ttk.Frame):
    """RISC-V 学习页面：左侧导航树 + 右侧分块渲染（区块缓存）"""

    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self._last_selected = "intro-intro"
        self._content_widgets: dict[str, tk.Widget] = {}
        self._images: list[tk.PhotoImage] = []
        self._sections: dict[str, ttk.Frame] = {}        # 区块缓存
        self._section_widgets: dict[str, dict] = {}       # 每区块的跳转引用
        self._current_section_key: str | None = None
        self.setup_ui()

    def setup_ui(self):
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # 全局样式：表格字体
        style = ttk.Style()
        style.configure("Treeview", font=("", 13), rowheight=30)
        style.configure("Treeview.Heading", font=("", 13, "bold"))

        # 左侧导航
        left = ttk.Frame(self, width=220)
        left.grid(row=0, column=0, sticky="ns", padx=(5, 0), pady=5)
        left.grid_propagate(False)
        ttk.Label(left, text="指令导航", font=("", 14, "bold")).pack(anchor="w", padx=5, pady=(5,5))
        self.tree = ttk.Treeview(left, show="tree", selectmode="browse")
        self.tree.pack(fill="both", expand=True, padx=5, pady=(0,5))
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self._build_nav_tree()

        # 右侧 Canvas + 滚动
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
        self.content_window = self.canvas.create_window((0,0), window=self.content_frame, anchor="nw", width=10)
        self.content_frame.bind("<Configure>", self._on_content_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # 鼠标滚轮：Canvas 聚焦 + 递归绑定内容区所有子控件
        self.canvas.bind("<Enter>", lambda e: self.canvas.focus_set())
        self._bind_mousewheel_recursive(self.content_frame)

        # 初始显示总述
        self.after(50, lambda: self._show_section("intro", "intro-intro"))

    def _on_content_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.content_window, width=event.width - 20)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ── 递归滚轮绑定 ───────────────────────────────────────
    def _bind_mousewheel_recursive(self, widget):
        """递归遍历 widget 子树，为每个非滚轮控件绑定 MouseWheel"""
        if isinstance(widget, (tk.Canvas, tk.Text)):
            return
        try:
            # 跳过已有自身滚轮的 ttk::treeview
            if widget.winfo_class() == "Treeview":
                return
        except tk.TclError:
            pass
        # 跳过 ttk::scrollbar
        try:
            if widget.winfo_class() in ("Scrollbar", "Radiobutton", "Checkbutton", "Button"):
                return
        except tk.TclError:
            pass
        widget.bind("<MouseWheel>", self._on_mousewheel)
        widget.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        widget.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))
        try:
            for child in widget.winfo_children():
                self._bind_mousewheel_recursive(child)
        except tk.TclError:
            pass

    # ── 导航树 ────────────────────────────────────────────────
    def _build_nav_tree(self):
        intro = self.tree.insert("", "end", text="总述", open=True)
        self.tree.insert(intro, "end", text="RISC-V 介绍", tags=("intro-intro",))
        self.tree.insert(intro, "end", text="寄存器一览表", tags=("intro-regs",))
        self.tree.insert(intro, "end", text="汇编与机器码总览表", tags=("intro-overview",))
        detail = self.tree.insert("", "end", text="基本语句说明", open=True)
        for fk, fn in [("R","R-type 指令"),("I","I-type 指令"),("S","S-type 指令"),("B","B-type 指令"),("U","U-type 指令"),("J","J-type 指令")]:
            node = self.tree.insert(detail, "end", text=fn, open=True)
            for inst in _INSTRUCTION_LIST:
                if inst["fmt"] == fk:
                    self.tree.insert(node, "end", text=f"{inst['name']} – {inst['desc_short']}", tags=(f"inst-{inst['name'].lower()}",))
        priv = self.tree.insert("", "end", text="特权指令 (Zicsr)", open=True)
        for inst in _CSR_INSTRUCTION_LIST:
            self.tree.insert(priv, "end", text=f"{inst['name']} – {inst['desc_short']}", tags=(f"inst-{inst['name'].lower()}",))
        pseudo = self.tree.insert("", "end", text="常用伪指令", open=True)
        for inst in _PSEUDO_INSTRUCTION_LIST:
            self.tree.insert(pseudo, "end", text=f"{inst['name']} – {inst['desc_short']}", tags=(f"inst-{inst['name'].lower()}",))

    # ── 分块渲染（区块缓存 + 隐藏/显示） ─────────────────────
    def _show_section(self, section_key: str, scroll_tag: str | None = None):
        # 1. 首次构建，缓存框架
        if section_key not in self._sections:
            new_frame = ttk.Frame(self.content_frame)
            new_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
            new_frame.columnconfigure(0, weight=1)

            self._content_widgets.clear()
            if section_key == "intro":
                self._build_intro_section(new_frame)
            elif section_key in ("R", "I", "S", "B", "U", "J"):
                self._build_format_section(new_frame, section_key)
            elif section_key == "csr":
                self._build_csr_section(new_frame)
            elif section_key == "pseudo":
                self._build_pseudo_section(new_frame)

            self._sections[section_key] = new_frame
            self._section_widgets[section_key] = self._content_widgets.copy()
            # 新区块的所有控件绑定滚轮
            self._bind_mousewheel_recursive(new_frame)

        # 2. 隐藏当前区块，显示目标区块
        if self._current_section_key and self._current_section_key in self._sections:
            self._sections[self._current_section_key].grid_remove()
        self._sections[section_key].grid()
        self._current_section_key = section_key
        self._content_widgets = self._section_widgets[section_key]

        # 3. 滚动至顶部，若指定标签则跳转
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.yview_moveto(0)
        if scroll_tag and scroll_tag in self._content_widgets:
            self.after(50, lambda: self._scroll_to_tag(scroll_tag))

    # ── 区块构建 ──────────────────────────────────────────
    def _build_intro_section(self, parent):
        self._h1(parent, "总述", "intro-intro")
        self._h2(parent, "RISC-V 介绍", "intro-intro")
        self._p(parent, "RISC-V（Reduced Instruction Set Computer V）是一种开源的指令集架构（ISA）。它采用精简指令集计算原则，设计简洁、高效且模块化，支持多种数据宽度。RISC-V 由加州大学伯克利分校于2010年发布，基于 RISC 原则。作为开源标准，RISC-V 允许任何个人或组织自由使用、修改和扩展。")
        self._ref(parent, "更多信息参考官网和诸多百科网站。")
        self._h2(parent, "寄存器意义编码一览表", "intro-regs")
        self._p(parent, "RISC-V32i 寄存器编码占5位，可命名为 x0~x31。")
        self._build_register_table(parent)
        self._h2(parent, "汇编指令对照机器码总览表", "intro-overview")
        self._p(parent, "RV32I 是32位基础整数指令集，支持32位寻址空间，小端格式。仅有40条指令，几乎能模拟所有扩展指令。")
        self._ref(parent, "参考文章：RISC-V RV32I Base Instruction Set（https://www.cnblogs.com/jerx2y/p/RISCV-RV32I.html）")
        for n in ("allcodes.png","typesdivision.png","picoftype.png"):
            self._image(parent, n)
        self._p(parent, "图像来自参考文章: 从零开始写 riscv 处理器（一）指令集（https://blog.csdn.net/mingtiauigena/article/details/150269814）")
        self._build_format_tables_treeview(parent)

    def _build_format_section(self, parent, fmt_key: str):
        nm = {"R":"R-type","I":"I-type","S":"S-type","B":"B-type","U":"U-type","J":"J-type"}
        self._h1(parent, f"{nm.get(fmt_key, fmt_key)} 指令")
        for inst in _INSTRUCTION_LIST:
            if inst["fmt"] == fmt_key:
                self._build_inst_card(parent, inst)

    def _build_csr_section(self, parent):
        self._h1(parent, "特权指令（Zicsr 扩展）")
        for inst in _CSR_INSTRUCTION_LIST:
            self._build_inst_card(parent, inst)

    def _build_pseudo_section(self, parent):
        self._h1(parent, "常用伪指令")
        for inst in _PSEUDO_INSTRUCTION_LIST:
            self._build_inst_card(parent, inst)

    # ── 排版 ──────────────────────────────────────────────
    def _h1(self, parent, text, tag=None):
        lbl = ttk.Label(parent, text=text, font=("",19,"bold"))
        lbl.grid(sticky="w", pady=(20,5))
        if tag: self._content_widgets[tag] = lbl

    def _h2(self, parent, text, tag=None):
        lbl = ttk.Label(parent, text=text, font=("",17,"bold"))
        lbl.grid(sticky="w", pady=(12,3))
        if tag: self._content_widgets[tag] = lbl

    def _h3(self, parent, text, tag=None):
        lbl = ttk.Label(parent, text=text, font=("",16,"bold"))
        lbl.grid(sticky="w", pady=(10,2))
        if tag: self._content_widgets[tag] = lbl

    def _p(self, parent, text):
        ttk.Label(parent, text=text, justify="left", anchor="w", wraplength=700, font=("",13)).grid(sticky="w", pady=2)

    def _code(self, parent, text):
        ttk.Label(parent, text=text, font=("Consolas",13), justify="left", anchor="w").grid(sticky="w", pady=1)

    def _ref(self, parent, text):
        ttk.Label(parent, text=text, foreground="#888888", font=("",11)).grid(sticky="w", pady=(0,4))

    def _image(self, parent, name):
        img = _load_gif(name)
        if img:
            self._images.append(img)
            ttk.Label(parent, image=img).grid(sticky="w", pady=5)
        else:
            ttk.Label(parent, text=f"[图片：{name}]", foreground="#999", background="#f0f0f0", font=("",11), padding=40).grid(sticky="ew", pady=5)

    def _build_register_table(self, parent):
        frame = ttk.LabelFrame(parent, text="寄存器编码表", padding=5)
        frame.grid(sticky="ew", pady=5)
        cols = ("编号","二进制","ABI名称","作用","调用约定")
        t = ttk.Treeview(frame, columns=cols, show="headings", height=len(_REGISTER_TABLE))
        for c in cols: t.heading(c, text=c)
        t.column("编号",width=60); t.column("二进制",width=80); t.column("ABI名称",width=85); t.column("作用",width=320); t.column("调用约定",width=85)
        for r in _REGISTER_TABLE: t.insert("","end",values=r)
        t.grid(sticky="ew")
        self._content_widgets["intro-regs"] = t

    def _build_format_tables_treeview(self, parent):
        cfg = {"R":("R型",["指令","funct7","rs2","rs1","funct3","rd","opcode","功能"]),
               "I":("I型",["指令","imm[11:0]","rs1","funct3","rd","opcode","功能"]),
               "S":("S型",["指令","imm[11:5]","rs2","rs1","funct3","imm[4:0]","opcode","功能"]),
               "B":("B型",["指令","imm[12|10:5]","rs2","rs1","funct3","imm[4:1|11]","opcode","功能"]),
               "U":("U型",["指令","imm[31:12]","rd","opcode","功能"]),
               "J":("J型",["指令","imm[20|10:1|11|19:12]","rd","opcode","功能"])}
        for fk,(title,cols) in cfg.items():
            data = _FORMAT_TABLES.get(fk)
            if not data: continue
            f = ttk.LabelFrame(parent, text=f"{title} 编码总览", padding=5)
            f.grid(sticky="ew", pady=5)
            t = ttk.Treeview(f, columns=cols, show="headings", height=len(data))
            for c in cols:
                t.heading(c, text=c)
                t.column(c, width=200 if c == "功能" else 110)
            for r in data: t.insert("","end",values=r)
            t.grid(sticky="ew")

    # ── 指令卡片（测试块始终可见） ────────────────────────
    def _build_inst_card(self, parent, inst):
        tag = f"inst-{inst['name'].lower()}"
        self._h3(parent, f"{inst['name']} – {inst['desc_short']}", tag)
        self._p(parent, f"类型：{inst['fmt_type']}")
        self._code(parent, f"示例：{inst['example']}")
        self._p(parent, "机器码格式：")
        for line in inst["machine_table"]:
            self._code(parent, f"  {line}")
        self._p(parent, inst["explanation"])

        # 测试块：始终可见
        ex = inst["example"]
        asm_val = ex if ex.startswith(inst["name"].lower()) else \
                  f"{inst['name'].lower()} {ex.split(' ',1)[-1]}" if " " in ex else \
                  f"{inst['name'].lower()} {ex}"

        f = ttk.LabelFrame(parent, text="试试看", padding=5)
        f.grid(sticky="ew", pady=(5,10))
        f.columnconfigure(1, weight=1)

        av = tk.StringVar(value=asm_val)
        hv = tk.StringVar()
        bv = tk.StringVar()
        st = ttk.Label(f, text="", foreground="#666")

        ttk.Label(f, text="汇编:",    font=("Consolas",12)).grid(row=0,column=0,sticky="w")
        ttk.Entry(f, textvariable=av, font=("Consolas",12)).grid(row=0,column=1,sticky="ew",padx=(0,4))
        ttk.Button(f, text="转换→",  width=8,
                   command=lambda: self._t_asm(av,hv,bv,st)).grid(row=0,column=2)

        ttk.Label(f, text="十六进制:", font=("Consolas",12)).grid(row=1,column=0,sticky="w",pady=(3,0))
        ttk.Entry(f, textvariable=hv, font=("Consolas",12)).grid(row=1,column=1,sticky="ew",padx=(0,4),pady=(3,0))
        ttk.Button(f, text="转换→",  width=8,
                   command=lambda: self._t_hex(hv,av,bv,st)).grid(row=1,column=2,pady=(3,0))

        ttk.Label(f, text="二进制:",  font=("Consolas",12)).grid(row=2,column=0,sticky="w",pady=(3,0))
        ttk.Entry(f, textvariable=bv, font=("Consolas",12)).grid(row=2,column=1,sticky="ew",padx=(0,4),pady=(3,0))
        ttk.Button(f, text="转换→",  width=8,
                   command=lambda: self._t_bin(bv,av,hv,st)).grid(row=2,column=2,pady=(3,0))

        st.grid(row=3,column=0,columnspan=3,sticky="w",pady=(2,0))
        # 自动执行一次
        self._t_asm(av,hv,bv,st)

    def _t_asm(self, a,h,b,s):
        t=a.get().strip()
        if not t: return
        d=assemble_line(t)
        if d: h.set(d.hex()); b.set(" ".join(f"{x:08b}" for x in d)); s.config(text="✅ 转换成功",foreground="green")
        else: h.set(""); b.set(""); s.config(text="❌ 转换失败",foreground="red")

    def _t_hex(self,h,a,b,s):
        t=h.get().strip()
        if len(t)!=8: s.config(text="需要8位十六进制",foreground="red"); return
        try:
            d=bytes.fromhex(t); r=disassemble_bytes(d)
            if r: a.set(r); b.set(" ".join(f"{x:08b}" for x in d)); s.config(text="✅ 转换成功",foreground="green")
            else: s.config(text="❌ 无效指令编码",foreground="red")
        except Exception as e: s.config(text=str(e),foreground="red")

    def _t_bin(self,b,a,h,s):
        t=b.get().strip().replace(" ","")
        if len(t)!=32: s.config(text="需要32位二进制",foreground="red"); return
        try:
            d=bytes(int(t[i:i+8],2) for i in range(0,32,8)); r=disassemble_bytes(d)
            if r: a.set(r); h.set(d.hex()); s.config(text="✅ 转换成功",foreground="green")
            else: s.config(text="❌ 无效指令编码",foreground="red")
        except Exception as e: s.config(text=str(e),foreground="red")

    # ── 跳转 ──────────────────────────────────────────────
    def _on_tree_select(self, event):
        s = self.tree.selection()
        if not s: return
        tags = self.tree.item(s[0], "tags")
        if not tags: return
        tag = tags[0]; self._last_selected = tag
        sec = _TAG_TO_SECTION.get(tag)
        if sec is None: return
        if sec != self._current_section_key:
            self._show_section(sec, tag)
        elif tag in self._content_widgets:
            self._scroll_to_tag(tag)

    def _scroll_to_tag(self, tag):
        w = self._content_widgets.get(tag)
        if not w: return
        self.canvas.update_idletasks()
        h = self.content_frame.winfo_height()
        if h > 0:
            y = self._get_widget_y(w)
            self.canvas.yview_moveto(max(0.0, min(1.0, y/h - 0.05)))
        try:
            o = w.cget("foreground")
            if o not in ("#3498db","blue",""):
                w.configure(foreground="#3498db")
                self.after(500, lambda w=w,fg=o: w.configure(foreground=fg))
        except tk.TclError: pass

    def _get_widget_y(self, widget):
        y = 0; w = widget
        while w and w is not self.content_frame:
            y += w.winfo_y(); w = w.master
        return y

    # ── 状态 ──────────────────────────────────────────────
    def load_state(self, state_data: dict):
        last = state_data.get("last_selected_instruction", "intro-intro")
        self._last_selected = last
        sec = _TAG_TO_SECTION.get(last, "intro")
        self.after(50, lambda: self._show_section(sec, last))

    def save_state(self) -> dict:
        return {"last_selected_instruction": self._last_selected}

    def reset(self):
        self._last_selected = "intro-intro"
        self._current_section_key = None
