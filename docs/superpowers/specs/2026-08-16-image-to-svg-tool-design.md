# 悟空图片转SVG工具 — 设计文档

日期：2026-08-16
状态：已确认（基础方案 + 2026-08-17 修订：2 页结构/自动转换/拖拽对比滑块/Segmentation/色块解析）

## 1. 背景与目标

将现有 `yunzhan365-scraper` Streamlit 应用**原地改造**成一个图片转矢量（Image → SVG）工具。

- 移除旧功能：PDF 下载、云展网数据分析、Node.js 解码、PDF 合成。
- 引入新能力：基于开源项目 **Vecto**（MIT，C# .NET 8 图片矢量化引擎）的官方 Linux CLI 二进制。
- 通过 **Streamlit 同步 `subprocess` 调二进制**（方案 A），完整复用 Vecto CLI 全部能力。

应用名称：**悟空图片转SVG工具**（中）/ Goku Image to SVG Tool（英）。

## 2. 核心技术决策

### 2.1 调用方式：Streamlit 同步 subprocess 调二进制（方案 A，已确认）

```
网页上传图片 → subprocess.run([vecto, "trace", ...]) → 得到 SVG → 预览/下载
```

依据（调研验证）：
- Vecto 官方 linux-x64 二进制为 **self-contained**，无需 .NET 运行时，仅 35MB。
- 已在本机 WSL 实测：启动 0.4s，trace 小图约 100ms，4K 图约 4.5s → 同步调用完全足够，无需异步队列（YAGNI）。
- 与现有 `utils.py:166` 调 Node.js 的 subprocess 模式一致。
- Streamlit 官方支持 `subprocess.run` 调外部程序。

### 2.2 二进制来源与存放（已确认）

- 来源：GitHub Releases 官方 `vecto-0.4.2-linux-x64`（MIT 许可）。
- 存放：**项目内 `tools/vecto`，入库（commit 到 git）**，保证部署即用。
- 兼容性：目前目标环境为 Linux / WSL。Windows/macOS 部署需换对应二进制（列入未来扩展）。

### 2.3 左右对比方式（2026-08-17 确认）

- 采用 **`streamlit-image-comparison` 拖拽滑块**（PyPI 0.0.4，MIT，基于 Knightlab JuxtaposeJS，接受 PIL 图像；调研已核实可安装、可传图片字节）。
- 替代方案（曾考虑）：`st.columns` 固定并排、`streamlit-extras` 的 `image_compare_slider`。用户选定拖拽滑块（更直观的对比体验）。
- 大图预览：先 PIL thumbnail 缩到宽 ≤1200 再传入组件，避免 JuxtaposeJS 处理超大图变慢。

### 2.4 页面结构（2026-08-17 确认）

- **2 页**：`0_Image_to_Vector.py`（统一工作台）+ `2_About.py`。
- 原「SVG 转 PNG」独立页（`1_SVG_to_PNG.py`）删除，能力并入工作台 Export PNG（带缩放倍数）。
- Nodes 视图不做（CLI 无此能力，需 C# 引擎）。

## 3. 架构

```
yunzhan365-scraper/
├── streamlit_app.py          # 主入口：保留外壳（logo / i18n / 布局 / 导航，2 页）
├── pages_content/
│   ├── 0_Image_to_Vector.py  # 统一工作台：上传 → 自动转换 → 拖拽对比 + 导出（trace/render/seg）
│   └── 2_About.py            # 关于 / 参数说明 / 许可
├── utils.py                  # 精简：二进制定位 + subprocess 封装 + 色块解析
├── tools/
│   └── vecto                 # 官方 linux-x64 二进制（35MB，入库）
├── locales/                  # zh.json / en.json（矢量转换文案，无 SVG→PNG 独立页）
├── i18n.py                   # 保留原样
├── requirements.txt          # streamlit + pillow + streamlit-image-comparison + pytest
├── README.md                 # 重写为新的工具说明
└── docs/superpowers/specs/   # 本文档
```

## 4. 功能规格

### 4.1 utils.py 核心函数（改造现有）

