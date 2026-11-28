# Code animation project

- Set `"aspect": "16:9"`, `"9:16"` or `"1:1"` for a default canvas, or also set an even custom width and height of that ratio. `still intro 0 --safe-area` draws 5% / 10% guide boxes in QA images only.
- `still intro --strip 4:10` writes six consecutive labeled frames to `qa/intro/sheet.png`. For a loop, use `loop dist/animation.mp4 --out dist/animation.webp --max-seam 12` (or `.gif`); `verify` accepts both extensions. The seam score is mean decoded RGB change from last to first on a 0–255 scale, not a substitute for visual playback. `--max-bytes` defaults to 3,000,000. Both loop formats are silent.
- For a captured shot, replace `renderer` with `"sequence": "cache/capture"` and supply all zero-based PNGs at the manifest resolution. A Python renderer can instead specify `"input_sequences": ["cache/pass"]` alongside `renderer`, and composite the RGBA PNGs itself.
- `"audio": "assets/voice.wav"` mixes a project-local WAV from time zero with any procedural cues. Short audio is padded; over-long audio is rejected. `"captions": "captions.json"` reads a JSON list of `{"start": 9, "end": 34, "text": "Blue skies ahead."}` (global, end-exclusive frame ranges), builds SRT and muxes a selectable timed-text track in MP4. Mouth-pose keys are shot-local.

Install Python 3.10+, FFmpeg and ffprobe (including libx264), then install the pinned Python requirements in a virtual environment. Run from this directory:

```sh
python -m pip install -r requirements.txt
python tools/animate.py validate
python tools/animate.py still intro 0 24 47 --sheet
python tools/animate.py render --only intro --range 20:40 --draft
python tools/animate.py render --jobs 2
python tools/animate.py assemble --out dist/animation.mp4
python tools/animate.py verify dist/animation.mp4
```

## Example brief

Make a four-second geometric logo-free bumper: a tile arrives, then a ring resolves the motion. 640×360, 24 fps, wide video. A pulse in the second shot is marked by one synthesized tap. All shapes and sound are generated from code.

## Start a new project

Copy the scaffold into your project directory. In `animation.json`, set a positive integer `fps`, an integer `seed`, and positive, even integer `width` and `height` (or select an `aspect` preset). List at least one shot in playback order. Each shot needs a unique `id` matching `[a-z][a-z0-9_-]*`, a positive integer `frames`, a nonempty `intent`, and either a Python `renderer` or a numbered PNG `sequence`. Events and assets are optional. Each event has an `id` unique within its shot, a zero-based local `frame`, and a nonempty `kind`.

For example, replace the bumper shots with this manifest and save the renderer below as `shots/marker.py`:

```json
{
  "width": 640, "height": 360, "fps": 24, "seed": 6,
  "shots": [
    {"id": "marker", "frames": 24, "intent": "A square crosses the canvas", "renderer": "shots/marker.py"}
  ]
}
```

```python
from PIL import Image, ImageDraw


def setup(spec, shot):
    size = spec["width"], spec["height"]

    def frame(n):
        im = Image.new("RGB", size, "midnightblue")
        x = n * (size[0] - 32) // max(1, shot["frames"] - 1)
        ImageDraw.Draw(im).rectangle((x, 150, x + 31, 181), fill="gold")
        return im

    return frame
```

In the commands above, replace `intro` with your shot ID and choose still indices in `0..frames-1`. For the example, use `still marker 0 12 23 --sheet` and `render --only marker --range 0:12 --draft`; the draft range excludes its end. Append another shot entry to make a two-shot scene.

Each shot's `renderer` names a project-relative Python file; `setup(spec, shot)` returns a function from local frame index to a Pillow RGB image matching the canvas. Use `shots/` for renderers, `lib/` for reusable code, and `assets/` for inputs. The render key includes project source and every declared asset. The source scan skips hidden files, Python environments and bytecode caches, and the generated directories at the project root.

The CLI supports optional procedural cue sounds `tap`, `charge`, `dash`, `beam`, and `impact`. Add an event's `sound` field to enable a cue; add `gain` (0–1) and `pan` (-1–1) to adjust it. Frame timing uses the manifest clock. An event without sound is a visual marker. For richer audio, author separate stems against these same event positions and use an appropriately tested mux workflow.

`verify` and `loop` read the manifest and encoded media only. Regenerate inputs such as captures or WAVs before using `validate`, `still`, `render`, or `assemble`. Captions are plain text: blank lines within cues are removed, and angle brackets are rejected.

Keep generated media under ignored output directories. Share verified renders as attachments or release assets, not Git commits.
