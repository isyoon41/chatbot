#!/usr/bin/env python3
"""Culture Festival 2026 sketch video generator (1920x1080, ~2 min).

Usage: python3 make_video.py <photo_dir> <font_dir> <out.mp4>
Renders frames with Pillow and pipes them to ffmpeg; also synthesizes
a simple upbeat background track with numpy.
"""
import math, os, random, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

PHOTOS, FONTS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
W, H, FPS = 1920, 1080, 30
XF = 0.6  # crossfade seconds

NAVY = (24, 40, 120)
BLUE = (38, 67, 184)
ORANGE = (255, 112, 48)
PALETTE = [(255, 112, 48), (255, 196, 0), (46, 196, 120), (0, 170, 230),
           (255, 92, 160), (150, 110, 230), (255, 255, 255)]

def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)

JUA = lambda s: font("Jua.ttf", s)
N9 = lambda s: font("NotoKR900.ttf", s)
N7 = lambda s: font("NotoKR700.ttf", s)

def ease_out(x):
    x = min(max(x, 0), 1); return 1 - (1 - x) ** 3

def ease_inout(x):
    x = min(max(x, 0), 1); return x * x * (3 - 2 * x)

def back_out(x):
    x = min(max(x, 0), 1); c = 1.9
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2

# ---------------------------------------------------------------- sources
SRC_W, SRC_H = int(W * 1.18), int(H * 1.18)

def load(name):
    return ImageOps.exif_transpose(Image.open(os.path.join(PHOTOS, name))).convert("RGB")

def cover(im, w, h):
    s = max(w / im.width, h / im.height)
    im = im.resize((math.ceil(im.width * s), math.ceil(im.height * s)), Image.LANCZOS)
    l, t = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((l, t, l + w, t + h))

def fitted_on_blur(im, w, h, margin=0.92):
    bg = cover(im, w // 4, h // 4).filter(ImageFilter.GaussianBlur(10)).resize((w, h), Image.BILINEAR)
    bg = Image.blend(bg, Image.new("RGB", (w, h), BLUE), 0.35)
    s = min(w * margin / im.width, h * margin / im.height)
    fg = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(sh)
    x, y = (w - fg.width) // 2, (h - fg.height) // 2
    d.rounded_rectangle((x + 10, y + 18, x + fg.width + 10, y + fg.height + 18), 24, fill=(0, 0, 0, 120))
    sh = sh.filter(ImageFilter.GaussianBlur(18))
    bg = Image.alpha_composite(bg.convert("RGBA"), sh)
    mask = Image.new("L", fg.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, fg.width, fg.height), 24, fill=255)
    bg.paste(fg, (x, y), mask)
    return bg.convert("RGB")

# ---------------------------------------------------------------- overlays
def text_w(d, s, f):
    return d.textbbox((0, 0), s, font=f)[2]

def caption_layer(tag, tag_color, ko, en):
    f_tag, f_ko, f_en = JUA(40), N9(58), N7(32)
    tmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    tw = text_w(tmp, tag, f_tag) + 44
    body_w = max(text_w(tmp, ko, f_ko), text_w(tmp, en, f_en))
    w = tw + body_w + 30 + 56
    h = 150
    im = Image.new("RGBA", (w + 30, h + 30), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((8, 14, w + 8, h + 14), 34, fill=(0, 0, 0, 90))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(10)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w, h), 34, fill=(255, 255, 255, 244))
    # colored tag chip
    d.rounded_rectangle((22, 22, 22 + tw, h - 22), 26, fill=tag_color)
    tb = d.textbbox((0, 0), tag, font=f_tag)
    d.text((22 + (tw - (tb[2] - tb[0])) / 2 - tb[0], (h - (tb[3] - tb[1])) / 2 - tb[1]), tag,
           font=f_tag, fill="white")
    x = 22 + tw + 30
    d.text((x, 18), ko, font=f_ko, fill=NAVY)
    d.text((x, 92), en, font=f_en, fill=(90, 100, 130))
    return im

