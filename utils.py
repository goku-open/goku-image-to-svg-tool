import base64
import mimetypes
import os
import re
import subprocess
import threading
from pathlib import Path

import streamlit as st

# .NET 运行时在无 libicu 的 Linux 容器（如 Streamlit Community Cloud 的 Debian 11）会
# 直接 FailFast 崩溃。强制 invariant 模式让 vecto 跳过 ICU；subprocess 继承本环境变量。
os.environ.setdefault("DOTNET_SYSTEM_GLOBALIZATION_INVARIANT", "1")
os.environ.setdefault("CORECLR_GLOBAL_INVARIANT", "1")  # 旧版运行时兼容兜底

# --- 并发保护 ---
_TRACE_SEM = threading.Semaphore(2)

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
    seg_png=None,
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
    if seg_png is not None:
        args += ["--seg-png", str(seg_png.resolve())]
    return run_vecto(args)


def render_svg(src: Path, dst: Path, *, scale: float = 1.0) -> tuple[int, str, str]:
    args = ["render", str(src.resolve()), "-o", str(dst.resolve()), "--scale", str(scale)]
    return run_vecto(args)


def parse_palette_from_svg(svg_text: str) -> list[str]:
    colors = re.findall(r'fill="?([#][0-9a-fA-F]{3,8})', svg_text)
    seen = []
    for raw in colors:
        normalized = "#" + raw[1:].lower()
        if normalized not in seen:
            seen.append(normalized)
    return seen


def summarize_stats(stats_text: str) -> str:
    match = re.search(r"\((\d+) ms, (\d+) colors, (\d+) regions, (\d+) nodes\)", stats_text)
    if not match:
        return ""
    ms, colors, regions, nodes = match.groups()
    return f"{ms} ms · {colors} colors · {regions} regions · {nodes} nodes"


def run_trace_workflow(
    image_bytes: bytes,
    filename: str,
    colors_count: int | None,
    max_colors: int,
    detail: str,
    style: str,
    polygons: bool,
    stats: bool,
) -> dict:
    import tempfile

    if not _TRACE_SEM.acquire(blocking=False):
        return {"ok": False, "busy": True, "err": "当前转换繁忙，请稍后再试", "stats": "", "svg": "", "preview": b"", "seg": b""}
    try:
        with tempfile.TemporaryDirectory(prefix="vecto_work_") as td:
            tmp = Path(td)
            ext = Path(filename).suffix.lower() or ".png"
            src = tmp / f"input{ext}"
            src.write_bytes(image_bytes)
            out_svg = tmp / "output.svg"
            seg_png = tmp / "seg.png"
            code, out, err = trace_image(
                src,
                out_svg,
                colors=colors_count,
                max_colors=max_colors,
                detail=detail,
                style=style,
                polygons=polygons,
                stats=stats,
                seg_png=seg_png,
            )
            if code != 0:
                return {"ok": False, "err": err, "stats": out, "svg": "", "preview": b"", "seg": b""}
            svg_text = out_svg.read_text(encoding="utf-8")
            preview = tmp / "preview.png"
            prev_code, _, prev_err = render_svg(out_svg, preview, scale=1.0)
            if prev_code != 0:
                return {
                    "ok": False,
                    "err": prev_err,
                    "stats": out,
                    "svg": svg_text,
                    "preview": b"",
                    "seg": seg_png.read_bytes() if seg_png.exists() else b"",
                }
            return {
                "ok": True,
                "err": "",
                "stats": out,
                "svg": svg_text,
                "preview": preview.read_bytes(),
                "seg": seg_png.read_bytes() if seg_png.exists() else b"",
            }
    finally:
        _TRACE_SEM.release()


def run_png_export(svg_text: str, scale: float) -> bytes:
    import tempfile

    if not _TRACE_SEM.acquire(blocking=False):
        raise RuntimeError("当前转换繁忙，请稍后再试")
    try:
        with tempfile.TemporaryDirectory(prefix="vecto_export_") as td:
            tmp = Path(td)
            src = tmp / "input.svg"
            src.write_text(svg_text, encoding="utf-8")
            dst = tmp / "output.png"
            code, _, err = render_svg(src, dst, scale=scale)
            if code != 0:
                raise RuntimeError(err)
            return dst.read_bytes()
    finally:
        _TRACE_SEM.release()


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
