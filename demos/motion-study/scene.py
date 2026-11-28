from PIL import Image, ImageDraw

from lib.graphics import gradient, label
from lib.motion import Camera, ease, keyframes, transition


def setup(spec, shot):
    size = spec["width"], spec["height"]
    sky = gradient(size, "#17223c", "#8f526c").convert("RGBA")
    ImageDraw.Draw(sky).ellipse((352,45,439,132), fill="#ffd399")
    ridge = Image.new("RGBA",size)
    ImageDraw.Draw(ridge).polygon([(0,175),(107,100),(177,170),(319,88),(460,158),(640,108),(640,360),(0,360)],fill="#3a355e")
    foreground = Image.new("RGBA",size)
    d = ImageDraw.Draw(foreground)
    d.polygon([(0,240),(166,209),(316,235),(640,205),(640,360),(0,360)], fill="#182e44")
    d.rectangle((0,245,640,360),fill="#182e44")
    for x in range(-50,700,80):
        d.line((x,260,x+68,256), fill="#637087", width=2)

    def stage(f):
        pan = keyframes([(0,(0,0)),(29,(-23,0)),(39,(-30,0))], f)
        cam = Camera(pan,1 + ease(f/39)*.16,2*ease((f-24)/10),f)
        im = sky.copy()
        for layer, depth in ((ridge,.35),(foreground,1)):
            im.alpha_composite(cam.layer(layer,depth))
        ImageDraw.Draw(im).rectangle((0,300,640,360),fill="#182e44")
        x = 80 + f*10
        d = ImageDraw.Draw(im)
        d.polygon([(x,224),(x+60,215),(x+44,239),(x-7,240)],fill="#f7b97e")
        d.line((x-40,228,x-4,226),fill="#ef84a3",width=3)
        return im.convert("RGB")

    def close(f, reverse=False):
        im = gradient(size,"#222c4f","#525175") if reverse else gradient(size,"#301e3f","#6a324f")
        d = ImageDraw.Draw(im)
        for i in range(13):
            y = 90+i*16
            x = (i*41+f*12)%200
            d.line((x,y,640,y-36),fill="#87526d",width=2)
        x = 225+4*f
        d.polygon([(x-90,237),(x+152,186),(x+53,256),(x-110,259)],fill="#f7b97e")
        d.polygon([(x-20,218),(x+59,197),(x+46,218)],fill="#ffecd3")
        label(d,(35,38),"02 / VELOCITY",24,"#ffdec0")
        return im

    def frame(f):
        if shot["id"] == "approach":
            im = stage(f)
            label(ImageDraw.Draw(im),(35,38),"01 / THE RIDGE",24,"#ffdec0")
            return im
        if f < 11:
            im = transition(stage(39+f),close(f),f/10,"wipe")
        elif f < 24:
            im = transition(close(f),close(f, reverse=True),(f-11)/12,"cut-on-action",action=1)
        else:
            alt = gradient(size,"#1b283e","#715a79")
            d = ImageDraw.Draw(alt)
            label(d,(320,158),"THROUGH THE PASS",39,"#ffe1ad",anchor="mm")
            label(d,(320,206),"A STUDY IN PARALLAX",17,"#e9b5a1",anchor="mm")
            im = transition(close(f, reverse=True),alt,(f-24)/12,"crossfade")
        return im
    return frame
