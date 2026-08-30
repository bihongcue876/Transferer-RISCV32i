import re
import pickle
from pathlib import Path
from typing import Optional
from core.isa_rv32i import (
    encode,
    decode,
    is_pseudo,
    expand_pseudo,
    get_format,
    parse_int,
    RV32I_INSTRUCTIONS,
)


CACHE_DIR = Path("_cachedata")
STATE_FILE = CACHE_DIR / "state.dat"

# 标签：字母/下划线/./$ 开头，后接字母数字/./$
LABEL_RE = re.compile(r"^\s*([A-Za-z_.$][A-Za-z0-9_.$]*)\s*:")
_LABEL_TOKEN_RE = re.compile(r"^[A-Za-z_.$][A-Za-z0-9_.$]*$")

# 需要标签解析为 auipc+xxx 的伪指令（固定展开为 2 条指令）
LABEL_PSEUDOS = ("la", "call", "tail")

# 尾操作数为跳转偏移的指令（标签 → 数值偏移）
_OFFSET_TAIL = {"beq", "bne", "blt", "bge", "bltu", "bgeu", "jal"}


def machine_code_to_bytes(machine_code: int) -> bytes:
    return bytes([
        machine_code & 0xFF,
        (machine_code >> 8) & 0xFF,
        (machine_code >> 16) & 0xFF,
        (machine_code >> 24) & 0xFF,
    ])


def bytes_to_hex_str(data: bytes) -> str:
    return data.hex()


def bytes_to_bin_str(data: bytes) -> str:
    return " ".join(f"{b:08b}" for b in data)


def format_machine_bytes(data: bytes, mode: str) -> str:
    if mode == "hex":
        return data.hex()
    elif mode == "bin":
        return " ".join(f"{b:08b}" for b in data)
    return data.hex()


def format_machine_bytes_endian(data: bytes, mode: str, endian: str = "little") -> str:
    if endian == "big":
        data = bytes(reversed(data))
    return format_machine_bytes(data, mode)


def parse_address(addr_str: str) -> Optional[int]:
    addr_str = addr_str.strip().lower()
    if addr_str.startswith("0x"):
        return int(addr_str, 16)
    elif addr_str.startswith("-0x"):
        return -int(addr_str[1:], 16)
    elif addr_str.lstrip("-").isdigit():
        return int(addr_str)
    return None


# ── 行解析 ───────────────────────────────────────────────────

def strip_comment(line: str) -> str:
    for marker in ("#", "//"):
        idx = line.find(marker)
        if idx != -1:
            line = line[:idx]
    return line.strip()


def split_labels(line: str) -> tuple[list[str], str]:
    """提取行首的所有标签定义，返回 (标签列表, 剩余指令文本)。"""
    labels = []
    rest = line
    while True:
        m = LABEL_RE.match(rest)
        if not m:
            break
        labels.append(m.group(1))
        rest = rest[m.end():]
    return labels, rest.strip()


def _instruction_text(mnem: str, ops: list[str]) -> str:
    return f"{mnem} {', '.join(ops)}" if ops else mnem


# ── 标签解析辅助 ─────────────────────────────────────────────

def _resolve_tail_label(mnem: str, ops: list[str], pc: int, symbols: dict) -> list[str]:
    """将末位操作数中的标签替换为相对 pc 的数值偏移。"""
    if mnem in _OFFSET_TAIL and ops:
        tok = ops[-1]
        try:
            parse_int(tok)
            return ops
        except ValueError:
            if tok in symbols:
                return ops[:-1] + [str(symbols[tok] - pc)]
            if _LABEL_TOKEN_RE.match(tok):
                raise ValueError(f"未知标签: {tok}")
            raise
    return ops


def _pcrel_parts(off: int) -> tuple[int, int]:
    """PC 相对偏移 → (auipc 20位立即数, addi/jalr 12位立即数)。"""
    hi = ((off + 0x800) >> 12) & 0xFFFFF
    hi_signed = hi - 0x100000 if hi & 0x80000 else hi
    lo = off - (hi_signed << 12)
    return hi, lo


def _expand_label_pseudo(name: str, ops: list[str], off: int) -> list[tuple[str, list[str]]]:
    """off 为目标地址相对当前指令的偏移（调用前已减去 pc）。"""
    hi, lo = _pcrel_parts(off)
    if name == "la":
        rd = ops[0]
        return [("auipc", [rd, str(hi << 12)]), ("addi", [rd, rd, str(lo)])]
    if name == "call":
        return [("auipc", ["x1", str(hi << 12)]), ("jalr", ["x1", "x1", str(lo)])]
    # tail
    return [("auipc", ["x6", str(hi << 12)]), ("jalr", ["x0", "x6", str(lo)])]


def _encode_chunk(mnem: str, ops: list[str], pc: int, symbols: dict) -> dict:
    text = _instruction_text(mnem, ops)
    try:
        ops2 = _resolve_tail_label(mnem, ops, pc, symbols)
        code = encode(mnem, ops2)
        return {
            "mnemonic": mnem,
            "text": _instruction_text(mnem, ops2),
            "data": machine_code_to_bytes(code),
            "error": None,
        }
    except ValueError as e:
        return {"mnemonic": mnem, "text": text, "data": None, "error": str(e)}
    except Exception as e:
        return {"mnemonic": mnem, "text": text, "data": None, "error": f"{mnem}: {e}"}


