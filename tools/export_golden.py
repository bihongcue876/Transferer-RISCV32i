#!/usr/bin/env python
"""导出 Web 版金标准向量与学习页数据。

Web 演示页的引擎是 core/ 的 JavaScript 移植版。为了让移植结果与原实现
逐位一致，本脚本调用原实现生成一批「输入 -> 期望输出」向量，Web 侧的
node:test 对拍测试读取同一份向量逐条比对。

用法：
    python tools/export_golden.py

输出：
    web/tests/golden.json          编解码/伪指令/汇编程序的期望结果
    web/src/data/instructions.json 学习页 37 条指令卡片
    web/src/data/format-tables.json 六种格式的字段矩阵

只要 core/ 的行为变了，重跑本脚本，Web 侧测试变红即说明两边分叉。
"""
import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.isa_rv32i import (  # noqa: E402
    RV32I_INSTRUCTIONS,
    PSEUDO_INSTRUCTIONS,
    REG_ALIASES,
    encode,
    decode,
    expand_pseudo,
    is_pseudo,
)
from core.assembler import assemble_program  # noqa: E402

WEB = ROOT / "web"
DATA_DIR = WEB / "src" / "data"
TEST_DIR = WEB / "tests"


# ── 工具函数 ─────────────────────────────────────────────────

def word_hex(word: int) -> str:
    return f"{word & 0xFFFFFFFF:08x}"


def le_hex(word: int) -> str:
    return (word & 0xFFFFFFFF).to_bytes(4, "little").hex()


def make_vector(mnemonic: str, operands: list[str]) -> dict:
    """编码一条指令，返回向量；失败返回带 error 的向量。"""
    asm = mnemonic if not operands else f"{mnemonic} {', '.join(operands)}"
    try:
        word = encode(mnemonic, operands)
    except Exception as exc:  # ValueError 及意外异常都记下来
        return {"asm": asm, "mnemonic": mnemonic, "operands": operands,
                "error": str(exc)}
    name, ops = decode(word)
    return {
        "asm": asm,
        "mnemonic": mnemonic,
        "operands": operands,
        "word": word & 0xFFFFFFFF,
        "hex": word_hex(word),
        "le": le_hex(word),
        "decodeName": name,
        "decodeOperands": ops,
    }


def candidates_for(name: str, info: dict) -> list[list[str]]:
    """按指令类型给出候选操作数组合。"""
    t = info["type"]
    if t == "R":
        return [["x5", "x6", "x7"], ["a0", "a1", "a2"], ["x0", "x31", "x1"]]
    if t == "I":
        if name in ("slli", "srli", "srai"):
            return [["x5", "x6", "0"], ["x5", "x6", "31"], ["a0", "a1", "1"]]
        return [
            ["x5", "x6", "0"], ["a0", "a1", "-1"],
            ["x1", "x2", "2047"], ["x3", "x4", "-2048"],
            ["t0", "t1", "0x7ff"],
        ]
    if t == "I_LOAD":
        return [
            ["x5", "0(x6)"], ["a0", "-4(sp)"],
            ["x1", "2047(x2)"], ["x3", "-2048(x4)"],
        ]
    if t == "I_JALR":
        return [["x1", "0(x6)"], ["x5", "-4(x6)"], ["x0", "x1", "0"]]
    if t == "S":
        return [
            ["x5", "0(x6)"], ["a0", "-8(sp)"],
            ["x1", "2047(x2)"], ["x3", "-2048(x4)"],
        ]
    if t == "B":
        return [
            ["x5", "x6", "0"], ["a0", "a1", "4"], ["x1", "x2", "-4"],
            ["x3", "x4", "4094"], ["x5", "x6", "-4096"],
        ]
    if t == "U":
        return [["x5", "0x12345"], ["a0", "0"], ["x1", "0xfffff"]]
    if t == "J":
        return [
            ["x1", "0"], ["x5", "4"], ["x6", "-4"],
            ["ra", "1048574"], ["x2", "-1048576"],
        ]
    if t == "I_SYSTEM":
        return [[]]
    if t == "I_CSR":
        if info["funct3"] in (0b101, 0b110, 0b111):
            return [["x5", "0x300", "0"], ["a0", "0x001", "31"]]
        return [["x5", "0x300", "x6"], ["a0", "0xfff", "ra"]]
    if t == "I_FENCE":
        return [["iorw", "iorw"], ["r", "w"], ["0", "0"], ["i", "o"]]
    return [[]]


