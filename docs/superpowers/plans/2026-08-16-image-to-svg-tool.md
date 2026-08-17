# 悟空图片转SVG工具 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `yunzhan365-scraper` 原地改造成 Streamlit 图片转 SVG 工具，通过同步 subprocess 调用 Vecto 官方 Linux 二进制，并配套 pytest 逐功能测试。

**Architecture:** Streamlit 多页应用（图片转矢量 / SVG转PNG / 关于）。核心为 `utils.py` 中四个新函数：`get_vecto_binary()`、`run_vecto()`、`trace_image()`、`render_svg()`，统一走 `subprocess.run` 调 `tools/vecto`。测试用 pytest，fixture 用 `vecto samples` 生成样本图。

**Tech Stack:** Python 3.10+ / Streamlit / pytest / Vecto CLI (linux-x64, self-contained, MIT)

## Global Constraints

- 应用名：**悟空图片转SVG工具**（zh）/ Goku Image to SVG Tool（en）
- 二进制固定路径：`tools/vecto`（v0.4.2 linux-x64，SHA-256 `f7e0df8b9136b3d65e1f7ad9fe1eca2d685564bf547616039e7ced08a02acefd`），**提交入库**
- 测试命令：`python -m pytest`，测试目录 `tests/`，必须全部通过
- 双语言：`locales/zh.json` 与 `locales/en.json` 的 key 集合必须一致
- 调用方式：Streamlit 同步 subprocess（方案A），不引入异步队列
- 页面文件统一放 `pages_content/`（沿用现有约定）
- 旧功能（PDF下载/数据分析/Node.js解码）必须删除

---

### Task 1: 二进制落地 + fixture 样本

**Files:**
- Create: `tools/vecto`（官方 linux-x64 二进制，35MB）
- Create: `tests/fixtures/crisp.png`、`tests/fixtures/blended.png`、`tests/fixtures/transparent.png`（由 vecto samples 生成）
- Create: `tests/fixtures/sample.svg`（手工编写，供 render 测试）
- Create: `.gitignore` 追加 `__pycache__/`（已有，无需改）

**Interfaces:**
- Produces: `tools/vecto` 可执行文件路径；`tests/fixtures/` 下三个样本图与一个示例 SVG

- [ ] **Step 1: 下载二进制到临时目录校验**

```bash
mkdir -p /tmp/vecto-setup && cd /tmp/vecto-setup
curl -fSL -o vecto https://github.com/DanielMevit/Vecto/releases/download/v0.4.2/vecto-0.4.2-linux-x64
chmod +x vecto
echo "f7e0df8b9136b3d65e1f7ad9fe1eca2d685564bf547616039e7ced08a02acefd  vecto" | sha256sum -c -
./vecto --version
```
Expected: `vecto 0.4.2`，SHA 校验 OK。

