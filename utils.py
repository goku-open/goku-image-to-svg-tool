import base64
import mimetypes
import os
import subprocess
from pathlib import Path

import streamlit as st

# --- Vecto 二进制封装 ---

VEKTO_BIN = Path(__file__).resolve().parent / "tools" / "vecto"
VEKTO_TIMEOUT = 120


def get_vecto_binary() -> Path:
    if not VEKTO_BIN.exists():
        raise RuntimeError(
            "未找到 Vecto 二进制 (tools/vecto)。请从 "
            "https://github.com/DanielMevit/Vecto/releases 下载 "
            "vecto-0.4.2-linux-x64 并放置到 tools/vecto 后重试。"
        )
    if not os.access(str(VEKTO_BIN), os.X_OK):
        raise RuntimeError("Vecto 二进制不可执行，请运行: chmod +x tools/vecto")
    return VEKTO_BIN


def run_vecto(args: list[str], cwd: Path | None = None, timeout: int = VEKTO_TIMEOUT) -> tuple[int, str, str]:
    exe = str(get_vecto_binary())
    try:
        result = subprocess.run(
            [exe, *args],
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"Vecto 执行超时 (> {timeout}s)")
    return result.returncode, result.stdout, result.stderr


def trace_image(
    src: Path,
    dst: Path,
    log_placeholder=None,
    *,
    colors=None,
    max_colors=None,
    detail=None,
    style=None,
    polygons: bool = False,
    epsilon=None,
    stats: bool = False,
) -> tuple[int, str, str]:
    args = ["trace", str(src.resolve()), "-o", str(dst.resolve())]
    if colors:
        args += ["--colors", str(colors)]
    if max_colors:
        args += ["--max-colors", str(max_colors)]
    if detail:
        args += ["--detail", detail]
    if style:
        args += ["--style", style]
    if polygons:
        args += ["--polygons"]
    if epsilon is not None:
        args += ["--epsilon", str(epsilon)]
    if stats:
        args += ["--stats"]
    return run_vecto(args)


def render_svg(src: Path, dst: Path, *, scale: float = 1.0) -> tuple[int, str, str]:
    args = ["render", str(src.resolve()), "-o", str(dst.resolve()), "--scale", str(scale)]
    return run_vecto(args)


# --- UI 工具函数 ---

def resolve_asset_path(file_name: str) -> str:
    APP_DIR = Path(__file__).resolve().parent
    candidates = [APP_DIR / file_name, Path.cwd() / file_name]
    for p in candidates:
        if p.exists():
            return str(p)
    return file_name


def image_to_data_uri(path: str) -> str:
    try:
        file_path = Path(path)
        if not file_path.exists():
            return ""
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = "image/png"
        data = file_path.read_bytes()
        encoded = base64.b64encode(data).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"
    except Exception:
        return ""


def init_state():
    defaults = {"lang": "zh"}
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
