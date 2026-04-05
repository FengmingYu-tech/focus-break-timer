#!/usr/bin/env python3
"""
20-5 工作休息循环计时器（Mac 友好版）

功能：
1) 20 分钟工作 -> 5 分钟休息自动循环
2) 休息开始时播放 10 秒悠扬音乐
3) 工作开始时播放 10 秒振奋音乐
4) 提供开始/暂停/重置按钮和剩余时间显示
"""

from __future__ import annotations

import math
import plistlib
import shutil
import subprocess
import sys
import threading
import tkinter as tk
import wave
from pathlib import Path
from tkinter import messagebox, ttk


DEFAULT_WORK_MINUTES = 20
DEFAULT_BREAK_MINUTES = 5
SAMPLE_RATE = 44_100
SAMPLE_WIDTH = 2
CHANNELS = 1
MAX_AMP = 32767


def _safe_filename(text: str) -> str:
    return "".join(ch for ch in text if ch.isalnum() or ch in ("_", "-")).strip("_-") or "sound"


def _make_tone_samples(frequency: float, duration: float, volume: float = 0.45) -> list[int]:
    frame_count = int(SAMPLE_RATE * duration)
    attack = int(frame_count * 0.04)
    release = int(frame_count * 0.12)
    sustain_start = attack
    sustain_end = max(attack, frame_count - release)
    samples: list[int] = []

    for i in range(frame_count):
        t = i / SAMPLE_RATE
        raw = math.sin(2 * math.pi * frequency * t)

        if i < sustain_start and sustain_start > 0:
            env = i / sustain_start
        elif i > sustain_end and release > 0:
            env = max(0.0, (frame_count - i) / release)
        else:
            env = 1.0

        value = int(MAX_AMP * volume * env * raw)
        samples.append(value)

    return samples


def _mix_notes(note_list: list[tuple[float, float]], total_seconds: float) -> list[int]:
    total_frames = int(total_seconds * SAMPLE_RATE)
    mix = [0.0] * total_frames
    cursor = 0

    for freq, sec in note_list:
        note_samples = _make_tone_samples(freq, sec)
        end = min(total_frames, cursor + len(note_samples))
        for i, sample in enumerate(note_samples[: end - cursor]):
            mix[cursor + i] += sample
        cursor = end
        if cursor >= total_frames:
            break

    if cursor < total_frames:
        tail = _make_tone_samples(261.63, (total_frames - cursor) / SAMPLE_RATE, volume=0.2)
        for i, sample in enumerate(tail):
            mix[cursor + i] += sample

    clipped = [max(-MAX_AMP, min(MAX_AMP, int(v))) for v in mix]
    return clipped


