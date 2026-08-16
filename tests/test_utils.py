from pathlib import Path

import pytest

from utils import get_vecto_binary, run_vecto, trace_image, render_svg

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_get_vecto_binary_exists_and_executable():
    assert get_vecto_binary().exists()
    assert get_vecto_binary().name == "vecto"


def test_run_vecto_version(monkeypatch):
    import utils
    monkeypatch.setattr(utils, "VEKTO_BIN", utils.VEKTO_BIN)
    code, out, err = run_vecto(["--version"])
    assert code == 0
    assert "vecto 0.4.2" in out


def test_get_vecto_binary_missing(monkeypatch):
    import utils
    monkeypatch.setattr(utils, "VEKTO_BIN", Path("/nonexistent/vecto"))
    with pytest.raises(RuntimeError) as exc:
        get_vecto_binary()
    assert "下载" in str(exc.value)


def test_run_vecto_unknown_command(monkeypatch):
    import utils
    monkeypatch.setattr(utils, "VEKTO_BIN", utils.VEKTO_BIN)
    code, out, err = run_vecto(["not-a-command"])
    assert code != 0
    assert err != ""


def test_trace_image_basic(tmp_path):
    src = FIXTURES / "crisp.png"
    dst = tmp_path / "out.svg"
    code, out, err = trace_image(src, dst)
    assert code == 0, err
    assert dst.exists()
    assert "svg" in dst.read_text(encoding="utf-8").lower()


def test_trace_image_transparent(tmp_path):
    src = FIXTURES / "transparent.png"
    dst = tmp_path / "out.svg"
    code, out, err = trace_image(src, dst)
    assert code == 0, err
    assert dst.exists()
    assert "svg" in dst.read_text(encoding="utf-8").lower()


def test_trace_image_missing_input(tmp_path):
    src = tmp_path / "nope.png"
    dst = tmp_path / "out.svg"
    code, out, err = trace_image(src, dst)
    assert code != 0


def test_trace_image_stats(tmp_path):
    src = FIXTURES / "crisp.png"
    dst = tmp_path / "out.svg"
    code, out, err = trace_image(src, dst, stats=True)
    assert code == 0, err
    assert "timings:" in out


def test_render_svg_basic(tmp_path):
    src = FIXTURES / "sample.svg"
    dst = tmp_path / "out.png"
    code, out, err = render_svg(src, dst)
    assert code == 0, err
    assert dst.exists()
    with open(dst, "rb") as f:
        assert f.read(8) == b"\x89PNG\r\n\x1a\n"


def test_render_svg_invalid(tmp_path):
    src = tmp_path / "bad.svg"
    src.write_text("not an svg", encoding="utf-8")
    dst = tmp_path / "bad.png"
    code, out, err = render_svg(src, dst)
    assert code != 0