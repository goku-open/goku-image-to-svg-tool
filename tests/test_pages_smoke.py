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


def test_workbench_radio_style_change():
    at = AppTest.from_file(str(PAGES / "0_Image_to_Vector.py"), default_timeout=120)
    at.run()
    image_bytes = (FIXTURES / "crisp.png").read_bytes()
    at.file_uploader[0].set_value(("crisp.png", image_bytes, "image/png"))
    at.run()
    assert not at.exception, f"raised: {[str(e) for e in at.exception]}"

    style_radios = [r for r in at.radio if r.key == "style_sel"]
    assert style_radios, "style radio with key=style_sel not found"
    style_radios[0].set_value("crisp")
    at.run()
    assert not at.exception, f"raised after style change: {[str(e) for e in at.exception]}"
    rendered = "\n".join(m.value for m in at.get("markdown"))
    assert "调色板" in rendered or "Palette" in rendered


def test_header_css_media_query():
    app = Path(__file__).resolve().parent.parent / "streamlit_app.py"
    at = AppTest.from_file(str(app), default_timeout=60)
    at.run()
    assert not at.exception, f"raised: {[str(e) for e in at.exception]}"
    assert any("@media" in m.value for m in at.get("markdown"))


def test_header_shows_x_logo_in_english():
    app = Path(__file__).resolve().parent.parent / "streamlit_app.py"
    at = AppTest.from_file(str(app), default_timeout=60)
    at.run()
    lang_radio = [r for r in at.radio if r.label == "Language Selector"]
    assert lang_radio, "language selector radio not found"
    lang_radio[0].set_value("English")
    at.run()
    assert not at.exception, f"raised after lang switch: {[str(e) for e in at.exception]}"
    raw = "\n".join(m.value for m in at.get("markdown"))
    assert "x.com/pachong888" in raw
    assert "@pachong888" in raw
    assert "公众号" not in raw


def test_header_shows_gzh_in_chinese():
    app = Path(__file__).resolve().parent.parent / "streamlit_app.py"
    at = AppTest.from_file(str(app), default_timeout=60)
    at.run()
    raw = "\n".join(m.value for m in at.get("markdown"))
    assert "公众号" in raw
    assert "x.com/pachong888" not in raw