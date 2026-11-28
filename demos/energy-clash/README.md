# Canyon Clash

An anime power-clash homage made entirely from code. Iri Moss is a teal-haired monk in slate and sage robes, with a staff slung across their back. Korr Flint is a broad, crimson-skinned brawler with curved horns, a scar, and an armored vest. Both fighters, their costumes, and the setting were created for this scene.

Generate the render and contact sheets locally with the commands below. Share media as attachments or release assets; do not commit it.

**Brief:** Make a ten-second, widescreen 1080p/24 fps anime action clip with no dialogue. Telegraph who is on each side, give the dash a clear direction, let the opposing beams meet visibly, then reveal the outcome. Audio is procedural stereo.

| Shot | Time | Beat |
|---|---:|---|
| Face-off | 0–3 s | Canyon geography and silhouettes; blue and gold auras build. |
| Rush | 3–5 s | Korr drives left across the frame; Iri braces and gathers energy. |
| Clash | 5–8 s | Both fire; the contact point strains and flashes. |
| Aftermath | 8–10 s | Dust parts and both fighters land back in their stances. |

## Reproduce

From the repository root, with Python 3.10+ and FFmpeg/ffprobe on PATH:

    python -m pip install -r demos/energy-clash/requirements.txt
    CLI=skills/code-animation/templates/project/tools/animate.py
    PROJECT=demos/energy-clash
    python "$CLI" --project "$PROJECT" validate
    for shot in faceoff rush clash aftermath; do
        python "$CLI" --project "$PROJECT" still "$shot" --sheet
    done
    python "$CLI" --project "$PROJECT" render --only clash --range 8:30 --draft
    python "$CLI" --project "$PROJECT" render --jobs 4
    python "$CLI" --project "$PROJECT" assemble --out dist/canyon-clash.mp4
    python "$CLI" --project "$PROJECT" verify dist/canyon-clash.mp4

The shot sheets and draft are written under the project's ignored qa/ directory.
