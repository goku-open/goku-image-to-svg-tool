"""验证 vecto CLI 支持的额外图片格式（对齐 CLI 放宽上传类型）。

vecto 用 ImageSharp 3.1 解码，支持 PNG/JPEG/BMP/GIF/TGA/TIFF/WebP/PBM/QOI。
png/jpg/bmp/gif 已有 fixtures 覆盖，这里补 tga/tiff/webp/pbm（PIL 临时生成）。
"""
import io
from pathlib import Path

import pytest
from PIL import Image

from utils import trace_image

FIXTURES = Path(__file__).resolve().parent / "fixtures"

# PIL 可生成的额外格式（QOI 无 PIL 支持，不在测试范围；PBM 族 PIL 仅能写 PPM，见 spec §8.9）
EXTRA_FORMATS = ["tga", "tiff", "webp", "ppm"]


def _make_image_bytes(ext: str) -> bytes:
    img = Image.new("RGB", (64, 48))
    px = img.load()
    for y in range(48):
        for x in range(64):
            px[x, y] = (x * 4 % 255, y * 5 % 255, (x + y) * 2 % 255)
    buf = io.BytesIO()
    img.save(buf, format=ext.upper())
    return buf.getvalue()


@pytest.mark.parametrize("ext", EXTRA_FORMATS)
def test_trace_extra_formats(tmp_path, ext):
    src = tmp_path / f"input.{ext}"
    src.write_bytes(_make_image_bytes(ext))
    dst = tmp_path / f"out_{ext}.svg"
    code, out, err = trace_image(src, dst)
    assert code == 0, f"{ext}: {err}"
    content = dst.read_text(encoding="utf-8")
    assert "svg" in content.lower()
