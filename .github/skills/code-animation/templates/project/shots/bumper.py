import math

from PIL import Image, ImageDraw


def setup(spec, shot):
    w, h = spec["width"], spec["height"]
    intro = shot["id"] == "intro"
    accent = next((event["frame"] for event in shot.get("events", []) if event["id"] == "pulse"), None)

    def frame(f):
        im = Image.new("RGB", (w, h), "#171e35")
        draw = ImageDraw.Draw(im)
        x, y = w / 2, h / 2
        if intro:
            x -= w * .7 * (1 - min(f / 32, 1)) ** 3
        elif accent is not None and f >= accent:
            r = 48 + (f - accent) * 2.6
            a = math.exp(-(f - accent) / 12)
            color = tuple(round(base + a * (peak - base))
                          for base, peak in zip((23, 30, 53), (29, 202, 181)))
            draw.ellipse((x-r, y-r, x+r, y+r), outline=color, width=3)
        draw.rounded_rectangle((x-42, y-42, x+42, y+42), 20, fill="#49e5ca")
        draw.ellipse((x-10, y-10, x+10, y+10), fill="#171e35")
        return im

    return frame
