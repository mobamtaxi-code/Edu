# v03: v02에서 04_건물외피 영역만 수정 (해 쪽 주황 반사광 + 외피 그림자 옅게). 나머지는 v02 그대로.
import sys, numpy as np
from PIL import Image, ImageFilter

base, src, out = sys.argv[1], sys.argv[2], sys.argv[3]
img = np.array(Image.open(src).convert('RGB')).astype(np.float32) / 255.
H, W, _ = img.shape
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

def blur(a, r):
    return np.array(Image.fromarray(np.clip(a * 255, 0, 255).astype('uint8')).filter(ImageFilter.GaussianBlur(r))).astype(np.float32) / 255.

raw = np.array(Image.open(f'{base}/영역마스크/04_건물외피.png').convert('L')).astype(np.float32) / 255.
fac = blur(raw, 0.6) * (raw > 0.5).astype(np.float32) + blur(raw, 0.6) * (raw <= 0.5) * 0.0
fac = blur(fac, 0.5)
lum = img @ np.array([0.299, 0.587, 0.114], np.float32)

# 해 위치(v01과 동일): 지평선 중앙 오른쪽, 건물 뒤쪽 -> 역광
sx, sy = 430.0, 150.0

# ---------- 1. 그림자 옅게: 외피의 어두운 부분을 들어 올리고 대비 완화 ----------
lsm = blur(lum, 2.0)
dark = np.clip((0.42 - lsm) / 0.30, 0, 1)                  # 어두운 아래쪽 곡면일수록 1
fill_col = np.array([0.56, 0.48, 0.50])                      # 노을 하늘이 비친 따뜻한 회보라 채움빛
lifted = img + (fill_col - img) * (0.45 * dark)[..., None]
lifted = lifted * (1 + 0.20 * dark)[..., None]

# ---------- 2. 해 쪽 주황 반사광 ----------
# (a) 해에 가까운 쪽(가로 거리)일수록, (b) 위쪽 면일수록, (c) 원래 밝은 면(지붕·윗면)일수록 강하게
dist = np.sqrt(((xx - sx) / 200.0) ** 2 + ((yy - sy) / 160.0) ** 2)
toward_sun = np.exp(-dist ** 2)
upper = np.clip((300 - yy) / 120, 0, 1)
bright = np.clip((lsm - 0.25) / 0.35, 0, 1)
refl = toward_sun * (0.35 + 0.65 * upper) * (0.3 + 0.7 * bright)

# (d) 윤곽 역광(rim light): 외피 마스크의 위쪽 경계를 따라 가는 금빛 선
inner = np.maximum(np.array(Image.open(f'{base}/영역마스크/05_유리면.png').convert('L')),
                   np.array(Image.open(f'{base}/영역마스크/06_중정.png').convert('L'))).astype(np.float32) / 255.
inner = blur(inner, 4) > 0.02                                 # 중정·유리면 근처는 제외(바깥 실루엣만)
up = np.roll(raw, 2, axis=0)                                  # 2px 위 픽셀
edge = np.clip(raw - up, 0, 1) * (~inner)
rim = blur(edge, 1.0) * 1.1 * (0.3 + 0.7 * toward_sun) * raw   # 외피 안쪽으로만
rim = np.clip(rim, 0, 0.6)

orange = np.array([1.00, 0.55, 0.22])
gold = np.array([1.00, 0.80, 0.45])
r = refl[..., None]
# 금속 외피라 색을 '곱하기 + 더하기'로 섞음: 결은 살리고 주황빛을 입힘
lit = lifted * (1 - 0.75 * r) + lifted * orange * 1.75 * (0.75 * r) + 0.22 * r * orange
lit = 1 - (1 - lit) * (1 - rim[..., None] * gold * 0.6)     # 스크린 합성
lit = np.clip(lit, 0, 1)

res = img * (1 - fac[..., None]) + lit * fac[..., None]
Image.fromarray((np.clip(res, 0, 1) * 255 + 0.5).astype('uint8')).save(out)
print('saved', out)
