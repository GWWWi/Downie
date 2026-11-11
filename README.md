# DownieWin — Windows 版视频下载器（Downie 4 风格）

一个运行在 Windows 上的视频下载工具，灵感来自 macOS 上的 **Downie 4**。
底层使用 **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** 负责解析与下载、
**[ffmpeg](https://ffmpeg.org/)** 负责音视频合并与转码，前端用 **PySide6**（Qt）
打造原生质感的图形界面。

> 说明：本项目为 Downie 的第三方开源复刻 / 学习用途实现，与原版作者无关。
> 请仅下载你拥有合法权利的内容，遵守当地法律法规与视频网站的服务条款。

---

## ✨ 功能特性

- 📋 **一键粘贴**：打开「添加」会自动读取剪贴板里的链接
- 🎚 **画质自选**：自动列出站点的所有可用格式（分辨率 / 编码 / 大小），也可选「最佳画质自动合并」「仅音频 MP3」等预设
- 📊 **实时进度**：百分比、速度、ETA、缩略图一目了然
- ⏸ **暂停 / 继续 / 取消 / 重试**（基于 .part 断点续传）
- 🔀 **并发下载**：可配置最大同时下载数（默认 3）
- 🌐 **浏览器扩展「发送到 Downie」**：在网页/视频上右键或点扩展图标，链接直接进下载队列（本地 HTTP 监听，不上传任何数据）
- 🔉 **音频提取**：一键下载并转为 MP3
- 📁 **自定义下载目录** + 系统托盘常驻
- 🔧 **环境诊断**：「帮助 ▸ 环境诊断」一键检查 yt-dlp / ffmpeg / 网络，并可跑一次极速下载测试验证「下载 + 合并」整条链路；启动时会自动检测并提醒缺失的依赖
- 🔞 **年龄验证 / 登录**：在「设置」里选择「从浏览器导入 cookies」或「使用 cookies.txt 文件」，即可下载年龄受限视频；下载受限内容失败时列表会提示去开启登录
- 🪟 **打包成独立 exe**：用 PyInstaller 一条命令生成 `DownieWin.exe`

支持 yt-dlp 支持的**上千个网站**（YouTube、B 站、Vimeo、Twitter/X、TikTok 等）。

---

## 🚀 快速开始（开发 / 直接运行）

需要 Windows + Python 3.10+。

```bash
# 1. 克隆 / 进入项目目录
cd Downie

# 2. 创建虚拟环境（推荐）并安装依赖
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 3. 准备 ffmpeg（合并音视频必需）
python get_ffmpeg.py        # 自动下载静态版 ffmpeg 到 bin/ 并写入配置

# 4. 启动
python main.py
# 或者：python -m downie4win
```

> 若 `get_ffmpeg.py` 因网络失败，可手动从
> https://www.gyan.dev/ffmpeg/builds/ 下载 `ffmpeg-release-essentials.zip`，
> 解压后把 `bin/ffmpeg.exe` 放到项目 `bin/` 目录，并在「设置」里指定该目录。

---

## 📦 打包成独立 exe（分发给别人）

最简单的方式——**双击 `build.bat`**（Windows），或手动运行：

```bash
python build.py
```

`build.py` 会自动完成：创建虚拟环境 `.venv` → 安装依赖 + PyInstaller →
下载 ffmpeg 到 `bin/`（除非设置 `SKIP_FFMPEG=1` 跳过）→ 调用 `build.spec`
打包。你再也不用记住那条长长的 pyinstaller 命令。

> 想跳过 ffmpeg 自动下载（比如你已手动放进 `bin/`）、加快构建：
> ```bash
> SKIP_FFMPEG=1 python build.py
> ```

产物在 `dist/DownieWin/DownieWin.exe`。若已运行过 `get_ffmpeg.py` 或
`build.py` 自动下载过，`build.spec` 会把 `bin/ffmpeg.exe` 一并打包进 exe，
双击即可使用，**无需安装 Python、也无需单独准备 ffmpeg**。

---

## 🧩 安装浏览器扩展（「发送到 Downie」）

1. 打开 Chrome / Edge 的扩展管理页（`chrome://extensions` 或 `edge://extensions`）
2. 开启「开发者模式」
3. 点击「加载已解压的扩展程序」，选择本项目的
   `downie4win/browser_extension/` 目录
4. 确保 DownieWin 已启动（默认监听 `127.0.0.1:7654`，可在设置里改端口）
5. 在任意视频页点击扩展图标，或右键页面 / 链接选「发送到 DownieWin」

链接通过本地回环地址直接发给本机程序，**不会上传到任何服务器**。

---

## ⚙️ 设置项

| 选项 | 说明 |
| --- | --- |
| 下载目录 | 文件保存位置（默认系统「下载」文件夹） |
| ffmpeg 目录 | 留空则使用系统 PATH 中的 ffmpeg |
| 最大同时下载数 | 1–8，默认 3 |
| 默认画质 | 新建下载时的默认格式 |
| 浏览器扩展 | 是否启用本地监听服务及端口 |

---

## 🗂 项目结构

```
Downie/
├── main.py                      # 入口（python main.py）
├── requirements.txt
├── build.spec                   # PyInstaller 打包配置
├── build.py                     # 一键打包脚本（python build.py / build.bat）
├── build.bat                    # Windows 双击打包
├── get_ffmpeg.py                # 自动下载 ffmpeg
├── bin/                         # ffmpeg 存放目录
├── downie4win/
│   ├── __init__.py
│   ├── __main__.py
│   ├── app.py                   # QApplication 启动
│   ├── config.py                # 设置（JSON）
│   ├── models.py                # 下载请求、任务与状态模型
│   ├── downloader.py            # yt-dlp 封装 + 后台 worker
│   ├── download_manager.py      # 下载队列、并发调度与状态机（无 UI 依赖）
│   ├── diagnostics.py           # 环境检查与下载自测
│   ├── browser_server.py        # 本地 HTTP「发送」服务
│   ├── ui/
│   │   ├── main_window.py       # 主窗口与任务状态展示
│   │   ├── add_dialog.py        # 添加链接 / 选画质
│   │   ├── settings_dialog.py   # 设置
│   │   ├── diagnostics_dialog.py# 环境诊断窗口
│   │   └── download_item.py     # 列表行控件
│   └── browser_extension/       # 浏览器扩展源码
└── README.md
```

---

## 📝 已知限制 / 后续可改进

- **暂停** 在当前实现中等同于「取消并保留 .part」，再次「继续」会断点续传（HTTP 源有效）。
  如需真正的流式暂停需自行接管 HTTP Range 请求。
- 默认 `noplaylist=True`，即链接是播放列表时只下载单个视频；如需整列下载可在
  `downloader.build_ydl_opts` 中放开。
- 可继续扩展：定时下载、下载完成通知音、格式预设保存到配置文件、订阅/频道监控等。

---

## 📜 许可

代码以 MIT 许可证开源（见 `LICENSE`）。yt-dlp 与 ffmpeg 各自遵循其许可证。
