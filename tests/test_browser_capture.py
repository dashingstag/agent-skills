"""Regression checks for deliberate browser holds."""

import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


CAPTURE = (Path(__file__).resolve().parents[1] /
           "skills/code-animation/templates/browser/capture.py")


@unittest.skipUnless(importlib.util.find_spec("playwright") and shutil.which("google-chrome"),
                     "requires optional Playwright and Google Chrome")
class BrowserCaptureTests(unittest.TestCase):
    def test_font_free_static_capture_and_motion_assertion(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            scene = root / "hold.html"
            scene.write_text('<body style="background:red"><script>'
                             'window.captureFonts=[]; window.setFrame=()=>{};</script>')
            out = root / "frames"
            cmd = [sys.executable, str(CAPTURE), str(scene), "--out", str(out),
                   "--frames", "3", "--width", "640", "--height", "360",
                   "--chromium", shutil.which("google-chrome")]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=75, check=True)
            self.assertIn("Warning: all captured frames are identical", result.stderr)
            frames = sorted(out.glob("*.png"))
            self.assertEqual(len(frames), 3)
            self.assertEqual(len({f.read_bytes() for f in frames}), 1)
            result = subprocess.run(cmd + ["--require-motion"], capture_output=True, text=True, timeout=75)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("all captured frames are identical", result.stderr)
