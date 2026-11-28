"""Frame-indexed Python renderer and FFmpeg export."""

import argparse
from array import array
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import random
import re
import runpy
import shutil
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory
import wave

from PIL import Image, ImageDraw

import delivery


RATE = 48000
LENGTH = {"tap": .23, "charge": 1.1, "dash": .4, "beam": 1.15, "impact": .65}
GENERATED = {"cache", "out", "qa", "dist"}
FRAME = None
TEMPLATE = Path(__file__).resolve().parents[1]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def positive(n):
    return type(n) is int and n > 0


def source(path):
    p = Path(path).resolve()
    require(p.is_file() and p.is_relative_to(Path.cwd()), f"invalid source: {path}")
    return p


def asset_source(path):
    logical = Path(path)
    resolved = source(logical)
    project = Path.cwd()
    if logical.is_absolute() and logical.is_relative_to(project):
        logical = logical.relative_to(project)
    elif logical.is_absolute() and logical.anchor == project.anchor:
        logical = Path(os.path.relpath(logical.anchor, project), *logical.parts[1:])
    return logical, resolved


def read_spec(*, check_inputs=True):
    spec = json.loads(Path("animation.json").read_text(encoding="utf-8"))
    delivery.canvas(spec)
    for key in ("width", "height", "fps"):
        require(positive(spec[key]), f"{key} must be a positive integer")
    require(spec["width"] % 2 == spec["height"] % 2 == 0, "canvas must have even dimensions")
    require(type(spec["seed"]) is int, "seed must be an integer")
    require(isinstance(spec["shots"], list) and spec["shots"], "shots must be a non-empty list")
    seen = set()
    assets = set()
    for shot in spec["shots"]:
        sid = shot["id"]
        require(re.fullmatch(r"[a-z][a-z0-9_-]*", sid) and sid not in seen, f"invalid shot ID: {sid}")
        seen.add(sid)
        require(positive(shot["frames"]), f"{sid}: invalid frame count")
        require(shot["intent"].strip(), f"{sid}: missing intent")
        require(("renderer" in shot) != ("sequence" in shot), f"{sid}: supply a renderer or sequence")
        if check_inputs:
            if "sequence" in shot:
                assets.update(asset_source(sequence_frame(shot, f)) for f in range(shot["frames"]))
            else:
                p = Path(shot["renderer"])
                source(p)
                require(p.suffix == ".py", f"{sid}: renderer must be a Python file")
                require(callable(runpy.run_path(str(p)).get("setup")), f"{sid}: missing setup(spec, shot)")
            for directory in shot.get("input_sequences", []):
                assets.update(asset_source(sequence_frame({"sequence": directory}, f)) for f in range(shot["frames"]))
            assets.update(asset_source(asset) for asset in shot.get("assets", []))
        ids = set()
        for e in shot.get("events", []):
            eid = e["id"]
            require(eid and eid not in ids, f"{sid}: duplicate or empty event ID {eid!r}")
            ids.add(eid)
            f = e["frame"]
            require(type(f) is int and 0 <= f < shot["frames"], f"{sid}/{eid}: event out of range")
            require(e["kind"].strip(), f"{sid}/{eid}: missing kind")
            require("sound" not in e or e["sound"] in LENGTH, f"{sid}/{eid}: unknown sound")
            require(0 <= e.get("gain", .65) <= 1 and -1 <= e.get("pan", 0) <= 1,
                    f"{sid}/{eid}: gain or pan out of range")
    if "audio" in spec:
        require(Path(spec["audio"]).suffix.lower() == ".wav", "external audio must be a WAV")
    if check_inputs:
        if "audio" in spec:
            assets.add(asset_source(spec["audio"]))
        if "captions" in spec:
            assets.add(asset_source(spec["captions"]))
            delivery.transcript(spec["captions"], total(spec))
    require(shutil.which("ffmpeg") and shutil.which("ffprobe"), "install FFmpeg and ffprobe on PATH")
    return spec, assets


def sequence_frame(shot, f):
    return Path(shot["sequence"]) / f"{f:04d}.png"


def open_frame(path):
    with Image.open(path) as im:
        return im.convert("RGB")