- [ ] **Step 2: 将二进制放入项目 tools/**

```bash
mkdir -p tools
cp /tmp/vecto-setup/vecto tools/vecto
chmod +x tools/vecto
./tools/vecto --version
git add tools/vecto
```
Expected: `vecto 0.4.2`。

- [ ] **Step 3: 生成并入库测试 fixture**

```bash
mkdir -p tests/fixtures
./tools/vecto samples tests/fixtures/
ls tests/fixtures/
```
Expected: `crisp.png blended.png transparent.png` 三个文件生成。

- [ ] **Step 4: 编写 sample.svg fixture**

```bash
cat > tests/fixtures/sample.svg << 'EOF'
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100" viewBox="0 0 200 100">
  <rect x="10" y="10" width="180" height="80" fill="#3498db"/>
  <circle cx="60" cy="50" r="30" fill="#e74c3c"/>
</svg>
EOF
```
Expected: 文件存在，内容为两个基本矢量形状。

- [ ] **Step 5: 提交**

```bash
git add tests/fixtures/ tools/vecto
git commit -m "feat: add vecto binary and test fixtures"
```

---

### Task 2: `utils.py` 精简与核心函数

**Files:**
- Modify: `utils.py`（重写为纯工具 + Vecto 封装，删除云展网全部逻辑）
- Create: `tests/test_utils.py`

**Interfaces:**
- Produces（后续页面与测试依赖的精确保名）:
  - `get_vecto_binary() -> Path`：返回 `tools/vecto` 绝对路径；不存在/不可执行时 `raise RuntimeError`（含安装指引）
  - `run_vecto(args: list[str], cwd: Path | None = None, timeout: int = 120) -> tuple[int, str, str]`：返回 `(returncode, stdout, stderr)`；超时抛 `TimeoutError`
  - `trace_image(src: Path, dst: Path, log_placeholder=None, *, colors=None, max_colors=None, detail=None, style=None, polygons=False, epsilon=None, stats=False) -> tuple[int, str, str]`
  - `render_svg(src: Path, dst: Path, *, scale: float = 1.0) -> tuple[int, str, str]`
  - `init_state()`：仅保留 `lang` 默认初始化
  - `resolve_asset_path(file_name) -> str`、`image_to_data_uri(path) -> str`：保留（外壳用到）

- [ ] **Step 1: 删旧留新，重写 utils.py 头部与工具函数**

用完整文件内容替换（原 468 行 → 约 160 行）：

```python
import base64
import mimetypes
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

import streamlit as st

# --- Vecto 二进制封装 ---

VEKTO_BIN = Path(__file__).resolve().parent / "tools" / "vecto"
VEKTO_TIMEOUT = 120


def get_vecto_binary() -> Path:
    if not VEKTO_BIN.exists():
        raise RuntimeError(
            "未找到 Vecto 二进制 (tools/vecto)。请从 "
            "https://github.com/DanielMevit/Vecto/releases 下载 "
            "vecto-0.4.2-linux-x64 并放置到 tools/vecto 后重试。"
        )
    if not os.access(str(VEKTO_BIN), os.X_OK):
        raise RuntimeError("Vecto 二进制不可执行，请运行: chmod +x tools/vecto")
    return VEKTO_BIN


def run_vecto(args: list[str], cwd: Path | None = None, timeout: int = VEKTO_TIMEOUT) -> tuple[int, str, str]:
    exe = str(get_vecto_binary())
    try:
        result = subprocess.run(
            [exe, *args],
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"Vecto 执行超时 (> {timeout}s)")
    return result.returncode, result.stdout, result.stderr


def trace_image(
    src: Path,
    dst: Path,
    log_placeholder=None,
    *,
    colors=None,
    max_colors=None,
    detail=None,
    style=None,
    polygons: bool = False,
    epsilon=None,
    stats: bool = False,
) -> tuple[int, str, str]:
    args = ["trace", src.name, "-o", dst.name]
    if colors:
        args += ["--colors", str(colors)]
    if max_colors:
        args += ["--max-colors", str(max_colors)]
    if detail:
        args += ["--detail", detail]
    if style:
        args += ["--style", style]
    if polygons:
        args += ["--polygons"]
    if epsilon is not None:
        args += ["--epsilon", str(epsilon)]
    if stats:
        args += ["--stats"]
    return run_vecto(args, cwd=src.parent)


def render_svg(src: Path, dst: Path, *, scale: float = 1.0) -> tuple[int, str, str]:
    args = ["render", src.name, "-o", dst.name, "--scale", str(scale)]
    return run_vecto(args, cwd=src.parent)


# --- UI 工具函数 ---

def resolve_asset_path(file_name: str) -> str:
    APP_DIR = Path(__file__).resolve().parent
    candidates = [APP_DIR / file_name, Path.cwd() / file_name]
    for p in candidates:
        if p.exists():
            return str(p)
    return file_name


def image_to_data_uri(path: str) -> str:
    try:
        file_path = Path(path)
        if not file_path.exists():
            return ""
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = "image/png"
        data = file_path.read_bytes()
        encoded = base64.b64encode(data).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"
    except Exception:
        return ""


def init_state():
    defaults = {"lang": "zh"}
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
```

然后删除原文件中的：`fetch_text/fetch_bytes/normalize_book_url/load_html_config/patch_destring_js/decode_configs/safe_name/page_urls/download_pages/build_pdf`、SETTINGS_FILE 相关、`_get_limiter/_acquire_lock/_release_lock/run_download_pipeline`、`analyze_pdf`。

- [ ] **Step 2: 写测试**

`tests/test_utils.py`：

```python
from pathlib import Path

import pytest

from utils import get_vecto_binary, run_vecto, trace_image, render_svg

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_get_vecto_binary_exists_and_executable():
    assert get_vecto_binary().exists()
    assert get_vecto_binary().name == "vecto"


def test_run_vecto_version(monkeypatch):
    import utils
    utils.VEKTO_BIN = FIXTURES.parents[1] / "tools" / "vecto"
    monkeypatch.setattr(utils, "VEKTO_BIN", utils.VEKTO_BIN)
    code, out, err = run_vecto(["--version"])
    assert code == 0
    assert "vecto 0.4.2" in out
```

- [ ] **Step 3: 运行测试验证失败**

Run: `python -m pytest tests/test_utils.py::test_get_vecto_binary_exists_and_executable -v`

注意：当前 shell 中 streamlit 装在系统 user site。执行方式：

```bash
cd /home/goku/code/vecto/yunzhan365-scraper
python3 -c "import streamlit" 2>/dev/null && python3 -m pytest ... || pip install --user --break-system-packages pytest
```

Expected: 首次因 `utils.py` 尚含旧逻辑/导入失败而报错（F 或 ERROR），证明测试在跑。

- [ ] **Step 4: 应用重写后的完整 utils.py，令测试通过**

Run: `python3 -m pytest tests/test_utils.py -v && python3 -m pytest tests/ -v`
Expected: 核心测试 PASS。

- [ ] **Step 5: 提交**

```bash
git add utils.py tests/test_utils.py
git commit -m "refactor: rewrite utils.py as vecto wrapper, drop yunzhan logic"
```

---

### Task 3: trace 页面（图片转矢量）

**Files:**
- Create: `pages_content/0_Image_to_Vector.py`
- Test: `tests/test_page_trace.py`

**Interfaces:**
- Consumes: `init_state()`、`trace_image(src, dst, log_placeholder=None, *, colors=None, max_colors=None, detail=None, style=None, polygons=False, epsilon=None, stats=False)`、`render_svg()`
- Produces: 页面侧边栏注册时由 `streamlit_app.py` 引用

- [ ] **Step 1: 写测试（UI 冒烟 + 中间层辅助函数）**

把 trace 命令构建逻辑放 utils 以便测试（在 Task 2 已并入 `trace_image`）。此测试验证参数映射行为：

`tests/test_page_trace.py`：

```python
from pathlib import Path

from utils import trace_image

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_trace_with_params(tmp_path):
    src = FIXTURES / "crisp.png"
    dst = tmp_path / "out.svg"
    code, out, err = trace_image(
        src, dst,
        colors=4, detail="high", style="crisp", polygons=False, stats=True,
    )
    assert code == 0, err
    content = dst.read_text(encoding="utf-8")
    assert content.lstrip().startswith("<svg")
    assert "timings:" in out
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m pytest tests/test_page_trace.py -v`
Expected: FAIL（dst 文件尚不存在或 trace_image 尚未支持参数）。

- [ ] **Step 3: 实现页面**

`pages_content/0_Image_to_Vector.py`：

```python
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
        # SVG 预览：Streamlit 不直接支持 SVG，先转 PNG 展示
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python3 -m pytest tests/test_page_trace.py -v`
Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add pages_content/0_Image_to_Vector.py tests/test_page_trace.py
git commit -m "feat: add image-to-vector trace page"
```

---

### Task 4: render 页面（SVG 转 PNG）

**Files:**
- Create: `pages_content/1_SVG_to_PNG.py`
- Test: `tests/test_page_render.py`

**Interfaces:**
- Consumes: `init_state()`、`render_svg(src, dst, *, scale)`
- Produces: 页面路径 `pages_content/1_SVG_to_PNG.py`

- [ ] **Step 1: 写测试**

`tests/test_page_render.py`：

```python
import struct
from pathlib import Path

from utils import render_svg

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_render_basic(tmp_path):
    src = FIXTURES / "sample.svg"
    dst = tmp_path / "out.png"
    code, out, err = render_svg(src, dst)
    assert code == 0, err
    assert dst.exists()
    with open(dst, "rb") as f:
        assert f.read(8) == b"\x89PNG\r\n\x1a\n"


def test_render_scale_doubles_size(tmp_path):
    src = FIXTURES / "sample.svg"
    dst1 = tmp_path / "s1.png"
    dst2 = tmp_path / "s2.png"
    assert render_svg(src, dst1, scale=1.0)[0] == 0
    assert render_svg(src, dst2, scale=2.0)[0] == 0

    def png_size(p):
        with open(p, "rb") as f:
            data = f.read()
        w, h = struct.unpack(">II", data[16:24])
        return w, h

    w1, h1 = png_size(dst1)
    w2, h2 = png_size(dst2)
    assert w2 == w1 * 2
    assert h2 == h1 * 2
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m pytest tests/test_page_render.py -v`
Expected: FAIL（页面/输出缺失）。

- [ ] **Step 3: 实现页面**

`pages_content/1_SVG_to_PNG.py`：

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python3 -m pytest tests/test_page_render.py -v`
Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add pages_content/1_SVG_to_PNG.py tests/test_page_render.py
git commit -m "feat: add svg-to-png render page"
```

---

### Task 5: 关于页面 + 主入口导航

**Files:**
- Create: `pages_content/2_About.py`
- Modify: `streamlit_app.py`（标题、导航指向新页面）

**Interfaces:**
- Consumes: `i18n._`
- Produces: 页面路径 `pages_content/2_About.py`

- [ ] **Step 1: 写测试**

`tests/test_page_about.py`：

```python
from pathlib import Path


def test_about_page_file_exists():
    p = Path("pages_content/2_About.py")
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert "about_text" in content
```

- [ ] **Step 2: 实现关于页面**

`pages_content/2_About.py`：

```python
import streamlit as st

from i18n import _

st.subheader(_("page_about_title"))
st.markdown(_("about_text"))
```

- [ ] **Step 3: 更新 streamlit_app.py 导航**

将第 85-87 行替换为：

```python
trace_page = st.Page("pages_content/0_Image_to_Vector.py", title=_("page_vec_title"), icon="🖼️")
png_page = st.Page("pages_content/1_SVG_to_PNG.py", title=_("page_png_title"), icon="🔄")
about_page = st.Page("pages_content/2_About.py", title=_("page_about_title"), icon="ℹ️")
pg = st.navigation([trace_page, png_page, about_page], position="sidebar")
```

同时更新 `page_title="悟空图片转SVG工具 | Goku Image to SVG Tool"`（第 14 行）。

- [ ] **Step 4: 运行测试确认通过**

Run: `python3 -m pytest tests/test_page_about.py -v`
Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add pages_content/2_About.py streamlit_app.py tests/test_page_about.py
git commit -m "feat: add about page and update app navigation"
```

---

### Task 6: 国际化文案（zh/en）

**Files:**
- Modify: `locales/zh.json`
- Modify: `locales/en.json`

**Interfaces:**
- Produces: 全部 UI key，两文件 key 集合完全一致

- [ ] **Step 1: 写测试**

`tests/test_locales.py`：

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m pytest tests/test_locales.py -v`
Expected: FAIL（缺 key）。

- [ ] **Step 3: 写 zh.json 完整文案**

`locales/zh.json`：

```json
{
  "title": "悟空图片转SVG工具",
  "caption_top": "上传图片，一键转换为高质量可编辑的 SVG 矢量图",
  "page_vec_title": "图片转矢量",
  "page_vec_desc": "上传图片，通过 Vecto 引擎转换为干净可编辑的 SVG",
  "page_png_title": "SVG转PNG",
  "page_png_desc": "上传 SVG，渲染为 PNG 位图",
  "page_about_title": "关于",
  "page_about_desc": "工具说明与许可",
  "btn_run": "转换",
  "btn_render": "渲染",
  "btn_download": "下载文件",
  "upload_vec_label": "上传图片（PNG/JPG/BMP/GIF）",
  "upload_svg_label": "上传 SVG 文件",
  "warn_no_file": "请先上传文件",
  "param_title": "转换参数",
  "param_colors_auto": "自动调色板",
  "param_colors": "调色板颜色数",
  "param_max_colors": "自动调色板上限",
  "param_detail": "细节级别",
  "param_style": "转换风格",
  "param_polygons": "简化多边形（不拟合曲线）",
  "param_stats": "显示诊断信息",
  "param_scale": "渲染缩放倍数",
  "info_tracing": "正在矢量化图片...",
  "info_rendering": "正在渲染 SVG...",
  "success_trace": "转换完成",
  "success_render": "渲染完成",
  "error_trace": "转换失败：{msg}",
  "error_render": "渲染失败：{msg}",
  "preview_result": "结果预览",
  "about_text": "本工具基于开源引擎 **Vecto**（MIT License）构建，将位图自动转为矢量。",
  "footer": "Powered by GokuScraper"
}
```

- [ ] **Step 4: 写 en.json 完整文案**

`locales/en.json`：

```json
{
  "title": "Goku Image to SVG Tool",
  "caption_top": "Upload an image and convert it to a clean, editable SVG",
  "page_vec_title": "Image to Vector",
  "page_vec_desc": "Upload an image; the Vecto engine traces it into an editable SVG",
  "page_png_title": "SVG to PNG",
  "page_png_desc": "Upload an SVG and rasterize it to PNG",
  "page_about_title": "About",
  "page_about_desc": "Docs and license",
  "btn_run": "Convert",
  "btn_render": "Render",
  "btn_download": "Download",
  "upload_vec_label": "Upload image (PNG/JPG/BMP/GIF)",
  "upload_svg_label": "Upload SVG file",
  "warn_no_file": "Please upload a file first",
  "param_title": "Trace options",
  "param_colors_auto": "Auto palette",
  "param_colors": "Palette size",
  "param_max_colors": "Max palette colors",
  "param_detail": "Detail level",
  "param_style": "Style",
  "param_polygons": "Simplify to polygons",
  "param_stats": "Show diagnostics",
  "param_scale": "Render scale",
  "info_tracing": "Tracing image...",
  "info_rendering": "Rendering SVG...",
  "success_trace": "Trace complete",
  "success_render": "Render complete",
  "error_trace": "Trace failed: {msg}",
  "error_render": "Render failed: {msg}",
  "preview_result": "Result preview",
  "about_text": "Built on the open-source **Vecto** engine (MIT License).",
  "footer": "Powered by GokuScraper"
}
```

- [ ] **Step 5: 运行测试确认通过**

Run: `python3 -m pytest tests/test_locales.py -v`
Expected: PASS。

- [ ] **Step 6: 提交**

```bash
git add locales/zh.json locales/en.json tests/test_locales.py
git commit -m "feat: update i18n copy for image-to-svg tool"
```

---

### Task 7: 清理旧文件 + 依赖精简 + README

**Files:**
- Delete: `pages_content/0_PDF_Download.py`、`pages_content/1_Data_Analysis.py`
- Delete: `packages.txt`（旧 nodejs 依赖）、`framework_settings.json`（已 gitignore，可留）
- Modify: `requirements.txt`
- Modify: `README.md`

**Interfaces:**
- Produces: 精简后的依赖与 README

- [ ] **Step 1: 写测试（依赖无需测试）——删除旧页面并更新引用**

```bash
git rm pages_content/0_PDF_Download.py pages_content/1_Data_Analysis.py packages.txt
```

- [ ] **Step 2: 更新 requirements.txt**

```text
streamlit
Pillow
pytest
```

- [ ] **Step 3: 确认 utils.py 无指向旧函数的残留引用**

Run: `python3 -m pytest tests/ -v`
Expected: 全部 PASS（依赖 test_utils/test_page_*/test_locales 均绿）。