- `get_vecto_binary()` — 校验 `tools/vecto` 存在且可执行；否则返回错误提示（含安装指引）。
- `run_vecto(args, cwd)` — 封装 `subprocess.run`，返回 `(code, stdout, stderr)`；统一设置超时、捕获输出、处理非零返回码。
- `trace_image(src, dst, opts)` — 拼 `vecto trace <src> -o <dst>` + 各参数；支持 `seg_png` 输出分割图。
- `render_svg(src, dst, scale)` — 拼 `vecto render <svg> -o <png> --scale <n>`。
- `parse_palette_from_svg(svg_text)` — 从 trace 输出 SVG 的 `fill` 颜色解析出 hex 列表，用于调色板色块展示。
- 输入输出统一放临时目录（`tempfile.TemporaryDirectory`），结束后清理。
- 删除：Node.js 解码（`decode_configs` 等）、PDF 合成相关全部函数。

### 4.2 页面 0「图片转矢量 / Image to Vector」(统一工作台，2 页结构主页面)

对标原版 Vecto 桌面 UI（`MainWindow.xaml` / `MainViewModel.cs`），改为单页面工作台：

```
上传 (top, full width)
┌─────────────────────────────────┬─────────────────────┐
│ 视图切换 [Vector|Segmentation]    │  Palette             │
│ 拖拽对比滑块 (原图 | 矢量)          │   ⚐ 自动调色板        │
│   （streamlit-image-comparison）  │   颜色数 2–32        │
│  ── Export SVG  Export PNG┌缩放┐ │   ▣ 色块 swatches   │
│                                 │  Style（Auto/Crisp/  │
│                                 │   Blended/Photo）    │
│                                 │  Detail（Low/Med/High）│
│                                 │  StatsText（常显）    │
└─────────────────────────────────┴─────────────────────┘
```

关键交互：
- **上传即转换**：`st.file_uploader` 后无「转换」按钮，直接用 `st.cache_data` 函数缓存转换结果，key = 文件字节 + 全部参数。上传/参数变更即自动重转（对应原版 250ms 防抖，Streamlit 无事件防抖 → 用整页 rerun + 缓存兜底）。
- **拖拽对比滑块**：`streamlit-image-comparison`（PyPI 0.0.4，MIT，JuxtaposeJS），`img1=原图`、`img2=矢量PNG预览`；**Streamlit 不支持直接显示 SVG → 预览先经 `vecto render --scale 1` 转 PNG**。大图先 PIL thumbnail 缩到 ≤1200 宽再传给组件。
- **视图切换**：Vector（SVG→PNG 预览）| Segmentation（`vecto trace --seg-png` 的分割图）。**Nodes 视图不做**（需 C# 引擎，CLI 无此能力）。
- **右侧参数面板**（映射原版右侧 232px 面板，完全对齐原版 UI 控件集合）：
  - Palette：`st.checkbox` 自动调色板（默认开）→ `st.slider` 2–32 颜色数（auto 时禁用，对齐原版）→ 从 SVG `fill` 解析的 **色块**（`parse_palette_from_svg`）**紧贴在下**（通过控件 `key` + `st.session_state` 读取 Style/Detail 最新值，实现"色块渲染在 Style 之前 + 改参数自动重转"两者兼得）。
  - Style：select Auto / Crisp(no blending) / Blended(anti-aliased) / Photo（默认 Auto）。
  - Detail：select Low / Medium / High（默认 Medium）。
  - StatsText：**常显**（对齐原版只读 StatsText），展示 `--stats` 解析参数与分段耗时；无开关。
  - **不做**（CLI 独有、原版 GUI 不暴露，已移除）：`--polygons`（简化多边形）、`--max-colors`（自动调色板上限滑块）、stats checkbox。
- **导出**：
  - Export SVG（下载原始 SVG）。
  - Export PNG（`st.number_input` 缩放倍数，默认 1 → `vecto render --scale <n>` 下载 PNG），替代原独立「SVG 转 PNG」页。
- 失败处理：展示 returncode + stderr + 友好提示（如缺二进制）。

### 4.3 页面 1「SVG 转 PNG」→ 已合并进 4.2 的 Export PNG

原独立页删除，`vecto render` 的 M/L/H/V/C/Z 路径能力通过 Export PNG（带缩放）保留。

### 4.4 页面 2「关于 / About」

