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
        "title", "caption_top", "page_vec_title", "page_vec_desc", "page_about_title",
        "page_about_desc", "upload_label", "warn_no_file",
        "palette", "palette_auto", "palette_max", "palette_count", "palette_empty",
        "style_label", "detail_label", "param_polygons", "param_stats",
        "view_mode", "view_vector", "view_segmentation",
        "label_original", "label_vector", "label_segmentation",
        "export_svg", "export_png", "export_scale",
        "error_trace", "error_render",
        "about_text", "about_params", "about_license", "footer",
    ]
    for k in required:
        assert k in zh, f"missing zh key: {k}"