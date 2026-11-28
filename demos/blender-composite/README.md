# The Tidal Relic

An original procedural mesh and two rings spin under colored lights. Blender renders transparent PNGs, then the Python scene composites the pass between 2D layers. Use the official Blender build with working OpenColorIO; this was tested on 3.6.23.

Generate the render and contact sheets locally with the commands below. Share media as attachments or release assets; do not commit it.

From this demo directory, set the template path and use a Python environment with the project template's requirements:

```sh
T=../../skills/code-animation/templates
A=$T/project/tools/animate.py
blender -b -noaudio --python-exit-code 1 --python "$T/blender/scene.py" -- --out cache/relic
python "$A" validate
python "$A" render --jobs 2
python "$A" assemble --out dist/blender-composite.mp4
python "$A" verify dist/blender-composite.mp4
python "$A" still relic --sheet
```
