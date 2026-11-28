from PIL import ImageDraw

from lib.effects import Emitter, composite
from lib.graphics import gradient, label


def setup(spec, shot):
    size = spec["width"], spec["height"]
    base = gradient(size,"#121b2c","#3b4e61")
    d = ImageDraw.Draw(base)
    d.polygon([(0,205),(113,104),(213,198),(373,88),(553,204),(640,151),(640,360),(0,360)],fill="#213149")
    d.polygon([(0,273),(131,238),(287,276),(463,221),(640,259),(640,360),(0,360)],fill="#152536")
    d.ellipse((247,215,412,301),fill="#342c3b")
    d.ellipse((279,235,373,284),fill="#644041")
    d.ellipse((305,250,350,269),fill="#d8734f")
    d.line((303,270,349,255),fill="#f79264",width=4)
    layers = [(Emitter(kind,size,spec["seed"]+i,shot["frames"],rate),color,mode)
              for i,(kind,rate,color,mode) in enumerate([
                  ("dust",5,(140,99,129),"over"),("sparks",4,(245,130,70),"add"),("snow",5,(154,203,218),"screen")])]
    label(d,(24,26),"EMBER WEATHER",33,"#ffca95")
    label(d,(26,68),"SNOW / DUST / SPARKS",15,"#bacfd2")

    def frame(f):
        im = base
        for emitter, color, mode in layers:
            im = composite(im,emitter.layer(f,color),mode)
        return im.convert("RGB")
    return frame
