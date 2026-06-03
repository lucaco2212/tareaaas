"""CLI del Reganómetro."""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass

from .audio import SoundConfig
from .idle_detection import UnsupportedIdleDetector, build_idle_detector
from .notifier import ScoldingRotator, TkAngryNotifier


@dataclass(frozen=True)
class ReganometroConfig:
    """Configuración validada para el monitor de inactividad."""

    idle_seconds: int = 5
    check_every: float = 0.5
    alert_every: int = 5
    burst_count: int = 3
    sound_enabled: bool = True
    sound_count: int = 3
    demo: bool = False

    def __post_init__(self) -> None:
        if self.idle_seconds < 1:
            raise ValueError("--idle-seconds debe ser mayor o igual a 1")
        if self.check_every <= 0:
            raise ValueError("--check-every debe ser mayor a 0")
        if self.alert_every < 1:
            raise ValueError("--alert-every debe ser mayor o igual a 1")
        if not 1 <= self.burst_count <= 10:
            raise ValueError("--burst-count debe estar entre 1 y 10")
        SoundConfig(enabled=self.sound_enabled, repeat_count=self.sound_count)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reganometro",
        description="Te regaña con ventanas emergentes cuando no escribes ni mueves el mouse.",
    )
    parser.add_argument(
        "--idle-seconds",
        type=int,
        default=5,
        help="segundos de inactividad necesarios antes de regañarte (default: 5)",
    )
    parser.add_argument(
        "--check-every",
        type=float,
        default=0.5,
        help="cada cuántos segundos revisar actividad (default: 0.5)",
    )
    parser.add_argument(
        "--alert-every",
        type=int,
        default=5,
        help="repetir regaño cada N segundos mientras sigas inactivo (default: 5)",
    )
    parser.add_argument(
        "--burst-count",
        type=int,
        default=3,
        help="cuántas ventanas abrir por regaño, máximo 10 (default: 3)",
    )
    parser.add_argument(
        "--sound-count",
        type=int,
        default=3,
        help="cuántos pitidos reproducir por regaño, máximo 10 (default: 3)",
    )
    parser.add_argument(
        "--no-sound",
        action="store_true",
        help="desactiva los sonidos y deja solo las ventanas emergentes",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="usa un temporizador interno si el sistema no permite leer actividad global",
    )
    return parser


def monitor(config: ReganometroConfig) -> int:
    detector = build_idle_detector(allow_process_timer_fallback=config.demo)
    if isinstance(detector, UnsupportedIdleDetector):
        print(f"No puedo detectar inactividad: {detector.reason}", file=sys.stderr)
        return 2

    rotator = ScoldingRotator()
    notifier = TkAngryNotifier(
        sound_config=SoundConfig(
            enabled=config.sound_enabled,
            repeat_count=config.sound_count,
        )
    )
    last_alert_at = 0.0
    was_idle = False
    print(
        f"Reganómetro activo con detector {detector.name}. "
        "Presiona Ctrl+C para salir."
    )

    try:
        while True:
            idle_for = detector.seconds_idle()
            now = time.monotonic()
            is_idle = idle_for >= config.idle_seconds

            if is_idle and (not was_idle or now - last_alert_at >= config.alert_every):
                notifier.show(rotator.next(), burst_count=config.burst_count)
                last_alert_at = now
            elif not is_idle:
                notifier.close_all()

            was_idle = is_idle
            notifier.tick()
            time.sleep(config.check_every)
    except KeyboardInterrupt:
        print("\nReganómetro apagado. Espero que hayas aprendido la lección.")
        return 0
    finally:
        notifier.destroy()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = ReganometroConfig(
            idle_seconds=args.idle_seconds,
            check_every=args.check_every,
            alert_every=args.alert_every,
            burst_count=args.burst_count,
            sound_enabled=not args.no_sound,
            sound_count=args.sound_count,
            demo=args.demo,
        )
    except ValueError as exc:
        parser.error(str(exc))
    return monitor(config)


if __name__ == "__main__":
    raise SystemExit(main())
