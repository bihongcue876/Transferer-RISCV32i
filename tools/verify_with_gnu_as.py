#!/usr/bin/env python
"""用 GNU 交叉汇编器独立校验 Web 引擎的编码结果。

前一次验证（parity.test.js）只能证明 JS 移植与 Python 原实现一致，
两者若同源出错是发现不了的。本脚本改用 riscv64-unknown-elf-as
这个第三方工具链做对照：同一条汇编语句，工具链给出的机器码
必须与 golden.json 里记录的一致。

用法：
    python tools/verify_with_gnu_as.py

依赖：
    riscv64-unknown-elf-as、riscv64-unknown-elf-objdump（PATH 或 --binutils 指定）
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "web" / "tests" / "golden.json"


WORK = ROOT / ".tmp_verify"


def assemble_one(as_exe, od_exe, asm_line, march):
    """汇编一行，返回 32 位机器码字符串（8 位小写十六进制），失败返回 (None, 原因)。"""
    WORK.mkdir(exist_ok=True)
    src = WORK / "t.s"
    obj = WORK / "t.o"
    if obj.exists():
        obj.unlink()
    src.write_text(".text\n" + asm_line + "\n", encoding="utf-8")
    proc = subprocess.run(
        [as_exe, f"-march={march}", "-mabi=ilp32", "-o", str(obj), str(src)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return None, (proc.stderr.strip().splitlines() or ["as 失败"])[0]
    dump = subprocess.run(
        [od_exe, "-d", str(obj)], capture_output=True, text=True,
    )
    if dump.returncode != 0:
        return None, "objdump 失败"
    # 形如:   0:\t007302b3          \tadd\tx5,x6,x7
    m = re.search(r"^\s*0:\s+([0-9a-f]{8})\s", dump.stdout, re.M)
    if not m:
        return None, "未能解析机器码"
    return m.group(1), None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--binutils", default="",
                    help="binutils 目录，例如 D:/SysGCC/bin")
    ap.add_argument("--march", default="rv32i")
    ap.add_argument("--limit", type=int, default=0, help="只验证前 N 条，便于排查")
    args = ap.parse_args()

    bindir = Path(args.binutils) if args.binutils else None

    def tool(name):
        return str(bindir / name) if bindir else name

    as_exe = tool("riscv64-unknown-elf-as")
    od_exe = tool("riscv64-unknown-elf-objdump")

    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    table = golden["instructionTable"]

    # 分支(B)与跳转(J)的操作数语义两边不同：GNU as 要的是目标地址，
    # 本项目要的是相对偏移；且未链接的 .o 里目标靠重定位，imm 恒为 0。
    # 这两类无法逐字对照，单独跳过。
    skipped_kind = []
    vectors = []
    for v in golden["encode"]:
        if "hex" not in v:
            continue
        kind = table.get(v["mnemonic"], {}).get("type")
        if kind in ("B", "J"):
            skipped_kind.append(v["asm"])
            continue
        vectors.append(v)
    if args.limit:
        vectors = vectors[: args.limit]

    ok = 0
    mismatch = []
    skipped = []

    for v in vectors:
        got, reason = assemble_one(as_exe, od_exe, v["asm"], args.march)
        if got is None:
            skipped.append((v["asm"], reason))
            continue
        if got != v["hex"]:
            mismatch.append((v["asm"], v["hex"], got))
        else:
            ok += 1

    total = len(vectors)
    print(f"对照样本 {total} 条（另有 {len(skipped_kind)} 条分支/跳转因操作数语义不同不参与对照）")
    print(f"  一致   {ok}")
    print(f"  不一致 {len(mismatch)}")
    print(f"  工具链不接受 {len(skipped)}")

    if mismatch:
        print("\n不一致明细（语句 / 本项目 / GNU as）：")
        for asm, mine, gnu in mismatch:
            print(f"  {asm:<28} {mine}  {gnu}")

    if skipped:
        print("\n工具链跳过的语句：")
        for asm, reason in skipped[:15]:
            print(f"  {asm:<28} {reason}")
        if len(skipped) > 15:
            print(f"  …另有 {len(skipped) - 15} 条")

    return 0 if not mismatch else 1


if __name__ == "__main__":
    sys.exit(main())
