"""Aspect guides, captions, and looping image delivery."""

import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

from PIL import Image, ImageChops, ImageDraw, ImageStat


ASPECT = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}


def canvas(spec):
    preset = spec.get("aspect")
    if preset is None:
        return
    w, h = ASPECT[preset]
    if "width" not in spec and "height" not in spec:
        spec.update(width=w, height=h)
    elif spec["width"] * h != spec["height"] * w:
        raise ValueError(f"canvas does not match {preset}")


def guides(im):
    w, h = im.size
    im = im.copy()
    d = ImageDraw.Draw(im, "RGBA")
    for margin, color in ((.05, (75, 231, 247, 210)), (.10, (255, 209, 91, 210))):
        x, y = round(w * margin), round(h * margin)
        d.rectangle((x, y, w-x-1, h-y-1), outline=color, width=max(1, w // 320))
    return im


def caption_text(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("captions must contain text")
    if "<" in text or ">" in text:
        raise ValueError("caption markup is not supported")
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def transcript(path, count):
    cues = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(cues, list) or not cues:
        raise ValueError("caption transcript must be a non-empty list")
    end = 0
    for cue in cues:
        a, b, text = cue["start"], cue["end"], cue["text"]
        if not (type(a) is int and type(b) is int and end <= a < b <= count):
            raise ValueError("captions must have ordered, non-overlapping frame ranges")
        caption_text(text)
        end = b
    return cues


def write_srt(path, cues, fps):
    def stamp(frame):
        sec, ms = divmod(round(frame * 1000 / fps), 1000)
        minute, sec = divmod(sec, 60)
        hour, minute = divmod(minute, 60)
        return f"{hour:02}:{minute:02}:{sec:02},{ms:03}"

    path.write_text("".join(f"{i}\n{stamp(c['start'])} --> {stamp(c['end'])}\n{caption_text(c['text'])}\n\n"
                            for i, c in enumerate(cues, 1)), encoding="utf-8")


def verify_loop(path, size, fps, frames, max_bytes, max_seam):
    if not (max_bytes > 0 and 0 <= max_seam <= 255):
        raise ValueError("invalid loop size or seam limit")
    nbytes = path.stat().st_size
    if nbytes > max_bytes:
        raise ValueError(f"{path}: {nbytes} bytes exceeds {max_bytes} byte limit")
    with Image.open(path) as im:
        expected = {".gif": "GIF", ".webp": "WEBP"}.get(path.suffix.lower())
        if expected is None or im.format != expected:
            raise ValueError(f"{path}: expected {expected or 'GIF or WebP'} data, found {im.format}")
        if not im.is_animated or im.size != size or im.info.get("loop") != 0:
            raise ValueError(f"{path}: expected an infinite animated loop at {size}")
        first = im.convert("RGB")
        duration = 0
        for i in range(im.n_frames):
            im.seek(i)
            im.load()
            duration += im.info.get("duration", 0)
        last = im.convert("RGB")
        seam = sum(ImageStat.Stat(ImageChops.difference(first, last)).mean) / 3
        if abs(duration / 1000 - frames / fps) > 1 / fps:
            raise ValueError(f"{path}: unexpected loop duration {duration} ms")
        if seam > max_seam:
            raise ValueError(f"{path}: loop seam difference {seam:.2f} exceeds {max_seam}")
        return f"{im.n_frames} frames, {size[0]}x{size[1]}, {duration/1000:.3f}s, {nbytes} bytes, seam {seam:.2f}/255"


def export_loop(src, dest, size, fps, frames, max_bytes, max_seam):
    dest.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=dest.parent, prefix=".loop-") as temp:
        out = Path(temp) / dest.name
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-an"]
        if dest.suffix == ".gif":
            cmd += ["-filter_complex_threads", "1", "-filter_complex",
                    "split[a][b];[a]palettegen[p];[b][p]paletteuse=dither=sierra2_4a", "-loop", "0"]
        else:
            cmd += ["-c:v", "libwebp_anim", "-quality", "80", "-loop", "0"]
        subprocess.run(cmd + [str(out)], check=True)
        result = verify_loop(out, size, fps, frames, max_bytes, max_seam)
        shutil.move(out, dest)
    print(f"Verified {dest}: {result}")
