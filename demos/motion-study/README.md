# Through the Pass

Pan, zoom and shake the ridge layers behind a moving craft. Two shots demonstrate a wipe, a matched-color cut on the craft's motion and a dissolve to the end title. The wipe and end title occupy explicit frame ranges within the second shot.

Generate the render and contact sheets locally with the commands below. Share media as attachments or release assets; do not commit it.

From this demo directory, set the template path and use a Python environment with the project template's requirements:

```sh
T=../../skills/code-animation/templates
A=$T/project/tools/animate.py
python "$A" validate
python "$A" render --jobs 2
python "$A" assemble --out dist/motion-study.mp4
python "$A" verify dist/motion-study.mp4
python "$A" still approach --sheet
python "$A" still velocity 0 5 11 22 23 30 41 --sheet
```
