from PIL import Image, ImageDraw

from lib.graphics import gradient, label
from lib.model_sheet import model_sheet
from lib.motion import ease, mix
from lib.rig import draw_rig, walk


def setup(spec, shot):
    size = spec["width"], spec["height"]

    def frame(f):
        im = gradient(size,"#254457","#547778")
        d = ImageDraw.Draw(im)
        d.ellipse((406,48,470,112),fill="#ebd0a3")
        d.polygon([(0,239),(120,175),(205,206),(352,152),(523,225),(640,194),(640,360),(0,360)],fill="#385f64")
        d.rectangle((0,280,640,360),fill="#213e4b")
        for x in range(20,640,72):
            d.line((x,302,x+23,302),fill="#5b7a7e",width=2)
        x = 136 + min(f,37)*7.2
        t = ease((f-37)/9)
        pose = mix(walk(min(f,37)/18),(-119,-14,13,-22,4,6,-7,8),t)
        d.ellipse((x-41,270,x+41,287),fill="#16303d")
        draw_rig(im,(x,146),1.24,pose,"joy" if f >= 40 else "calm")
        label(d,(29,25),"MILO / FIELD NOTES",26,"#ffdaa3")
        label(d,(30,61),"01   /   WALK  +  GREETING",15,"#d0e9df")
        return im
    return frame


if __name__ == "__main__":
    def expression(im, pos, name):
        portrait = Image.new("RGBA", (80,58))
        draw_rig(portrait,(40,55),.86,expression=name)
        im.paste(portrait,(pos[0]-40,pos[1]-45),portrait)

    model_sheet("Milo",lambda im,pos,view: draw_rig(im,pos,.95,view=view),expression,
                [("#162e38","Ink"),("#e68e4c","Coat"),("#ffcf79","Trim"),
                 ("#ca825f","Skin"),("#68bab2","Cap")]).save("dist/model-sheet.png")
