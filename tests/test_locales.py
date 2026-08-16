import json
from pathlib import Path

LOCALES = Path(__file__).resolve().parent.parent / "locales"


def test_locale_keys_in_sync():
    zh = json.loads((LOCALES / "zh.json").read_text(encoding="utf-8"))
    en = json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))
    assert set(zh.keys()) == set(en.keys())


def test_required_keys_present():
    zh = json.loads((LOCALES / "zh.json").read_text(encoding="utf-8"))
    required = [
        "title", "page_vec_title", "page_vec_desc", "page_png_title", "page_png_desc",
        "page_about_title", "page_about_desc", "btn_run", "btn_render", "btn_download",
        "upload_vec_label", "upload_svg_label", "warn_no_file", "param_title",
        "param_colors_auto", "param_colors", "param_max_colors", "param_detail",
        "param_style", "param_polygons", "param_stats", "param_scale",
        "info_tracing", "info_rendering", "success_trace", "success_render",
        "error_trace", "error_render", "preview_result", "about_text", "footer",
    ]
    for k in required:
        assert k in zh, f"missing zh key: {k}"