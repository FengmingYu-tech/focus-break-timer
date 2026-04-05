# 20-5 工作休息提醒器

一个轻量级的专注计时工具，支持：

- 工作 `N` 分钟（默认 `20`）
- 休息 `M` 分钟（默认 `5`）
- 自动循环
- 阶段切换播放 10 秒提示音乐（休息悠扬、开工振奋）

## 跨平台支持

- macOS：可用
- Windows：可用

## 快速开始

### 1) 安装 Python 3

- macOS：建议使用 Python.org 安装包或 Homebrew
- Windows：建议从 Python.org 安装，并勾选 `Add python.exe to PATH`

### 2) 运行程序

```bash
python3 focus_break_timer.py
```

Windows 可以用：

```bat
python focus_break_timer.py
```

也可以双击仓库里的启动脚本：

- macOS：`start_timer_macos.command`
- Windows：`start_timer_windows.bat`

## 界面功能

- `开始`：启动计时
- `暂停`：暂停计时
- `重置`：回到工作阶段（当前设置值）
- `应用时长`：应用你输入的工作/休息分钟数（会自动重置到工作阶段）
- `隐藏到菜单栏/托盘`：窗口隐藏到后台托盘（需安装可选依赖）
- `创建桌面一键启动图标`：自动在桌面生成启动器（macOS 为 `.app`，Windows 为 `.bat`）

## 一键双击启动（无需 Terminal）

在程序中点击 `创建桌面一键启动图标` 后：

- macOS：生成 `专注休息提醒器.app`，双击即可启动
- Windows：生成 `专注休息提醒器.bat`，双击即可启动

## 可选依赖（托盘后台运行）

如果你想使用“隐藏到菜单栏/托盘”，安装：

```bash
python3 -m pip install -r requirements.txt
```

Windows：

```bat
python -m pip install -r requirements.txt
```

## 日志与排障

- macOS 启动器日志：`~/Library/Logs/focus-break-launcher.log`
- 若双击无反应，先直接命令行运行一次，看是否缺少 Python 或权限问题
