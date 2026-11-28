"""Small reusable helpers for titles and gradients."""

from PIL import Image, ImageColor, ImageDraw, ImageFont

from lib.motion import mix


def gradient(size, top, bottom):
    a, b = ImageColor.getrgb(top), ImageColor.getrgb(bottom)
    w, h = size
    stripe = Image.new("RGB", (1, h))
    stripe.putdata([tuple(round(c) for c in mix(a, b, y/max(1,h-1))) for y in range(h)])
    return stripe.resize(size)


def label(draw, position, text, size, fill, *, anchor=None):
    draw.text(position, text, font=ImageFont.load_default(size=size), fill=fill, anchor=anchor)
