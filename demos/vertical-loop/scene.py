import math

from PIL import ImageDraw

from lib.graphics import gradient, label


def setup(spec, shot):
    w,h = spec["width"],spec["height"]
    base = gradient((w,h),"#1b2743","#473357")
    d = ImageDraw.Draw(base)
    center = (w/2,h/2)
    for radius in (62,85,111):
        x,y = center
        d.ellipse((x-radius,y-radius,x+radius,y+radius),outline="#78718d",width=1)
    label(d,(w/2,91),"ORBITAL",31,"#f9d099",anchor="mm")
    label(d,(w/2,119),"A   P E R I O D I C   L O O P",12,"#b9bad1",anchor="mm")
    label(d,(w/2,414),"01  /  REVOLUTION",14,"#f6c9a0",anchor="mm")
    for i in range(18):
        a = i*math.tau/18
        x,y = center[0]+111*math.cos(a),center[1]+111*math.sin(a)
        d.ellipse((x-2,y-2,x+2,y+2),fill="#aaa0b6")

    def frame(f):
        im = base.copy()
        d = ImageDraw.Draw(im)
        t = math.tau*f/shot["frames"]
        for i in range(9,-1,-1):
            a = t-i*.09
            x,y = center[0]+84*math.cos(a),center[1]+84*math.sin(a)
            r = 10-i*.76
            d.ellipse((x-r,y-r,x+r,y+r), fill="#ffe3a4" if i == 0 else "#bf708b")
        x,y = center[0]+29*math.cos(-t),center[1]+29*math.sin(-t)
        d.ellipse((x-5,y-5,x+5,y+5),fill="#86c3c0")
        return im
    return frame
