#!/usr/bin/env python3
"""
Pure-logic unit tests for FFmpeg Video Toolkit Pro.
Runs 100% offline with zero external dependencies (no FFmpeg required).
"""

from pathlib import Path
import unittest

from engine.video_toolkit import (
    build_atempo_filter_chain,
    calculate_two_pass_bitrate,
    compute_keep_segments,
    escape_concat_demuxer_path,
    load_platform_limits,
    parse_silencedetect_stderr,
    parse_time_to_seconds,
)


class TestPureLogic(unittest.TestCase):

    def test_parse_time_to_seconds(self):
        self.assertEqual(parse_time_to_seconds(10), 10.0)
        self.assertEqual(parse_time_to_seconds(12.5), 12.5)
        self.assertEqual(parse_time_to_seconds("45"), 45.0)
        self.assertEqual(parse_time_to_seconds("01:30"), 90.0)
        self.assertEqual(parse_time_to_seconds("01:02:03"), 3723.0)

    def test_calculate_two_pass_bitrate_normal(self):
        # 10 MB in 60s
        target_bytes = 10 * 1024 * 1024
        duration = 60.0
        v_bit, a_bit = calculate_two_pass_bitrate(
            target_bytes=target_bytes,
            duration_s=duration,
            audio_bitrate_bps=128_000,
            safety_margin=0.05,
            width=1280,
            height=720,
            fps=30.0,
        )
        self.assertGreater(v_bit, 0)
        self.assertEqual(a_bit, 128_000)

        # Confirm total calculated size is strictly <= target_bytes
        total_bitrate = v_bit + a_bit
        projected_bytes = (total_bitrate * duration) / 8.0
        self.assertLessEqual(projected_bytes, target_bytes * 0.96)

    def test_calculate_two_pass_bitrate_small_envelope_downscales_audio(self):
        # 600 KB in 30s -> low total bitrate (< 250k), audio steps down to 64k
        target_bytes = 600 * 1024
        duration = 30.0
        v_bit, a_bit = calculate_two_pass_bitrate(
            target_bytes=target_bytes,
            duration_s=duration,
            audio_bitrate_bps=128_000,
            width=320,
            height=240,
            fps=24.0,
        )
        self.assertEqual(a_bit, 64_000)
        self.assertGreater(v_bit, 48_000)

    def test_calculate_two_pass_bitrate_impossible_size_raises(self):
        # 10 KB for 60 seconds is mathematically impossible
        with self.assertRaises(ValueError) as ctx:
            calculate_two_pass_bitrate(
                target_bytes=10_000,
                duration_s=60.0,
                width=1920,
                height=1080,
            )
        self.assertIn("too small", str(ctx.exception))

    def test_calculate_two_pass_bitrate_bppf_rejection_suggests_scale(self):
        # 2 MB for 1080p 60s produces very low bppf (<0.04), should raise recommending scale
        with self.assertRaises(ValueError) as ctx:
            calculate_two_pass_bitrate(
                target_bytes=2 * 1024 * 1024,
                duration_s=60.0,
                width=1920,
                height=1080,
                fps=30.0,
            )
        self.assertIn("--scale", str(ctx.exception))

    def test_build_atempo_filter_chain_identity(self):
        self.assertEqual(build_atempo_filter_chain(1.0), "atempo=1.0")

    def test_build_atempo_filter_chain_speedup_powers_of_two(self):
        self.assertEqual(build_atempo_filter_chain(2.0), "atempo=2.0")
        self.assertEqual(build_atempo_filter_chain(4.0), "atempo=2.0,atempo=2.0")
        self.assertEqual(build_atempo_filter_chain(8.0), "atempo=2.0,atempo=2.0,atempo=2.0")

    def test_build_atempo_filter_chain_slowdown_powers_of_two(self):
        self.assertEqual(build_atempo_filter_chain(0.5), "atempo=0.5")
        self.assertEqual(build_atempo_filter_chain(0.25), "atempo=0.5,atempo=0.5")

    def test_build_atempo_filter_chain_arbitrary_factors(self):
        # 3.0x -> atempo=2.0,atempo=1.5
        self.assertEqual(build_atempo_filter_chain(3.0), "atempo=2.0,atempo=1.5")
        # 0.35x -> atempo=0.5,atempo=0.7
        self.assertEqual(build_atempo_filter_chain(0.35), "atempo=0.5,atempo=0.7")

    def test_build_atempo_filter_chain_invalid_factor(self):
        with self.assertRaises(ValueError):
            build_atempo_filter_chain(0.0)
        with self.assertRaises(ValueError):
            build_atempo_filter_chain(-1.5)

    def test_parse_silencedetect_stderr(self):
        sample_stderr = """
[Parsed_silencedetect_0 @ 00000173012a0100] silence_start: 1.002
[Parsed_silencedetect_0 @ 00000173012a0100] silence_end: 2.504 | silence_duration: 1.502
[Parsed_silencedetect_0 @ 00000173012a0100] silence_start: 5.100
[Parsed_silencedetect_0 @ 00000173012a0100] silence_end: 7.200 | silence_duration: 2.100
"""
        silences = parse_silencedetect_stderr(sample_stderr, total_duration=10.0)
        self.assertEqual(len(silences), 2)
        self.assertAlmostEqual(silences[0][0], 1.002, places=3)
        self.assertAlmostEqual(silences[0][1], 2.504, places=3)
        self.assertAlmostEqual(silences[1][0], 5.100, places=3)
        self.assertAlmostEqual(silences[1][1], 7.200, places=3)

    def test_compute_keep_segments_inversion_and_padding(self):
        silences = [(1.0, 3.0)]
        total_duration = 5.0
        # pad=0.1 means silence becomes (1.1, 2.9)
        # keep becomes [(0, 1.1), (2.9, 5.0)]
        keep = compute_keep_segments(silences, total_duration, pad_s=0.1)
        self.assertEqual(len(keep), 2)
        self.assertAlmostEqual(keep[0][0], 0.0, places=3)
        self.assertAlmostEqual(keep[0][1], 1.1, places=3)
        self.assertAlmostEqual(keep[1][0], 2.9, places=3)
        self.assertAlmostEqual(keep[1][1], 5.0, places=3)

    def test_compute_keep_segments_empty_silence(self):
        keep = compute_keep_segments([], total_duration=10.0)
        self.assertEqual(keep, [(0.0, 10.0)])

    def test_escape_concat_demuxer_path(self):
        # Forward slashes and quote escaping
        p1 = Path("/tmp/video.mp4")
        self.assertEqual(escape_concat_demuxer_path(p1), "file '/tmp/video.mp4'")

        p2 = Path("/tmp/video with spaces.mp4")
        self.assertEqual(escape_concat_demuxer_path(p2), "file '/tmp/video with spaces.mp4'")

        p3 = Path("/tmp/dave's video.mp4")
        self.assertEqual(escape_concat_demuxer_path(p3), r"file '/tmp/dave'\''s video.mp4'")

    def test_platform_limits_structure(self):
        limits = load_platform_limits()
        self.assertIn("discord", limits)
        self.assertIn("whatsapp", limits)
        self.assertIn("github", limits)

        for key, info in limits.items():
            self.assertIn("target_bytes", info)
            self.assertGreater(info["target_bytes"], 0)
            self.assertIn("status", info)
            self.assertIn("last_verified", info)


if __name__ == "__main__":
    unittest.main()
