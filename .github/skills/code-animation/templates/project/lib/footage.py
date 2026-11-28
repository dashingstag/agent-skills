"""Explicit integer-FPS conversion and reference tracking for footage plates."""

from fractions import Fraction
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from PIL import Image

from lib.motion import keyframes


def video_frames(path, *, source_fps, fps, size, frames):
    info = json.loads(subprocess.check_output([
        "ffprobe","-v","error","-select_streams","v","-show_frames",
        "-show_entries","stream=width,height,avg_frame_rate,time_base,duration:"
        "stream_tags=rotate:stream_side_data_list:frame=best_effort_timestamp",
        "-of","json",str(path)]))
    if len(info["streams"]) != 1:
        raise ValueError("plate must contain a single video track")
    s = info["streams"][0]
    rotation = Fraction(next((d["rotation"] for d in s.get("side_data_list", []) if "rotation" in d),
                             s.get("tags", {}).get("rotate", 0)))
    if rotation % 90:
        raise ValueError("normalize non-quarter-turn plate rotation before import")
    display_size = (s["height"], s["width"]) if rotation % 180 else (s["width"], s["height"])
    times = [int(f["best_effort_timestamp"]) for f in info.get("frames", [])]
    duration = Fraction(len(times), source_fps)
    unit = Fraction(s["time_base"])
    reported_duration = s.get("duration")
    if (Fraction(s["avg_frame_rate"]) != source_fps or duration != Fraction(frames,fps)
            or (reported_duration not in (None, "N/A")
                and abs(Fraction(reported_duration)-duration) > Fraction(1, source_fps))
            or any(abs((stamp-times[0])*unit - Fraction(i,source_fps)) > unit
                   for i, stamp in enumerate(times))
            or display_size != size):
        raise ValueError("plate fps, duration, or canvas does not match its declaration")
    with TemporaryDirectory() as scratch:
        result = Path(scratch)
        subprocess.run(["ffmpeg","-v","error","-xerror","-i",str(path),"-vf",
                        f"fps={fps}:round=near","-an","-threads","1","-start_number","0",
                        str(result / "%04d.png")], check=True)
        paths = sorted(result.glob("*.png"))
        if len(paths) != frames:
            raise ValueError(f"converted plate has {len(paths)} frames, expected {frames}")
        result = []
        for p in paths:
            with Image.open(p) as frame:
                if frame.size != size:
                    raise ValueError(f"decoded plate frame {p.name} has size {frame.size}, expected {size}")
                result.append(frame.convert("RGB"))
        return result


def track(keys, frame):
    return keyframes(keys, frame, curve=lambda t: t)
