from pathlib import Path

from utils import trace_image

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_trace_with_params(tmp_path):
    src = FIXTURES / "crisp.png"
    dst = tmp_path / "out.svg"
    code, out, err = trace_image(
        src, dst,
        colors=4, detail="high", style="crisp", polygons=False, stats=True,
    )
    assert code == 0, err
    content = dst.read_text(encoding="utf-8")
    assert "svg" in content.lower()
    assert "timings:" in out