# 故意写错的输入，用于固定错误文案
BAD_INPUTS = [
    ("add", ["x1", "x2"]),
    ("add", ["x1", "x2", "x32"]),
    ("addi", ["x1", "x2", "2048"]),
    ("addi", ["x1", "x2", "-2049"]),
    ("lw", ["x1", "0"]),
    ("sw", ["x1", "x2", "x3"]),
    ("beq", ["x1", "x2", "3"]),
    ("beq", ["x1", "x2", "4096"]),
    ("jal", ["x1", "2"]),
    ("jal", ["x1", "1048576"]),
    ("lui", ["x1", "1048576"]),
    ("csrrw", ["x1", "4096", "x2"]),
    ("csrrwi", ["x1", "0x300", "32"]),
    ("slli", ["x1", "x2", "32"]),
    ("nosuch", ["x1"]),
    ("add", ["x1", "x2", "ra"]),
    ("add", ["x1", "x2", "zero"]),
    ("add", ["x1", "x2", "x03"]),
]

# 多行程序样本：标签、PC 相对、锚点、错误混合
PROGRAMS = [
    {
        "name": "basic",
        "lines": [
            "addi x1, x2, 100",
            "sw x5, -8(sp)",
            "lw x6, 0(x1)",
            "ecall",
        ],
        "addrLines": None,
    },
    {
        "name": "labels",
        "lines": [
            "start: addi x1, x0, 0",
            "loop: addi x1, x1, 1",
            "blt x1, x2, loop",
            "j start",
            "nop",
        ],
        "addrLines": None,
    },
    {
        "name": "pcrel",
        "lines": [
            "main: la x6, data",
            "call func",
            "tail func",
            "ret",
            "func: addi x1, x0, 1",
            "ret",
            "data: addi x2, x0, 2",
        ],
        "addrLines": None,
    },
    {
        "name": "pseudo",
        "lines": [
            "li x1, 0",
            "li x2, 2047",
            "li x3, 0x12345",
            "mv x4, x5",
            "not x6, x7",
            "neg x8, x9",
            "seqz x10, x11",
            "beqz x12, 8",
        ],
        "addrLines": None,
    },
    {
        "name": "anchors",
        "lines": [
            "addi x1, x2, 1",
            "addi x1, x2, 2",
            "addi x1, x2, 3",
            "addi x1, x2, 4",
        ],
        "addrLines": ["", "00001000", "", ""],
    },
    {
        "name": "errors",
        "lines": [
            "addi x1, x2, 99999",
            "foo x1",
            "addi x1, x2",
            "dup: nop",
            "dup: nop",
            "beq x1, x2, nowhere",
            "",
            "add x5, x6, x7",
        ],
        "addrLines": None,
    },
    {
        "name": "comments",
        "lines": [
            "# 纯注释行",
            "addi x1, x2, 1  # 行尾注释",
            "   ",
            "label_only:",
            "addi x1, x2, 2",
        ],
        "addrLines": None,
    },
]


def serialise_program(sample: dict) -> dict:
    lines = sample["lines"]
    addr_lines = sample.get("addrLines")
    results = assemble_program(lines, addr_lines)
    out = []
    for r in results:
        chunks = []
        for c in r["chunks"]:
            data = c.get("data")
            chunks.append({
                "mnemonic": c["mnemonic"],
                "text": c["text"],
                "le": data.hex() if data else None,
                "error": c["error"],
            })
        out.append({
            "labels": r["labels"],
            "address": r["address"],
            "size": r["size"],
            "chunks": chunks,
            "error": r["error"],
        })
    return {
        "name": sample["name"],
        "lines": lines,
        "addrLines": addr_lines,
        "result": out,
    }


