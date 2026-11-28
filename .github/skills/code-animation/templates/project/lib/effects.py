"""Seekable particles and straight-alpha compositing."""

from dataclasses import dataclass
import math
import random

from PIL import Image, ImageChops, ImageDraw


@dataclass(frozen=True)
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    birth: int
    life: int
    radius: float
    phase: float


class Emitter:
    def __init__(self, kind, size, seed, frames, rate=4):
        if kind not in {"snow", "sparks", "dust"}:
            raise ValueError(f"unknown particle preset {kind}")
        self.kind, self.size = kind, size
        w, h = size
        rng = random.Random(seed)
        self.particles = []
        for f in range(-60, frames):
            for _ in range(rate):
                if kind == "snow":
                    p = (rng.uniform(0,w), rng.uniform(-25,h), rng.uniform(-.6,.6), rng.uniform(.6,2.8))
                elif kind == "sparks":
                    p = (w*.51, h*.72, rng.uniform(-5,5), rng.uniform(-8,-2))
                else:
                    p = (rng.uniform(0,w), rng.uniform(h*.56,h), rng.uniform(.4,2.2), rng.uniform(-.8,0))
                self.particles.append(Particle(*p, f, rng.randint(22,60), rng.uniform(1,3), rng.random()*math.tau))

    def layer(self, frame, color):
        im = Image.new("RGBA", self.size)
        for p in self.particles:
            age = frame - p.birth
            if not 0 <= age < p.life:
                continue
            t = age/p.life
            x = p.x + p.vx*age + 3*math.sin(p.phase+age*.10)
            y = p.y + p.vy*age + (.12*age*age if self.kind == "sparks" else 0)
            opacity = round(220*min(1,t*8,(1-t)*4))
            if not opacity:
                continue
            r = p.radius
            if self.kind == "sparks":
                x2, y2 = x-p.vx*1.5, y-1.5*(p.vy+.24*age)
                width = round(r)
                left, top = math.floor(min(x,x2))-width, math.floor(min(y,y2))-width
                right, bottom = math.ceil(max(x,x2))+width, math.ceil(max(y,y2))+width
                mark = Image.new("RGBA", (right-left+1, bottom-top+1))
                ImageDraw.Draw(mark).line((x-left,y-top,x2-left,y2-top), fill=(*color,opacity), width=width)
            else:
                left, top = math.floor(x-r), math.floor(y-r)
                right, bottom = math.ceil(x+r), math.ceil(y+r)
                mark = Image.new("RGBA", (right-left+1, bottom-top+1))
                ImageDraw.Draw(mark).ellipse((x-r-left,y-r-top,x+r-left,y+r-top), fill=(*color,opacity))
            im.alpha_composite(mark, dest=(left,top))
        return im


def composite(base, layer, mode="over"):
    base, layer = base.convert("RGBA"), layer.convert("RGBA")
    if mode == "over":
        return Image.alpha_composite(base, layer)
    fn = {"add": ImageChops.add, "screen": ImageChops.screen, "multiply": ImageChops.multiply}[mode]
    rgb = Image.composite(fn(base.convert("RGB"), layer.convert("RGB")), layer.convert("RGB"), base.getchannel("A"))
    rgb.putalpha(layer.getchannel("A"))
    return Image.alpha_composite(base, rgb)
