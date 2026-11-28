"""Frame-indexed interpolation, 2D camera, and editorial transitions."""

from bisect import bisect_right
from dataclasses import dataclass
import math

from PIL import Image, ImageDraw


def ease(t):
    t = min(1, max(0, t))
    return t*t*(3-2*t)


def mix(a, b, t):
    if isinstance(a, (tuple, list)):
        return tuple(mix(x, y, t) for x, y in zip(a, b, strict=True))
    return a + (b-a)*t


def keyframes(keys, t, curve=ease):
    times, values = zip(*keys)
    if any(a >= b for a, b in zip(times, times[1:])):
        raise ValueError("keys must be strictly increasing")
    i = bisect_right(times, t)
    if i == 0:
        return values[0]
    if i == len(keys):
        return values[-1]
    return mix(values[i-1], values[i], curve((t-times[i-1])/(times[i]-times[i-1])))


@dataclass(frozen=True)
class Camera:
    pan: tuple = (0, 0)
    zoom: float = 1
    shake: float = 0
    phase: float = 0

    def layer(self, layer, depth=1):
        w, h = layer.size
        z = 1 + (self.zoom-1)*depth
        if z <= 0:
            raise ValueError("layer zoom must be positive")
        px, py = self.pan
        dx = px*depth + self.shake*math.sin(self.phase*2.1)
        dy = py*depth + self.shake*math.sin(self.phase*2.9 + 1)
        return layer.convert("RGBA").transform(
            (w, h), Image.Transform.AFFINE,
            (1/z, 0, w/2-(w/2+dx)/z, 0, 1/z, h/2-(h/2+dy)/z), Image.Resampling.BICUBIC)


def transition(outgoing, incoming, progress, mode, action=.5):
    t = max(0, min(1, progress))
    if mode == "cut-on-action":
        return incoming if t >= action else outgoing
    if mode == "crossfade":
        if outgoing.mode == incoming.mode == "RGBA":
            if t == 0 or t == 1:
                return outgoing if t == 0 else incoming
            return Image.blend(outgoing.convert("RGBa"), incoming.convert("RGBa"), t).convert("RGBA")
        return Image.blend(outgoing, incoming, t)
    if mode == "wipe":
        mask = Image.new("L", outgoing.size)
        x = round(mask.width*t)
        if x:
            ImageDraw.Draw(mask).rectangle((0, 0, x-1, mask.height-1), fill=255)
        return Image.composite(incoming, outgoing, mask)
    raise ValueError(f"unknown transition: {mode}")