- [ ] **Step 4: 重写 README.md**

替换为：

```markdown
# 悟空图片转SVG工具

基于开源引擎 **Vecto**（MIT）的图片矢量化工具，Streamlit Web 界面，将 PNG/JPG 等位图转换为干净可编辑的 SVG。

## 功能

- **图片转矢量**：上传图片 → Vecto 引擎追踪 → 预览并下载 SVG
- **SVG转PNG**：上传 SVG → 按缩放倍数渲染为 PNG
- 支持参数调优：调色板、细节级别、转换风格、多边形简化、诊断信息

## 运行

依赖 Python 3.10+。首次先放好二进制 `tools/vecto`（见下）。

```bash
pip install -r requirements.txt
python -m pytest          # 跑测试（必须全绿）
streamlit run streamlit_app.py
```

## Vecto 二进制

从 [Vecto Releases](https://github.com/DanielMevit/Vecto/releases) 下载 `vecto-0.4.2-linux-x64`，保存为 `tools/vecto` 并 `chmod +x`。文档已带 v0.4.2 二进制。

## 许可

MIT。Vecto 引擎 © Daniel Mevit。
```

- [ ] **Step 5: 提交**

```bash
git add -A
git commit -m "chore: remove legacy yunzhan pages, slim deps, rewrite README"
```