def brand_layer():
    f = JUA(30)
    s = "제5회 이주민과 함께하는 Culture Festival"
    tmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    w = text_w(tmp, s, f) + 70
    im = Image.new("RGBA", (w, 56), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, 55), 28, fill=(38, 67, 184, 215))
    d.ellipse((18, 18, 38, 38), fill=(255, 196, 0))
    d.text((48, 9), s, font=f, fill="white")
    return im

BRAND = None

def paste_alpha(base, layer, xy, alpha):
    if alpha <= 0: return
    if alpha < 1:
        layer = layer.copy()
        a = layer.getchannel("A").point(lambda v: int(v * alpha))
        layer.putalpha(a)
    base.alpha_composite(layer, (int(xy[0]), int(xy[1])))

def progress_bar(base, frac):
    d = ImageDraw.Draw(base)
    seg = W / len(PALETTE[:6])
    end = W * frac
    for i, c in enumerate(PALETTE[:6]):
        x0 = i * seg
        if x0 >= end: break
        d.rectangle((x0, H - 10, min(end, x0 + seg), H), fill=c)

# ---------------------------------------------------------------- confetti
class Confetti:
    def __init__(self, n, seed):
        r = random.Random(seed)
        self.p = [dict(x=r.uniform(0, W), y=r.uniform(-H, H), r=r.uniform(8, 26),
                       vy=r.uniform(60, 180), vx=r.uniform(-30, 30), ph=r.uniform(0, 6.28),
                       c=r.choice(PALETTE[:6]), k=r.choice(["c", "c", "s", "r"])) for _ in range(n)]

    def draw(self, im, t):
        d = ImageDraw.Draw(im)
        for p in self.p:
            y = (p["y"] + p["vy"] * t) % (H + 120) - 60
            x = (p["x"] + p["vx"] * t + 25 * math.sin(t * 2 + p["ph"])) % W
            r = p["r"]
            if p["k"] == "c":
                d.ellipse((x - r, y - r, x + r, y + r), fill=p["c"])
            elif p["k"] == "s":
                a = t * 2 + p["ph"]
                pts = [(x + r * math.cos(a + k * math.pi / 2), y + r * math.sin(a + k * math.pi / 2)) for k in range(4)]
                d.polygon(pts, fill=p["c"])
            else:
                d.rounded_rectangle((x - r * 1.3, y - r * 0.45, x + r * 1.3, y + r * 0.45), int(r * 0.45), fill=p["c"])

def gradient(c1, c2):
    g = np.linspace(0, 1, H)[:, None, None]
    arr = (np.array(c1)[None, None, :] * (1 - g) + np.array(c2)[None, None, :] * g)
    arr = np.repeat(arr, W, axis=1).astype(np.uint8)
    return Image.fromarray(arr, "RGB")

def centered(d, y, s, f, fill, cx=W / 2, stroke=0, stroke_fill=None):
    b = d.textbbox((0, 0), s, font=f, stroke_width=stroke)
    d.text((cx - (b[2] - b[0]) / 2 - b[0], y), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)

# ---------------------------------------------------------------- scenes
class PhotoScene:
    def __init__(self, img, dur, caption=None, motion=0, portrait=False):
        if portrait:
            self.src = fitted_on_blur(img, SRC_W, SRC_H, margin=0.88)
        else:
            self.src = cover(img, SRC_W, SRC_H)
        self.dur = dur
        self.cap = caption_layer(*caption) if caption else None
        zi = [(1.0, 1.12), (1.12, 1.0), (1.04, 1.14), (1.14, 1.04)][motion % 4]
        pans = [((0.48, 0.5), (0.52, 0.48)), ((0.52, 0.52), (0.48, 0.48)),
                ((0.45, 0.5), (0.55, 0.5)), ((0.55, 0.48), (0.45, 0.52))][motion % 4]
        self.z0, self.z1 = zi
        self.c0, self.c1 = pans

    def frame(self, t):
        u = ease_inout(t / self.dur)
        z = self.z0 + (self.z1 - self.z0) * u
        cx = self.c0[0] + (self.c1[0] - self.c0[0]) * u
        cy = self.c0[1] + (self.c1[1] - self.c0[1]) * u
        bw, bh = SRC_W / z, SRC_H / z
        x0 = min(max(cx * SRC_W - bw / 2, 0), SRC_W - bw)
        y0 = min(max(cy * SRC_H - bh / 2, 0), SRC_H - bh)
        im = self.src.transform((W, H), Image.EXTENT, (x0, y0, x0 + bw, y0 + bh), Image.BILINEAR).convert("RGBA")
        if getattr(self, "brand", True):
            paste_alpha(im, BRAND, (W - BRAND.width - 40, 36), ease_out((t - 0.2) / 0.5))
        if self.cap:
            a_in = ease_out((t - 0.35) / 0.55)
            a_out = 1 - ease_inout((t - (self.dur - XF - 0.35)) / 0.35)
            a = min(a_in, a_out)
            x = 60 - (1 - a_in) * 220
            paste_alpha(im, self.cap, (x, H - self.cap.height - 50), a)
        return im

