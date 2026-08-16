import base64
from pathlib import Path

import streamlit as st

_logo_path = Path(__file__).parent / "logo.svg"
if _logo_path.exists():
    _svg_b64 = base64.b64encode(_logo_path.read_bytes()).decode()
    _icon = f"data:image/svg+xml;base64,{_svg_b64}"
else:
    _icon = "🛠️"

st.set_page_config(
    page_title="悟空图片转SVG工具 | Goku Image to SVG Tool",
    page_icon=_icon,
    layout="wide"
)

st.markdown(
    """
    <style>
    #MainMenu, .stDeployButton, [data-testid="stStatusWidget"] { visibility: hidden; display: none; }
    </style>
    """,
    unsafe_allow_html=True,
)

from i18n import _
from utils import (
    init_state,
    resolve_asset_path,
    image_to_data_uri,
)

init_state()

title_col1, title_col2, title_col3 = st.columns([1, 10, 5])
with title_col1:
    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    logo_path = resolve_asset_path("logo.svg")
    try:
        with open(logo_path, "r", encoding="utf-8") as f:
            svg_content = f.read()
        st.image(svg_content, width=42)
    except Exception:
        st.image(logo_path, width=42)

with title_col2:
    st.markdown(f"<h1 style='margin: 0; margin-left: -22px;'>{_('title')}</h1>", unsafe_allow_html=True)
with title_col3:
    right_col1, right_col2 = st.columns([1, 1])
    with right_col2:
        gzh_src = image_to_data_uri(resolve_asset_path("gzh.jpg"))
        if gzh_src:
            st.markdown(
                """
                <div style="display:flex; flex-direction:column; align-items:center; width:140px; margin:0 auto;">
                    <img src="{src}" style="width:140px; height:auto; display:block;" />
                    <div style="margin-top:4px; text-align:center;">公众号-反馈/建议</div>
                </div>
                """.format(src=gzh_src),
                unsafe_allow_html=True,
            )
        else:
            st.image(resolve_asset_path("gzh.jpg"), width=140)
            st.markdown("<div style='text-align: center; margin-top: 4px;'>公众号-反馈/建议</div>", unsafe_allow_html=True)

st.caption(_("caption_top"))

lang_options = {"简体中文": "zh", "English": "en"}
current_lang_idx = list(lang_options.values()).index(st.session_state.lang)
selected_lang = st.radio(
    "Language Selector",
    options=list(lang_options.keys()),
    index=current_lang_idx,
    horizontal=True,
    label_visibility="collapsed",
)
if lang_options[selected_lang] != st.session_state.lang:
    st.session_state.lang = lang_options[selected_lang]
    st.rerun()

st.divider()

trace_page = st.Page("pages_content/0_Image_to_Vector.py", title=_("page_vec_title"), icon="🖼️")
png_page = st.Page("pages_content/1_SVG_to_PNG.py", title=_("page_png_title"), icon="🔄")
about_page = st.Page("pages_content/2_About.py", title=_("page_about_title"), icon="ℹ️")
pg = st.navigation([trace_page, png_page, about_page], position="sidebar")
pg.run()

st.divider()
st.caption(_("footer"))
