# Ember Weather

Deterministic dust, sparks and snow are rendered as separate seeded layers. Dust uses over, sparks use add and snow uses screen. The six consecutive frames show short-term motion rather than just sparse layout samples.

Generate the render and contact sheets locally with the commands below. Share media as attachments or release assets; do not commit it.

From this demo directory, set the template path and use a Python environment with the project template's requirements:

```sh
T=../../skills/code-animation/templates
A=$T/project/tools/animate.py
python "$A" validate
python "$A" render --jobs 2
python "$A" assemble --out dist/weather-effects.mp4
python "$A" verify dist/weather-effects.mp4
python "$A" still embers --sheet
mv qa/embers/sheet.png qa/embers/contact.png
python "$A" still embers --strip 17:23
```
