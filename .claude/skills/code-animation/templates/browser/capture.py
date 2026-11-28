"""Capture one local browser scene PNG per explicitly requested frame."""

import argparse
from hashlib import sha256
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from playwright.sync_api import sync_playwright


def capture(args):
    args.out.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=args.out.parent, prefix=".capture-") as temp, sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.chromium)
        page = browser.new_page(viewport={"width": args.width, "height": args.height},
                                device_scale_factor=1, reduced_motion="reduce")
        page.goto(args.page.resolve().as_uri(), wait_until="load")
        page.evaluate("""async () => {
            if (!Array.isArray(window.captureFonts) || !window.captureFonts.length)
                throw Error("declare captureFonts");
            const results = await Promise.all(captureFonts.map(font => document.fonts.load(font)));
            await document.fonts.ready;
            if (!results.every(faces => faces.length && faces.every(face => face.status === "loaded"))
                || !captureFonts.every(font => document.fonts.check(font)))
                throw Error("capture fonts are not ready");
        }""")
        loaded = page.evaluate("captureFonts")
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        def frame(f):
            page.evaluate("(n) => window.setFrame(n)", f)
            return page.screenshot(animations="disabled", caret="hide", scale="css")

        hashes = {}
        samples = {0, args.frames // 2, args.frames - 1}
        first = None
        has_motion = False
        for f in range(args.frames):
            png = frame(f)
            (Path(temp) / f"{f:04d}.png").write_bytes(png)
            digest = sha256(png).digest()
            if f == 0:
                first = digest
            elif digest != first:
                has_motion = True
            if f in samples:
                hashes[f] = digest
        for f in sorted(samples, reverse=True):
            if hashes[f] != sha256(frame(f)).digest():
                raise ValueError(f"frame {f} changed when captured out of order")
        if args.frames > 1 and not has_motion:
            raise ValueError("all captured frames are identical")
        if errors:
            raise ValueError("; ".join(errors))
        browser.close()
        filenames = sorted(Path(temp).glob("*.png"))
        for old in args.out.glob("*.png"):
            if old.is_file() and re.fullmatch(r"(?:[0-9]{4}|[1-9][0-9]{4,})\.png", old.name):
                old.unlink()
        for f in filenames:
            f.replace(args.out / f.name)
    print(f"Captured {args.frames} frames at {args.width}x{args.height}; fonts ready: {', '.join(loaded)}; seek check passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("page", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--frames", type=int, required=True)
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--height", type=int, required=True)
    parser.add_argument("--chromium")
    args = parser.parse_args()
    if min(args.frames, args.width, args.height) <= 0:
        parser.error("frame count and dimensions must be positive")
    capture(args)
