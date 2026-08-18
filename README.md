<div align="center">
  <h1>🐵 悟空图片转SVG工具</h1>
  <p><em>基于 Vecto 引擎的图片矢量化工具:上传位图,自动转为干净可编辑的 SVG。</em></p>
</div>

<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/中文-blue?style=flat-square" alt="中文"></a>
  <a href="README_EN.md"><img src="https://img.shields.io/badge/English-gray?style=flat-square" alt="English"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/goku-open/goku-image-to-svg-tool?style=flat-square" alt="License"></a>
  <a href="https://github.com/goku-open/goku-image-to-svg-tool/stargazers"><img src="https://img.shields.io/github/stars/goku-open/goku-image-to-svg-tool?style=flat-square" alt="Stars"></a>
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
</p>

<p align="center">
  <img src="assets/banner.png" alt="悟空图片转SVG工具 banner">
</p>

把 Vecto 命令行引擎(开源 .NET 矢量化核心)包上一层 Streamlit Web 界面:不需要敲命令,选图即转、改参即重转,原图 / 矢量 / 分割视图三合一对比,导出 SVG 或按倍率渲染 PNG。

## 为什么选悟空图片转SVG工具?

- **上传即转换,改参即重转**:免命令行,选图自动 trace,拖动参数立刻看到新结果
- **原版 Vecto 参数零阉割**:调色板(自动/指定颜色数,含色块预览)、风格、细节、诊断信息与 Vecto CLI 完全对齐
- **拖拽滑块对比**:原图 / 矢量 / 分割视图一键切换,导出前先看清效果
- **免配置即用**:单文件二进制引擎随仓库分发(`tools/vecto`,v0.4.2 linux-x64),一条命令跑起来
- **中英双语界面**:语言一键切换,右上角公众号 / X 入口
- **云端可部署**:Streamlit Community Cloud 免费托管;实测单次转换峰值 60~490MB,个人使用无忧

## 对比

| 能力 | 悟空图片转SVG | Vectorizer.AI | Illustrator 图像描摹 | Inkscape 位图描摹 | vecto CLI(裸用) |
|------|:---:|:---:|:---:|:---:|:---:|
| 开源免费 | ✅ | ❌ | ❌ | ✅ | ✅ |
| 浏览器即用,免安装 | ✅ | ✅ | ❌ | ❌ | ❌ |
| 上传即自动转换 | ✅ | ✅ | ❌ | ❌ | ❌ |
| 调色板/风格/细节参数 | ✅ | ✅ | ✅ | ✅ | ✅(命令行) |
| 分割视图+滑块对比 | ✅ | 部分 | ❌ | ❌ | ❌ |
| 中英双语界面 | ✅ | 部分 | 部分 | ✅ | ❌ |

> 对比基于各产品公开能力,以实际体验为准;Illustrator / Inkscape 与在线服务的功能随版本变化。

## 安装 / 在线使用

**在线使用(推荐)**: [image-to-svg.streamlit.app](https://image-to-svg.streamlit.app)——免安装、打开即用。

需要本地运行:

```bash
git clone https://github.com/goku-open/goku-image-to-svg-tool.git
cd goku-image-to-svg-tool
pip install -r requirements.txt
streamlit run streamlit_app.py
```

打开 <http://localhost:8501> 即可使用。`tools/vecto` 二进制已随仓库提供(v0.4.2 linux-x64);如需要自行下载,见 [Vecto Releases](https://github.com/DanielMevit/Vecto/releases)。

## 使用

启动后浏览器显示:

```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

1. **上传图片**:支持 PNG / JPG / BMP / GIF / TGA / TIFF / WebP / PBM / PPM,上传即自动转换
2. **调参数**:右栏与 Vecto CLI 对齐——调色板(自动或指定颜色数,带色块预览)、风格、细节,改动即时重转
3. **看效果**:拖拽滑块对比原图 / 矢量 / 分割视图
4. **导出**:下载 SVG,或按缩放倍数渲染为 PNG

## 工作原理

```
Streamlit 前端 ──subprocess──▶ tools/vecto trace(位图 → SVG)──▶ 解析 stats
      ▲                                                              │
      └──────────── 滑块对比 + 导出 SVG / PNG(render) ◀──────────────┘
```

矢量化核心是 [Vecto](https://github.com/DanielMevit/Vecto)(.NET, MIT):ImageSharp 解码图片、多边形拟合生成矢量路径;本项目负责 Web 交互、参数透传、三视图对比与导出。

## 贡献与开发

- 测试: `python -m pytest`(项目所有功能必须配套测试)
- 改页面在 `pages_content/`,逻辑在 `utils.py`,文案在 `locales/`
- 欢迎提交 Issue / PR;改动请保持测试全绿

## 支持

我养了两只猫,汤圆和饺子。如果你觉得悟空图片转SVG工具给你的生活带来了快乐,你可以喂它们 [罐头食品 🥩](https://ko-fi.com/gokuscraper)。

## License

[MIT](LICENSE) © 2026 Goku-Scraper。Vecto 引擎 © Daniel Mevit。

---

*Keywords: 图片转矢量, 位图转SVG, 图片矢量化, svg 转换, 在线矢量化工具, vecto 引擎, streamlit 应用, 免费开源, 中英双语, image to vector, raster to svg, image tracing, bitmap to svg, svg converter, vector graphics, vecto engine, streamlit app, open source*