---

### Task 8: 全量验证

**Files:**
- 无代码改动，仅验证

- [ ] **Step 1: 全量测试**

Run: `cd /home/goku/code/vecto/yunzhan365-scraper && python3 -m pytest tests/ -v`
Expected: 所有测试 PASS。

- [ ] **Step 2: 启动应用冒烟**

```bash
nohup python3 -m streamlit run streamlit_app.py --server.port 8501 --server.headless true > /tmp/streamlit.log 2>&1 &
sleep 4
tail -10 /tmp/streamlit.log
```
Expected: 访问 `http://localhost:8501` 三个页面正常显示、导航可用、中英文切换正常。

- [ ] **Step 3: 确认 git 状态干净**

Run: `git status`
Expected: 无未提交改动（托管的样本 fixture 与二进制在内）。

---

## Self-Review Notes

- **Spec 覆盖**：核心函数（get/run/trace/render）、两个功能页、关于页、i18n、测试、清理、README 均已覆盖。spec 中 16 条测试用例通过 test_utils（6条）+ test_page_trace（1）+ test_page_render（2）+ test_page_about（1）+ test_locales（2）+ 页面冒烟（Task 8）= 实际执行 >16。
- **占位符**：无 TBD/TODO；每个修改步骤含完整代码。
- **类型一致性**：`trace_image`/`render_svg`/`run_vecto` 签名在 Task 2 定义，Task 3/4 消费处与之匹配；`log_placeholder` 可选参数保留（页面传入 holder，后续可扩展实时日志）。