class TitleScene:
    def __init__(self, dur):
        self.dur = dur
        self.bg = gradient((40, 74, 200), (22, 36, 110))
        self.conf = Confetti(46, 1)
        f = JUA(200)
        self.letters = []
        word = "Culture Festival"
        cols = [(255, 255, 255), (255, 112, 48), (255, 196, 0), (255, 112, 48), (46, 196, 120), (0, 170, 230),
                (255, 92, 160), None, (255, 112, 48), (255, 196, 0), (46, 196, 120), (0, 170, 230), (255, 92, 160),
                (150, 110, 230), (255, 196, 0), (46, 196, 120)]
        tmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        total = text_w(tmp, word, f)
        x = (W - total) / 2
        for i, ch in enumerate(word):
            adv = tmp.textlength(ch, font=f)
            if ch != " ":
                L = Image.new("RGBA", (260, 300), (0, 0, 0, 0))
                ImageDraw.Draw(L).text((30, 20), ch, font=f, fill=cols[i], stroke_width=8, stroke_fill=NAVY)
                self.letters.append((L, x - 30, 380 - 20, i))
            x += adv

    def frame(self, t):
        im = self.bg.copy()
        self.conf.draw(im, t)
        im = im.convert("RGBA")
        d = ImageDraw.Draw(im)
        a = ease_out(t / 0.6)
        top = Image.new("RGBA", (W, 160), (0, 0, 0, 0))
        dt = ImageDraw.Draw(top)
        centered(dt, 20, "제5회 이주민과 함께하는", JUA(84), (255, 255, 255))
        paste_alpha(im, top, (0, 190 - (1 - a) * 40), a)
        for L, x, y, i in self.letters:
            k = back_out((t - 0.4 - i * 0.06) / 0.5)
            if k <= 0: continue
            sz = (max(1, int(L.width * k)), max(1, int(L.height * k)))
            bob = 8 * math.sin(t * 3 + i * 0.6)
            Lk = L.resize(sz, Image.BILINEAR)
            im.alpha_composite(Lk, (int(x + (L.width - sz[0]) / 2), int(y + (L.height - sz[1]) / 2 + bob)))
        a2 = ease_out((t - 1.7) / 0.6)
        if a2 > 0:
            sub = Image.new("RGBA", (W, 320), (0, 0, 0, 0))
            ds = ImageDraw.Draw(sub)
            pill_w = 980
            ds.rounded_rectangle(((W - pill_w) / 2, 10, (W + pill_w) / 2, 110), 50, fill=(255, 236, 214))
            centered(ds, 22, "함께 달려가 어울리는 우리", JUA(64), NAVY)
            centered(ds, 140, "Running Together, Growing Together", JUA(52), (255, 255, 255))
            centered(ds, 222, "2026. 11. 7 (토) – 8 (일)", N9(46), (255, 196, 0))
            paste_alpha(im, sub, (0, 650 + (1 - a2) * 50), a2)
        return im

class PosterScene(PhotoScene):
    def __init__(self, img, dur):
        self.src = fitted_on_blur(img, SRC_W, SRC_H, margin=0.9)
        self.dur, self.cap, self.brand = dur, None, False
        self.z0, self.z1, self.c0, self.c1 = 1.0, 1.08, (0.5, 0.45), (0.5, 0.5)

