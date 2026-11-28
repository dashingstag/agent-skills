# Orbital

A 9:16 animated orbit with launch-platform-agnostic 5% / 10% guide lines for stills. Frame 40 would repeat frame 0; only frames 0–39 are exported. The GIF and animated WebP are silent.

Generate the render and contact sheets locally with the commands below. Share media as attachments or release assets; do not commit it.

From this demo directory, set the template path and use a Python environment with the project template's requirements:

```sh
T=../../skills/code-animation/templates
A=$T/project/tools/animate.py
python "$A" validate
python "$A" render --jobs 2
python "$A" assemble --out dist/vertical-loop.mp4
python "$A" verify dist/vertical-loop.mp4
python "$A" still orbit --sheet
mv qa/orbit/sheet.png qa/orbit/contact.png
python "$A" still orbit --sheet --safe-area
python "$A" loop dist/vertical-loop.mp4 --out dist/vertical-loop.webp --max-seam 2
python "$A" loop dist/vertical-loop.mp4 --out dist/vertical-loop.gif --max-seam 2
```
