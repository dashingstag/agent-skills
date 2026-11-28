# Small Signals

A fictional dataset revealed with SVG bars and animated type; Canvas draws the background and progress rule. Capture uses numbered frame indices, not wall time. Install DejaVu Sans regular and bold, plus the browser requirements. Install Chromium with Playwright, or add `--chromium /path/to/chromium` below.

Generate the render and contact sheets locally with the commands below. Share media as attachments or release assets; do not commit it.

From this demo directory, set the template path and use a Python environment with the project template's requirements:

```sh
T=../../skills/code-animation/templates
A=$T/project/tools/animate.py
python -m pip install -r "$T/browser/requirements.txt"
python -m playwright install chromium
python "$T/browser/capture.py" "$T/browser/index.html" --out cache/browser --width 640 --height 360 --frames 64
python "$A" validate
python "$A" render --jobs 2
python "$A" assemble --out dist/browser-explainer.mp4
python "$A" verify dist/browser-explainer.mp4
python "$A" still chart --sheet
```
