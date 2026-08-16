import struct
from pathlib import Path

from utils import render_svg

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_render_basic(tmp_path):
    src = FIXTURES / "sample.svg"
    dst = tmp_path / "out.png"
    code, out, err = render_svg(src, dst)
    assert code == 0, err
    assert dst.exists()
    with open(dst, "rb") as f:
        assert f.read(8) == b"\x89PNG\r\n\x1a\n"


def test_render_scale_doubles_size(tmp_path):
    src = FIXTURES / "sample.svg"
    dst1 = tmp_path / "s1.png"
    dst2 = tmp_path / "s2.png"
    assert render_svg(src, dst1, scale=1.0)[0] == 0
    assert render_svg(src, dst2, scale=2.0)[0] == 0

    def png_size(p):
        with open(p, "rb") as f:
            data = f.read()
        w, h = struct.unpack(">II", data[16:24])
        return w, h

    w1, h1 = png_size(dst1)
    w2, h2 = png_size(dst2)
    assert w2 == w1 * 2
    assert h2 == h1 * 2