from pathlib import Path


def test_about_page_file_exists():
    p = Path("pages_content/2_About.py")
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert "about_text" in content


def test_main_navigation_updates():
    app = Path("streamlit_app.py")
    content = app.read_text(encoding="utf-8")
    assert "0_Image_to_Vector.py" in content
    assert "1_SVG_to_PNG.py" not in content
    assert "2_About.py" in content
    assert "0_PDF_Download.py" not in content
    assert "1_Data_Analysis.py" not in content