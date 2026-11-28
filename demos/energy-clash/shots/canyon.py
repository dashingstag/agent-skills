import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


W, H = 960, 540
INK = "#141325"
BLUE = ("#25a3ef", "#64ddfb", "#e4fcff")
GOLD = ("#ef7a35", "#ffbe59", "#fff2bf")


def mix(a, b, u):
    return a + (b - a) * u


def smooth(a, b, x):
    if a == b:
        return float(x >= b)
    t = max(0, min(1, (x-a)/(b-a)))
    return t*t*(3-2*t)


def canyon(seed, close):
    y, x = np.mgrid[:H, :W]
    u = (y / H)[..., None]
    sky = (1-u) * np.array([43, 36, 72]) + u * np.array([217, 117, 109])
    halo = (np.exp(-((x-482)**2 + (y-238)**2) / 33000) * (1-y/H))[..., None]
    sky = np.uint8(np.clip(sky + halo * np.array([122, 59, 10]), 0, 255))
    im = Image.fromarray(sky)
    d = ImageDraw.Draw(im, "RGBA")
    d.ellipse((425, 153, 550, 278), fill=(255, 207, 143, 220))
    rng = random.Random(seed)
    for i in range(34):
        yy = rng.randrange(106, 294)
        xx = rng.randrange(-120, W)
        span = rng.randrange(22, 180)
        d.polygon([(xx, yy), (xx+span//3, yy-3), (xx+span, yy-2), (xx+span//2, yy+2)],
                  fill=(255, 198, 178, 30 if i % 3 else 55))
    for ridge, fill in [(0, "#986482"), (1, "#765571"), (2, "#503b59")]:
        points = [(-50, H)]
        for k in range(-50, W+80, 37):
            level = 262 + ridge*36 + 16*math.cos(k / (83 + ridge*20))
            points.append((k, level - rng.randrange(6, 52)))
        d.polygon(points + [(W+80, H)], fill=fill)
    d.polygon([(286, 424), (476, 333), (694, 379), (W, 464), (W, H), (0, H)],
              fill="#61405a")
    for j in range(16):
        yy = 354 + 10*j
        xx = rng.randrange(350, 680)
        d.polygon([(xx, yy), (xx+120, yy-9), (W, yy+27), (xx+90, yy+6)], fill=(239, 127, 125, 17))
    if not close:
        for left in (True, False):
            def pts(values):
                return [(q if left else W-q, z - (13 if left else 0)) for q, z in values]
            d.polygon(pts([(0, 390), (125, 388), (228, 407), (322, 414), (349, 439), (309, 480),
                           (305, 550), (0, 550)]), fill="#28253f")
            d.polygon(pts([(0, 390), (125, 388), (228, 407), (322, 414), (349, 439), (310, 454),
                           (151, 433), (47, 440), (0, 433)]), fill="#845561")
            d.polygon(pts([(127, 433), (250, 450), (222, 552), (92, 552)]), fill="#3d2b46")
            d.polygon(pts([(285, 454), (349, 439), (313, 481), (310, 514), (264, 532)]), fill="#55384b")
            for _ in range(19):
                a = rng.randrange(0, 307)
                b = rng.randrange(435, 548)
                d.line(pts([(a, b), (a+26, b+5), (a+37, b+5)]), fill=(225, 127, 120, 56), width=1)
    return im


def fighter(im, x, y, scale, direction, brawler=False, pose="guard", tilt=0):
    d = ImageDraw.Draw(im)
    c, s = math.cos(tilt), math.sin(tilt)

    def tr(pts):
        return [(x + scale*direction*(a*c-b*s), y + scale*(a*s+b*c)) for a, b in pts]

    def shape(pts, fill, stroke=INK):
        p = tr(pts)
        d.polygon(p, fill=fill)
        if stroke:
            d.line(p+[p[0]], fill=stroke, width=max(1, round(2.2*scale)), joint="curve")

    def mark(pts, fill, width=1.4):
        d.line(tr(pts), fill=fill, width=max(1, round(width*scale)), joint="curve")

    if brawler:
        korr(shape, mark)
        arm, glove, seam = "#b33553", "#552b42", "#df7b71"
    else:
        iri(shape, mark)
        arm, glove, seam = "#829e78", "#d9b884", "#68694b"

    if pose == "fire":
        shape([(14,31),(28,29),(43,37),(61,28),(67,35),(50,51),(34,52),(23,46),(13,41)], arm)
        shape([(54,31),(65,24),(71,23),(81,24),(81,28),(73,31),(83,30),(84,34),(70,39),(57,39)], glove)
        mark([(65,36),(69,31),(75,30)], seam)
    elif pose == "dash":
        shape([(12,26),(31,24),(48,33),(57,30),(63,38),(55,49),(37,54),(19,48),(10,39)], arm)
        shape([(51,34),(59,25),(70,26),(77,33),(72,46),(63,50),(54,46)], glove)
        mark([(60,32),(62,38),(71,37)], seam)
    else:
        shape([(15,28),(28,25),(38,38),(52,32),(58,37),(58,46),(42,56),(26,52),(15,41)], arm)
        shape([(42,36),(53,29),(61,31),(63,40),(56,47),(47,45)], glove)
        mark([(55,34),(58,39),(54,43)], seam)
    return tr([(81 if pose == "fire" else 60, 30)])[0]


def iri(shape, mark):
    shape([(-55,-39),(-49,-40),(11,119),(6,122)], "#9f754d")
    shape([(-57,-44),(-52,-47),(-47,-40),(-51,-35)], "#ead39d")
    shape([(-21,86),(2,91),(-8,116),(-30,140),(-44,139),(-34,120)], "#384755")
    shape([(6,87),(23,86),(30,109),(23,125),(29,140),(14,144),(8,124),(12,106)], "#485768")
    shape([(-43,131),(-28,138),(-34,151),(-31,158),(-33,162),(-58,162),(-57,155)], "#303b46")
    shape([(14,139),(28,135),(35,149),(49,154),(51,162),(20,162),(14,155)], "#303b46")
    for i in range(3):
        mark([(-44-i*3,140+i*4),(-34-i*3,145+i*3)], "#c9b998", 1.6)
        mark([(19+i,142+i*4),(29+i,139+i*4)], "#c9b998", 1.6)
    shape([(-20,46),(16,48),(22,76),(35,114),(15,119),(1,105),(-31,124),(-43,116),(-28,84)], "#647d6a")
    shape([(-22,65),(-13,74),(-25,114),(-38,116)], "#405b59", None)
    mark([(-15,94),(-26,117),(-35,118)], "#b5c7a4", 1.6)
    mark([(17,77),(20,99),(29,113)], "#b5c7a4", 1.6)
    shape([(-20,18),(-30,36),(-40,61),(-31,73),(-20,64),(-23,55),(-9,34)], "#687e74")
    shape([(-18,13),(11,11),(24,23),(26,39),(19,63),(-17,72),(-24,45),(-27,30)], "#7e9290")
    shape([(-16,21),(11,18),(4,41),(-6,62),(-17,60),(-12,47),(-20,34)], "#526668")
    shape([(-9,4),(8,4),(13,17),(5,27),(-12,22),(-17,15)], "#9a6149")
    shape([(-16,11),(13,12),(17,23),(4,30),(-17,24),(-24,19)], "#a6b187")
    shape([(-20,15),(-63,19),(-81,5),(-75,24),(-61,32),(-20,25)], "#93a77d")
    mark([(-64,21),(-45,23),(-25,19)], "#d2d9ad", 1.8)
    shape([(-24,61),(18,56),(23,65),(17,71),(-14,75),(-24,70)], "#bf9d62")
    shape([(-5,72),(-9,96),(-21,105),(-17,90),(-19,76)], "#9b8059")
    shape([(-18,-26),(6,-32),(17,-24),(19,-13),(27,-6),(21,-2),(22,7),(14,12),
           (1,14),(-12,7),(-20,-1),(-24,-15)], "#c48a65")
    shape([(-17,-16),(-11,-6),(-6,6),(6,12),(-3,12),(-17,3),(-22,-6)], "#9a6149", None)
    shape([(-16,-28),(-36,-37),(-39,-47),(-34,-56),(-20,-60),(-10,-54),(-9,-43),
           (5,-44),(16,-39),(22,-29),(19,-23),(13,-21),(11,-30),(5,-24),(-4,-22),
           (-10,-11),(-15,-12),(-19,-4),(-25,-13),(-25,-24)], "#237578")
    mark([(-36,-46),(-25,-52),(-17,-51)], "#65bdac", 2.4)
    mark([(-22,-28),(-13,-34),(-2,-38),(11,-36),(16,-32)], "#65bdac", 2)
    shape([(3,-13),(17,-14),(13,-8),(6,-8)], "#fff0d6")
    mark([(13,-13),(12,-9)], "#224c4d", 1.7)
    mark([(12,5),(19,4)], "#66433d")
    mark([(-12,-7),(-10,-2),(-13,0)], "#f3dc9e", 2.1)


def korr(shape, mark):
    shape([(-34,61),(-3,66),(-5,97),(-22,114),(-35,148),(-57,148),(-55,131),(-46,96)], "#492c3c")
    shape([(-12,65),(31,65),(44,91),(33,114),(40,142),(15,147),(8,123),(12,100),(-18,91)], "#6d3947")
    shape([(25,87),(38,93),(27,113),(28,133),(18,119),(21,99)], "#a15358", None)
    shape([(-55,137),(-32,142),(-35,152),(-31,156),(-33,162),(-66,162),(-69,156)], "#422633")
    shape([(13,140),(39,136),(47,150),(59,154),(61,162),(21,162),(13,155)], "#422633")
    mark([(-65,156),(-35,157)], "#ae736a", 2.2)
    mark([(24,157),(55,157)], "#ae736a", 2.2)
    shape([(-27,18),(-43,30),(-53,49),(-56,62),(-47,72),(-35,69),(-29,59),(-39,56),(-24,37)], "#913245")
    shape([(-28,11),(12,9),(36,21),(40,41),(28,71),(10,81),(-25,78),(-37,55),(-40,32)], "#a53753")
    shape([(-29,11),(-19,7),(-4,15),(6,29),(1,46),(8,69),(-5,80),(-30,75),(-36,56),(-33,34)], "#563749")
    shape([(13,12),(30,17),(39,29),(32,47),(25,69),(15,76),(10,67),(16,48),(12,32)], "#754151")
    mark([(-31,57),(-18,63),(-7,67),(-3,73)], "#d88870", 2)
    mark([(30,28),(24,44),(21,64)], "#de9678", 2)
    shape([(-45,19),(-34,9),(-21,11),(-9,23),(-18,37),(-34,43),(-49,35)], "#80505d")
    shape([(-46,22),(-36,14),(-24,17),(-18,24),(-35,29),(-46,27)], "#ba6c6d", None)
    shape([(-33,65),(-14,69),(16,65),(29,61),(28,73),(12,80),(-20,82),(-32,76)], "#382737")
    shape([(-9,69),(7,67),(11,74),(2,81),(-11,77)], "#b98462")
    mark([(-4,73),(5,72)], "#654044", 2)
    shape([(-16,0),(16,1),(21,15),(12,24),(-8,24),(-21,15)], "#8e2f4e")
    shape([(3,-26),(18,-32),(27,-41),(30,-55),(26,-65),(34,-62),(40,-52),(40,-40),
           (34,-28),(20,-17),(8,-15)], "#bd9478")
    shape([(-19,-30),(-37,-36),(-50,-46),(-55,-59),(-50,-73),(-46,-61),(-37,-53),
           (-22,-52),(-10,-44),(-7,-32)], "#e8c7a0")
    shape([(-50,-68),(-48,-57),(-39,-49),(-21,-46),(-12,-37),(-19,-33),(-36,-41),
           (-47,-48),(-53,-59)], "#a77b66", None)
    shape([(-24,-36),(-9,-45),(11,-44),(25,-35),(29,-20),(27,-9),(33,-3),(29,5),
           (23,7),(20,16),(2,20),(-17,15),(-27,1),(-32,-18)], "#bb3d56")
    shape([(-25,-31),(-14,-34),(-15,-20),(-21,-8),(-11,12),(4,17),(-4,18),(-22,12),
           (-31,-8),(-30,-20)], "#8e2f4e", None)
    shape([(-9,-40),(10,-42),(23,-36),(18,-31),(5,-33),(-6,-32)], "#df6a6d", None)
    shape([(8,-20),(26,-22),(23,-13),(12,-13)], "#ffcf87")
    mark([(20,-21),(18,-14)], INK, 2)
    mark([(4,-28),(27,-25)], "#702c46", 2.8)
    mark([(4,-34),(-1,-25),(2,-16),(-5,-5),(-5,2)], "#ffd0af", 2.8)
    mark([(13,8),(22,7)], "#602a41", 2)


def bolts(d, center, span, f, seed, color, count=9):
    rng = random.Random(seed*3001+f)
    for _ in range(count):
        x = center[0] + rng.uniform(-span, span)
        y = center[1] + rng.uniform(-span*.55, span*.55)
        dx, dy = rng.uniform(-47, 47), rng.uniform(-24, 24)
        zig = [(x,y), (x+dx,y+dy*.35), (x+dx*.65,y+dy*.65), (x+dx*1.3,y+dy)]
        d.line(zig, fill=color, width=rng.choice((1, 1, 2)))


def aura(overlay, x, y, size, f, power, palette, seed):
    if power <= 0:
        return
    rng = random.Random(seed)
    d = ImageDraw.Draw(overlay)
    outer = [(x-size*1.1,y+10)]
    for i in range(19):
        u = i / 18
        wave = math.sin(f*.43+i*1.88)
        p = math.sin(u*math.pi)
        outer.append((x+size*2.3*(u-.5) + wave*size*.12,
                      y - size*p*(2.05 + power*.76 + rng.uniform(-.21, .23) + wave*.32*(i%2))))
    outer.append((x+size*1.16,y+10))
    rgb = tuple(bytes.fromhex(palette[0][1:]))
    d.polygon(outer, fill=rgb+(round(power*67),),
              outline=tuple(bytes.fromhex(palette[1][1:]))+(round(power*174),), width=2)
    for i in range(18):
        u = (f*.027 + rng.random()) % 1
        xx = x + size*rng.uniform(-1.3, 1.3)
        yy = y-u*size*3
        d.line((xx,yy,xx+(xx-x)*.071,yy+4+u*10), fill=rgb+(round(215*power*(1-u)),), width=2)


def ground_dust(overlay, f, power, seed):
    rng = random.Random(seed)
    d = ImageDraw.Draw(overlay)
    for i in range(76):
        u = (rng.random() + f*.007) % 1
        xx = (rng.randrange(W) + f*(i%6+1)*.42) % W
        yy = H-10-u*rng.randrange(30, 145)
        r = rng.randrange(2, 22)
        a = round(74*power*(1-u))
        d.ellipse((xx-r,yy-r*.45,xx+r,yy+r*.45), fill=(229, 158, 151, a))


def wind(im, f, seed, rush):
    d = ImageDraw.Draw(im, "RGBA")
    rng = random.Random(seed)
    for i in range(55 if rush else 40):
        y = rng.randrange(H)
        x = (rng.randrange(W) - f*(rng.randrange(22, 48) if rush else rng.uniform(.6, 3))) % W
        k = max(1, abs(y-H/2)/42) if rush else 1
        length = rng.uniform(13, 65)*k if rush else rng.uniform(7, 25)
        d.polygon([(x, y), (x+length, y+2*k), (x+length*.25, y+k)], fill=(244, 203, 186, 75 if rush else 35))


def beam(d, start, end, f, palette, power):
    if power <= 0:
        return
    x, y = start
    xx, yy = end
    dx, dy = xx-x, yy-y
    length = max(1, math.hypot(dx, dy))
    n = (-dy/length, dx/length)
    radius = (9 + 7*power) * (.87 + .15*math.sin(f*.96))
    for width, color in [(2.1, palette[0]), (1.45, palette[1]), (.65, palette[2]), (.23, "#ffffff")]:
        d.line((start, end), fill=color, width=max(1, round(radius*width*2)))
    for j in range(3):
        path = []
        for i in range(12):
            t = i/11
            r = math.sin(t*25 - f*.7 + j*2) * radius*.9
            path.append((x+t*dx+n[0]*r, y+t*dy+n[1]*r))
        d.line(path, fill=palette[2], width=2)


def bloom(im, center, r, color):
    light = Image.new("RGBA", im.size)
    x, y = center
    rgb = tuple(bytes.fromhex(color[1:]))
    d = ImageDraw.Draw(light)
    d.ellipse((x-r, y-r, x+r, y+r), fill=rgb+(142,))
    light = light.filter(ImageFilter.GaussianBlur(max(4, r*.68)))
    im.paste(light, mask=light.getchannel("A"))


def sphere(d, x, y, r, palette):
    for rad, color in [(r*1.36, palette[0]), (r, palette[1]), (r*.67, palette[2]), (r*.43, "#ffffff")]:
        d.ellipse((x-rad,y-rad,x+rad,y+rad), fill=color)


def finish(im, seed, size):
    d = ImageDraw.Draw(im, "RGBA")
    rng = random.Random(seed)
    for _ in range(680):
        x, y = rng.randrange(W), rng.randrange(H)
        d.point((x, y), fill=(255, 236, 227, 19) if rng.getrandbits(1) else (23, 19, 41, 26))
    d.rectangle((0, 0, W, 29), fill="#100f1c")
    d.rectangle((0, H-30, W, H), fill="#100f1c")
    return im.resize(size, Image.Resampling.LANCZOS)


def setup(spec, shot):
    ident, seed = shot["id"], spec["seed"]
    event = {e["id"]: e["frame"] for e in shot["events"]}
    plate = canyon(seed, ident in ("rush", "clash"))
    size = (spec["width"], spec["height"])

    def frame(f):
        im = plate.copy()
        wind(im, f, seed, ident == "rush" and f >= event["dash"])
        fx = Image.new("RGBA", im.size)
        if ident == "faceoff":
            a = smooth(event["blue-charge"], event["blue-charge"]+20, f)
            b = smooth(event["gold-charge"], event["gold-charge"]+18, f)
            x, xx = 224+f*.43, 735-f*.43
            aura(fx, x, 411, 64, f, a, BLUE, 5)
            aura(fx, xx, 424, 68, f, b, GOLD, 8)
            im.paste(fx, mask=fx.getchannel("A"))
            fighter(im, x, 285+math.sin(f*.18)*2, .77, 1)
            fighter(im, xx, 295+math.sin(f*.16)*2, .80, -1, True)
        elif ident == "rush":
            dash = event["dash"]
            split = event["gather"]
            if f < split:
                u = smooth(dash, split-2, f)
                x, y = mix(738, 309, u), mix(305, 287, u)
                aura(fx, x+21, y+191, 83, f, .73, GOLD, 8)
                im.paste(fx, mask=fx.getchannel("A"))
                fighter(im, x, y, 1.2+u*.18, -1, True, "dash", .08+u*.57)
                if f >= dash:
                    d = ImageDraw.Draw(im, "RGBA")
                    for i in range(12):
                        yy = y + (i-5)*17
                        start = x-102+(i*37)%91
                        d.line((start, yy, min(W, start+78+u*264+i*9), yy-10),
                               fill=(255, 208, 131, 43 + i%3*20), width=1+i%2)
            else:
                p = smooth(split-1, split+13, f)
                aura(fx, 400, 476, 118, f, .95, BLUE, 5)
                im.paste(fx, mask=fx.getchannel("A"))
                x, y = fighter(im, 378+f*.8, 325, 1.8, 1, False, "fire", -.20)
                bloom(im, (x, y), 23+32*p, BLUE[1])
                d = ImageDraw.Draw(im)
                sphere(d, x, y, 5+13*p, BLUE)
                bolts(d, (x, y), 31*p, f, 6, BLUE[2], 4)
        elif ident == "clash":
            launch, meet, flare = (event[k] for k in ("release", "meet", "flare"))
            shake = 3*math.sin(f*2.14) * smooth(launch, meet, f)
            x, y = fighter(im, 193+shake, 310, 1.14, 1, False, "fire", -.20)
            xx, yy = fighter(im, 763-shake, 314, 1.14, -1, True, "fire", -.17)
            center = 480 + 24*math.sin((f-meet)*.16), (y+yy)/2 + 5*math.cos(f*.36)
            d = ImageDraw.Draw(im)
            if launch <= f < flare+12:
                power = smooth(launch-1, meet, f)*(1-smooth(flare+2, flare+12, f))
                length = smooth(launch-1, meet, f)
                br = (mix(x, center[0], length), mix(y, center[1], length))
                gr = (mix(xx, center[0], length), mix(yy, center[1], length))
                beam(d, (x, y), br, f, BLUE, power)
                beam(d, (xx, yy), gr, f+7, GOLD, power)
                if f >= meet:
                    r = (15+17*smooth(meet, flare, f)+5*math.sin(f*.71)) * max(.02, power)
                    bloom(im, center, r*2.7, "#ffcf9c")
                    d = ImageDraw.Draw(im)
                    cx, cy = center
                    for i in range(9):
                        angle = i*math.tau/9+f*.08
                        ux, uy = math.cos(angle), math.sin(angle)
                        v = r*(1.3 + .7*math.sin(i*17+f*.45)**2)
                        d.polygon([(cx+uy*r*.3, cy-ux*r*.3), (cx+ux*v, cy+uy*v),
                                   (cx-uy*r*.3, cy+ux*r*.3)], fill="#ffd88f" if ux>0 else "#aafbff")
                    sphere(d, *center, r, ("#659ddf", "#ddcefc", "#fff6d8"))
                    bolts(d, center, 84, f, 12, BLUE[2])
            if f >= flare:
                t = f-flare
                for j in range(3):
                    r = max(1, 22 + 22*t - 33*j)
                    ImageDraw.Draw(fx).ellipse((center[0]-r,center[1]-r*.54,center[0]+r,center[1]+r*.54),
                                               outline=(255,222,175,max(0,160 - 8*t)), width=3)
                ground_dust(fx, f, smooth(flare, flare+10, f), seed)
                im.paste(fx, mask=fx.getchannel("A"))
                if t < 9:
                    flash = Image.new("RGB", im.size, "#fff3d8")
                    im = Image.blend(im, flash, .72*(1-t/9)**2)
        else:
            t = f-event["land"]
            fall = 47*(1-smooth(-9, 0, t))
            bounce = 4*math.sin(t)*math.exp(-max(0, t)/4) if t >= 0 else 0
            fighter(im, 228, 285-fall+bounce, .77, 1)
            fighter(im, 730, 295-fall+bounce, .80, -1, True)
            ground_dust(fx, f, 1.6*(1-smooth(0, 45, f)), seed)
            im.paste(fx, mask=fx.getchannel("A"))
            dust = Image.new("RGB", im.size, "#bd8d91")
            im = Image.blend(im, dust, .42*(1-smooth(0, 39, f)))
        return finish(im, seed+f, size)

    return frame
