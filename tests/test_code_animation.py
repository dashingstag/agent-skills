"""Checks for the code-animation scaffold. Run: python -m unittest discover -s tests."""

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
import wave

from PIL import Image

REPO = Path(__file__).resolve().parents[1]
PROJECT = REPO / "skills/code-animation/templates/project"
sys.path[:0] = [str(PROJECT), str(PROJECT / "tools")]

from animate import soundtrack
from delivery import canvas, guides, transcript, verify_loop, write_srt
from lib.effects import Emitter, Particle, composite
from lib.footage import track, video_frames
from lib.motion import Camera, keyframes, transition
from lib.rig import mirror, viseme_at, walk
from shots.bumper import setup as bumper_setup


class AnimationTests(unittest.TestCase):
    def test_bumper_pulse_is_optional_and_selected_by_id(self):
        spec = {"width": 180, "height": 160}
        shot = {"id": "resolve"}
        without_pulse = bumper_setup(spec, shot)
        self.assertEqual(without_pulse(0).tobytes(), without_pulse(14).tobytes())
        shot["events"] = [{"id": "marker", "frame": 0}, {"id": "pulse", "frame": 12}]
        with_pulse = bumper_setup(spec, shot)
        self.assertEqual(without_pulse(11).tobytes(), with_pulse(11).tobytes())
        self.assertNotEqual(without_pulse(12).tobytes(), with_pulse(12).tobytes())

    def test_rgba_crossfade_does_not_bleed_hidden_rgb(self):
        red = Image.new("RGBA", (1, 1), (255, 0, 0, 255))
        clear_blue = Image.new("RGBA", (1, 1), (0, 0, 255, 0))
        self.assertEqual(transition(red, clear_blue, .5, "crossfade").getpixel((0, 0)),
                         (255, 0, 0, 127))

    def test_camera_and_transitions(self):
        black = Image.new("RGB", (10, 8), "black")
        white = Image.new("RGB", black.size, "white")
        self.assertEqual(Camera(pan=(20,12)).layer(white,0).convert("RGB").tobytes(), white.tobytes())
        self.assertEqual(transition(black,white,.5,"wipe").getpixel((4,0)), (255,255,255))
        self.assertEqual(transition(black,white,.5,"wipe").getpixel((5,0)), (0,0,0))
        self.assertEqual(transition(black,white,.5,"crossfade").getpixel((5,0)), (127,127,127))
        self.assertIs(transition(black,white,.49,"cut-on-action"),black)
        self.assertIs(transition(black,white,.5,"cut-on-action"),white)
        self.assertEqual(keyframes([(0,2),(8,10)],4),6)
        self.assertEqual(track([(0,(2,8)),(4,(10,0))],1),(4,6))

    def test_particle_seek_is_deterministic(self):
        for seed, kind in enumerate(("sparks","snow","dust")):
            emitter = Emitter(kind,(80,40),seed,24)
            frame = emitter.layer(13,(250,200,150)).tobytes()
            emitter.layer(5,(250,200,150))
            self.assertEqual(frame,emitter.layer(13,(250,200,150)).tobytes())
            self.assertNotEqual(frame,emitter.layer(14,(250,200,150)).tobytes())

    def test_particles_composite_over_each_other(self):
        emitter = Emitter("snow", (10, 10), 1, 1)
        existing = Particle(5, 5, 0, 0, 0, 30, 2, 0)
        newborn = Particle(5, 5, 0, 0, 8, 30, 2, 0)
        emitter.particles = [existing]
        color = (255, 255, 255)
        one = emitter.layer(8, color).getpixel((5, 5))
        emitter.particles.append(newborn)
        self.assertEqual(emitter.layer(8, color).getpixel((5, 5)), one)
        emitter.particles = [existing, existing]
        self.assertEqual(emitter.layer(8, color).getpixel((5, 5)), (255, 255, 255, 250))

    def test_transparent_blend_and_edge(self):
        base = Image.new("RGB",(1,1),(40,80,120))
        layer = Image.new("RGBA",(1,1),(200,160,120,64))
        self.assertEqual(composite(base,layer).getpixel((0,0)),(80,100,120,255))
        self.assertEqual(composite(base,layer,"add").getpixel((0,0)),(90,120,150,255))
        clear = Image.new("RGBA",(1,1),(255,255,255,0))
        for mode in ("over","add","screen","multiply"):
            self.assertEqual(composite(base,clear,mode).convert("RGB").tobytes(),base.tobytes())

    def test_walk_and_visemes(self):
        self.assertEqual(walk(.5),mirror(walk(0)))
        self.assertEqual(walk(0),walk(1))
        self.assertEqual(mirror(mirror(walk(0))),walk(0))
        self.assertEqual(viseme_at([(0,"rest"),(3,"open"),(6,"closed")],8,5),"open")
        with self.assertRaises(ValueError):
            viseme_at([(0,"rest"),(0,"open")],8,0)

    def test_aspect_and_safe_guides(self):
        for preset, size in (("16:9",(1920,1080)),("9:16",(1080,1920)),("1:1",(1080,1080))):
            spec = {"aspect":preset}
            canvas(spec)
            self.assertEqual((spec["width"],spec["height"]),size)
        with self.assertRaises(ValueError):
            canvas({"aspect":"9:16","width":640,"height":360})
        im = Image.new("RGB",(100,100))
        out = guides(im)
        self.assertNotEqual(out.getpixel((5,5)),im.getpixel((5,5)))
        self.assertEqual(out.getpixel((50,50)),im.getpixel((50,50)))

    def test_caption_ranges_and_srt(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp)/"cue.json"
            path.write_text(json.dumps([{"start":9,"end":34,"text":"Blue skies ahead."}]))
            cues = transcript(path,60)
            out = path.with_suffix(".srt")
            write_srt(out,cues,24)
            self.assertEqual(out.read_text(),"1\n00:00:00,375 --> 00:00:01,417\nBlue skies ahead.\n\n")
            with self.assertRaises(ValueError):
                transcript(path,20)
            write_srt(out, [{"start": 0, "end": 12, "text": "First\n \t\nSecond"}], 24)
            self.assertIn("\nFirst\nSecond\n\n", out.read_text())
            with self.assertRaisesRegex(ValueError, "markup"):
                write_srt(out, [{"start": 0, "end": 12, "text": "<b>not markup</b>"}], 24)

    def test_loop_rejects_large_or_hard_seams(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp)/"loop.gif"
            a,b = [Image.new("RGB",(10,10),c) for c in ("black","white")]
            a.save(path,save_all=True,append_images=[b],duration=50,loop=0)
            self.assertIn("2 frames",verify_loop(path,(10,10),20,2,5000,255))
            with self.assertRaisesRegex(ValueError,"byte limit"):
                verify_loop(path,(10,10),20,2,1,255)
            with self.assertRaisesRegex(ValueError,"seam difference"):
                verify_loop(path,(10,10),20,2,5000,2)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "requires FFmpeg")
    def test_truncated_wav_is_rejected(self):
        with TemporaryDirectory() as tmp:
            src = Path(tmp) / "voice.wav"
            out = Path(tmp) / "out.wav"
            with wave.open(str(src), "wb") as wav:
                wav.setparams((1, 2, 48000, 0, "NONE", ""))
                wav.writeframes(b"\x12\x44" * 48000)
            spec = {"audio": str(src), "fps": 24, "seed": 1, "shots": [{"frames": 24}]}
            soundtrack(spec, out)
            src.write_bytes(src.read_bytes()[:-411])
            with self.assertRaises((ValueError, subprocess.CalledProcessError)):
                soundtrack(spec, out)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "requires FFmpeg")
    def test_valid_pcm_and_mp3_in_wav(self):
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.wav"
            for codec in ("pcm_s16le", "libmp3lame"):
                with self.subTest(codec=codec):
                    src = Path(tmp) / f"{codec}.wav"
                    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                                    "sine=frequency=440:sample_rate=44100:duration=0.35",
                                    "-c:a", codec, str(src)], check=True)
                    soundtrack({"audio": str(src), "fps": 24, "seed": 1, "shots": [{"frames": 24}]}, out)
                    with wave.open(str(out), "rb") as wav:
                        self.assertEqual(wav.getnframes(), 48000)
                        self.assertNotEqual(wav.readframes(48000), bytes(48000 * 4))

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "requires FFmpeg")
    def test_verify_without_capture_inputs(self):
        demo = REPO / "demos/browser-explainer"
        with TemporaryDirectory() as tmp:
            manifest = Path(shutil.copy(demo / "animation.json", tmp))
            spec = json.loads(manifest.read_text())
            count = sum(shot["frames"] for shot in spec["shots"])
            video = Path(tmp) / "fixture.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                            f"color=s={spec['width']}x{spec['height']}:r={spec['fps']}",
                            "-frames:v", str(count), "-c:v", "libx264", "-threads", "1",
                            "-pix_fmt", "yuv420p", str(video)], check=True)
            cmd = [sys.executable, str(PROJECT / "tools/animate.py"), "--project", tmp]
            result = subprocess.run(cmd + ["verify", str(video)],
                                    check=True, capture_output=True, text=True)
            self.assertIn(f"{count} frames", result.stdout)
            result = subprocess.run(cmd + ["validate"], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("cache/browser/0000.png", result.stderr)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "requires FFmpeg")
    def test_footage_mkv_and_display_rotation(self):
        with TemporaryDirectory() as tmp:
            src, mkv, rotated = (Path(tmp) / name for name in ("raw.mp4", "clip.mkv", "rotate.mp4"))
            ff = ["ffmpeg", "-v", "error"]
            subprocess.run(ff + ["-f", "lavfi", "-i", "color=c=blue:s=64x48:r=30:d=1",
                                 "-c:v", "libx264", str(src)], check=True)
            subprocess.run(ff + ["-i", str(src), "-c", "copy", str(mkv)], check=True)
            subprocess.run(ff + ["-i", str(src), "-c", "copy",
                                 "-metadata:s:v:0", "rotate=90", str(rotated)], check=True)
            for path, size in ((mkv, (64,48)), (rotated, (48,64))):
                frames = video_frames(path, source_fps=30, fps=24, size=size, frames=24)
                self.assertEqual(len(frames), 24)
                self.assertTrue(all(frame.size == size for frame in frames))
            with self.assertRaisesRegex(ValueError, "does not match"):
                video_frames(rotated, source_fps=30, fps=24, size=(64,48), frames=24)

    @unittest.skipUnless(importlib.util.find_spec("playwright") and shutil.which("google-chrome"),
                         "requires optional Playwright and Google Chrome")
    def test_browser_repeated_samples_and_owned_frame_names(self):
        with TemporaryDirectory() as tmp:
            work = Path(tmp)
            scene = work / "scene.html"
            scene.write_text('''<!doctype html>
<style>@font-face {font-family: Capture; src: local("DejaVu Sans")}
body {font-family: Capture}</style><p>Capture fixture</p>
<script>
window.captureFonts = ["16px Capture"];
window.setFrame = n => { document.body.style.background = n===1 ? "tomato" : "white"; };
</script>''', encoding="utf-8")
            out = work / "frames"
            out.mkdir()
            for name in ("9-reference.png", "9999.png"):
                Image.new("RGB", (8, 8)).save(out / name)
            result = subprocess.run([sys.executable, str(PROJECT.parent / "browser/capture.py"),
                                     str(scene), "--out", str(out), "--width", "640", "--height", "360",
                                     "--frames", "5", "--chromium", shutil.which("google-chrome")],
                                    timeout=75, check=True, capture_output=True, text=True)
            self.assertIn("Captured 5 frames", result.stdout)
            self.assertTrue((out / "9-reference.png").is_file())
            self.assertFalse((out / "9999.png").exists())
