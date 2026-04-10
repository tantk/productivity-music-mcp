"""Cross-platform audio player."""

import platform
import subprocess
import threading
from pathlib import Path

_current_process: subprocess.Popen | None = None
_lock = threading.Lock()


def _command_exists(cmd: str) -> bool:
    try:
        subprocess.run(
            ["which", cmd] if platform.system() != "Windows" else ["where", cmd],
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _get_play_command(file_path: str) -> list[str]:
    system = platform.system()
    if system == "Darwin":
        return ["afplay", file_path]
    elif system == "Linux":
        for cmd in ["ffplay", "paplay", "aplay"]:
            if _command_exists(cmd):
                if cmd == "ffplay":
                    return [
                        "ffplay",
                        "-nodisp",
                        "-autoexit",
                        "-loglevel",
                        "quiet",
                        file_path,
                    ]
                return [cmd, file_path]
        raise RuntimeError(
            "No audio player found. Install ffmpeg, pulseaudio, or alsa-utils."
        )
    elif system == "Windows":
        return [
            "powershell",
            "-c",
            f'(New-Object Media.SoundPlayer "{file_path}").PlaySync()',
        ]
    raise RuntimeError(f"Unsupported platform: {system}")


def play(file_path: str, background: bool = True) -> str:
    global _current_process
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        return f"Error: File not found: {path}"

    try:
        cmd = _get_play_command(str(path))
    except RuntimeError as e:
        return f"Error: {e}"

    with _lock:
        if background:
            stop()
            _current_process = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return f"Now playing: {path.name}"
        else:
            subprocess.run(cmd, check=True, capture_output=True)
            return f"Finished playing: {path.name}"


def play_loop(file_path: str) -> str:
    global _current_process
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        return f"Error: File not found: {path}"

    with _lock:
        stop()
        system = platform.system()
        if system == "Darwin":
            if _command_exists("ffplay"):
                cmd = [
                    "ffplay",
                    "-nodisp",
                    "-loop",
                    "0",
                    "-loglevel",
                    "quiet",
                    str(path),
                ]
            else:
                return "Error: Looping requires ffplay on macOS. Install ffmpeg."
        elif system == "Linux":
            if _command_exists("ffplay"):
                cmd = [
                    "ffplay",
                    "-nodisp",
                    "-loop",
                    "0",
                    "-loglevel",
                    "quiet",
                    str(path),
                ]
            else:
                return "Error: Looping requires ffplay. Install ffmpeg."
        else:
            return "Error: Looping not supported on this platform."

        _current_process = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return f"Looping: {path.name}"


def stop() -> str:
    global _current_process
    if _current_process is not None:
        try:
            _current_process.terminate()
            _current_process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            _current_process.kill()
        except Exception:
            pass
        finally:
            _current_process = None
        return "Audio stopped."
    return "No audio is currently playing."


def is_playing() -> bool:
    return _current_process is not None and _current_process.poll() is None