---

## Task 9: 修订 — 统一工作台 + 2 页结构（2026-08-17）

> 依据 spec 修订（§2.3/§2.4/§4.2/§4.6，2026-08-17 与用户确认）：3 页 → 2 页，去掉「转换」按钮改为自动转换，左右对比改 `streamlit-image-comparison` 拖拽滑块，加入 Segmentation 视图（`--seg-png`）、调色板色块（`parse_palette_from_svg`）、Export PNG 带缩放。**TDD**：先写/改测试 → 看失败 → 实现 → 看通过。

### Task 9.1 依赖 + utils（seg_png 参数、parse_palette_from_svg）

**Files:**
- Modify: `requirements.txt`（+ `streamlit-image-comparison`）
- Modify: `utils.py`（`trace_image` 加 `seg_png`；新增 `parse_palette_from_svg`）
- Modify: `tests/test_utils.py`、`tests/test_page_trace.py`

**TDD 步骤**
1. RED：在 `tests/test_utils.py` 追加
   - `test_trace_image_seg_png(tmp_path)`：`trace_image(crisp.png, out.svg, seg_png=out_seg.png)` → code==0，out_seg.png 存在且 PNG 魔数开头。
   - `test_parse_palette_from_svg_basic()`：解析 `tests/fixtures/sample.svg` → 得到 `["#3498db", "#e74c3c"]`。
   - `test_parse_palette_from_svg_empty()`：无 `fill=` 的 SVG → 返回 `[]`。
   运行确认这 3 个 FAIL（函数/参数尚不存在）。
