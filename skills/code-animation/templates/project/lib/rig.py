"""An original geometric cutout with hierarchical bones and replaceable expressions."""

import math

from PIL import Image, ImageDraw

from lib.motion import keyframes


NEUTRAL = (7, -7, -5, 5, 7, 9, 7, 9)
EXPRESSIONS = ("calm", "joy", "wonder")
VISEMES = ("rest", "open", "wide", "round", "closed")


def mirror(pose):
    a,b,c,d,e,f,g,h = pose
    return (-c,-d,-a,-b,-g,-h,-e,-f)


def walk(phase):
    opposite = (26,-18,-18,12,-25,14,24,4)
    return keyframes([(0,opposite),(.25,NEUTRAL),(.5,mirror(opposite)),(.75,NEUTRAL),(1,opposite)], phase%1)


def bone(origin, length, angle):
    x, y = origin
    t = math.radians(angle)
    return x+length*math.sin(t), y+length*math.cos(t)


def viseme_at(track, count, frame):
    if not track or track[0][0] != 0 or any(
        type(f) is not int or not 0 <= f < count or pose not in VISEMES for f, pose in track
    ) or any(a[0] >= b[0] for a,b in zip(track,track[1:])):
        raise ValueError("visemes must start at zero and use strictly increasing frame indices")
    return next(pose for f, pose in reversed(track) if f <= frame)


def draw_rig(im, origin, scale, pose=NEUTRAL, expression="calm", mouth="rest", view=1):
    if expression not in EXPRESSIONS or mouth not in VISEMES or view not in (-1,0,1):
        raise ValueError("invalid expression, mouth shape or view")
    d = ImageDraw.Draw(im)
    x,y = origin
    ink, coat, trim, skin, cap = "#162e38","#e68e4c","#ffcf79","#ca825f","#68bab2"

    def xy(p):
        return (x + scale*(p[0] if view >= 0 else -p[0]), y + scale*p[1])

    def ellipse(p, rx, ry, color):
        a,b = xy(p)
        d.ellipse((a-rx*scale,b-ry*scale,a+rx*scale,b+ry*scale), fill=color)

    def limb(p, length_a, length_b, angle, bend, color, width):
        mid = bone(p,length_a,angle)
        end = bone(mid,length_b,angle+bend)
        d.line([xy(p),xy(mid),xy(end)], fill=color, width=max(1,round(width*scale)), joint="curve")
        ellipse(mid,width/2,width/2,color)
        return end

    a,b,c,e,f,g,h,i = pose
    for k, upper, lower in ((-1,f,g),(1,h,i)):
        foot = limb((12*k,59),28,23,upper,lower,ink,14)
        ellipse((foot[0]+4,foot[1]),11,6,ink)
    for k, upper, lower in ((-1,a,b),(1,c,e)):
        hand = limb((25*k,15),27,22,upper,lower,coat,14)
        ellipse(hand,8,8,skin)
    d.polygon([xy(p) for p in [(-24,8),(22,8),(31,61),(-32,61)]], fill=coat)
    d.line([xy((-16,31)),xy((16,31))],fill=trim,width=max(1,round(4*scale)))
    ellipse((0,-19),29,29,skin)
    ellipse((-4,-41),31,11,cap)
    ellipse((-26,-30),8,17,cap)
    ellipse((17,-44),7,6,trim)
    if view != 0:
        ellipse((-2,-22),2.4,4,ink)
        ellipse((15,-22),2.4,4,ink)
        shape = {"rest":(5,1.5),"open":(5,5),"wide":(8,2.5),"round":(3.5,4.5),"closed":(4,1)}[mouth]
        if mouth == "rest" and expression != "calm":
            shape = (7,3) if expression == "joy" else (3.5,4.5)
        ellipse((7,-9),*shape,ink)
    else:
        ellipse((0,-19),25,23,cap)
