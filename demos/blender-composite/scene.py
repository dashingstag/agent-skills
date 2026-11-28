from pathlib import Path

from PIL import Image, ImageDraw

from lib.graphics import gradient, label


def setup(spec, shot):
    size = spec["width"],spec["height"]
    base = gradient(size,"#172838","#465976").convert("RGBA")
    d = ImageDraw.Draw(base)
    for x in range(18,480,16):
        for y in range(19,270,16):
            d.point((x,y),fill="#698496")
    d.ellipse((151,53,332,232),outline="#728b9b",width=1)
    d.line((241,130,439,130),fill="#728b9b",width=1)
    label(d,(19,22),"THE TIDAL RELIC",24,"#ffd7a4")
    label(d,(19,54),"FIELD ARCHIVE  /  OBJECT 03",11,"#c5d9e6")

    def frame(f):
        im = base.copy()
        with Image.open(Path("cache/relic") / f"{f:04d}.png") as layer:
            if layer.mode != "RGBA" or layer.size != size:
                raise ValueError("expected the declared transparent Blender sequence")
            im.alpha_composite(layer)
        d = ImageDraw.Draw(im)
        d.line((19,241,460,241),fill="#7290a0",width=1)
        label(d,(20,253),"PROCEDURAL GEOMETRY   +   2D GRAPHICS",10,"#dae6e7")
        label(d,(459,253),f"{f+1:02}/{shot['frames']:02}",10,"#ffd7a4",anchor="ra")
        return im.convert("RGB")
    return frame
