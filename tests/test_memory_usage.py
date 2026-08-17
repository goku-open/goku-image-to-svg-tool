"""测量 Vecto 转换进程的峰值内存（为 Streamlit Community Cloud 2.7GB 限额提供依据）。

用 os.wait4 拿单个子进程的 ru_maxrss（Linux 单位 KB），不引入新依赖。
运行：python3 -m pytest tests/test_memory_usage.py -v -s
"""
import os
import subprocess
import tempfile
import time
from pathlib import Path

from PIL import Image

from utils import VEKTO_BIN, VEKTO_TIMEOUT

FIXTURES = Path(__file__).resolve().parent / "fixtures"

# 宽松阈值（防回归）；真实数字看 print 输出
TRACE_SMALL_LIMIT_MB = 200
TRACE_LARGE_LIMIT_MB = 1500
RENDER_LIMIT_MB = 1500


def _run_vecto_measure(args: list[str], cwd: Path | None = None) -> tuple[int, str, str, int, float]:
    """运行 vecto 并返回 (code, stdout, stderr, peak_kb, seconds)。"""
    proc = subprocess.Popen(
        [str(VEKTO_BIN), *args],
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    start = time.monotonic()
    try:
        pid, status, rusage = os.wait4(proc.pid, 0)
        stdout, stderr = proc.communicate(timeout=VEKTO_TIMEOUT)
    except ChildProcessError:
        raise TimeoutError(f"Vecto 执行超时 (> {VEKTO_TIMEOUT}s)")
    elapsed = time.monotonic() - start
    peak_kb = rusage.ru_maxrss
    return status, stdout, stderr, peak_kb, elapsed


def _make_large_image(path: Path, size: int = 3000) -> None:
    """临时生成 size×size 渐变+色块大图（不落库，避免仓库膨胀）。"""
    img = Image.new("RGB", (size, size))
    px = img.load()
    block = size // 8
    for y in range(size):
        for x in range(size):
            px[x, y] = ((x * 255 // size) % 255, (y * 255 // size) % 255, (x + y) * 255 // (2 * size))
    for by in range(8):
        for bx in range(8):
            if (bx + by) % 3 == 0:
                for y in range(by * block, min((by + 1) * block, size)):
                    for x in range(bx * block, min((bx + 1) * block, size)):
                        px[x, y] = (bx * 32, by * 32, 128)
    img.save(path)


def test_trace_peak_memory_fixture():
    src = FIXTURES / "crisp.png"
    with tempfile.TemporaryDirectory(prefix="mem_trace_") as td:
        dst = Path(td) / "out.svg"
        code, out, err, peak_kb, secs = _run_vecto_measure(
            ["trace", str(src.resolve()), "-o", str(dst.resolve()), "--style", "crisp", "--stats"]
        )
        assert code == 0, err
        peak_mb = peak_kb / 1024
        print(f"\n[trace fixture crisp.png {src.stat().st_size} bytes] peak={peak_mb:.1f} MB, {secs:.2f}s")
        assert peak_mb < TRACE_SMALL_LIMIT_MB, f"peak {peak_mb:.1f}MB >= {TRACE_SMALL_LIMIT_MB}MB"


def test_trace_peak_memory_large():
    with tempfile.TemporaryDirectory(prefix="mem_trace_") as td:
        tmp = Path(td)
        src = tmp / "large.png"
        _make_large_image(src, size=3000)
        dst = tmp / "out.svg"
        code, out, err, peak_kb, secs = _run_vecto_measure(
            ["trace", str(src.resolve()), "-o", str(dst.resolve()), "--stats"]
        )
        assert code == 0, err
        peak_mb = peak_kb / 1024
        print(f"\n[trace large 3000x3000] peak={peak_mb:.1f} MB, {secs:.2f}s")
        assert peak_mb < TRACE_LARGE_LIMIT_MB, f"peak {peak_mb:.1f}MB >= {TRACE_LARGE_LIMIT_MB}MB"


def test_render_png_peak_memory():
    with tempfile.TemporaryDirectory(prefix="mem_render_") as td:
        tmp = Path(td)
        src = tmp / "large.png"
        _make_large_image(src, size=3000)
        svg = tmp / "out.svg"
        code, _, err, _, _ = _run_vecto_measure(
            ["trace", str(src.resolve()), "-o", str(svg.resolve())]
        )
        assert code == 0, err
        dst = tmp / "out.png"
        code, _, err, peak_kb, secs = _run_vecto_measure(
            ["render", str(svg.resolve()), "-o", str(dst.resolve()), "--scale", "2"]
        )
        assert code == 0, err
        peak_mb = peak_kb / 1024
        print(f"\n[render scale=2 from 3000x3000] peak={peak_mb:.1f} MB, {secs:.2f}s")
        assert peak_mb < RENDER_LIMIT_MB, f"peak {peak_mb:.1f}MB >= {RENDER_LIMIT_MB}MB"
