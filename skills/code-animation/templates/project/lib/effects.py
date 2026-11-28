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
        d = ImageDraw.Draw(im)
        for p in self.particles:
            age = frame - p.birth
            if not 0 <= age < p.life:
                continue
            t = age/p.life
            x = p.x + p.vx*age + 3*math.sin(p.phase+age*.10)
            y = p.y + p.vy*age + (.12*age*age if self.kind == "sparks" else 0)
            opacity = round(220*min(1,t*8,(1-t)*4))
            r = p.radius
            if self.kind == "sparks":
                d.line((x,y,x-p.vx*1.5,y-1.5*(p.vy+.24*age)), fill=(*color,opacity), width=round(r))
            else:
                d.ellipse((x-r,y-r,x+r,y+r), fill=(*color,opacity))
        return im


def composite(base, layer, mode="over"):
    base, layer = base.convert("RGBA"), layer.convert("RGBA")
    if mode == "over":
        return Image.alpha_composite(base, layer)
    fn = {"add": ImageChops.add, "screen": ImageChops.screen, "multiply": ImageChops.multiply}[mode]
    rgb = Image.composite(fn(base.convert("RGB"), layer.convert("RGB")), layer.convert("RGB"), base.getchannel("A"))
    rgb.putalpha(layer.getchannel("A"))
    return Image.alpha_composite(base, rgb)