- Vecto 引擎介绍、各参数含义说明、MIT 许可、免责声明。

### 4.5 外壳保留（已确认）

- 保留 `i18n.py` + `locales/` 中英文切换机制。
- 保留 logo、顶部布局、侧边栏 `st.navigation` 多页结构（**2 页**：工作台 + 关于）。
- 前端（`streamlit_app.py`）顶部"开源"入口此前已按用户要求删除，保持删除状态。

### 4.6 调研结论：原版 Vecto UI 元素 → Streamlit 替代（2026-08-17）

| 原版元素（`Vecto.App/MainWindow.xaml`） | Streamlit 替代 | 说明 |
|------|------|------|
| 顶栏 Open/Paste/Export SVG/Copy SVG/Export PNG | 上传即转换；右侧 Export SVG + Export PNG（缩放）按钮 | 无手动按钮，全自动 |
| 左侧 ScrollViewer 原始位图 | 拖拽对比滑块的左半（img1=原图） | `streamlit-image-comparison` |
| 右侧 ScrollViewer Vector/Segmentation/Nodes ComboBox | 视图切换 selectbox（Vector/Segmentation） | Nodes 不做 |
| 中缝 GridSplitter 拖拽分栏 | JuxtaposeJS 拖拽滑块（用户选定） | 见决策 2.3 |
| 右侧 232px 参数面板 | `st.columns` 右侧栏（Palette/Style/Detail/Stats） | 用户选定「右侧栏内」 |
| 自动 trace + 250ms 防抖（MainViewModel） | `st.cache_data`（key=文件字节+参数）上传/改参即重转 | Streamlit 无防抖事件 |
| 调色板色块（Swatches，Brush） | `parse_palette_from_svg()` 从 SVG `fill` 解析 hex 展示，**置于 Palette 区滑块正下方（Style 之前）** | 用户选定；用控件 `key`+session_state 读取 Style/Detail 最新值实现 |
| 底部 Status 栏 + StatsText | `st.caption` StatsText 常显（`--stats`） | 对齐原版，无开关 |
| Zoom Fit/1:1/± （桌面级缩放平移） | **不做** | Streamlit 预览不缩放，PNG 导出用 `--scale` 兜底 |

> **对齐原版 UI 控件集合（2026-08-17 二次确认）**：原版 `MainWindow.xaml` 面板仅含 Palette(checkbox+颜色数滑块+色块)、Style、Detail、StatsText。CLI 独有、GUI 不暴露的 `--polygons`、`--max-colors`、stats checkbox 已从页面移除（`--max-colors` 固定传 16，`--polygons` 不传，stats 常显）。
>
> 实现技巧：左栏/右栏渲染顺序按脚本执行顺序；色块需显示在 Style 控件之前，但 trace 需读取 Style/Detail 的参数值。解法 = 控件加 `key=`，用 `st.session_state.get("style_sel","auto")` 在控件前读取用户最新提交值（Widget 交互值会先写入 session_state 再 rerun，已用 AppTest 验证），实现"色块位置 + 改参自动重转"两者兼得。

依赖：`streamlit-image-comparison`（PyPI 0.0.4，MIT，基于 Knightlab JuxtaposeJS，接受 PIL 图像）。

## 5. 数据流 / 错误处理

1. 上传文件写入缓存目录（文件字节 + 参数为 `st.cache_data` key）。
2. `st.cache_data` 中调 `trace_image` → `vecto trace`（`subprocess.run` 带 `timeout` 120s）。
3. 预览：`render_svg --scale 1` 输出 PNG（Streamlit 不能直接显示 SVG）；Segmentation 视图输出 `--seg-png`。
4. 成功：展示 SVG/下载；失败：展示 `returncode`、`stderr`、提示（如"请确认 tools/vecto 存在且可执行"）。
5. 结束：清理临时目录。

## 6. 测试（每个功能必须配套测试）

测试框架：**pytest**，测试文件放 `tests/` 目录，命令 `python -m pytest`。

### 6.1 测试前置（fixture）

- `vecto samples` 生成测试样本图（crisp.png / blended.png / transparent.png）放入 `tests/fixtures/`（入库）。
- 一个简单 SVG fixture（`tests/fixtures/sample.svg`），供 render 测试使用。

