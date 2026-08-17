# 悟空图片转SVG工具

基于开源引擎 **Vecto**（MIT）的图片矢量化工具，Streamlit Web 界面，将 PNG/JPG 等位图转换为干净可编辑的 SVG。

## 功能

- **图片转矢量**：上传即自动转换，拖拽滑块对比原图/矢量/分割视图，导出 SVG
- **导出 PNG**：按缩放倍数渲染为 PNG
- 参数面板对齐原版 Vecto UI：调色板（自动/指定颜色数，含色块预览）、风格、细节、诊断信息常显
- 中英文双语言切换

## 运行

依赖 Python 3.10+。首次先放好二进制 `tools/vecto`（见下）。

```bash
pip install -r requirements.txt
python -m pytest          # 跑测试（必须全绿）
streamlit run streamlit_app.py
```

## Vecto 二进制

从 [Vecto Releases](https://github.com/DanielMevit/Vecto/releases) 下载 `vecto-0.4.2-linux-x64`，保存为 `tools/vecto` 并 `chmod +x`。本仓库已带 v0.4.2 二进制。

## 许可

MIT。Vecto 引擎 © Daniel Mevit。