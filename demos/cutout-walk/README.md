# Milo / Field Notes

An original geometric cutout walks in and waves. The reference board records the silhouette, mirrored and back views, expressions and color palette. This simple rig animates angles, not ground-aware inverse kinematics.

Generate the render and contact sheets locally with the commands below. Share media as attachments or release assets; do not commit it.

From this demo directory, set the template path and use a Python environment with the project template's requirements:

```sh
T=../../skills/code-animation/templates
A=$T/project/tools/animate.py
python "$A" validate
python "$A" render --jobs 2
python "$A" assemble --out dist/cutout-walk.mp4
python "$A" verify dist/cutout-walk.mp4
python "$A" still greeting --sheet
PYTHONPATH="$T/project" python scene.py
```