class ChapterScene:
    def __init__(self, dur, day, color1, color2, title_en, title_ko, when, where, seed):
        self.dur = dur
        self.bg = gradient(color1, color2)
        self.conf = Confetti(30, seed)
        self.day, self.title_en, self.title_ko, self.when, self.where = day, title_en, title_ko, when, where

    def frame(self, t):
        im = self.bg.copy()
        self.conf.draw(im, t)
        im = im.convert("RGBA")
        k = back_out((t - 0.1) / 0.55)
        if k > 0:
            L = Image.new("RGBA", (W, 300), (0, 0, 0, 0))
            centered(ImageDraw.Draw(L), 20, self.day, JUA(230), (255, 255, 255), stroke=10, stroke_fill=NAVY)
            sz = (max(1, int(W * k)), max(1, int(300 * k)))
            im.alpha_composite(L.resize(sz, Image.BILINEAR), (int((W - sz[0]) / 2), int(150 + (300 - sz[1]) / 2)))
        a = ease_out((t - 0.6) / 0.5)
        if a > 0:
            L = Image.new("RGBA", (W, 470), (0, 0, 0, 0))
            d = ImageDraw.Draw(L)
            centered(d, 0, self.title_en, JUA(96), (255, 255, 255))
            centered(d, 120, self.title_ko, JUA(60), (255, 236, 150))
            pw = 1500
            d.rounded_rectangle(((W - pw) / 2, 230, (W + pw) / 2, 440), 40, fill=(255, 255, 255, 236))
            centered(d, 252, self.when, N9(54), NAVY)
            centered(d, 342, self.where, N7(42), (80, 90, 130))
            paste_alpha(im, L, (0, 470 + (1 - a) * 60), a)
        return im

class OutroScene:
    def __init__(self, dur):
        self.dur = dur
        self.bg = gradient((40, 74, 200), (22, 36, 110))
        self.conf = Confetti(56, 7)

    def frame(self, t):
        im = self.bg.copy()
        self.conf.draw(im, t)
        im = im.convert("RGBA")
        items = [
            (0.1, 150, "함께 달려가 어울리는 우리", JUA(110), (255, 255, 255)),
            (0.5, 290, "Running Together, Growing Together", JUA(60), (255, 196, 0)),
            (1.0, 420, "“너희는 다 그리스도 예수 안에서 하나이니라” (갈라디아서 3:28)", N7(40), (230, 236, 255)),
            (1.2, 480, "“You are all one in Christ Jesus.” (Galatians 3:28)", N7(36), (200, 210, 245)),
            (1.8, 600, "주최 SD미션센터   ·   협조 상당교회, 기아대책", N7(40), (255, 255, 255)),
            (1.9, 656, "Hosted by SD Mission Center  ·  Supported by Sangdang Church, Food for the Hungry", N7(32), (200, 210, 245)),
        ]
        for st, y, s, f, c in items:
            a = ease_out((t - st) / 0.6)
            if a <= 0: continue
            L = Image.new("RGBA", (W, f.size + 40), (0, 0, 0, 0))
            centered(ImageDraw.Draw(L), 0, s, f, c)
            paste_alpha(im, L, (0, y + (1 - a) * 40), a)
        k = back_out((t - 2.6) / 0.6)
        if k > 0:
            L = Image.new("RGBA", (1100, 170), (0, 0, 0, 0))
            d = ImageDraw.Draw(L)
            d.rounded_rectangle((0, 0, 1099, 169), 85, fill=ORANGE)
            centered(d, 30, "감사합니다!  Thank you!", JUA(92), (255, 255, 255), cx=550)
            sz = (max(1, int(1100 * k)), max(1, int(170 * k)))
            im.alpha_composite(L.resize(sz, Image.BILINEAR), (int((W - sz[0]) / 2), int(790 + (170 - sz[1]) / 2)))
        # fade to white-ish at very end
        fo = ease_inout((t - (self.dur - 0.8)) / 0.8)
        if fo > 0:
            im = Image.blend(im, Image.new("RGBA", (W, H), (255, 255, 255, 255)), fo)
        return im

