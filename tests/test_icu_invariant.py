"""验证 utils.py 会为 .NET 设置 invariant 环境变量（云端无 ICU 时 vecto 才能跑）。

Streamlit Community Cloud 的容器没有 libicu，.NET 程序启动会 FailFast。
utils.py 模块加载时必须 set env，vecto subprocess 继承后以 invariant 模式运行。
"""
import os

from utils import trace_image

FIXTURES = __import__("pathlib").Path(__file__).resolve().parent / "fixtures"


def test_import_sets_dotnet_invariant_env():
    assert os.environ.get("DOTNET_SYSTEM_GLOBALIZATION_INVARIANT") == "1"


def test_import_sets_coreclr_invariant_env():
    assert os.environ.get("CORECLR_GLOBAL_INVARIANT") == "1"


def test_trace_image_works_with_invariant_env(tmp_path):
    src = FIXTURES / "crisp.png"
    dst = tmp_path / "out.svg"
    code, out, err = trace_image(
        src, dst, colors=4, detail="high", style="crisp", polygons=False, stats=True
    )
    assert code == 0, err
    content = dst.read_text(encoding="utf-8")
    assert "svg" in content.lower()