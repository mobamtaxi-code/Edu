# v02: v01에서 06_중정, 07_전경만 수정 (밝게 + 가로등 + 산책/휴식하는 사람). 나머지는 v01 그대로.
import sys, numpy as np
from PIL import Image, ImageDraw, ImageFilter

base, src, out = sys.argv[1], sys.argv[2], sys.argv[3]
SS = 4  # 그리기 해상도 배율(안티에일리어싱)

v01 = np.array(Image.open(src).convert('RGB')).astype(np.float32) / 255.
H, W, _ = v01.shape
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

def mask(name, blur=1.5):
    m = Image.open(f'{base}/영역마스크/{name}.png').convert('L').filter(ImageFilter.GaussianBlur(blur))
    return np.array(m).astype(np.float32) / 255.

court = mask('06_중정')
fore = mask('07_전경')
region = np.maximum(court, fore)

# 워터마크 영역(오른쪽 아래)은 건드리지 않음
wm = ((xx > 512) & (yy > 382)).astype(np.float32)
wm = np.array(Image.fromarray((wm * 255).astype('uint8')).filter(ImageFilter.GaussianBlur(3))) / 255.
region = region * (1 - wm)

# ---------- 가로등 위치(전경 잔디 안, 바깥 산책로 흰 선을 따라) ----------
lamps_fore = [(38, 318), (92, 352), (160, 380), (238, 400), (330, 410), (425, 409), (505, 386), (582, 362), (640, 336)]
lamps_court = [(300, 241), (355, 252), (415, 257)]          # 중정은 낮은 볼라드 조명

# ---------- 1. 밝기: 저녁 분위기 유지하면서 전체 리프트 + 조명 웅덩이 ----------
lit = v01 * 1.30 + 0.025
# 조명 웅덩이(바닥에 납작한 타원형 빛)
pool = np.zeros((H, W), np.float32)
for x, y in lamps_fore:
    pool += np.exp(-(((xx - x) / 30) ** 2 + ((yy - y) / 11) ** 2))
for x, y in lamps_court:
    pool += 0.8 * np.exp(-(((xx - x) / 22) ** 2 + ((yy - y) / 7) ** 2))
pool = np.clip(pool, 0, 1.3)[..., None]
warm = np.array([1.00, 0.72, 0.40])
lit = lit * (1 + 0.55 * pool * warm) + 0.10 * pool * warm
lit = np.clip(lit, 0, 1)

res = v01 * (1 - region[..., None]) + lit * region[..., None]

# ---------- 2. 가로등·사람 그리기(고해상도 레이어) ----------
layer = Image.new('RGBA', (W * SS, H * SS), (0, 0, 0, 0))
glow = Image.new('RGBA', (W * SS, H * SS), (0, 0, 0, 0))
d, g = ImageDraw.Draw(layer), ImageDraw.Draw(glow)
S = lambda v: v * SS

def lamp(x, y, h=13, bollard=False):
    pole = (38, 34, 40, 255)
    if bollard:
        d.rectangle([S(x) - 2, S(y - 3), S(x) + 2, S(y)], fill=pole)
        d.ellipse([S(x) - 3, S(y - 4) - 3, S(x) + 3, S(y - 4) + 3], fill=(255, 225, 160, 255))
        g.ellipse([S(x) - 22, S(y - 4) - 22, S(x) + 22, S(y - 4) + 22], fill=(255, 180, 90, 120))
        return
    d.line([S(x), S(y), S(x), S(y - h)], fill=pole, width=4)
    d.line([S(x), S(y - h), S(x) + 9, S(y - h)], fill=pole, width=3)      # 팔
    d.ellipse([S(x) + 5, S(y - h) - 1, S(x) + 15, S(y - h) + 7], fill=(255, 232, 170, 255))
    g.ellipse([S(x) + 10 - 34, S(y - h) - 30, S(x) + 10 + 34, S(y - h) + 38], fill=(255, 180, 90, 130))