### 6.2 逐功能测试用例

| # | 被测功能 | 测试用例 | 断言 |
|---|---------|---------|------|
| 1 | `get_vecto_binary()` | 二进制存在且可执行 | 返回绝对路径，无报错 |
| 2 | `get_vecto_binary()` 错误路径 | 模拟二进制缺失/不可执行 | 抛出友好异常，含安装指引 |
| 3 | `run_vecto()` 成功路径 | 调 `vecto --version` | `code==0`，stdout 含 `vecto 0.4.2` |
| 4 | `run_vecto()` 非零返回码 | 调未知命令 | 返回非零 code，stderr 非空 |
| 5 | `run_vecto()` 超时 | 短 timeout 下跑慢命令 | 抛超时异常，不悬挂 |
| 6 | `trace_image()` 基础 | crisp.png → SVG | 成功，输出文件存在、非空、含 `svg` |
| 7 | `trace_image()` 各参数映射 | colors/detail/style/polygons 各组合 | 命令参数正确拼装且执行成功 |
| 8 | `trace_image()` --stats | 开启 stats | stdout 含 `timings:` 诊断信息 |
| 9 | `trace_image()` 透明图 | transparent.png | 成功输出 SVG，保留透明度语义 |
| 10 | `trace_image()` 无效输入 | 传入不存在的文件 | 非零返回码，友好报错 |
| 11 | `trace_image()` --seg-png | crisp.png, seg_png 目标路径 | seg PNG 文件存在且为 PNG 魔数 |
| 12 | `parse_palette_from_svg()` 基础 | sample.svg（含 fill） | 返回去重后的 hex 颜色列表 |
| 13 | `parse_palette_from_svg()` 空/无fill | 无 `<path fill>` 的 SVG | 返回空列表，不抛异常 |
| 14 | `render_svg()` 基础 | sample.svg → PNG | 成功，输出 PNG 文件存在、非空、PNG 魔数开头 |
| 15 | `render_svg()` --scale | scale=2 | 输出 PNG 尺寸约为 scale=1 的 2 倍 |
| 16 | `render_svg()` 无效 SVG | 损坏内容 | 非零返回码，友好报错 |
| 17 | 临时目录清理 | 转换完成后 | 临时目录被删除，无残留文件 |
| 18 | i18n 双语言 | 所有 UI key | zh/en 两个 locale 的 key 集合一致，无缺失 |
| 19 | 页面可渲染（2 页） | 用 `streamlit.testing` 跑工作台+关于页 | 页面脚本无异常执行 |
| 20 | 导航 | `streamlit_app.py` | 含 `0_Image_to_Vector.py`、`2_About.py`，不含 `1_SVG_to_PNG.py` |

### 6.3 手动验收（发布前必过）

- 浏览器打开：上传→自动转换→拖拽对比→改参数自动重转→Export SVG/PNG 全流程。
- 中英文切换后文案正常。
- 无 `tools/vecto` 时的错误提示友好。

## 7. 交付物清单

- [x] `tools/vecto` 二进制落地（chmod +x），提交入库
- [ ] `utils.py`：`trace_image` 支持 `seg_png`、新增 `parse_palette_from_svg`
- [x] `pages_content/0_Image_to_Vector.py`（转换按钮版）、`2_About.py`；**本次改为工作台版 + 删 `1_SVG_to_PNG.py`**
- [ ] `streamlit_app.py` 导航 2 页
- [ ] `locales/zh.json`、`en.json` 新文案（Export PNG/缩放/视图/色块等）
- [ ] `requirements.txt`（+ `streamlit-image-comparison`）
- [ ] `tests/` 上述测试用例全部通过（`python -m pytest` 全绿）
- [x] `tests/fixtures/` 样本图与 SVG fixture 入库
- [x] `README.md` 重写（含测试运行说明）
- [x] 删除旧文件：`0_PDF_Download.py`、`1_Data_Analysis.py`、Node.js 相关代码
- [ ] 本机运行验证 + i18n 双语言验证

## 8. 明确不做（YAGNI / 范围外）

