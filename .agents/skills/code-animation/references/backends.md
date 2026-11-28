# Renderer recipes

Keep the brief, ordered shot spec, local frame numbering, and QA gates regardless of renderer. The CLI runs Python/Pillow shots or imports numbered PNG sequences. Keep generated frames and renders local; share final media as attachments or release assets, never as Git commits.

| Request | Approach | Preview and delivery |
|---|---|---|
| Raster illustration, procedural effects, compositing | Python/Pillow; add NumPy or Cairo only as needed. Render at integer frame indices; put static artwork in setup. | Use the scaffold tools. H.264/AAC MP4 is the default; use an alpha-capable codec or PNG sequence when the brief needs transparency. |
| UI, typography, charts, responsive or interactive graphics | SVG/CSS or Canvas. For capture, expose a deterministic `setFrame(n)`; wait for fonts/asset loads and capture frames at fixed size, not real-time screenshots. | Deliver the running component/page for interaction. For video, export a numbered lossless image sequence, then encode with FFmpeg at the manifest rate. Check the target viewport and reduced-motion behavior where applicable. |
| True depth, camera moves, lighting, rigged 3D | Blender, with cameras and shot ranges defined by the manifest. Set FPS and resolution, pin render engine/settings, and convert zero-based local indices to Blender's frame range. | Render one representative still first. For a 32-frame shot starting at frame zero, run `blender -b scene.blend -o //frames/#### -F PNG -s 0 -e 31 -a`. This writes `frames/0000.png` through `frames/0031.png` beside the blend file; replace 31 with the shot frame count minus one. |

Set `"sequence": "cache/browser"` instead of `"renderer"` for a full RGB shot. Name frames `0000.png`, `0001.png`, etc. For RGBA passes composited by a renderer, declare `"input_sequences": ["cache/pass"]` on the shot so changes invalidate the render key.

## Browser capture

Set `SKILL` to the absolute path of the directory containing this skill's `SKILL.md`; the browser and Blender commands below use it. Install `python -m pip install -r "$SKILL/templates/browser/requirements.txt"`, then run `python -m playwright install chromium` (or pass `--chromium` pointing at an installed executable). The example page requires both DejaVu Sans Regular and DejaVu Sans Bold installed on the machine. From the project directory:

```sh
python "$SKILL/templates/browser/capture.py" "$SKILL/templates/browser/index.html" \
  --out cache/browser --width 640 --height 360 --frames 64
```

Declare the font queries in `window.captureFonts`, or use an empty array for a font-free scene. Bundle or pin any fonts you need; a failed font load is an error. Implement `setFrame(n)` so it sets the entire state and returns only after synchronous drawing or an awaited draw completes. Do not depend on wall time, transitions or previous frames. The capture script checks a sample in reverse order and warns if every frame is identical; pass `--require-motion` when a static result should fail. For an actual screen recording, start from the footage recipe.

## Photo and footage

Record creator, license or generation command and source FPS. Place photos on the canvas before compositing. For short footage plates, `lib.footage.video_frames` checks declared dimensions, integer source FPS and expected duration, then uses FFmpeg's `fps` filter to duplicate/drop into the target timeline. Trim, retime or resize upstream explicitly if the plate doesn't match. Log the conversion and verify tracking after conversion against the source. Normalize tagged footage to an agreed SDR space first; compare untouched patches against the normalized source and view the overlay over bright and dark edges.

## Blender and mixed media

The runnable example uses CPU Cycles and was tested with the official Blender 3.6.23 build. Prefer a build with bundled OpenColorIO configuration; Ubuntu Jammy's Blender 3.0.1 package used a broken fallback and output black opaque PNGs in our test. Preview one frame when changing geometry or lighting; render the transparent pass with:

```sh
blender -b -noaudio --python-exit-code 1 --python "$SKILL/templates/blender/scene.py" -- \
  --out cache/relic --width 480 --height 270 --fps 16 --frames 32
```

Use zero-based local frames and keep straight RGBA while compositing over the background; add foreground elements after the 3D pass. Check transparency, color and edge halos; then use the same render, assembly and verification commands as ordinary 2D shots.