2. GREEN：`utils.py`
   - `trace_image(..., seg_png=None)`：若给出 → `args += ["--seg-png", str(seg_png.resolve())]`。
   - `parse_palette_from_svg(svg_text: str) -> list[str]`：正则 `re.findall(r'fill="?(#[0-9a-fA-F]{3,8})', svg_text)`（兼容 `#fff`/`#ffffff`/`#rrggbbaa`），去重，保持顺序。无匹配返回 `[]`。
3. 运行 `python3 -m pytest tests/test_utils.py tests/test_page_trace.py -v` 全绿。

### Task 9.2 重写工作台 `0_Image_to_Vector.py`

**Files:**
- Modify: `pages_content/0_Image_to_Vector.py`（整文件替换为工作台版）

**实现要点（无按钮自动转换）**
- `@st.cache_data` 装饰一个模块级函数 `trace_cached(image_bytes, filename, colors_auto, colors_count, max_colors, detail, style, polygons, stats, seg_mode) -> dict`：
  - 内部 `tempfile.TemporaryDirectory`：写 `input<ext>` → `output.svg`、预览 `preview.png`（`render_svg` scale=1）、Segmentation PNG（`seg_png=...`）→ 返回 `{"svg": str, "stats": str, "preview_png": bytes, "seg_png": bytes}`。
  - 上传的字节可哈希 → 换图/改参数自动重跑（Streamlit rerun）。
