"""Sonidos enojados para acompañar las alertas del Reganómetro."""

from __future__ import annotations

import importlib
import importlib.util
import platform
import shutil
import subprocess
import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class SoundConfig:
    """Configuración de la ráfaga de sonidos de cada regaño."""

    enabled: bool = True
    repeat_count: int = 3
    gap_seconds: float = 0.18

    def __post_init__(self) -> None:
        if self.repeat_count < 1:
            raise ValueError("--sound-count debe ser mayor o igual a 1")
        if self.repeat_count > 10:
            raise ValueError("--sound-count debe estar entre 1 y 10")
        if self.gap_seconds < 0:
            raise ValueError("El intervalo entre sonidos no puede ser negativo")


class AngrySoundPlayer:
    """Reproduce una ráfaga sonora sin bloquear el bucle de ventanas."""

    def __init__(self, config: SoundConfig | None = None) -> None:
        self.config = config or SoundConfig()
        self._stop_event = threading.Event()

    def play_async(self) -> None:
        if not self.config.enabled:
            return
        self.cancel()
        self._stop_event = threading.Event()
        thread = threading.Thread(
            target=self._play_sequence,
            args=(self._stop_event,),
            daemon=True,
        )
        thread.start()

    def cancel(self) -> None:
        self._stop_event.set()

    def _play_sequence(self, stop_event: threading.Event) -> None:
        for index in range(self.config.repeat_count):
            if stop_event.is_set():
                return
            self._play_once()
            if index + 1 < self.config.repeat_count and stop_event.wait(
                self.config.gap_seconds
            ):
                return

    def _play_once(self) -> None:
        system = platform.system().lower()
        if system == "windows" and _play_windows_beep():
            return
        if system == "darwin" and _play_macos_alert():
            return
        if system == "linux" and _play_linux_alert():
            return
        print("\a", end="", flush=True)


def _play_windows_beep() -> bool:
    if importlib.util.find_spec("winsound") is None:
        return False
    winsound = importlib.import_module("winsound")
    try:
        winsound.MessageBeep(winsound.MB_ICONHAND)
        winsound.Beep(880, 140)
    except RuntimeError:
        return False
    return True


def _play_macos_alert() -> bool:
    afplay = shutil.which("afplay")
    if not afplay:
        return False
    return _run_quietly([afplay, "/System/Library/Sounds/Basso.aiff"])


def _play_linux_alert() -> bool:
    canberra = shutil.which("canberra-gtk-play")
    if canberra and _run_quietly([canberra, "-i", "dialog-warning"]):
        return True

    paplay = shutil.which("paplay")
    if paplay:
        for path in (
            "/usr/share/sounds/freedesktop/stereo/dialog-warning.oga",
            "/usr/share/sounds/freedesktop/stereo/bell.oga",
        ):
            if _run_quietly([paplay, path]):
                return True

    aplay = shutil.which("aplay")
    if aplay:
        for path in (
            "/usr/share/sounds/alsa/Front_Center.wav",
            "/usr/share/sounds/speech-dispatcher/test.wav",
        ):
            if _run_quietly([aplay, path]):
                return True
    return False


def _run_quietly(command: list[str]) -> bool:
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0
