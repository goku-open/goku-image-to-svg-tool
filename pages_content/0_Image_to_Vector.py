import io
from pathlib import Path

import streamlit as st
from PIL import Image
from streamlit_image_comparison import image_comparison

from i18n import _
from utils import (
    init_state,
    parse_palette_from_svg,
    run_png_export,
    run_trace_workflow,
)

init_state()

MAX_PREVIEW_W = 1200
_IMAGE_TYPES = ["png", "jpg", "jpeg", "bmp", "gif"]
_DEFAULT_STYLE = "auto"
_DEFAULT_DETAIL = "medium"


@st.cache_data(show_spinner=False)
def trace_cached(image_bytes, filename, colors_count, max_colors, detail, style, polygons, stats):
    return run_trace_workflow(
        image_bytes, filename, colors_count, max_colors, detail, style, polygons, stats
    )


@st.cache_data(show_spinner=False)
def png_cached(svg_text, scale):
    return run_png_export(svg_text, scale)


def _thumbnail(img: Image.Image, max_w: int) -> Image.Image:
    copy = img.copy()
    copy.thumbnail((max_w, max_w))
    return copy


st.subheader(_("page_vec_title"))
st.caption(_("page_vec_desc"))

uploaded = st.file_uploader(_("upload_label"), type=_IMAGE_TYPES)

if uploaded is None:
    st.info(_("warn_no_file"))
    st.stop()

image_bytes = uploaded.getvalue()
filename = uploaded.name
stem = Path(filename).stem

left, right = st.columns([8, 3], gap="medium")

with right:
    # --- Palette 区（对齐原版：automatic checkbox + 颜色数滑块 + 色块） ---
    st.markdown(f"**{_('palette')}**")
    auto_colors = st.checkbox(_("palette_auto"), value=True, key="auto_colors_cb")
    colors_count = st.slider(
        _("palette_count"), 2, 32, 12, disabled=auto_colors, key="colors_sel"
    )
    effective_colors = None if auto_colors else int(st.session_state.get("colors_sel", 12))

    # 读取 Style/Detail 最新值（控件在下方渲染，用 key 从 session_state 取回）
    style = st.session_state.get("style_sel", _DEFAULT_STYLE)
    detail = st.session_state.get("detail_sel", _DEFAULT_DETAIL)

    result = trace_cached(
        image_bytes, filename, effective_colors, 16, detail, style, False, True
    )

    swatches = parse_palette_from_svg(result["svg"]) if result["ok"] else []
    if swatches:
        swatch_html = "".join(
            f'<span title="{c}" style="display:inline-block;width:20px;height:20px;'
            f'border-radius:5px;border:1px solid #888;background:{c};margin:0 4px 4px 0;"></span>'
            for c in swatches
        )
        st.markdown(f"<div style='display:flex;flex-wrap:wrap;'>{swatch_html}</div>", unsafe_allow_html=True)
    elif result["ok"]:
        st.caption(_("palette_empty"))

    # --- Style 区 ---
    st.markdown(f"**{_('style_label')}**")
    st.selectbox(
        _("style_label"),
        ["auto", "crisp", "blended", "photo"],
        index=["auto", "crisp", "blended", "photo"].index(_DEFAULT_STYLE),
        label_visibility="collapsed",
        key="style_sel",
    )

    # --- Detail 区 ---
    st.markdown(f"**{_('detail_label')}**")
    st.selectbox(
        _("detail_label"),
        ["low", "medium", "high"],
        index=1,
        label_visibility="collapsed",
        key="detail_sel",
    )

    # --- StatsText（常显，对齐原版） ---
    if result["ok"] and result["stats"]:
        st.caption(result["stats"].strip())

with left:
    if not result["ok"]:
        st.error(_("error_trace").format(msg=result["err"]))
        st.stop()

    view_mode = st.radio(_("view_mode"), (_("view_vector"), _("view_segmentation")), horizontal=True)

    orig_img = Image.open(io.BytesIO(image_bytes))
    orig_disp = _thumbnail(orig_img, MAX_PREVIEW_W)
    vector_disp = _thumbnail(Image.open(io.BytesIO(result["preview"])), MAX_PREVIEW_W)

    if view_mode == _("view_segmentation") and result["seg"]:
        seg_disp = _thumbnail(Image.open(io.BytesIO(result["seg"])), MAX_PREVIEW_W)
        image_comparison(
            orig_disp,
            seg_disp,
            label1=_("label_original"),
            label2=_("label_segmentation"),
            show_labels=True,
            starting_position=50,
            make_responsive=True,
            in_memory=True,
        )
    else:
        image_comparison(
            orig_disp,
            vector_disp,
            label1=_("label_original"),
            label2=_("label_vector"),
            show_labels=True,
            starting_position=50,
            make_responsive=True,
            in_memory=True,
        )

    b1, b2 = st.columns([1, 2])
    with b1:
        st.download_button(
            _("export_svg"),
            data=result["svg"].encode("utf-8"),
            file_name=f"{stem}.svg",
            mime="image/svg+xml",
            use_container_width=True,
        )
    with b2:
        scale = st.number_input(_("export_scale"), min_value=0.1, max_value=10.0, value=1.0, step=0.5)
        try:
            st.download_button(
                _("export_png"),
                data=png_cached(result["svg"], float(scale)),
                file_name=f"{stem}.png",
                mime="image/png",
                use_container_width=True,
            )
        except RuntimeError as exc:
            st.error(_("error_render").format(msg=str(exc)))