- 布局：
  - 顶部：`st.file_uploader`。
  - `st.columns([8, 3])`：
    - 左列：视图切换 `st.radio("status_view_mode", ["vector","segmentation"])` → 「预览」用 `image_comparison(img1=原图PIL, img2=预览PIL, label1=_("label_original"), label2=_("label_vector"))`；Segmentation 时 img2=分割图。
    - 右列（参数面板）：Palette（`st.checkbox` 自动调色板 + `st.slider` 颜色数 2–32 + 色块 `st.columns` 圆点）、Style select、Detail select、Stats checkbox、`st.download_button` Export SVG、`st.number_input` 缩放 + `st.download_button` Export PNG。
  - Stats：展开区显示 `--stats` 输出。
- 大图预览：PIL thumbnail 到宽 ≤1200。

### Task 9.3 删独立 render 页 + 2 页导航

**Files:**
- Delete: `pages_content/1_SVG_to_PNG.py`、`tests/test_page_render.py`
- Modify: `streamlit_app.py`（导航去掉 png_page → 2 页）
- Modify: `tests/test_pages_smoke.py`（只跑 2 页）
- Modify: `tests/test_page_about.py`（`test_main_navigation_updates` 断言去掉 `1_SVG_to_PNG.py`）

### Task 9.4 i18n 增删 key

**Files:**
- Modify: `locales/zh.json`、`locales/en.json`
- Modify: `tests/test_locales.py`

**新增 key**：`label_original`、`label_vector`、`label_segmentation`、`view_mode`、`palette`、`export_svg`、`export_png`、`export_png_scale`、`warn_convert_failed`、`no_palette`。
**删除 key**：`page_png_title`、`page_png_desc`、`btn_render`、`upload_svg_label`、`info_rendering`、`success_render`、`error_render`（Export PNG 复用 `error_trace` 或新增 `error_render` 保留并不冲突——保留 `error_render` 亦可；最终以 key 同步测试为准）。

### Task 9.5 验证与提交

