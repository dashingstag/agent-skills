---
name: code-animation
description: Create reproducible animation from code, from a UI loop or data explainer to a cinematic scene. Use when asked to animate a brief, storyboard, simulation, or design and deliver runnable source, a preview, or an encoded render.
---

# Code Animation

1. **Define the deliverable.** Record audience, visible action, platform and format, duration or loop, canvas, style, text, and audio in the project README. Ask only questions that change the delivery; otherwise state assumptions. Match the source project's stack when it fits. Default video to 1080p at 24 fps and silence unless sound serves the brief.
2. **Storyboard the changes.** List beats and what the viewer should notice. Break them into shots with frame budgets and clearly distinguish anticipation, action, and reaction. Pick one risky composition to preview first. For character work, resolve silhouettes and screen direction before adding effects.
3. **Choose a renderer.** Copy `templates/project/` as the export scaffold and use the routing table below. Prefer native browser output for interaction, and keep the rebuildable source with the captured export.
4. **Author the timeline.** In `animation.json`, each shot has an ID, intent, length, renderer, and optional assets and zero-based local events. Global start is the sum of preceding shot lengths. Each Python renderer exposes `setup(spec, shot)` returning `frame(local_frame)`, a Pillow RGB image. Seed stochastic elements from the project and shot; make frames independent of evaluation order. Keep shared drawing in reusable modules. Put asset sources in the project's README.
5. **Review before full render.** Run `validate`, make a labeled contact sheet of start, middle, end, and event frames, and render a short range around the riskiest action. Check readability at delivery size, continuity, and framing. Keep preview outputs separate from assembly inputs.
6. **Deliver and verify.** Render full shots, then assemble in manifest order; run `verify`. Watch the final encode through cuts and loop seams. For sound, compare the planned and audible accent near the beginning, middle, and end; listen for clipping, masking, and truncation. Review captions when present. For web output, exercise the actual controls and playback in the target browser.
7. **Hand off.** Commit editable source and reproduction commands, not generated media. Deliver videos and QA sheets as attachments or release assets, and note any unverified checks. If time or memory fails, limit workers or use a draft range first. If stale render inputs are rejected, rerender rather than bypassing verification.

| If the scene needs… | Start with… |
|---|---|
| Camera moves, parallax, wipes, matched cuts or dissolves | Python scaffold + `lib/motion.py` |
| Animated type, charts or scripted UI | `templates/browser/` SVG/Canvas + captured `sequence` |
| Consistent original characters, poses or walks | `lib/rig.py` + `lib/model_sheet.py` |
| Vertical/square framing or an animated loop | Aspect preset, `still --safe-area`, then `loop` |
| Voice, captions or lip-sync | External WAV, timed transcript, and shot-local visemes |
| Snow, sparks, dust or blended layers | `lib/effects.py` + `still --strip` |
| Real photo or footage with a graphic overlay | `lib/footage.py` + explicit FPS conversion and tracking |
| True depth or 3D mixed with 2D | `templates/blender/` + PNG sequence compositing |

See the [scaffold commands](templates/project/README.md), [renderer recipes](references/backends.md) and [scene technique checklist](references/scene-techniques.md).
