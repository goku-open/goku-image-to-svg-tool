from pathlib import Path

from streamlit.testing.v1 import AppTest

PAGES = Path(__file__).resolve().parent.parent / "pages_content"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_workbench_renders_without_upload():
    at = AppTest.from_file(str(PAGES / "0_Image_to_Vector.py"), default_timeout=60)
    at.run()
    assert not at.exception, f"raised: {[str(e) for e in at.exception]}"


def test_workbench_auto_converts_on_upload():
    at = AppTest.from_file(str(PAGES / "0_Image_to_Vector.py"), default_timeout=120)
    at.run()
    image_bytes = (FIXTURES / "crisp.png").read_bytes()
    at.file_uploader[0].set_value(("crisp.png", image_bytes, "image/png"))
    at.run()
    assert not at.exception, f"raised: {[str(e) for e in at.exception]}"
    rendered = "".join(m.value for m in at.get("markdown"))
    assert "调色板" in rendered or "Palette" in rendered


def test_about_page_renders():
    at = AppTest.from_file(str(PAGES / "2_About.py"), default_timeout=30)
    at.run()
    assert not at.exception, f"raised: {[str(e) for e in at.exception]}"