def build_golden() -> dict:
    encode_vectors = []
    error_vectors = []

    for name, info in RV32I_INSTRUCTIONS.items():
        for operands in candidates_for(name, info):
            vec = make_vector(name, operands)
            if "error" in vec:
                error_vectors.append(vec)
            else:
                encode_vectors.append(vec)

    for mnemonic, operands in BAD_INPUTS:
        vec = make_vector(mnemonic, operands)
        if "error" in vec:
            error_vectors.append(vec)

    # 伪指令：展开序列 + 编码结果
    pseudo_vectors = []
    pseudo_candidates = {
        "li": [["x1", "0"], ["x2", "2047"], ["x3", "-2048"], ["x4", "0x12345"],
               ["x5", "-1"], ["x6", "0x800"]],
        "mv": [["x1", "x2"]],
        "not": [["x1", "x2"]],
        "neg": [["x1", "x2"]],
        "la": [["x1", "0x1000"]],
        "nop": [[]],
        "unimp": [[]],
        "ret": [[]],
        "call": [["0x100"]],
        "tail": [["0x100"]],
        "j": [["0x20"]],
        "jr": [["x1"]],
        "jalr": [["x1"], ["x1", "x2"]],
        "beqz": [["x1", "8"]],
        "bnez": [["x1", "8"]],
        "blez": [["x1", "8"]],
        "bgez": [["x1", "8"]],
        "bltz": [["x1", "8"]],
        "bgtz": [["x1", "8"]],
        "seqz": [["x1", "x2"]],
        "snez": [["x1", "x2"]],
        "sltz": [["x1", "x2"]],
        "sgtz": [["x1", "x2"]],
        "bgt": [["x1", "x2", "8"]],
        "ble": [["x1", "x2", "8"]],
        "bgtu": [["x1", "x2", "8"]],
        "bleu": [["x1", "x2", "8"]],
    }
    for name in PSEUDO_INSTRUCTIONS:
        for operands in pseudo_candidates.get(name, [[]]):
            asm = name if not operands else f"{name} {', '.join(operands)}"
            try:
                expanded = expand_pseudo(name, operands)
            except Exception as exc:
                pseudo_vectors.append({
                    "asm": asm, "mnemonic": name, "operands": operands,
                    "error": str(exc),
                })
                continue
            chunks = []
            ok = True
            for mnem, ops in expanded:
                try:
                    word = encode(mnem, ops)
                    chunks.append({
                        "mnemonic": mnem, "operands": ops,
                        "word": word & 0xFFFFFFFF,
                        "hex": word_hex(word),
                        "le": le_hex(word),
                    })
                except Exception as exc:
                    ok = False
                    chunks.append({"mnemonic": mnem, "operands": ops,
                                   "error": str(exc)})
            pseudo_vectors.append({
                "asm": asm,
                "mnemonic": name,
                "operands": operands,
                "expand": [[m, list(o)] for m, o in expanded],
                "chunks": chunks,
                "ok": ok,
            })

    return {
        "meta": {
            "generatedBy": "tools/export_golden.py",
            "version": 1,
            "instructionCount": len(RV32I_INSTRUCTIONS),
            "pseudoCount": len(PSEUDO_INSTRUCTIONS),
            "registerAliasCount": len(REG_ALIASES),
            "encodeCount": len(encode_vectors),
            "errorCount": len(error_vectors),
            "pseudoVectorCount": len(pseudo_vectors),
            "programCount": len(PROGRAMS),
        },
        "registers": REG_ALIASES,
        "instructionTable": {
            name: {k: v for k, v in info.items()}
            for name, info in RV32I_INSTRUCTIONS.items()
        },
        "pseudoNames": sorted(PSEUDO_INSTRUCTIONS),
        "encode": encode_vectors,
        "errors": error_vectors,
        "pseudo": pseudo_vectors,
        "programs": [serialise_program(p) for p in PROGRAMS],
    }


def extract_learn_data() -> tuple[list, dict]:
    """用 ast 解析 ui/learn_page.py，取出指令卡片与格式表。"""
    src = (ROOT / "ui" / "learn_page.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            target = getattr(node.targets[0], "id", "")
            if target in ("_INSTRUCTION_LIST", "_FORMAT_TABLES"):
                found[target] = ast.literal_eval(node.value)
    return found.get("_INSTRUCTION_LIST", []), found.get("_FORMAT_TABLES", {})


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TEST_DIR.mkdir(parents=True, exist_ok=True)

    golden = build_golden()
    (TEST_DIR / "golden.json").write_text(
        json.dumps(golden, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    instructions, format_tables = extract_learn_data()
    (DATA_DIR / "instructions.json").write_text(
        json.dumps(instructions, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    (DATA_DIR / "format-tables.json").write_text(
        json.dumps(format_tables, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    meta = golden["meta"]
    print("golden.json 生成完毕")
    print(f"  指令表      {meta['instructionCount']} 条")
    print(f"  伪指令      {meta['pseudoCount']} 条")
    print(f"  寄存器别名  {meta['registerAliasCount']} 个")
    print(f"  编码向量    {meta['encodeCount']} 条")
    print(f"  错误向量    {meta['errorCount']} 条")
    print(f"  伪指令向量  {meta['pseudoVectorCount']} 条")
    print(f"  程序样本    {meta['programCount']} 个")
    print(f"  指令卡片    {len(instructions)} 张")
    print(f"  格式表      {len(format_tables)} 张")


if __name__ == "__main__":
    main()