def setup(spec, shot):
    global FRAME
    if "sequence" in shot:
        FRAME = lambda f: open_frame(sequence_frame(shot, f))
    else:
        FRAME = runpy.run_path(shot["renderer"])["setup"](spec, shot)
    require(callable(FRAME), "setup must return a frame function")


def image(f, spec):
    im = FRAME(f)
    require(isinstance(im, Image.Image) and im.mode == "RGB" and
            im.size == (spec["width"], spec["height"]), f"frame {f}: expected canvas-sized RGB image")
    return im


def pixels(f, spec, size):
    im = image(f, spec)
    if im.size != size:
        im = im.resize(size, Image.Resampling.LANCZOS)
    return im.tobytes()


def total(spec):
    return sum(s["frames"] for s in spec["shots"])


def events(spec):
    start = 0
    for s in spec["shots"]:
        yield from ((start + e["frame"], e) for e in s.get("events", []) if "sound" in e)
        start += s["frames"]


def render_key(assets):
    h = hashlib.sha256()
    for program in ("ffmpeg", "ffprobe"):
        h.update(subprocess.check_output([program, "-version"]).splitlines()[0])
    h.update(sys.version.encode())
    h.update(Image.__version__.encode())
    for p in sorted((*Path(__file__).resolve().parent.glob("*.py"), *(TEMPLATE / "lib").glob("*.py"))):
        h.update(p.relative_to(TEMPLATE).as_posix().encode())
        h.update(b"\0")
        h.update(hashlib.sha256(p.read_bytes()).digest())
    project = Path.cwd()
    paths = {p.relative_to(project): p for _, p in assets}
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"
                   and not (root == "." and d in GENERATED) and not Path(root, d, "pyvenv.cfg").is_file()]
        for name in files:
            path = Path(root, name)
            if (not name.startswith(".") or name == ".gitignore") and path not in paths:
                paths[path] = source(path)
    digests = {}
    for path, p in sorted(paths.items()):
        if p not in digests:
            digests[p] = hashlib.sha256(p.read_bytes()).digest()
        h.update(path.as_posix().encode())
        h.update(b"\0")
        h.update(digests[p])
    for logical, resolved in sorted(assets):
        h.update(b"asset\0")
        h.update(logical.as_posix().encode())
        h.update(b"\0")
        h.update(resolved.relative_to(project).as_posix().encode())
        h.update(b"\0")
        h.update(digests[resolved])
    return h.hexdigest()


def probe(path):
    result = subprocess.check_output(["ffprobe", "-v", "error", "-count_frames",
                                     "-show_streams", "-show_format", "-of", "json", str(path)])
    return json.loads(result)


def verify_media(path, n, size, fps, audio, final=False, captions=False):
    info = probe(path)
    streams = info["streams"]
    vs = [s for s in streams if s["codec_type"] == "video"]
    au = [s for s in streams if s["codec_type"] == "audio"]
    subs = [s for s in streams if s["codec_type"] == "subtitle" and s["codec_name"] == "mov_text"]
    require(len(vs) == 1 and len(au) == int(audio) and len(subs) == int(captions)
            and len(streams) == 1 + int(audio) + int(captions),
            f"{path}: unexpected streams")
    v = vs[0]
    require(int(v.get("nb_read_frames", 0)) == n, f"{path}: expected {n} decoded frames")
    require((v["width"], v["height"]) == size and Fraction(v["avg_frame_rate"]) == fps and
            v["codec_name"] == "h264" and v["pix_fmt"] == "yuv420p", f"{path}: wrong video format")
    require(abs(float(info["format"]["duration"]) - n / fps) <= 1 / fps,
            f"{path}: unexpected duration")
    if au:
        a = au[0]
        require(int(a["sample_rate"]) == RATE and a["channels"] == 2 and a["codec_name"] == "aac",
                f"{path}: wrong audio format")
        require(abs(float(a["duration"]) - n / fps) <= 1 / fps and
                abs(float(a["start_time"]) - float(v["start_time"])) <= 1 / fps,
                f"{path}: audio timeline does not match picture")
    if final:
        subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(path), "-f", "null", "-"],
                       check=True)
        print(f"Verified {path}: {n} frames, {size[0]}x{size[1]} at {fps} fps, "
              f"{n / fps:.3f}s, {'stereo AAC' if audio else 'no audio'}"
              + (", timed text" if captions else ""))


