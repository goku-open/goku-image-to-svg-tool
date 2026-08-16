# 悟空图片转SVG工具 — 设计文档

日期：2026-08-16
状态：已确认（用户已批准核心方案）

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

## 3. 架构

```
yunzhan365-scraper/
├── streamlit_app.py          # 主入口：保留外壳（logo / i18n / 布局 / 导航）
├── pages_content/
│   ├── 0_Image_to_Vector.py  # 图片 → SVG（trace）
│   ├── 1_SVG_to_PNG.py       # SVG → PNG（render）
│   └── 2_About.py            # 关于 / 参数说明 / 许可（可选页）
├── utils.py                  # 精简：二进制定位 + subprocess 封装 + 临时文件管理
├── tools/
│   └── vecto                 # 官方 linux-x64 二进制（35MB，入库）
├── locales/                  # zh.json / en.json 改为矢量转换文案
├── i18n.py                   # 保留原样
├── requirements.txt          # 精简为 streamlit + pillow
├── README.md                 # 重写为新的工具说明
└── docs/superpowers/specs/   # 本文档
```

## 4. 功能规格

### 4.1 utils.py 核心函数（改造现有）

- `get_vecto_binary()` — 校验 `tools/vecto` 存在且可执行；否则返回错误提示（含安装指引）。
- `run_vecto(args, cwd)` — 封装 `subprocess.run`，返回 `(code, stdout, stderr)`；统一设置超时、捕获输出、处理非零返回码。
- `trace_image(src, dst, opts)` — 拼 `vecto trace <src> -o <dst>` + 各参数。
- `render_svg(src, dst, scale)` — 拼 `vecto render <svg> -o <png> --scale <n>`。
- 输入输出统一放临时目录（`tempfile.TemporaryDirectory`），结束后清理。
- 删除：Node.js 解码（`decode_configs` 等）、PDF 合成相关全部函数。

### 4.2 页面 0「图片转矢量 / Image to Vector」(trace)

- 上传图片类型：png / jpg / bmp / gif；上传后 `st.image` 预览原图。
- 参数控件（对应 CLI）：
  - `--colors`：滑块 2–32，或 "auto"（默认 auto，即 `--colors auto`）
  - `--max-colors`：自动调色板上限，默认 16
  - `--detail`：select（low / medium / high，默认 medium）
  - `--style`：select（auto / crisp / blended / photo，默认 auto）
  - `--polygons`：checkbox（跳过曲线拟合，输出简化多边形）
  - `--epsilon`：多边形简化容差（px），默认按 CLI 默认
  - `--stats`：checkbox（显示解析出的参数与分阶段耗时）
  - `--seg-png`：可选输出分割图（体现"二进制有啥功能就做全"）
- 交互：点「转换」→ `st.spinner` → 成功显示 SVG 预览 + 下载按钮；失败显示 returncode + stderr。

### 4.3 页面 1「SVG 转 PNG / SVG to PNG」(render)

- 上传 SVG → 预览 → `--scale`（数字输入，默认 1）→ 下载 PNG。
- 支持 Vecto render 的 M/L/H/V/C/Z 路径。

### 4.4 页面 2「关于 / About」

- Vecto 引擎介绍、各参数含义说明、MIT 许可、免责声明。

### 4.5 外壳保留（已确认）

- 保留 `i18n.py` + `locales/` 中英文切换机制。
- 保留 logo、顶部布局、侧边栏 `st.navigation` 多页结构。
- 前端（`streamlit_app.py`）顶部"开源"入口此前已按用户要求删除，保持删除状态。

## 5. 数据流 / 错误处理

1. 上传文件写入临时目录（有扩展名，供 Vecto 识别类型）。
2. 调 `run_vecto`：`subprocess.run` 带 `timeout`（如 120s），`cwd` 指向临时目录。
3. 成功：读取 SVG/PNG → 展示/下载。
4. 失败：展示 `returncode`、`stderr`、提示信息（如"请确认 tools/vecto 存在且可执行"）。
5. 结束：清理临时目录。

## 6. 测试

- 手动验证：用 Vecto `vecto samples` 生成的测试图（crisp/blended/transparent）走通 trace 与 render 流程。
- 校验 SVG 可正常预览、PNG 可正常显示。
- 校验各参数控件能映射到正确 CLI 参数并成功执行。
- 校验错误路径：无二进制时给出友好提示。

## 7. 交付物清单

- [ ] `tools/vecto` 二进制落地（chmod +x），提交入库
- [ ] `utils.py` 精简与新增函数完成
- [ ] `pages_content/0_Image_to_Vector.py`、`1_SVG_to_PNG.py`、`2_About.py`
- [ ] `streamlit_app.py` 导航更新
- [ ] `locales/zh.json`、`en.json` 新文案
- [ ] `requirements.txt` 精简
- [ ] `README.md` 重写
- [ ] 删除旧文件：`0_PDF_Download.py`、`1_Data_Analysis.py`、Node.js 相关代码
- [ ] 本机运行验证 + i18n 双语言验证

## 8. 明确不做（YAGNI / 范围外）

- 不引入异步任务队列 / Celery / Redis（Vecto 足够快）。
- 不重写 Vecto C# 引擎为 Python（2200 行核心，无意义）。
- 不接入 Streamlit Community Cloud 部署配置（用户未要求；二进制入库已为云端就绪铺路）。
- 不做多用户并发调度（个人工具场景）。

## 9. 参考

- Vecto 仓库：https://github.com/danielmevit/vecto （MIT）
- CLI 帮助：`vecto --help`（trace / render / samples / bench）
- 二进制 SHA-256（v0.4.2 linux-x64）：`f7e0df8b9136b3d65e1f7ad9fe1eca2d685564bf547616039e7ced08a02acefd`