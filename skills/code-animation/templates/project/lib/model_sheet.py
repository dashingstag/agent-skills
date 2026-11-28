"""Reference board for consistent cutout characters."""

from PIL import Image, ImageDraw

from lib.graphics import label


def model_sheet(name, pose, expression, palette):
    im = Image.new("RGB",(740,520),"#284854")
    d = ImageDraw.Draw(im)
    label(d,(33,21),name.upper()+" / MODEL SHEET",30,"#ffcf91")
    for i,(heading,view) in enumerate((("FRONT",1),("MIRRORED",-1),("BACK",0))):
        x = 136+i*234
        d.rectangle((x-96,76,x+96,316),fill="#355968")
        d.line((x-96,273,x+96,273),fill="#66848d")
        pose(im,(x,169),view)
        label(d,(x,335),heading,17,"#d6ebe1",anchor="mm")
    for i,name in enumerate(("calm","joy","wonder")):
        x = 136+i*234
        expression(im,(x,414),name)
        label(d,(x,452),name.upper(),14,"#ffcf91",anchor="mm")
    for i,(color,name) in enumerate(palette):
        x = 22+i*int(695/len(palette))
        d.rectangle((x,480,x+25,496),fill=color)
        label(d,(x+31,480),name,12,"#e1f0e7")
    return im