def render(spec, shot, indices, jobs, draft, key):
    size = (spec["width"], spec["height"])
    if draft:
        size = tuple(max(2, d // 4 * 2) for d in size)
    directory = Path("qa/drafts" if draft else f"out/{key}")
    directory.mkdir(parents=True, exist_ok=True)
    tag = f"{shot['id']}-{indices.start}-{indices.stop}" if draft else shot["id"]
    out = directory / f"{tag}.mp4"
    tmp = directory / f"{tag}.part.mp4"
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{size[0]}x{size[1]}", "-r", str(spec["fps"]), "-i", "-", "-an", "-c:v",
           "libx264", "-threads", "2", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p", str(tmp)]
    try:
        with subprocess.Popen(cmd, stdin=subprocess.PIPE) as p:
            with ProcessPoolExecutor(jobs, initializer=setup, initargs=(spec, shot)) as pool:
                pending = iter(indices)
                while batch := list(itertools.islice(pending, jobs * 2)):
                    for rgb in pool.map(pixels, batch, itertools.repeat(spec), itertools.repeat(size)):
                        p.stdin.write(rgb)
            p.stdin.close()
            require(p.wait() == 0, "shot encoder failed")
        verify_media(tmp, len(indices), size, spec["fps"], False)
        tmp.replace(out)
    finally:
        tmp.unlink(missing_ok=True)
    print(f"Rendered {out}: {len(indices)} frames")


def cue(kind, elapsed, noise):
    t = elapsed
    if kind == "tap":
        return math.sin(math.tau * 625 * t) * math.exp(-18 * t)
    if kind == "charge":
        return (.7 * math.sin(math.tau * (48 * t + 118 * t*t)) + noise * .23) * math.sin(math.pi * t / LENGTH[kind])
    if kind == "dash":
        return (noise * .6 + .4 * math.sin(math.tau * (290 * t - 240 * t*t))) * math.exp(-8 * t)
    if kind == "beam":
        return (.65 * math.sin(math.tau * (97 * t + 15 * t*t)) + .2 * math.sin(math.tau * 351 * t) +
                noise * .14) * math.exp(-2.5 * t)
    return (.62 * math.sin(math.tau * (95 * t - 49 * t*t)) + noise * .36) * math.exp(-6 * t)


def wav_timing(path, fps):
    try:
        with wave.open(path, "rb") as wav:
            return Fraction(wav.getnframes(), wav.getframerate()), 1
    except (wave.Error, EOFError):
        data = json.loads(subprocess.check_output([
            "ffprobe", "-v", "error", "-select_streams", "a:0",
            "-show_entries", "stream=codec_name,duration_ts,time_base,sample_rate", "-of", "json", path]))
        stream = data["streams"][0]
        if stream.get("duration_ts") in (None, "N/A"):
            return None, None
        unit = Fraction(stream["time_base"])
        exact = stream["codec_name"].startswith("pcm_") and unit * int(stream["sample_rate"]) == 1
        return int(stream["duration_ts"]) * unit, 1 if exact else Fraction(RATE, fps)


def decode_wav(path, fps):
    result = subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", path, "-map", "0:a:0",
                             "-ar", str(RATE), "-ac", "2", "-f", "s16le", "-"], capture_output=True)
    require(result.returncode == 0 and not result.stderr,
            f"external audio decode failed: {result.stderr.decode(errors='replace').strip() or result.returncode}")
    samples = array("h")
    samples.frombytes(result.stdout)
    duration, tolerance = wav_timing(path, fps)
    require(duration is None or abs(len(samples) // 2 - duration * RATE) <= tolerance,
            "external audio decoded sample count does not match the source duration")
    if sys.byteorder != "little":
        samples.byteswap()
    return samples


def soundtrack(spec, path):
    n = round(total(spec) * RATE / spec["fps"])
    pcm = array("f", [0]) * (2 * n)
    if "audio" in spec:
        samples = decode_wav(spec["audio"], spec["fps"])
        require(0 < len(samples) <= len(pcm), "external audio is empty or exceeds the timeline")
        for i, sample in enumerate(samples):
            pcm[i] = sample / 32768
    rng = random.Random(spec["seed"])
    for frame, e in events(spec):
        kind = e["sound"]
        start = round(frame * RATE / spec["fps"])
        pan = (e.get("pan", 0) + 1) * math.pi / 4
        left, right = math.cos(pan), math.sin(pan)
        gain = e.get("gain", .65)
        samples = min(round(LENGTH[kind] * RATE), n - start)
        for i in range(samples):
            t = i / RATE
            v = cue(kind, t, rng.uniform(-1, 1)) * gain * min(i / 96, 1, (samples - i) / 480)
            j = 2 * (start + i)
            pcm[j] += v * left
            pcm[j + 1] += v * right
    peak = max(map(abs, pcm), default=0)
    scale = 32767 * min(1, .92 / peak) if peak else 0
    data = array("h", (round(x * scale) for x in pcm))
    if sys.byteorder != "little":
        data.byteswap()
    with wave.open(str(path), "wb") as wav:
        wav.setparams((2, struct.calcsize("h"), RATE, 0, "NONE", "not compressed"))
        wav.writeframes(data.tobytes())


def assemble(spec, target, key):
    size = (spec["width"], spec["height"])
    fps = spec["fps"]
    directory = Path("out") / key
    clips = []
    for shot in spec["shots"]:
        p = directory / f"{shot['id']}.mp4"
        require(p.is_file(), f"missing or stale shot {shot['id']}; run render")
        verify_media(p, shot["frames"], size, fps, False)
        clips.append(p)
    listing = directory / "concat.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in clips), encoding="utf-8")
    has_audio = "audio" in spec or any(events(spec))
    has_caps = "captions" in spec
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "1", "-i", str(listing)]
    if has_audio:
        wav = directory / "soundtrack.wav"
        soundtrack(spec, wav)
        cmd += ["-i", str(wav)]
    target.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=target.parent, prefix=".assemble-") as scratch:
        tmp = Path(scratch) / target.name
        if has_caps:
            srt = Path(scratch) / "captions.srt"
            delivery.write_srt(srt, delivery.transcript(spec["captions"], total(spec)), fps)
            cmd += ["-i", str(srt)]
        cmd += ["-map", "0:v:0"]
        if has_audio:
            cmd += ["-map", "1:a:0", "-c:a", "aac", "-b:a", "160k"]
        if has_caps:
            cmd += ["-map", f"{1 + int(has_audio)}:s:0", "-c:s", "mov_text"]
        subprocess.run(cmd + ["-vf", f"setpts=N/({fps}*TB)", "-r", str(fps),
                              "-c:v", "libx264", "-threads", "4", "-preset", "fast", "-crf", "21",
                              "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(tmp)], check=True)
        verify_media(tmp, total(spec), size, fps, has_audio, captions=has_caps)
        tmp.replace(target)
    print(f"Assembled {target}")


def still(spec, shot, frames, sheet, safe_area=False):
    setup(spec, shot)
    dest = Path("qa") / shot["id"]
    dest.mkdir(parents=True, exist_ok=True)
    thumbs = []
    for f in frames:
        require(0 <= f < shot["frames"], f"still frame {f} is out of range")
        im = image(f, spec)
        if safe_area:
            im = delivery.guides(im)
        if sheet:
            thumb = im.copy()
            thumb.thumbnail((480, 270), Image.Resampling.LANCZOS)
            thumbs.append((f, thumb))
        else:
            im.save(dest / f"{f:04d}.png")
    if sheet:
        w, h = thumbs[0][1].size
        cols = min(3, len(thumbs))
        board = Image.new("RGB", (cols*w, math.ceil(len(thumbs) / cols)*(h+20)), "#151822")
        draw = ImageDraw.Draw(board)
        for i, (f, im) in enumerate(thumbs):
            x, y = i % cols * w, i // cols * (h+20)
            board.paste(im, (x, y))
            draw.text((x+5, y+h+3), f"{shot['id']} / frame {f}", fill="white")
        board.save(dest / "sheet.png")
    print(f"Stills: {dest}")


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--project", type=Path, default=Path("."))
    sub = cli.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    s = sub.add_parser("still")
    s.add_argument("shot")
    s.add_argument("frames", nargs="*", type=int)
    s.add_argument("--sheet", action="store_true")
    s.add_argument("--strip", help="half-open START:STOP[:STEP], written as a labeled sheet")
    s.add_argument("--safe-area", action="store_true")
    r = sub.add_parser("render")
    r.add_argument("--only")
    r.add_argument("--jobs", type=int, default=2)
    r.add_argument("--range", dest="span")
    r.add_argument("--draft", action="store_true")
    a = sub.add_parser("assemble")
    a.add_argument("--out", type=Path, default=Path("dist/animation.mp4"))
    v = sub.add_parser("verify")
    v.add_argument("file", type=Path)
    loop = sub.add_parser("loop")
    loop.add_argument("file", type=Path)
    loop.add_argument("--out", type=Path, required=True)
    for cmd in (v, loop):
        cmd.add_argument("--max-bytes", type=int, default=3_000_000)
        cmd.add_argument("--max-seam", type=float, default=12)
    args = cli.parse_args()
    os.chdir(args.project)
    sys.path[:0] = [str(Path.cwd()), str(TEMPLATE)]
    spec, assets = read_spec(check_inputs=args.command not in ("verify", "loop"))
    shots = {s["id"]: s for s in spec["shots"]}
    size = (spec["width"], spec["height"])
    has_audio = "audio" in spec or any(events(spec))
    has_caps = "captions" in spec
    if args.command == "validate":
        print(f"Valid: {len(shots)} shots, {total(spec)} frames, {total(spec) / spec['fps']:.3f}s")
    elif args.command == "still":
        shot = shots[args.shot]
        n = shot["frames"]
        frames = args.frames or sorted({0, n // 2, n - 1, *(e["frame"] for e in shot.get("events", []))})
        if args.strip:
            require(not args.frames, "use frames or --strip, not both")
            parts = [int(x) for x in args.strip.split(":")]
            require(len(parts) in (2, 3), "use START:STOP[:STEP]")
            frames = range(*parts)
            require(frames.step > 0 and frames and 0 <= frames.start < frames.stop <= n, "invalid strip range")
        still(spec, shot, frames, args.sheet or bool(args.strip), args.safe_area)
    elif args.command == "render":
        require(1 <= args.jobs <= 8, "--jobs must be between 1 and 8")
        require(not args.span or args.only and args.draft, "--range requires --only and --draft")
        key = None if args.draft else render_key(assets)
        for shot in ([shots[args.only]] if args.only else shots.values()):
            start, stop = map(int, args.span.split(":")) if args.span else (0, shot["frames"])
            require(0 <= start < stop <= shot["frames"], "invalid half-open frame range")
            render(spec, shot, range(start, stop), args.jobs, args.draft, key)
    elif args.command == "assemble":
        require(args.out.suffix == ".mp4" and args.out.parent.resolve().is_relative_to(Path("dist").resolve()),
                "output must be an MP4 under dist/")
        assemble(spec, args.out, render_key(assets))
    elif args.command == "loop":
        require(args.out.suffix in (".gif", ".webp"), "loop output must be GIF or WebP")
        verify_media(args.file, total(spec), size, spec["fps"], has_audio, captions=has_caps)
        delivery.export_loop(args.file, args.out, size, spec["fps"], total(spec), args.max_bytes, args.max_seam)
    elif args.file.suffix in (".gif", ".webp"):
        result = delivery.verify_loop(args.file, size, spec["fps"], total(spec), args.max_bytes, args.max_seam)
        print(f"Verified {args.file}: {result}")
    else:
        verify_media(args.file, total(spec), size, spec["fps"], has_audio, final=True, captions=has_caps)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, TypeError, KeyError, subprocess.CalledProcessError) as exc:
        sys.exit(f"Animation failed: {exc}")
