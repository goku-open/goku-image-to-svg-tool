import tempfile
from pathlib import Path

import streamlit as st

from i18n import _
from utils import init_state, trace_image, render_svg

init_state()

st.subheader(_("page_vec_title"))
st.caption(_("page_vec_desc"))

uploaded = st.file_uploader(_("upload_vec_label"), type=["png", "jpg", "jpeg", "bmp", "gif"])

with st.expander(_("param_title"), expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        colors_auto = st.checkbox(_("param_colors_auto"), value=True)
        max_colors = st.slider(_("param_max_colors"), 2, 64, 16)
        detail = st.selectbox(_("param_detail"), ["low", "medium", "high"], index=1)
    with c2:
        style = st.selectbox(_("param_style"), ["auto", "crisp", "blended", "photo"], index=0)
        polygons = st.checkbox(_("param_polygons"))
        stats = st.checkbox(_("param_stats"))
        colors = None if colors_auto else st.slider(_("param_colors"), 2, 32, 8)

if st.button(_("btn_run"), type="primary", use_container_width=True):
    if uploaded is None:
        st.warning(_("warn_no_file"))
        st.stop()
    with tempfile.TemporaryDirectory(prefix="vecto_trace_") as td:
        tmp = Path(td)
        ext = Path(uploaded.name).suffix
        src = tmp / f"input{ext}"
        src.write_bytes(uploaded.getvalue())
        dst = tmp / "output.svg"
        status = st.empty()
        holder = st.empty()
        status.info(_("info_tracing"))
        code, out, err = trace_image(
            src, dst, holder,
            colors=colors, max_colors=max_colors,
            detail=detail, style=style,
            polygons=polygons, stats=stats,
        )
        if code != 0:
            status.error(_("error_trace").format(msg=err))
            st.stop()
        status.success(_("success_trace"))
        svg_text = dst.read_text(encoding="utf-8")
        png = tmp / "preview.png"
        r_code, r_out, r_err = render_svg(dst, png)
        if r_code == 0:
            st.image(str(png), caption=_("preview_result"))
        else:
            st.code(svg_text, language="xml")
        if stats:
            with st.expander(_("param_stats"), expanded=False):
                st.code(out, language="bash")
        st.download_button(
            _("btn_download"),
            data=svg_text,
            file_name=f"{Path(uploaded.name).stem}.svg",
            mime="image/svg+xml",
            use_container_width=True,
        )