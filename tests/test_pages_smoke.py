from pathlib import Path

from streamlit.testing.v1 import AppTest

PAGES = Path(__file__).resolve().parent.parent / "pages_content"


def test_all_pages_render_without_exceptions():
    for name in ["0_Image_to_Vector.py", "1_SVG_to_PNG.py", "2_About.py"]:
        at = AppTest.from_file(str(PAGES / name), default_timeout=30)
        at.run()
        assert not at.exception, f"{name} raised: {[str(e) for e in at.exception]}"