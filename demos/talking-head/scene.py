import json
from pathlib import Path

from PIL import ImageDraw

from lib.graphics import gradient, label
from lib.rig import draw_rig, viseme_at


def setup(spec, shot):
    track = json.loads(Path("visemes.json").read_text())

    def frame(f):
        im = gradient((spec["width"],spec["height"]),"#28394f","#527d77")
        d = ImageDraw.Draw(im)
        d.ellipse((169,39,471,341),fill="#608c81")
        d.ellipse((184,54,456,326),outline="#89aaa3",width=2)
        draw_rig(im,(320,211),2.35,mouth=viseme_at(track,shot["frames"],f))
        label(d,(25,24),"FIELD RADIO",29,"#ffe2a7")
        label(d,(27,67),"MILO  /  01",15,"#dce9c9")
        d.rounded_rectangle((481,31,610,63),radius=16,fill="#1d3745")
        d.ellipse((494,41,505,52),fill="#f0877e")
        label(d,(558,46),"ON AIR",15,"#ffdea4",anchor="mm")
        return im
    return frame
