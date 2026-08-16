import tempfile
from pathlib import Path

import streamlit as st

from i18n import _
from utils import init_state, render_svg

init_state()

st.subheader(_("page_png_title"))
st.caption(_("page_png_desc"))

uploaded = st.file_uploader(_("upload_svg_label"), type=["svg"])

scale = st.number_input(_("param_scale"), min_value=0.1, max_value=10.0, value=1.0, step=0.5)

if st.button(_("btn_render"), type="primary", use_container_width=True):
    if uploaded is None:
        st.warning(_("warn_no_file"))
        st.stop()
    with tempfile.TemporaryDirectory(prefix="vecto_render_") as td:
        tmp = Path(td)
        src = tmp / "input.svg"
        src.write_bytes(uploaded.getvalue())
        dst = tmp / "output.png"
        status = st.empty()
        status.info(_("info_rendering"))
        code, out, err = render_svg(src, dst, scale=scale)
        if code != 0:
            status.error(_("error_render").format(msg=err))
            st.stop()
        status.success(_("success_render"))
        st.image(str(dst), caption=_("preview_result"))
        st.download_button(
            _("btn_download"),
            data=dst.read_bytes(),
            file_name=f"{Path(uploaded.name).stem}.png",
            mime="image/png",
            use_container_width=True,
        )