def _write_wav(path: Path, samples: list[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(int(s).to_bytes(2, byteorder="little", signed=True) for s in samples))


def generate_sound_files(base_dir: Path) -> tuple[Path, Path]:
    """
    生成两段 10 秒提示音：
    - break_start.wav: 悠扬（较慢、和谐音程）
    - work_start.wav : 振奋（节奏更密集、上行旋律）
    """
    break_path = base_dir / f"{_safe_filename('break_start')}.wav"
    work_path = base_dir / f"{_safe_filename('work_start')}.wav"

    if not break_path.exists():
        gentle_notes = [
            (523.25, 1.2),  # C5
            (659.25, 1.2),  # E5
            (783.99, 1.2),  # G5
            (659.25, 1.2),  # E5
            (587.33, 1.2),  # D5
            (783.99, 1.2),  # G5
            (880.00, 1.2),  # A5
            (783.99, 1.6),  # G5
        ]
        _write_wav(break_path, _mix_notes(gentle_notes, total_seconds=10.0))

    if not work_path.exists():
        energetic_notes = [
            (392.00, 0.5),  # G4
            (440.00, 0.5),  # A4
            (493.88, 0.5),  # B4
            (523.25, 0.5),  # C5
            (587.33, 0.5),  # D5
            (659.25, 0.5),  # E5
            (698.46, 0.5),  # F5
            (783.99, 0.5),  # G5
            (659.25, 0.5),
            (783.99, 0.5),
            (880.00, 0.5),
            (987.77, 0.5),
            (880.00, 0.5),
            (783.99, 0.5),
            (659.25, 0.5),
            (523.25, 2.5),
        ]
        _write_wav(work_path, _mix_notes(energetic_notes, total_seconds=10.0))

    return break_path, work_path


def play_sound(path: Path) -> None:
    if sys.platform == "darwin":
        subprocess.Popen(["afplay", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif sys.platform.startswith("win"):
        try:
            import winsound  # type: ignore

            winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            pass
    else:
        # Linux 兼容：尝试 aplay；失败则忽略
        try:
            subprocess.Popen(["aplay", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


def notify(title: str, message: str) -> None:
    if sys.platform == "darwin":
        script = f'display notification "{message}" with title "{title}"'
        subprocess.Popen(["osascript", "-e", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif sys.platform.startswith("win"):
        # Windows 下用系统消息框做兜底提醒（无需额外依赖）。
        try:
            import ctypes

            def _show_message() -> None:
                ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)

            threading.Thread(target=_show_message, daemon=True).start()
        except Exception:
            pass


class FocusBreakApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("20-5 工作休息提醒器")
        self.root.geometry("480x340")
        self.root.resizable(False, False)

        audio_dir = Path(__file__).parent / "audio_assets"
        self.break_sound, self.work_sound = generate_sound_files(audio_dir)

        self.work_minutes_var = tk.StringVar(value=str(DEFAULT_WORK_MINUTES))
        self.break_minutes_var = tk.StringVar(value=str(DEFAULT_BREAK_MINUTES))
        self.work_seconds = DEFAULT_WORK_MINUTES * 60
        self.break_seconds = DEFAULT_BREAK_MINUTES * 60

        self.is_running = False
        self.is_work_phase = True
        self.remaining = self.work_seconds
        self._after_id: str | None = None
        self.tray_icon = None
        self._tray_thread: threading.Thread | None = None
        self._tray_supported = False
        self._tray_modules: dict[str, object] = {}
        self._is_quitting = False

        self._init_tray_support()

        self.phase_label = ttk.Label(root, text="当前阶段：工作中", font=("Arial", 18, "bold"))
        self.phase_label.pack(pady=(18, 10))

        self.time_label = ttk.Label(root, text=self._format_time(self.remaining), font=("Arial", 40))
        self.time_label.pack(pady=8)

        self.hint_label = ttk.Label(
            root,
            text="",
            font=("Arial", 11),
        )
        self.hint_label.pack(pady=(2, 14))

        settings = ttk.LabelFrame(root, text="时长设置（分钟）")
        settings.pack(padx=18, pady=(2, 12), fill="x")

        ttk.Label(settings, text="工作").grid(row=0, column=0, padx=(10, 6), pady=8)
        self.work_entry = ttk.Entry(settings, textvariable=self.work_minutes_var, width=8)
        self.work_entry.grid(row=0, column=1, padx=(0, 10), pady=8)

        ttk.Label(settings, text="休息").grid(row=0, column=2, padx=(0, 6), pady=8)
        self.break_entry = ttk.Entry(settings, textvariable=self.break_minutes_var, width=8)
        self.break_entry.grid(row=0, column=3, padx=(0, 10), pady=8)

        self.apply_btn = ttk.Button(settings, text="应用时长", command=self.apply_durations)
        self.apply_btn.grid(row=0, column=4, padx=(0, 12), pady=8)

        controls = ttk.Frame(root)
        controls.pack()

        self.start_btn = ttk.Button(controls, text="开始", command=self.start)
        self.start_btn.grid(row=0, column=0, padx=8)

        self.pause_btn = ttk.Button(controls, text="暂停", command=self.pause)
        self.pause_btn.grid(row=0, column=1, padx=8)

        self.reset_btn = ttk.Button(controls, text="重置", command=self.reset)
        self.reset_btn.grid(row=0, column=2, padx=8)

        tray_controls = ttk.Frame(root)
        tray_controls.pack(pady=(14, 0))
        self.tray_btn = ttk.Button(tray_controls, text="隐藏到菜单栏", command=self.hide_to_tray)
        self.tray_btn.grid(row=0, column=0, padx=8)

        startup_controls = ttk.Frame(root)
        startup_controls.pack(pady=(10, 0))
        self.create_launcher_btn = ttk.Button(
            startup_controls, text="创建桌面一键启动图标", command=self.create_desktop_launcher
        )
        self.create_launcher_btn.grid(row=0, column=0, padx=8)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._update_hint_label()

    @staticmethod
    def _format_time(seconds: int) -> str:
        m, s = divmod(seconds, 60)
        return f"{m:02d}:{s:02d}"

    def _update_hint_label(self) -> None:
        self.hint_label.config(
            text=f"工作 {self.work_seconds // 60} 分钟，休息 {self.break_seconds // 60} 分钟，自动循环"
        )

    def _update_ui(self) -> None:
        phase_text = "当前阶段：工作中" if self.is_work_phase else "当前阶段：休息中"
        self.phase_label.config(text=phase_text)
        self.time_label.config(text=self._format_time(self.remaining))

    def _tick(self) -> None:
        if not self.is_running:
            return

        self.remaining -= 1
        self._update_ui()

        if self.remaining <= 0:
            self._switch_phase()

        self._after_id = self.root.after(1000, self._tick)

    def _switch_phase(self) -> None:
        self.is_work_phase = not self.is_work_phase

        if self.is_work_phase:
            self.remaining = self.work_seconds
            notify("开工提醒", f"休息结束，开始进入 {self.work_seconds // 60} 分钟专注时间")
            play_sound(self.work_sound)
        else:
            self.remaining = self.break_seconds
            notify("休息提醒", f"{self.work_seconds // 60} 分钟已到，开始休息 {self.break_seconds // 60} 分钟")
            play_sound(self.break_sound)

        self._update_ui()

    def start(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        self._after_id = self.root.after(1000, self._tick)

    def pause(self) -> None:
        self.is_running = False
        if self._after_id:
            self.root.after_cancel(self._after_id)
            self._after_id = None

    def reset(self) -> None:
        self.pause()
        self.is_work_phase = True
        self.remaining = self.work_seconds
        self._update_ui()

    def apply_durations(self) -> None:
        try:
            work_mins = int(self.work_minutes_var.get().strip())
            break_mins = int(self.break_minutes_var.get().strip())
        except ValueError:
            messagebox.showerror("输入错误", "请填写整数分钟，比如工作 20、休息 5。")
            return

        if not (1 <= work_mins <= 180 and 1 <= break_mins <= 90):
            messagebox.showerror("输入范围错误", "工作时间请设为 1-180 分钟，休息时间请设为 1-90 分钟。")
            return

        self.work_seconds = work_mins * 60
        self.break_seconds = break_mins * 60
        self.reset()
        self._update_hint_label()
        messagebox.showinfo("设置完成", f"已应用：工作 {work_mins} 分钟 / 休息 {break_mins} 分钟。")

    def _init_tray_support(self) -> None:
        try:
            import pystray  # type: ignore
            from PIL import Image, ImageDraw  # type: ignore

            self._tray_modules = {"pystray": pystray, "Image": Image, "ImageDraw": ImageDraw}
            self._tray_supported = True
        except Exception:
            self._tray_supported = False

    def _build_tray_image(self):
        image_mod = self._tray_modules["Image"]
        draw_mod = self._tray_modules["ImageDraw"]
        image = image_mod.new("RGB", (64, 64), color=(30, 30, 30))
        draw = draw_mod.Draw(image)
        draw.ellipse((8, 8, 56, 56), fill=(44, 136, 255))
        draw.ellipse((20, 20, 44, 44), fill=(245, 245, 245))
        draw.rectangle((30, 22, 34, 40), fill=(44, 136, 255))
        return image

    def _toggle_from_tray(self) -> None:
        self.root.after(0, self.pause if self.is_running else self.start)

    def _show_from_tray(self) -> None:
        def _show() -> None:
            self.root.deiconify()
            self.root.lift()
            self.root.after(200, lambda: self.root.attributes("-topmost", False))
            self._stop_tray_icon()

        self.root.after(0, _show)

    def _quit_from_tray(self) -> None:
        def _quit() -> None:
            self._is_quitting = True
            self._stop_tray_icon()
            self.pause()
            self.root.destroy()

        self.root.after(0, _quit)

    def _run_tray_icon(self) -> None:
        pystray = self._tray_modules["pystray"]
        menu = pystray.Menu(
            pystray.MenuItem("显示窗口", lambda icon, item: self._show_from_tray()),
            pystray.MenuItem(
                lambda item: "暂停计时" if self.is_running else "开始计时",
                lambda icon, item: self._toggle_from_tray(),
            ),
            pystray.MenuItem("退出", lambda icon, item: self._quit_from_tray()),
        )
        self.tray_icon = pystray.Icon("focus-break-timer", self._build_tray_image(), "专注休息提醒", menu)
        self.tray_icon.run()

    def _stop_tray_icon(self) -> None:
        if self.tray_icon is not None:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
            self.tray_icon = None
        self._tray_thread = None

    def hide_to_tray(self) -> None:
        if not self._tray_supported:
            messagebox.showinfo(
                "菜单栏功能需安装依赖",
                "请先安装：\npython3 -m pip install pystray Pillow\n\n安装后重启本程序即可使用菜单栏后台运行。",
            )
            return

        if self._tray_thread and self._tray_thread.is_alive():
            self.root.withdraw()
            return

        self.root.withdraw()
        self._tray_thread = threading.Thread(target=self._run_tray_icon, daemon=True)
        self._tray_thread.start()

    @staticmethod
    def _pick_gui_python() -> Path:
        # 选择可用且支持 tkinter 的解释器，避免拿到不带 Tk 的 pyenv 解释器。
        raw_candidates = [
            sys.executable,
            "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3",
            "/Library/Frameworks/Python.framework/Versions/3.10/bin/python3",
            "/usr/local/bin/python3",
            "/usr/bin/python3",
            str(Path.home() / "opt" / "anaconda3" / "bin" / "python3"),
        ]
        candidates: list[Path] = []
        for item in raw_candidates:
            if not item:
                continue
            path = Path(item).expanduser().resolve()
            if path.exists() and path.is_file():
                candidates.append(path)

        for path in candidates:
            probe = subprocess.run(
                [str(path), "-c", "import tkinter"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if probe.returncode == 0:
                return path

        raise RuntimeError("没有找到可用的 GUI Python（tkinter）解释器。")

    def create_desktop_launcher(self) -> None:
        try:
            if sys.platform == "darwin":
                output = self._create_macos_launcher()
                messagebox.showinfo("创建成功", f"桌面已生成：{output.name}\n以后双击即可启动。")
            elif sys.platform.startswith("win"):
                output = self._create_windows_launcher()
                messagebox.showinfo("创建成功", f"桌面已生成：{output.name}\n以后双击即可启动。")
            else:
                messagebox.showinfo(
                    "当前系统不支持",
                    "当前系统暂未内置桌面启动器生成功能。\n请使用命令行运行：python3 focus_break_timer.py",
                )
        except Exception as exc:
            messagebox.showerror("创建失败", f"桌面启动图标创建失败：{exc}")

    @staticmethod
    def _desktop_dir() -> Path:
        return Path.home() / "Desktop"

    def _create_macos_launcher(self) -> Path:
        desktop_app = self._desktop_dir() / "专注休息提醒器.app"
        python_exec = self._pick_gui_python()
        script_path = Path(__file__).resolve()
        log_file = Path.home() / "Library" / "Logs" / "focus-break-launcher.log"
        app_contents = desktop_app / "Contents"
        macos_dir = app_contents / "MacOS"
        launcher_file = macos_dir / "launch.sh"
        plist_file = app_contents / "Info.plist"

        if desktop_app.exists():
            shutil.rmtree(desktop_app)

        macos_dir.mkdir(parents=True, exist_ok=True)
        launcher_file.write_text(
            "\n".join(
                [
                    "#!/bin/zsh",
                    f'exec "{python_exec}" "{script_path}" >> "{log_file}" 2>&1',
                    "",
                ]
            ),
            encoding="utf-8",
        )
        launcher_file.chmod(0o755)

        info = {
            "CFBundleName": "专注休息提醒器",
            "CFBundleDisplayName": "专注休息提醒器",
            "CFBundleIdentifier": "com.focus.break.timer.launcher",
            "CFBundleVersion": "1.0",
            "CFBundleShortVersionString": "1.0",
            "CFBundlePackageType": "APPL",
            "CFBundleExecutable": "launch.sh",
            "LSMinimumSystemVersion": "10.13",
            "NSHighResolutionCapable": True,
        }
        with plist_file.open("wb") as f:
            plistlib.dump(info, f)

        subprocess.run(["xattr", "-dr", "com.apple.quarantine", str(desktop_app)], check=False)
        return desktop_app

    def _create_windows_launcher(self) -> Path:
        desktop_dir = self._desktop_dir()
        launcher_file = desktop_dir / "专注休息提醒器.bat"
        script_path = Path(__file__).resolve()
        python_exec = Path(sys.executable or "python").resolve()
        pythonw_exec = python_exec.with_name("pythonw.exe")
        if not pythonw_exec.exists():
            pythonw_exec = python_exec

        launcher_file.write_text(
            "\n".join(
                [
                    "@echo off",
                    "setlocal",
                    f'start "" "{pythonw_exec}" "{script_path}"',
                    "exit /b 0",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return launcher_file

    def on_close(self) -> None:
        if self._is_quitting:
            self.pause()
            self._stop_tray_icon()
            self.root.destroy()
            return

        if self._tray_supported:
            self.hide_to_tray()
        else:
            self.pause()
            self.root.destroy()


def main() -> None:
    root = tk.Tk()
    style = ttk.Style()
    if "clam" in style.theme_names():
        style.theme_use("clam")

    app = FocusBreakApp(root)
    app._update_ui()
    root.mainloop()


if __name__ == "__main__":
    main()
