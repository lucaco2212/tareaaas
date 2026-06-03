"""Notificaciones visuales para el Reganómetro."""

from __future__ import annotations

import itertools
import random
import tkinter as tk
from dataclasses import dataclass, field
from typing import Iterable

from .audio import AngrySoundPlayer, SoundConfig

DEFAULT_SCOLDINGS = (
    "¿Y esas manos quietas? ¡A mover el mouse o escribir algo ya!",
    "¡Ey! El teclado no se va a presionar solo. ¿Qué estás esperando?",
    "Tu computadora está llorando de aburrimiento. ¡Haz algo productivo!",
    "¡Alerta de flojera! No detecto ni un triste movimiento del mouse.",
    "¿Modo estatua activado? Despierta y vuelve a la tarea.",
    "Te estoy viendo... y no estás haciendo nada. ¡Muévete!",
    "Ese cursor parece de museo. ¡Escribe, mueve, trabaja!",
)


@dataclass
class ScoldingRotator:
    """Entrega regaños variados sin repetir el mismo texto consecutivamente."""

    messages: Iterable[str] = DEFAULT_SCOLDINGS
    shuffle: bool = True
    _cycle: itertools.cycle[str] | None = field(init=False, default=None)
    _last: str | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        cleaned = [message.strip() for message in self.messages if message.strip()]
        if not cleaned:
            raise ValueError("Debes proporcionar al menos un regaño")
        if self.shuffle:
            random.shuffle(cleaned)
        self._cycle = itertools.cycle(cleaned)

    def next(self) -> str:
        assert self._cycle is not None
        message = next(self._cycle)
        if message == self._last:
            message = next(self._cycle)
        self._last = message
        return message


class TkAngryNotifier:
    """Muestra ventanas emergentes llamativas y deliberadamente insistentes."""

    def __init__(
        self,
        title: str = "REGANÓMETRO ENOJADO",
        sound_config: SoundConfig | None = None,
    ) -> None:
        self.root = tk.Tk()
        self.root.withdraw()
        self.title = title
        self.sound_config = sound_config or SoundConfig()
        self.sound_player = AngrySoundPlayer(self.sound_config)
        self._open_windows: list[tk.Toplevel] = []
        self._bell_after_ids: list[str] = []

    def show(self, message: str, burst_count: int = 1) -> None:
        self.sound_player.play_async()
        self._schedule_gui_bells()
        for index in range(max(1, burst_count)):
            self._spawn_window(message, index)
        self.root.update_idletasks()
        self.root.update()

    def tick(self) -> None:
        self.root.update_idletasks()
        self.root.update()

    def close_all(self) -> None:
        self.sound_player.cancel()
        self._cancel_gui_bells()
        for window in list(self._open_windows):
            if window.winfo_exists():
                window.destroy()
        self._open_windows.clear()

    def _schedule_gui_bells(self) -> None:
        if not self.sound_config.enabled:
            return
        self._cancel_gui_bells()
        for index in range(self.sound_config.repeat_count):
            delay_ms = int(index * self.sound_config.gap_seconds * 1000)
            after_id = self.root.after(delay_ms, self.root.bell)
            self._bell_after_ids.append(after_id)

    def _cancel_gui_bells(self) -> None:
        for after_id in self._bell_after_ids:
            try:
                self.root.after_cancel(after_id)
            except tk.TclError:
                pass
        self._bell_after_ids.clear()

    def destroy(self) -> None:
        self.close_all()
        self.root.destroy()

    def _spawn_window(self, message: str, index: int) -> None:
        window = tk.Toplevel(self.root)
        window.title(self.title)
        window.attributes("-topmost", True)
        window.configure(bg="#8b0000")
        offset = index * 36
        window.geometry(f"420x170+{80 + offset}+{80 + offset}")

        label = tk.Label(
            window,
            text=f"😡 {message}",
            bg="#8b0000",
            fg="white",
            font=("Arial", 14, "bold"),
            wraplength=360,
            justify="center",
            padx=18,
            pady=18,
        )
        label.pack(expand=True, fill="both")

        button = tk.Button(window, text="Ya voy, ya voy", command=window.destroy)
        button.pack(pady=(0, 12))
        window.after(10_000, window.destroy)
        self._open_windows.append(window)