# ---------------------------------------------------------------- build timeline
def build():
    global BRAND
    BRAND = brand_layer()
    D1, D2 = ("DAY 1", ORANGE), ("DAY 2", BLUE)
    day1 = [
        ("766479f0-image.jpg", "개회 & 환영 인사", "Opening & Welcome"),
        ("1f6bd7ac-image.jpg", "가을 하늘 아래 모인 팀들", "Teams gather under the autumn sky"),
        ("f704ba82-image.jpg", "남자 풋살 · 경기 전 한 컷!", "Men's Futsal · Pre-match lineup"),
        ("c0dfea10-image.jpg", "뜨거운 승부의 시작", "Game on!"),
        ("e90ed253-image.jpg", "골문을 향해!", "Driving to goal!"),
        ("b4f2df88-image.jpg", "여자 풋살 · 파이팅!", "Women's Futsal · Let's go!"),
        ("f1402a4f-image.jpg", "함께 뛰는 즐거움", "The joy of playing together"),
        ("6086eda5-image.jpg", "숨멎는 승부차기", "Penalty shootout!"),
        ("a215db73-image.jpg", "든든한 우리 골키퍼", "Our trusty keeper"),
        ("94be74f9-image.jpg", "웃음 가득한 팀워크", "All smiles, all teamwork"),
        ("ec40fe94-image.jpg", "남자부 4등 축하해요!", "Men's Division · 4th Place"),
        ("8a5656b1-image.jpg", "남자부 3등 축하해요!", "Men's Division · 3rd Place"),
        ("3a946961-image.jpg", "여자부 준우승 축하해요!", "Women's Division · Runners-up"),
    ]
    day2 = [
        ("e60b5779-image.jpg", "연합 예배 & 찬양", "United Worship & Praise", False),
        ("cfdbdc32-image.jpg", "다문화 축하 공연", "Multicultural celebration performance", True),
        ("dcd237c3-image.jpg", "모두 함께 레크리에이션", "Recreation for everyone", False),
        ("d231cb16-image.jpg", "웃음이 넘치는 시간", "Laughter all around", False),
    ]
    scenes = [TitleScene(6.5), PosterScene(load("0e0989cf-image.png"), 5.5),
              ChapterScene(4.5, "DAY 1", (255, 140, 60), (240, 80, 40), "Futsal Tournament", "이주민과 함께하는 풋살대회",
                           "11. 7 (Sat)  9AM – 1PM", "@ Bunpyeong Futsal Field (27 Yongpyeong-ro 94beon-gil)", 3)]
    for i, (f, ko, en) in enumerate(day1):
        scenes.append(PhotoScene(load(f), 5.6, (D1[0], D1[1], ko, en), motion=i))
    scenes.append(ChapterScene(4.5, "DAY 2", (60, 110, 235), (30, 50, 160), "United Worship & Performance",
                               "연합 예배 & 다문화 축하 공연", "11. 8 (Sun)  12PM – 5:30PM",
                               "@ Bareun Sports World (535-83 Namseok-ro)", 5))
    for i, (f, ko, en, portrait) in enumerate(day2):
        scenes.append(PhotoScene(load(f), 6.4, (D2[0], D2[1], ko, en), motion=i + 1, portrait=portrait))
    scenes.append(OutroScene(8.0))
    return scenes

def render(scenes, video_path):
    starts, t = [], 0.0
    for s in scenes:
        starts.append(t); t += s.dur - XF
    total = starts[-1] + scenes[-1].dur
    n = int(round(total * FPS))
    print(f"total {total:.1f}s, {n} frames", flush=True)
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                          "-crf", "21", "-pix_fmt", "yuv420p", video_path], stdin=subprocess.PIPE)
    for fi in range(n):
        tt = fi / FPS
        act = [(i, tt - starts[i]) for i in range(len(scenes)) if starts[i] <= tt < starts[i] + scenes[i].dur]
        if len(act) == 1:
            im = scenes[act[0][0]].frame(act[0][1])
        else:
            (i1, t1), (i2, t2) = act[0], act[1]
            a = ease_inout(t2 / XF)
            im = Image.blend(scenes[i1].frame(t1), scenes[i2].frame(t2), a)
        im = im.convert("RGB")
        # progress bar only over photo portion
        progress_bar(im, tt / total)
        p.stdin.write(im.tobytes())
        if fi % 300 == 0: print(f"frame {fi}/{n}", flush=True)
    p.stdin.close(); p.wait()
    return total

