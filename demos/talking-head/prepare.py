"""Synthesize the original demo line locally with FFmpeg's bundled Flite filter."""

from pathlib import Path
import subprocess


if __name__ == "__main__":
    out = Path("assets/voice.wav")
    out.parent.mkdir(exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                    "flite=text=Blue skies ahead.:voice=slt", "-af", "adelay=167,apad",
                    "-t", "2.25", "-ar", "48000", str(out)], check=True)
