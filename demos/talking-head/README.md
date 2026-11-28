# Field Radio

Original line, “Blue skies ahead,” synthesized locally with FFmpeg's bundled Flite filter (voice `slt`). Waveform-based onset and rest timing bounds the hand-authored visemes; it is not phoneme alignment. Enable the selectable captions in the MP4 player.

Generate the render and contact sheets locally with the commands below. Share media as attachments or release assets; do not commit it.

From this demo directory, set the template path and use a Python environment with the project template's requirements:

```sh
T=../../skills/code-animation/templates
A=$T/project/tools/animate.py
python prepare.py
python "$A" validate
python "$A" render --jobs 2
python "$A" assemble --out dist/talking-head.mp4
python "$A" verify dist/talking-head.mp4
python "$A" still message 0 9 12 18 24 32 40 --sheet
ffmpeg -v error -i dist/talking-head.mp4 -map 0:s:0 -f srt -
```