def person(x, y, h=7.0, color=(30, 26, 32), walk=0, sit=False, lit_side=1):
    c = color + (255,)
    hh = S(h)
    head = hh * 0.17
    if sit:
        # 앉은 사람: 몸통 + 앞으로 뻗은 다리
        d.ellipse([S(x) - head, S(y) - hh * 0.62 - head, S(x) + head, S(y) - hh * 0.62 + head], fill=(60, 45, 40, 255))
        d.rounded_rectangle([S(x) - hh * 0.13, S(y) - hh * 0.5, S(x) + hh * 0.13, S(y)], radius=3, fill=c)
        d.line([S(x), S(y) - 1, S(x) + hh * 0.42 * lit_side, S(y) - 1], fill=c, width=int(hh * 0.16))
        return
    d.ellipse([S(x) - head, S(y) - hh + 0, S(x) + head, S(y) - hh + 2 * head], fill=(60, 45, 40, 255))
    d.rounded_rectangle([S(x) - hh * 0.13, S(y) - hh + 2 * head, S(x) + hh * 0.13, S(y) - hh * 0.42], radius=3, fill=c)
    s = hh * 0.12 * walk
    leg = (35, 32, 40, 255)
    d.line([S(x) - hh * 0.05, S(y) - hh * 0.45, S(x) - hh * 0.05 - s, S(y)], fill=leg, width=int(hh * 0.11))
    d.line([S(x) + hh * 0.05, S(y) - hh * 0.45, S(x) + hh * 0.05 + s, S(y)], fill=leg, width=int(hh * 0.11))
    # 발밑 그림자(가로등 반대쪽으로)
    d.ellipse([S(x) - hh * 0.35 - lit_side * hh * 0.25, S(y) - 3, S(x) + hh * 0.35 - lit_side * hh * 0.25, S(y) + 4], fill=(10, 10, 15, 110))
    # 가로등 쪽 따뜻한 테두리 빛
    d.line([S(x) + hh * 0.13 * lit_side, S(y) - hh + 3 * head, S(x) + hh * 0.13 * lit_side, S(y) - hh * 0.45],
           fill=(240, 170, 100, 200), width=2)

for p in lamps_fore:
    lamp(*p)
for p in lamps_court:
    lamp(*p, bollard=True)

# 산책: 바깥 산책로를 따라 걷는 사람들(혼자/둘이)
walkers = [(82, 350, 1), (88, 352, -1), (172, 384, 1), (252, 404, -1), (259, 405, 1),
           (342, 413, 1), (438, 412, -1), (498, 392, 1), (592, 367, -1)]
cloth = [(150, 70, 60), (60, 80, 120), (200, 190, 170), (90, 110, 80), (170, 120, 70), (70, 60, 90), (210, 200, 185), (120, 60, 70), (60, 90, 110)]
for (x, y, s), c in zip(walkers, cloth):
    person(x, y, h=11.0, walk=s, lit_side=s, color=c)
# 휴식: 잔디에 앉은 사람들
sitters = [(122, 372, 1), (129, 373, -1), (300, 425, 1), (400, 425, -1), (407, 425, 1)]
for (x, y, s), c in zip(sitters, cloth[3:]):
    person(x, y, h=10.0, sit=True, lit_side=s, color=c)
# 중정: 산책·휴식(작게)
for x, y, s in [(322, 247, 1), (338, 249, -1), (392, 255, 1)]:
    person(x, y, h=7.0, walk=s, lit_side=s, color=(200, 190, 175))
for x, y, s in [(372, 260, 1), (377, 260, -1)]:
    person(x, y, h=6.5, sit=True, lit_side=s, color=(150, 80, 70))

glow = glow.filter(ImageFilter.GaussianBlur(S(3)))
glow = glow.resize((W, H), Image.LANCZOS)
layer = layer.resize((W, H), Image.LANCZOS)

img = Image.fromarray((np.clip(res, 0, 1) * 255 + 0.5).astype('uint8')).convert('RGBA')
# 빛 번짐은 '스크린' 방식으로 더함
gl = np.array(glow).astype(np.float32) / 255.
base_rgb = np.array(img)[..., :3].astype(np.float32) / 255.
add = gl[..., :3] * gl[..., 3:4]
base_rgb = 1 - (1 - base_rgb) * (1 - add)
img = Image.fromarray((base_rgb * 255 + 0.5).astype('uint8')).convert('RGBA')
img = Image.alpha_composite(img, layer).convert('RGB')
img.save(out)
print('saved', out)