- 不引入异步任务队列 / Celery / Redis（Vecto 足够快）。
- 不重写 Vecto C# 引擎为 Python（2200 行核心，无意义）。
- 不接入 Streamlit Community Cloud 部署配置（用户未要求；二进制入库已为云端就绪铺路）。
- 不做多用户并发调度（个人工具场景）。
- 测试仅覆盖本工具自有代码（utils / 页面 / i18n），不测试 Vecto 引擎本身的正确性（上游项目已自带 14 项几何不变量测试 + `vecto bench`）。

## 8.5 手机端适配调研结论（2026-08-17，仅调研未实施）

> 用户要求"调研一下"Streamlit 手机适配方案，**保持现状暂不改代码**，本节目的是留档，不含任何待办。

**结论：Streamlit 无官方"移动版开关"**，手机浏览器直接访问 URL 即用；其 Web 布局非移动优先，有若干已知痛点：

| 痛点 | 说明 | 状态 |
|------|------|------|
| `st.columns` 窄屏自动垂直堆叠 | 官方文档明确：屏幕过窄时 columns stack 而非 flex 换行。本项目 `[8,3]` 左右分栏在手机上为"预览在上、参数面板在下"，顺序可用但需滚动 | 无官方关闭开关（streamlit/streamlit#16056 请求中） |
| `st.selectbox` 手机上点触发虚拟键盘 | 实现为输入框+下拉，point-and-tap 时先弹键盘 | 社区多年抱怨无官方修复；可用 `st.radio`(horizontal) 替代 |
| sidebar → 汉堡菜单 | `st.navigation` sidebar 位置在窄屏自动折叠为汉堡菜单 | 官方已适配 |
| 顶部固定 `st.columns` 标题栏 | logo/标题/图片在窄屏挤成一列 | 可用 CSS 处理，未做 |
| 拖拽对比滑块 | `streamlit-image-comparison`（JuxtaposeJS 定宽）窄屏勉强可用 | 第三方便宜行事 |

**官方推荐的适配手段**：① `st.container(horizontal=True)` 横向容器窄屏自动 flex 换行（vs columns 堆叠更可控）；② `st.markdown` 注入 CSS media query；③ 元素 `width="stretch"` 自适应。

**本工具已实施的优化（2026-08-17，见 §8.6）**：
1. Style/Detail 的 `st.selectbox` → `st.radio`(horizontal)，避免手机弹键盘；
2. 顶部标题栏加响应式 CSS（media query），窄屏隐藏公众号块、标题/logo 居中、字号缩小；
3. 参数面板 `[8,3]` 分栏在窄屏保持自动堆叠（预览在上、参数在下），**未挪 sidebar**——避免破坏桌面"右栏对齐原版"，列为已知限制。

## 8.6 手机端适配改动（2026-08-17，已实施）

> 依据 §8.5 调研结论，实施 2 项低成本改动消除手机三大痛点中最影响使用的前两项目；不动布局结构。

### 改动 1：Style/Detail selectbox → radio(horizontal)
- **文件**：`pages_content/0_Image_to_Vector.py`
- 两处 `st.selectbox` 换为 `st.radio(label_visibility="collapsed", horizontal=True, key="style_sel"/"detail_sel")`。
- **关键**：`key` 不变，`st.session_state.get("style_sel","auto")` 技巧（色块位置正确 + 改参自动重转）完全兼容，无行为变化。
- 桌面观感：横排小按钮，仍在原版面板位置。

### 改动 2：streamlit_app.py 响应式 CSS
- media query：`@media (max-width: 700px)`——公众号图（gzh 块）`display:none`；标题/logo 居中；`h1` 字号缩小。桌面不受影响。

### 已知限制（本次不改）
- `st.columns([8,3])` 手机堆叠为"预览在上、参数在下"，需滚动；未挪 sidebar（桌面右栏对齐原版优先）。
- `streamlit-image-comparison` + slider 触摸体验受第三方组件限制。
- 不能关闭 columns stacking（streamlit/streamlit#16056 未合并）。

## 9. 参考

- Vecto 仓库：https://github.com/danielmevit/vecto （MIT）
- CLI 帮助：`vecto --help`（trace / render / samples / bench）
- 二进制 SHA-256（v0.4.2 linux-x64）：`f7e0df8b9136b3d65e1f7ad9fe1eca2d685564bf547616039e7ced08a02acefd`