# ── 两遍汇编 ─────────────────────────────────────────────────

def _plan_line(line: str) -> dict:
    """第一遍：解析标签与指令结构，确定块数。"""
    text = strip_comment(line)
    labels, rest = split_labels(text)
    plan = {"labels": labels, "name": None, "operands": [], "count": 0, "error": None}
    if not rest:
        return plan
    parts = rest.replace(",", " ").split()
    if not parts:
        return plan
    name = parts[0].lower()
    operands = parts[1:]
    plan["name"] = name
    plan["operands"] = operands
    if name in LABEL_PSEUDOS:
        plan["count"] = 2
        return plan
    if is_pseudo(name):
        try:
            plan["count"] = len(expand_pseudo(name, operands))
        except ValueError as e:
            plan["count"] = 1
            plan["error"] = str(e)
        except IndexError:
            plan["count"] = 1
            plan["error"] = f"{name}: 操作数不足"
        return plan
    if name in RV32I_INSTRUCTIONS:
        plan["count"] = 1
        return plan
    plan["count"] = 1
    plan["error"] = f"未知指令: {name}"
    return plan


def compute_addresses(addr_lines: list[str], sizes: list[int]) -> list[str]:
    """
    根据每行占用的字节数与手动地址锚点，计算每行显示地址。
    规则：
    - 手动输入的地址（有效十六进制）作为锚点，绝对保留；
    - 自动行从上一行末尾递增（按该行实际字节数推进）；
    - 零字节行（纯标签行）显示当前地址但不推进；
    - 即将越过下一个锚点的自动行留空（不推进）。
    """
    anchors = {}
    for i, line in enumerate(addr_lines or []):
        stripped = line.strip()
        if stripped:
            try:
                anchors[i] = int(stripped, 16)
            except ValueError:
                pass
    anchor_keys = sorted(anchors.keys())

    result = []
    current_addr = 0
    for i, size in enumerate(sizes):
        if i in anchors:
            result.append(f"{anchors[i]:08x}")
            current_addr = anchors[i] + size
            continue
        next_anchor = next((k for k in anchor_keys if k > i), None)
        if size == 0:
            result.append(f"{current_addr:08x}")
        elif next_anchor is not None and current_addr >= anchors[next_anchor]:
            result.append("")
        else:
            result.append(f"{current_addr:08x}")
            current_addr += size
    return result


def assemble_program(lines: list[str], addr_lines: Optional[list[str]] = None,
                     base_addr: int = 0) -> list[dict]:
    """
    两遍汇编。
    第一遍：收集标签 → 符号表；确定每行指令块数与地址。
    第二遍：逐块编码，解析标签为偏移/PC相对地址。
    返回与输入行一一对应的结果列表：
    {
      "labels": [str],
      "address": int,
      "size": int,
      "chunks": [{"mnemonic", "text", "data": bytes|None, "error": str|None}],
      "error": str|None,   # 行级错误（重复标签/解析错误/首个块错误）
    }
    """
    plans = [_plan_line(l) for l in lines]
    sizes = [4 * p["count"] for p in plans]

    if addr_lines is None:
        addrs = []
        cur = base_addr
        for s in sizes:
            addrs.append(f"{cur:08x}")
            cur += s
    else:
        addrs = compute_addresses(addr_lines, sizes)

    # 第一遍：符号表
    symbols: dict[str, int] = {}
    dup_errors: dict[int, str] = {}
    last_addr = 0
    for i, plan in enumerate(plans):
        row_addr = int(addrs[i], 16) if addrs[i] else last_addr
        last_addr = row_addr
        for lab in plan["labels"]:
            if lab in symbols:
                dup_errors.setdefault(i, f"重复定义标签: {lab}")
            else:
                symbols[lab] = row_addr

    # 第二遍：逐块编码
    results = []
    for i, plan in enumerate(plans):
        pc = int(addrs[i], 16) if addrs[i] else 0
        chunks: list[dict] = []
        line_err = dup_errors.get(i) or plan["error"]
        name = plan["name"]
        operands = plan["operands"]

        if name is None:
            pass
        elif name in LABEL_PSEUDOS and operands and operands[-1] in symbols:
            target = symbols[operands[-1]]
            off = target - pc
            seq = _expand_label_pseudo(name, operands, off)
            for j, (mnem, ops2) in enumerate(seq):
                chunks.append(_encode_chunk(mnem, ops2, pc + 4 * j, symbols))
        elif is_pseudo(name):
            try:
                seq = expand_pseudo(name, operands)
            except ValueError as e:
                line_err = line_err or str(e)
                seq = []
            except IndexError:
                line_err = line_err or f"{name}: 操作数不足"
                seq = []
            for j, (mnem, ops2) in enumerate(seq):
                chunks.append(_encode_chunk(mnem, ops2, pc + 4 * j, symbols))
        else:
            chunks.append(_encode_chunk(name, operands, pc, symbols))

        chunk_err = next((c["error"] for c in chunks if c["error"]), None)
        results.append({
            "labels": plan["labels"],
            "address": pc,
            "size": sum(len(c["data"]) for c in chunks if c["data"]),
            "chunks": chunks,
            "error": line_err or chunk_err,
        })
    return results


