import unittest

from reganometro.app import ReganometroConfig, build_parser
from reganometro.audio import SoundConfig
from reganometro.notifier import ScoldingRotator


class ConfigTests(unittest.TestCase):
    def test_defaults_reganan_after_five_seconds_with_sound(self):
        config = ReganometroConfig()
        self.assertEqual(config.idle_seconds, 5)
        self.assertEqual(config.alert_every, 5)
        self.assertEqual(config.check_every, 0.5)
        self.assertEqual(config.burst_count, 3)
        self.assertTrue(config.sound_enabled)
        self.assertEqual(config.sound_count, 3)

    def test_accepts_valid_configuration(self):
        config = ReganometroConfig(
            idle_seconds=10,
            check_every=0.5,
            alert_every=3,
            burst_count=4,
            sound_enabled=False,
            sound_count=2,
            demo=True,
        )
        self.assertEqual(config.idle_seconds, 10)
        self.assertFalse(config.sound_enabled)
        self.assertTrue(config.demo)

    def test_rejects_too_many_popup_windows(self):
        with self.assertRaisesRegex(ValueError, "burst-count"):
            ReganometroConfig(burst_count=11)

    def test_rejects_too_many_sounds(self):
        with self.assertRaisesRegex(ValueError, "sound-count"):
            ReganometroConfig(sound_count=11)

    def test_parser_exposes_sound_and_demo_flags(self):
        args = build_parser().parse_args(
            ["--demo", "--no-sound", "--sound-count", "4", "--idle-seconds", "5"]
        )
        self.assertTrue(args.demo)
        self.assertTrue(args.no_sound)
        self.assertEqual(args.sound_count, 4)
        self.assertEqual(args.idle_seconds, 5)


class SoundConfigTests(unittest.TestCase):
    def test_rejects_zero_sounds(self):
        with self.assertRaisesRegex(ValueError, "sound-count"):
            SoundConfig(repeat_count=0)


class ScoldingRotatorTests(unittest.TestCase):
    def test_requires_at_least_one_message(self):
        with self.assertRaisesRegex(ValueError, "regaño"):
            ScoldingRotator(messages=["", "   "], shuffle=False)

    def test_rotates_messages_without_immediate_repeat(self):
        rotator = ScoldingRotator(messages=["uno", "dos"], shuffle=False)
        seen = [rotator.next() for _ in range(4)]
        self.assertEqual(seen, ["uno", "dos", "uno", "dos"])


if __name__ == "__main__":
    unittest.main()
