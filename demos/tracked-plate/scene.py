from pathlib import Path
import random
import subprocess

from PIL import Image, ImageDraw

from lib.footage import track, video_frames
from lib.graphics import gradient, label


SIZE = 640,360
PLATE = "assets/plate.mp4"


def setup(spec, shot):
    # Shared absolute timeline in seconds; reference marks were measured on the generated plate.
    plates = video_frames(PLATE, source_fps=30,fps=spec["fps"],size=SIZE,frames=shot["frames"])
    samples = [(0,(144,227)),(12,(234,222)),(24,(324,217)),(36,(414,212)),(47,(496.5,207.4))]

    def frame(f):
        im = plates[f].convert("RGBA")
        layer = Image.new("RGBA", SIZE)
        d = ImageDraw.Draw(layer)
        x,y = track(samples,f)
        d.ellipse((x-28,y-28,x+28,y+28),outline=(128,239,217,210),width=3)
        d.line((x+20,y-18,x+49,y-58,x+92,y-58),fill=(128,239,217,230),width=2)
        d.rounded_rectangle((x+40,y-89,x+118,y-62),radius=4,fill=(14,36,47,214))
        label(d,(x+79,y-76),"BUOY 01",12,"#aff2de",anchor="mm")
        d.line((26,80,141,80),fill=(128,239,217,190),width=2)
        label(d,(26,26),"ESTUARY LOG",28,"#fff0d0")
        label(d,(26,61),"TRACK 01  /  30 → 24 FPS",15,"#c8e7de")
        im.alpha_composite(layer)
        return im.convert("RGB")
    return frame


def make_plate(path):
    rng = random.Random(98)
    ripple = [(rng.randrange(640),rng.randrange(183,359),rng.randrange(12,90)) for _ in range(96)]
    base = gradient(SIZE,"#596f75","#b2a88d")
    d = ImageDraw.Draw(base)
    d.ellipse((462,55,514,107),fill="#ebc8a5")
    d.polygon([(0,181),(155,97),(264,144),(339,101),(465,169),(577,117),(640,144),(640,215),(0,216)],fill="#405c62")
    base.paste(gradient((640,180),"#3b616b","#213c49"),(0,180))
    with subprocess.Popen(["ffmpeg","-y","-v","error","-f","rawvideo","-pix_fmt","rgb24","-s","640x360",
                           "-r","30","-i","-","-an","-vf","scale=out_color_matrix=bt709",
                           "-c:v","libx264","-preset","fast",
                           "-crf","16","-pix_fmt","yuv420p","-colorspace","bt709","-color_trc","bt709",
                           "-color_primaries","bt709",str(path)],stdin=subprocess.PIPE) as proc:
        for f in range(60):
            im = base.copy()
            d = ImageDraw.Draw(im)
            for x,y,w in ripple:
                u = (x+f) % 660 - 20
                d.line((u,y,u+w,y),fill="#50727a")
            x,y = 144+6*f,227-f/3
            d.ellipse((x-23,y+8,x+25,y+14),fill="#294552")
            d.polygon([(x-16,y),(x-5,y-13),(x+6,y-13),(x+17,y),(x+9,y+7),(x-9,y+7)],fill="#ffb883")
            d.line((x,y-12,x,y-26),fill="#fad5ad",width=2)
            proc.stdin.write(im.tobytes())
        proc.stdin.close()
        if proc.wait():
            raise RuntimeError("plate encoder failed")


if __name__ == "__main__":
    Path(PLATE).parent.mkdir(exist_ok=True)
    make_plate(PLATE)