def assemble_line(line: str, current_address: int = 0) -> bytes:
    """单行汇编（无标签上下文），多指令行（伪指令展开）返回拼接字节，失败返回空字节串。"""
    results = assemble_program([line], None, base_addr=current_address)
    datas = [c["data"] for c in results[0]["chunks"] if c["data"]]
    return b"".join(datas)


def assemble_line_hex(line: str, current_address: int = 0) -> str:
    result = assemble_line(line, current_address)
    return result.hex() if result else ""


def disassemble_bytes(data: bytes) -> Optional[str]:
    if len(data) != 4:
        return None
    try:
        machine_code = int.from_bytes(data, "little")
        name, operands = decode(machine_code)
        if name is None:
            return None
        if operands:
            return f"{name} {', '.join(operands)}"
        return name
    except Exception:
        return None


def disassemble_hex(hex_str: str) -> Optional[str]:
    hex_str = hex_str.strip().lower()
    if len(hex_str) != 8:
        return None
    try:
        data = bytes.fromhex(hex_str)
        return disassemble_bytes(data)
    except Exception:
        return None


def analyze_assembly_line(line: str, symbols: Optional[dict] = None,
                          symbol_addrs: Optional[dict] = None) -> dict:
    """
    单行浅析（不生成机器码时的提示信息）。
    symbols: 已知标签集合；symbol_addrs: 标签 → 地址。
    """
    result = {
        "valid": False,
        "format": "",
        "name": "",
        "operands": [],
        "labels": [],
        "detail": "",
        "error": "",
        "expanded_count": 1,
    }
    text = strip_comment(line)
    labels, rest = split_labels(text)
    result["labels"] = labels

    if not rest:
        if labels:
            result["valid"] = True
            result["format"] = "Label"
            result["name"] = labels[0]
            if symbol_addrs and labels[0] in symbol_addrs:
                result["detail"] = f"标签 {labels[0]} → 地址 0x{symbol_addrs[labels[0]]:08x}"
        return result

    parts = rest.replace(",", " ").split()
    if not parts:
        return result
    name = parts[0].lower()
    operands = parts[1:]
    result["name"] = name
    result["operands"] = operands
    if isinstance(symbol_addrs, dict) and symbol_addrs:
        sym = dict(symbol_addrs)
    elif isinstance(symbols, dict):
        sym = symbols
    else:
        # symbols 为集合（只有名字没有地址）
        sym = {s: 0 for s in (symbols or ())}

    try:
        if name in LABEL_PSEUDOS and symbols is not None and operands and operands[-1] in symbols:
            result["format"] = "Pseudo"
            result["valid"] = True
            result["expanded_count"] = 2
            if symbol_addrs and operands[-1] in symbol_addrs:
                result["detail"] = (
                    f"{name} {operands[-1]} → 目标地址 0x{symbol_addrs[operands[-1]]:08x} "
                    f"(展开为 auipc + {'jalr' if name != 'la' else 'addi'})"
                )
            return result

        if is_pseudo(name):
            result["format"] = "Pseudo"
            expanded = expand_pseudo(name, operands)
            result["expanded_count"] = len(expanded)
            ok = 0
            first_err = ""
            for mn, mo in expanded:
                try:
                    mo2 = _resolve_tail_label(mn, mo, 0, sym)
                    encode(mn, mo2)
                    ok += 1
                except ValueError as e:
                    if not first_err:
                        first_err = str(e)
            if expanded and ok == len(expanded):
                result["valid"] = True
                inner = get_format(expanded[0][0]) if len(expanded) == 1 else "Pseudo"
                result["format"] = inner if len(expanded) == 1 else f"Pseudo (展开 {len(expanded)} 条)"
            else:
                result["error"] = first_err or "操作数无效"
            return result

        if name in RV32I_INSTRUCTIONS:
            ops2 = _resolve_tail_label(name, operands, 0, sym)
            encode(name, ops2)
            result["valid"] = True
            result["format"] = get_format(name)
        else:
            result["error"] = f"未知指令: {name}"
    except ValueError as e:
        result["error"] = str(e)
    except Exception as e:
        result["error"] = str(e)
    return result


# ── 状态缓存 ─────────────────────────────────────────────────

def load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        with open(STATE_FILE, "rb") as f:
            return pickle.load(f)
    except Exception:
        return {}


def save_state(data: dict):
    if not CACHE_DIR.exists():
        CACHE_DIR.mkdir()
    try:
        with open(STATE_FILE, "wb") as f:
            pickle.dump(data, f)
    except Exception:
        pass


def clear_cache():
    if not CACHE_DIR.exists():
        return
    for file in CACHE_DIR.iterdir():
        if file.is_file():
            try:
                file.unlink()
            except Exception:
                pass
