#!/usr/bin/env python3
"""
Integration tests for FFmpeg Video Toolkit Pro.
Generates synthetic media fixtures with FFmpeg lavfi and tests every subcommand.
Skips cleanly if FFmpeg or FFprobe are absent.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from engine.video_toolkit import ExitCode, FFmpegRunner, main


def is_ffmpeg_available() -> bool:
    ffmpeg_exe = os.environ.get("FFMPEG_PATH") or shutil.which("ffmpeg")
    ffprobe_exe = os.environ.get("FFPROBE_PATH") or shutil.which("ffprobe")
    return bool(ffmpeg_exe and ffprobe_exe)


@unittest.skipUnless(is_ffmpeg_available(), "FFmpeg and/or FFprobe not available in environment")
class TestEngineIntegration(unittest.TestCase):
    temp_dir: str
    fixtures_dir: Path
    runner: FFmpegRunner

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp(prefix="fvt_test_integ_")
        cls.fixtures_dir = Path(cls.temp_dir) / "fixtures"
        cls.fixtures_dir.mkdir(parents=True, exist_ok=True)
        cls.runner = FFmpegRunner()

        ffmpeg = cls.runner.ffmpeg

        # 1. Standard clip (3.0s, 320x240, 24fps video + 44.1kHz mono sine audio)
        cls.std_clip = cls.fixtures_dir / "standard.mp4"
        subprocess.run([
            ffmpeg, "-y",
            "-f", "lavfi", "-i", "testsrc=duration=3:size=320x240:rate=24",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=3",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            str(cls.std_clip),
        ], capture_output=True, check=True)

        # 2. Silent-gap clip (sine 1s, silence 1s, sine 1s = 3.0s total)
        cls.silent_clip = cls.fixtures_dir / "silent_gap.mp4"
        subprocess.run([
            ffmpeg, "-y",
            "-f", "lavfi", "-i", "testsrc=duration=3:size=320x240:rate=24",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
            "-f", "lavfi", "-i", "anullsrc=duration=1:sample_rate=44100:channel_layout=mono",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
            "-filter_complex", "[1:a][2:a][3:a]concat=n=3:v=0:a=1[outa]",
            "-map", "0:v", "-map", "[outa]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            str(cls.silent_clip),
        ], capture_output=True, check=True)

        # 3. No-audio clip (2.0s, 320x240)
        cls.no_audio_clip = cls.fixtures_dir / "no_audio.mp4"
        subprocess.run([
            ffmpeg, "-y",
            "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=24",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(cls.no_audio_clip),
        ], capture_output=True, check=True)

        # 4. Vertical clip (1080x1920, 2.0s)
        cls.vertical_clip = cls.fixtures_dir / "vertical.mp4"
        subprocess.run([
            ffmpeg, "-y",
            "-f", "lavfi", "-i", "testsrc=duration=2:size=1080x1920:rate=24",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(cls.vertical_clip),
        ], capture_output=True, check=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_compress_three_different_inputs_and_targets(self):
        """Asserts compress output size is strictly under target for 3 different targets."""
        targets = [
            (80 * 1024, "target_80k.mp4"),
            (120 * 1024, "target_120k.mp4"),
            (200 * 1024, "target_200k.mp4"),
        ]
        for target_bytes, out_name in targets:
            out_file = Path(self.temp_dir) / out_name
            code = main([
                "compress",
                str(self.std_clip),
                str(out_file),
                "--target-size-bytes", str(target_bytes),
                "--overwrite",
            ])
            self.assertEqual(code, ExitCode.SUCCESS, f"Compression failed for {out_name}")
            self.assertTrue(out_file.exists(), f"Output file missing for {out_name}")
            actual_size = out_file.stat().st_size
            self.assertLess(
                actual_size,
                target_bytes,
                f"Compressed file {out_name} size ({actual_size:,}) exceeded target limit ({target_bytes:,})",
            )

    def test_trim_silence_removes_gap(self):
        out_file = Path(self.temp_dir) / "trimmed.mp4"
        code = main([
            "trim-silence",
            str(self.silent_clip),
            str(out_file),
            "--noise=-30dB",
            "--min-silence", "0.5",
            "--pad", "0.05",
            "--overwrite",
        ])
        self.assertEqual(code, ExitCode.SUCCESS)
        self.assertTrue(out_file.exists())

        probe = self.runner.run_probe(out_file)
        dur = float(probe["format"]["duration"])
        # Original is 3.0s with 1.0s silence in middle. Output duration should be ~2.0s
        self.assertLess(dur, 2.5)
        self.assertGreater(dur, 1.8)

    def test_trim_silence_no_audio_fails_with_stream_error(self):
        out_file = Path(self.temp_dir) / "fail_trim.mp4"
        code = main([
            "trim-silence",
            str(self.no_audio_clip),
            str(out_file),
            "--overwrite",
        ])
        self.assertEqual(code, ExitCode.STREAM_ERROR)
        self.assertFalse(out_file.exists())

    def test_shorts_crop_mode(self):
        out_file = Path(self.temp_dir) / "shorts_crop.mp4"
        code = main([
            "shorts",
            str(self.std_clip),
            str(out_file),
            "--mode", "crop",
            "--overwrite",
        ])
        self.assertEqual(code, ExitCode.SUCCESS)
        self.assertTrue(out_file.exists())

        probe = self.runner.run_probe(out_file)
        v = next(s for s in probe["streams"] if s["codec_type"] == "video")
        self.assertEqual(int(v["width"]), 1080)
        self.assertEqual(int(v["height"]), 1920)

    def test_shorts_blur_mode(self):
        out_file = Path(self.temp_dir) / "shorts_blur.mp4"
        code = main([
            "shorts",
            str(self.std_clip),
            str(out_file),
            "--mode", "blur",
            "--overwrite",
        ])
        self.assertEqual(code, ExitCode.SUCCESS)
        self.assertTrue(out_file.exists())

        probe = self.runner.run_probe(out_file)
        v = next(s for s in probe["streams"] if s["codec_type"] == "video")
        self.assertEqual(int(v["width"]), 1080)
        self.assertEqual(int(v["height"]), 1920)

    def test_convert_format(self):
        out_file = Path(self.temp_dir) / "converted.mp4"
        code = main([
            "convert",
            str(self.std_clip),
            str(out_file),
            "--format", "mp4",
            "--overwrite",
        ])
        self.assertEqual(code, ExitCode.SUCCESS)
        self.assertTrue(out_file.exists())

    def test_extract_audio_formats(self):
        for fmt in ["wav", "flac", "mp3"]:
            out_file = Path(self.temp_dir) / f"audio.{fmt}"
            code = main([
                "extract-audio",
                str(self.std_clip),
                str(out_file),
                "--format", fmt,
                "--overwrite",
            ])
            self.assertEqual(code, ExitCode.SUCCESS, f"Audio extraction failed for {fmt}")
            self.assertTrue(out_file.exists())
            probe = self.runner.run_probe(out_file)
            self.assertTrue(any(s["codec_type"] == "audio" for s in probe["streams"]))

    def test_cut_stream_copy_and_precise(self):
        out_copy = Path(self.temp_dir) / "cut_copy.mp4"
        code_copy = main([
            "cut",
            str(self.std_clip),
            str(out_copy),
            "--start", "00:00:01",
            "--duration", "1.0",
            "--overwrite",
        ])
        self.assertEqual(code_copy, ExitCode.SUCCESS)
        self.assertTrue(out_copy.exists())

        out_precise = Path(self.temp_dir) / "cut_precise.mp4"
        code_precise = main([
            "cut",
            str(self.std_clip),
            str(out_precise),
            "--start", "1.0",
            "--duration", "1.0",
            "--precise",
            "--overwrite",
        ])
        self.assertEqual(code_precise, ExitCode.SUCCESS)
        self.assertTrue(out_precise.exists())
        probe = self.runner.run_probe(out_precise)
        dur = float(probe["format"]["duration"])
        self.assertAlmostEqual(dur, 1.0, delta=0.2)

    def test_merge_matching_clips(self):
        out_file = Path(self.temp_dir) / "merged.mp4"
        code = main([
            "merge",
            str(self.std_clip),
            str(self.std_clip),
            "--output", str(out_file),
            "--overwrite",
        ])
        self.assertEqual(code, ExitCode.SUCCESS)
        self.assertTrue(out_file.exists())
        probe = self.runner.run_probe(out_file)
        dur = float(probe["format"]["duration"])
        # std_clip is 3s, merged should be ~6s
        self.assertAlmostEqual(dur, 6.0, delta=0.5)

    def test_merge_mismatch_fails_without_reencode_and_succeeds_with_reencode(self):
        # std_clip (320x240) and vertical_clip (1080x1920) differ in resolution
        out_fail = Path(self.temp_dir) / "merged_fail.mp4"
        code_fail = main([
            "merge",
            str(self.std_clip),
            str(self.vertical_clip),
            "--output", str(out_fail),
            "--overwrite",
        ])
        self.assertEqual(code_fail, ExitCode.VERIFICATION_ERROR)
        self.assertFalse(out_fail.exists())

        # With --reencode it succeeds
        out_ok = Path(self.temp_dir) / "merged_reencode.mp4"
        code_ok = main([
            "merge",
            str(self.std_clip),
            str(self.vertical_clip),
            "--output", str(out_ok),
            "--reencode",
            "--overwrite",
        ])
        self.assertEqual(code_ok, ExitCode.SUCCESS)
        self.assertTrue(out_ok.exists())

    def test_gif_and_webp_generation(self):
        out_gif = Path(self.temp_dir) / "anim.gif"
        code_gif = main([
            "gif",
            str(self.std_clip),
            str(out_gif),
            "--fps", "10",
            "--width", "160",
            "--max-seconds", "1.5",
            "--overwrite",
        ])
        self.assertEqual(code_gif, ExitCode.SUCCESS)
        self.assertTrue(out_gif.exists())

        out_webp = Path(self.temp_dir) / "anim.webp"
        code_webp = main([
            "gif",
            str(self.std_clip),
            str(out_webp),
            "--format", "webp",
            "--fps", "10",
            "--width", "160",
            "--max-seconds", "1.5",
            "--overwrite",
        ])
        self.assertEqual(code_webp, ExitCode.SUCCESS)
        self.assertTrue(out_webp.exists())

    def test_speed_adjustment(self):
        out_file = Path(self.temp_dir) / "speed2x.mp4"
        code = main([
            "speed",
            str(self.std_clip),
            str(out_file),
            "--factor", "2.0",
            "--overwrite",
        ])
        self.assertEqual(code, ExitCode.SUCCESS)
        self.assertTrue(out_file.exists())
        probe = self.runner.run_probe(out_file)
        dur = float(probe["format"]["duration"])
        # std_clip is 3s, at 2x it becomes ~1.5s
        self.assertAlmostEqual(dur, 1.5, delta=0.2)

    def test_strip_meta(self):
        # Create clip with metadata tags
        meta_clip = Path(self.temp_dir) / "tagged.mp4"
        subprocess.run([
            self.runner.ffmpeg, "-y",
            "-i", str(self.std_clip),
            "-metadata", "title=Secret Title",
            "-metadata", "author=Alice",
            "-c", "copy",
            str(meta_clip),
        ], capture_output=True, check=True)

        clean_clip = Path(self.temp_dir) / "stripped.mp4"
        code = main([
            "strip-meta",
            str(meta_clip),
            str(clean_clip),
            "--overwrite",
        ])
        self.assertEqual(code, ExitCode.SUCCESS)
        self.assertTrue(clean_clip.exists())

        probe = self.runner.run_probe(clean_clip)
        tags = probe.get("format", {}).get("tags", {})
        self.assertNotIn("title", tags)
        self.assertNotIn("author", tags)

    def test_thumbs_contact_sheet(self):
        out_sheet = Path(self.temp_dir) / "contact_sheet.jpg"
        code = main([
            "thumbs",
            str(self.std_clip),
            str(out_sheet),
            "--cols", "2",
            "--rows", "2",
            "--width", "160",
            "--overwrite",
        ])
        self.assertEqual(code, ExitCode.SUCCESS)
        self.assertTrue(out_sheet.exists())

    def test_dry_run_does_not_create_file(self):
        out_file = Path(self.temp_dir) / "dry_run.mp4"
        code = main([
            "shorts",
            str(self.std_clip),
            str(out_file),
            "--dry-run",
        ])
        self.assertEqual(code, ExitCode.SUCCESS)
        self.assertFalse(out_file.exists())

    def test_overwrite_protection(self):
        out_file = Path(self.temp_dir) / "protected.mp4"
        # Create existing file
        out_file.touch()
        code = main([
            "cut",
            str(self.std_clip),
            str(out_file),
            "--duration", "1",
            # No --overwrite
        ])
        self.assertEqual(code, ExitCode.VERIFICATION_ERROR)


if __name__ == "__main__":
    unittest.main()
