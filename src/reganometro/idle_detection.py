"""Detección de inactividad del sistema con dependencias de biblioteca estándar.

El módulo intenta usar APIs nativas por plataforma y devuelve el tiempo desde la
última interacción de teclado o mouse en segundos.
"""

from __future__ import annotations

import ctypes
import platform
import shutil
import struct
import subprocess
import time
from dataclasses import dataclass
from typing import Protocol


class IdleDetector(Protocol):
    """Contrato para detectores de inactividad."""

    name: str

    def seconds_idle(self) -> float:
        """Devuelve segundos desde la última entrada del usuario."""


@dataclass(frozen=True)
class UnsupportedIdleDetector:
    """Detector explícito para plataformas sin método disponible."""

    reason: str
    name: str = "unsupported"

    def seconds_idle(self) -> float:
        raise RuntimeError(self.reason)


class WindowsIdleDetector:
    """Detecta inactividad con GetLastInputInfo."""

    name = "windows"

    class _LastInputInfo(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

    def seconds_idle(self) -> float:
        info = self._LastInputInfo()
        info.cbSize = ctypes.sizeof(info)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            raise OSError("GetLastInputInfo falló")
        tick_count = ctypes.windll.kernel32.GetTickCount()
        return max(0.0, (tick_count - info.dwTime) / 1000.0)


class MacOSIdleDetector:
    """Detecta inactividad consultando IOHIDSystem con ioreg."""

    name = "macos-ioreg"

    def seconds_idle(self) -> float:
        completed = subprocess.run(
            ["ioreg", "-c", "IOHIDSystem"],
            check=True,
            capture_output=True,
            text=True,
            timeout=3,
        )
        for line in completed.stdout.splitlines():
            if "HIDIdleTime" in line:
                _, value = line.split("=", 1)
                return max(0.0, int(value.strip()) / 1_000_000_000.0)
        raise RuntimeError("No se encontró HIDIdleTime en ioreg")


class XPrintIdleDetector:
    """Detecta inactividad en X11 usando el comando xprintidle."""

    name = "linux-xprintidle"

    def seconds_idle(self) -> float:
        completed = subprocess.run(
            ["xprintidle"],
            check=True,
            capture_output=True,
            text=True,
            timeout=3,
        )
        return max(0.0, int(completed.stdout.strip()) / 1000.0)


class XScreenSaverIdleDetector:
    """Detecta inactividad en X11 llamando libXss directamente."""

    name = "linux-xss"

    class _XScreenSaverInfo(ctypes.Structure):
        _fields_ = [
            ("window", ctypes.c_ulong),
            ("state", ctypes.c_int),
            ("kind", ctypes.c_int),
            ("since", ctypes.c_ulong),
            ("idle", ctypes.c_ulong),
            ("event_mask", ctypes.c_ulong),
        ]

    def __init__(self) -> None:
        self._x11 = ctypes.cdll.LoadLibrary("libX11.so.6")
        self._xss = ctypes.cdll.LoadLibrary("libXss.so.1")
        self._x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        self._x11.XOpenDisplay.restype = ctypes.c_void_p
        self._x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        self._x11.XDefaultRootWindow.restype = ctypes.c_ulong
        self._x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
        self._xss.XScreenSaverAllocInfo.restype = ctypes.POINTER(self._XScreenSaverInfo)
        self._xss.XScreenSaverQueryInfo.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.POINTER(self._XScreenSaverInfo),
        ]
        self._xss.XScreenSaverQueryInfo.restype = ctypes.c_int
        self._libc = ctypes.CDLL("libc.so.6")
        self._libc.free.argtypes = [ctypes.c_void_p]

    def seconds_idle(self) -> float:
        display = self._x11.XOpenDisplay(None)
        if not display:
            raise RuntimeError("No se pudo abrir DISPLAY de X11")
        info = self._xss.XScreenSaverAllocInfo()
        if not info:
            self._x11.XCloseDisplay(display)
            raise RuntimeError("No se pudo reservar XScreenSaverInfo")
        try:
            root = self._x11.XDefaultRootWindow(display)
            if not self._xss.XScreenSaverQueryInfo(display, root, info):
                raise RuntimeError("XScreenSaverQueryInfo falló")
            return max(0.0, info.contents.idle / 1000.0)
        finally:
            self._libc.free(info)
            self._x11.XCloseDisplay(display)


class MonotonicFallbackDetector:
    """Fallback útil para pruebas: cuenta desde que inició el proceso."""

    name = "monotonic-fallback"

    def __init__(self) -> None:
        self._started_at = time.monotonic()

    def seconds_idle(self) -> float:
        return max(0.0, time.monotonic() - self._started_at)


def build_idle_detector(allow_process_timer_fallback: bool = False) -> IdleDetector:
    """Selecciona el mejor detector disponible para el sistema actual."""

    system = platform.system().lower()
    if system == "windows":
        return WindowsIdleDetector()
    if system == "darwin":
        if shutil.which("ioreg"):
            return MacOSIdleDetector()
        return UnsupportedIdleDetector("macOS requiere el comando ioreg")
    if system == "linux":
        if shutil.which("xprintidle"):
            return XPrintIdleDetector()
        if struct.calcsize("P") * 8 == 64:
            try:
                return XScreenSaverIdleDetector()
            except OSError:
                pass
        if allow_process_timer_fallback:
            return MonotonicFallbackDetector()
        return UnsupportedIdleDetector(
            "Linux requiere X11 con libXss o el comando xprintidle; "
            "en Wayland instala xprintidle-compatible o ejecuta con --demo."
        )
    if allow_process_timer_fallback:
        return MonotonicFallbackDetector()
    return UnsupportedIdleDetector(f"Sistema no soportado: {platform.system()}")
