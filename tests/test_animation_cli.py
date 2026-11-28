"""Regression checks for the animation scaffold CLI."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from PIL import Image


PROJECT = Path(__file__).resolve().parents[1] / "skills/code-animation/templates/project"


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "requires FFmpeg")
class AnimationCliTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.shots = [{"id": "sample", "intent": "Exercise the timeline", "frames": 4,
                       "renderer": "sample.py"}]
        self.write_manifest()
        self.renderer = self.root / "sample.py"
        self.renderer.write_text("from PIL import Image\n"
                                 "def setup(spec, shot):\n"
                                 "    return lambda n: Image.new('RGB', (64, 48))\n")
        self.cli = [sys.executable, str(PROJECT / "tools/animate.py"), "--project", str(self.root)]

    def write_manifest(self):
        (self.root / "animation.json").write_text(json.dumps({
            "width": 64, "height": 48, "fps": 4, "seed": 1, "shots": self.shots,
        }))

    def run_cli(self, *args, check=True):
        return subprocess.run(self.cli + list(args), check=check, capture_output=True, text=True,
                              timeout=30)

    def test_validate_checks_signature_and_first_image(self):
        self.run_cli("validate")
        for source, error in (
            ("def setup(spec):\n    pass\n", "invalid setup(spec, shot) signature"),
            ("def setup(spec, shot):\n    return 0\n", "setup must return a frame function"),
            ("def setup(spec, shot):\n    return lambda n: n\n", "expected canvas-sized RGB image"),
            ("from PIL import Image\ndef setup(spec, shot):\n"
             "    return lambda n: Image.new('RGBA', (64, 48))\n", "expected canvas-sized RGB image"),
            ("from PIL import Image\ndef setup(spec, shot):\n"
             "    return lambda n: Image.new('RGB', (48, 64))\n", "expected canvas-sized RGB image"),
        ):
            with self.subTest(source=source):
                self.renderer.write_text(source)
                result = self.run_cli("validate", check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("sample: ", result.stderr)
                self.assertIn(error, result.stderr)

    def test_unknown_shot_lists_valid_ids(self):
        self.shots.append({**self.shots[0], "id": "next"})
        self.write_manifest()
        for args in (("still", "missing"), ("render", "--only", "missing")):
            with self.subTest(args=args):
                result = self.run_cli(*args, check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("unknown shot ID 'missing'; valid IDs: sample, next", result.stderr)

    def test_verify_rejects_uneven_frame_timestamps_at_correct_average_rate(self):
        video = self.root / "uneven.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=s=64x48:r=4:d=1",
                        "-vf", "settb=1/8,setpts='if(eq(N,0),0,if(eq(N,1),1,if(eq(N,2),5,6)))'",
                        "-enc_time_base", "1:8", "-vsync", "vfr", "-c:v", "libx264",
                        "-video_track_timescale", "8", str(video)], check=True)
        result = self.run_cli("verify", str(video), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("frame 1 is off the expected 4 fps timestamp grid", result.stderr)

    def test_frames_only_affect_cache_when_declared(self):
        frames = self.root / "frames"
        frames.mkdir()
        for f in range(4):
            Image.new("RGB", (64, 48)).save(frames / f"{f:04d}.png")
        self.shots[0]["input_sequences"] = ["frames"]
        self.write_manifest()
        self.run_cli("render")
        Image.new("RGB", (64, 48)).save(frames / "unused.png")
        self.run_cli("assemble")
        Image.new("RGB", (64, 48), "blue").save(frames / "0000.png")
        result = self.run_cli("assemble", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing or stale shot sample", result.stderr)

    def test_simultaneous_renders_do_not_share_scratch_paths(self):
        args = self.cli + ["render", "--only", "sample"]
        with (subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as first,
              subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as second):
            for process in (first, second):
                stdout, stderr = process.communicate(timeout=30)
                self.assertEqual(process.returncode, 0, stdout + stderr)
        self.assertEqual(len(list((self.root / "out").glob("*/sample.mp4"))), 1)
        self.assertEqual(list((self.root / "out").glob("*/.render-*")), [])

    def test_loop_rejects_mislabeled_animation(self):
        path = self.root / "fake.gif"
        a = Image.new("RGB", (64, 48), "black")
        b = a.copy()
        b.putpixel((0, 0), (255, 255, 255))
        a.save(path, format="PNG", save_all=True, append_images=[b], duration=500, loop=0)
        result = self.run_cli("verify", str(path), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected GIF data, found PNG", result.stderr)
