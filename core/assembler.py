import pickle
from pathlib import Path
from typing import Optional
from core.isa_rv32i import encode, decode, is_pseudo, expand_pseudo, get_format, RV32I_INSTRUCTIONS


CACHE_DIR = Path("_cachedata")
STATE_FILE = CACHE_DIR / "state.dat"


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


def parse_address(addr_str: str) -> Optional[int]:
    addr_str = addr_str.strip().lower()
    if addr_str.startswith("0x"):
        return int(addr_str, 16)
    elif addr_str.startswith("-0x"):
        return -int(addr_str[1:], 16)
    elif addr_str.lstrip("-").isdigit():
        return int(addr_str)
    return None


def assemble_line(line: str, current_address: int = 0) -> bytes:
    line = line.strip()
    if not line or line.startswith("#"):
        return b""
    if "#" in line:
        line = line.split("#")[0].strip()
    if not line:
        return b""
    try:
        parts = line.replace(",", " ").split()
        if not parts:
            return b""
        name = parts[0].lower()
        operands = parts[1:]
        
        if is_pseudo(name):
            expanded = expand_pseudo(name, operands)
            result = b""
            for inst_name, inst_operands in expanded:
                inst_operands = _process_operands(inst_name, inst_operands, current_address)
                machine_code = encode(inst_name, inst_operands)
                result += machine_code_to_bytes(machine_code)
            return result
        else:
            operands = _process_operands(name, operands, current_address)
            machine_code = encode(name, operands)
            return machine_code_to_bytes(machine_code)
    except Exception:
        return b""


def _process_operands(name: str, operands: list[str], current_address: int) -> list[str]:
    # 暂时不做地址偏移计算，直接返回原操作数
    # 后续如需支持标签跳转，可在此处扩展
    return operands


def assemble_line_hex(line: str, current_address: int = 0) -> str:
    result = assemble_line(line, current_address)
    if result:
        return result.hex()
    return ""


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


def format_machine_bytes_endian(data: bytes, mode: str, endian: str = "little") -> str:
    if endian == "big":
        data = bytes(reversed(data))
    return format_machine_bytes(data, mode)


def analyze_assembly_line(line: str) -> dict:
    result = {
        "valid": False,
        "format": "",
        "name": "",
        "operands": [],
        "immediate": None,
        "error": "",
        "expanded_count": 1,
    }
    line = line.strip()
    if not line or line.startswith("#"):
        result["valid"] = False
        return result
    if "#" in line:
        line = line.split("#")[0].strip()
    if not line:
        return result
    try:
        parts = line.replace(",", " ").split()
        if not parts:
            return result
        name = parts[0].lower()
        operands = parts[1:]
        result["name"] = name
        result["operands"] = operands
        if is_pseudo(name):
            result["format"] = "Pseudo"
            expanded = expand_pseudo(name, operands)
            inner = []
            for rn, ro in expanded:
                try:
                    code = encode(rn, ro)
                    inner.append((rn, ro, code))
                except Exception:
                    pass
            result["valid"] = len(inner) > 0
            result["expanded_count"] = len(inner)
            if inner and len(inner) == 1:
                result["format"] = get_format(inner[0][0])
            return result
        if name in RV32I_INSTRUCTIONS:
            encode(name, operands)
            result["valid"] = True
            result["format"] = get_format(name)
        else:
            result["error"] = f"Unknown instruction: {name}"
    except (ValueError, IndexError, KeyError) as e:
        result["error"] = str(e)
    return result


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


def compute_addresses(addr_lines: list[str], num_lines: int) -> list[str]:
    """
    根据现有地址行和需要的行数，计算新的地址列表。
    规则：
    - 手动输入的地址（有效的十六进制）作为锚点，绝对保留。
    - 锚点之间的自动行从上一行+4递增，若即将超过下一个锚点则留空。
    - 首个锚点之前从 0x00000000 开始递增。
    - 最后一个锚点之后从该锚点+4继续递增。
    """
    # 找出所有手动锚点 (行索引 -> 地址值)
    anchors = {}
    for i, line in enumerate(addr_lines):
        stripped = line.strip()
        if stripped:
            try:
                anchors[i] = int(stripped, 16)
            except ValueError:
                pass

    result = []
    current_addr = 0
    anchor_keys = sorted(anchors.keys())

    for i in range(num_lines):
        if i in anchors:
            result.append(f"{anchors[i]:08x}")
            current_addr = anchors[i] + 4
        else:
            next_anchor_idx = None
            for idx in anchor_keys:
                if idx > i:
                    next_anchor_idx = idx
                    break

            if next_anchor_idx is not None:
                if current_addr >= anchors[next_anchor_idx]:
                    result.append("")
                else:
                    result.append(f"{current_addr:08x}")
                    current_addr += 4
            else:
                result.append(f"{current_addr:08x}")
                current_addr += 4

    return result


def clear_cache():
    if not CACHE_DIR.exists():
        return
    for file in CACHE_DIR.iterdir():
        if file.is_file():
            try:
                file.unlink()
            except Exception:
                pass