# ---------------------------------------------------------------- music
def music(path, dur, sr=44100):
    bpm = 120; beat = 60 / bpm
    n = int(dur * sr); out = np.zeros(n)
    t_all = np.arange(n) / sr
    midi = lambda m: 440 * 2 ** ((m - 69) / 12)
    prog = [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]]  # C G Am F
    def add(start, sig):
        i = int(start * sr)
        if i >= n: return
        j = min(n, i + len(sig)); out[i:j] += sig[:j - i]
    def pluck(f, d, amp):
        tt = np.arange(int(d * sr)) / sr
        env = np.exp(-tt * 6) * np.minimum(1, tt * 200)
        return amp * env * (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(4 * np.pi * f * tt) + 0.12 * np.sin(6 * np.pi * f * tt))
    def kick():
        tt = np.arange(int(0.35 * sr)) / sr
        f = 50 + 90 * np.exp(-tt * 25)
        return 0.9 * np.exp(-tt * 9) * np.sin(2 * np.pi * np.cumsum(f) / sr)
    rng = np.random.default_rng(0)
    def hat(a):
        tt = np.arange(int(0.06 * sr)) / sr
        nz = rng.standard_normal(len(tt)); nz = np.diff(nz, prepend=0)
        return a * nz * np.exp(-tt * 70)
    def clap():
        tt = np.arange(int(0.2 * sr)) / sr
        return 0.35 * rng.standard_normal(len(tt)) * np.exp(-tt * 22)
    melody = [72, 76, 79, 76, 74, 79, 83, 79, 76, 72, 74, 76, 77, 76, 74, 72]
    bars = int(dur / (4 * beat)) + 1
    for b in range(bars):
        ch = prog[b % 4]; t0 = b * 4 * beat
        intro = b < 2
        for s in range(8):  # eighth-note arpeggio
            note = ch[s % 3] + (12 if s in (3, 7) else 0)
            add(t0 + s * beat / 2, pluck(midi(note), 0.5, 0.16))
        add(t0, pluck(midi(ch[0] - 24), 1.8, 0.35)); add(t0 + 2 * beat, pluck(midi(ch[0] - 24), 1.8, 0.3))
        if not intro:
            for q in range(4):
                add(t0 + q * beat, kick())
                add(t0 + q * beat + beat / 2, hat(0.25))
            add(t0 + beat, clap()); add(t0 + 3 * beat, clap())
            if (b // 4) % 2 == 1:  # melody every other 4-bar phrase
                for k in range(4):
                    m = melody[((b % 4) * 4 + k) % 16]
                    tone = pluck(midi(m), 0.9, 0.13)
                    add(t0 + k * beat, tone)
    # simple echo for warmth
    dl = int(beat * 0.75 * sr); echo = np.zeros(n); echo[dl:] = out[:-dl] * 0.25; out += echo
    fade = np.ones(n); fi, fo = int(1.5 * sr), int(4 * sr)
    fade[:fi] = np.linspace(0, 1, fi); fade[-fo:] = np.linspace(1, 0, fo)
    out *= fade; out = np.tanh(out * 1.2); out /= np.abs(out).max() / 0.8
    st = np.stack([out, out], 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((st * 32767).astype(np.int16).tobytes())

if __name__ == "__main__":
    tmpdir = os.path.dirname(os.path.abspath(OUT))
    vid = os.path.join(tmpdir, "_video.mp4"); aud = os.path.join(tmpdir, "_music.wav")
    total = render(build(), vid)
    music(aud, total)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", vid, "-i", aud, "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT], check=True)
    os.remove(vid); os.remove(aud)
    print("done", OUT)