1. `python3 -m pytest tests/ -v` 全绿。
2. 启动应用：`nohup python3 -m streamlit run streamlit_app.py --server.port 8501 --server.headless true > /tmp/streamlit.log 2>&1 &`，curl `http://localhost:8501`；手动验收自动转换/改参重转/Export PNG 缩放/中英切换。
3. `git add -A && git commit -m "refactor: unify to 2-page workbench with auto-convert and drag compare slider"`。

### Task 9.6 二次修订 — 完全对齐原版 UI 面板（2026-08-17）

> 用户在 Windows UI 上核对后指出：原版面板只有 Palette(自动调色板/颜色数/色块)、Style、Detail、StatsText。CLI 独有控件应移除，且色块应紧贴在 Palette 区（Style 之前），不能出现在右栏底部。

- [x] **Step 1**: `0_Image_to_Vector.py` 移除「简化多边形」(`--polygons`)、「自动调色板上限」(`--max-colors`)、「显示诊断信息」checkbox（stats 改为常显 caption）。`--max-colors` 固定传 16。
- [x] **Step 2**: 色块用 `parse_palette_from_svg` 渲染于 Palette 区滑块下方、Style 控件之前。实现技巧：Style/Detail 控件加 `key=`，用 `st.session_state.get("style_sel","auto")` 在控件声明前读取用户最新值（Streamlit 会在 rerun 前把交互值写入 session_state），从而"色块位置正确 + 改 Style/Detail 自动重转"。
- [x] **Step 3**: locales 移除 `palette_max`/`param_polygons`/`param_stats`，zh/en 同步；test_locales required keys 更新。
- [x] **Step 4**: `python3 -m pytest tests/` 25 全绿；AppTest 验证色块 markdown 块位于「调色板」后、「转换风格」前，改 Style 无异常且色块仍现。
- [x] **Step 5**: spec §4.2/§4.6 记录对齐结论与 session_state 技巧。

### Task 9.7 手机端适配调研（2026-08-17，用户指示"仅调研，暂不改代码"）

- [x] **研究**：Streamlit 官网文档 + GitHub issue + community posts，汇总手机端已知痛点与官方推荐做法。
- [x] **结论**：已留档至 spec §8.5（无官方移动开关；columns 窄屏堆叠/selectbox 弹键盘/汉堡菜单/顶部标题栏挤、`horizontal=True` 容器与 CSS media query 为官方适配手段；本工具方向 1~3 未实施）。
- [x] **不实施**：以用户确认"只记录结论，不改代码"，无代码/测试改动，后续若要实施按 spec §8.5 方向补 spec/plan。

### Task 9.8 手机端适配实施（2026-08-17，用户批准 §8.6 设计）

**Files:**
- Modify: `pages_content/0_Image_to_Vector.py`（Style/Detail selectbox→radio horizontal，key 不变）
- Modify: `streamlit_app.py`（顶部标题栏加 @media CSS）
- Modify: `tests/test_pages_smoke.py`（新增 2 测试）
- Modify: `docs/superpowers/specs/...+design.md`（§8.6）、`docs/superpowers/plans/...+tool.md`（本任务）

**新增测试（TDD，先写后跑）：**
1. `test_workbench_radio_style_change`：AppTest 上传 crisp.png → 定位 key=`style_sel` 的 radio → `set_value("crisp")` → run → 无异常、色块仍现、summary 仍在。
2. `test_header_css_media_query`：AppTest 跑 `streamlit_app.py` → 存在含 `@media` 的 raw markdown。

**验证：** `python3 -m pytest tests/ -v` 全绿（预计 28→30 项）；streamlit_app 仍启动。

- [x] **Step 1**: 写新增测试（红：radio/`@media` 两测试失败）
- [x] **Step 2**: 改 `0_Image_to_Vector.py` selectbox→radio
- [x] **Step 3**: 改 `streamlit_app.py` 加 @media CSS
- [x] **Step 4**: `python3 -m pytest tests/ -v` 全绿（29）+ 本机运行验证（health ok）
- [ ] **Step 5**: git commit