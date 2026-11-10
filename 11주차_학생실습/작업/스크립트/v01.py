# v01: 시간대 변경(한낮 -> 해 질 녘) + 주변(하늘, 수면, 전경/원경) 보정
# 건물 외피 전용 하이라이트는 다음 단계에서 다룸. 여기서는 전체 톤만 맞춤.
import sys, numpy as np
from PIL import Image, ImageFilter

base = sys.argv[1]          # 학생실습 폴더
out = sys.argv[2]

def load(p):
    return np.array(Image.open(p).convert('RGB')).astype(np.float32) / 255.

def mask(name, blur=2):
    m = Image.open(f'{base}/영역마스크/{name}.png').convert('L')
    m = m.filter(ImageFilter.GaussianBlur(blur))
    return np.array(m).astype(np.float32) / 255.

img = load(f'{base}/00_원본.png')
H, W, _ = img.shape
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
lum = img @ np.array([0.299, 0.587, 0.114], np.float32)

# ---------- 1. 하늘: 노을 그라데이션 ----------
sky_m = mask('01_하늘', 1.5)
# 산·건물 경계 보정: 마스크 안에서도 밝고 푸른 하늘색 픽셀만 하늘로 인정
r, g, b = img[..., 0], img[..., 1], img[..., 2]
skyish = np.clip((lum - 0.55) / 0.15, 0, 1) * np.clip((b - r + 0.02) / 0.08, 0, 1)
skyish = np.array(Image.fromarray((skyish * 255).astype('uint8')).filter(ImageFilter.GaussianBlur(1))) / 255.
sky_a = sky_m * np.maximum(skyish, np.clip((135 - yy) / 30, 0, 1))

horizon = 145.0
t = np.clip(yy / horizon, 0, 1)[..., None]           # 0=위, 1=지평선
stops = [(0.00, (0.20, 0.17, 0.38)),                  # 위: 짙은 보라남색
         (0.45, (0.62, 0.36, 0.52)),                  # 중간: 분홍 보라
         (0.75, (0.96, 0.55, 0.38)),                  # 주황
         (1.00, (1.00, 0.78, 0.48))]                  # 지평선: 밝은 금빛
sky = np.zeros_like(img)
for (t0, c0), (t1, c1) in zip(stops[:-1], stops[1:]):
    w = np.clip((t - t0) / (t1 - t0), 0, 1)
    seg = (t >= t0) & (t <= t1)
    col = np.array(c0) * (1 - w) + np.array(c1) * w
    sky = np.where(seg, col, sky)
# 해 위치: 지평선 중앙 오른쪽(건물 뒤쪽 역광)
sx, sy = 430.0, 150.0
d = np.sqrt((xx - sx) ** 2 + ((yy - sy) * 1.6) ** 2)
glow = np.exp(-(d / 140.0) ** 2)[..., None]
sky = sky + glow * np.array([0.35, 0.22, 0.05])
# 얇은 구름 띠(가로 줄무늬 노이즈)
rng = np.random.default_rng(11)
n = rng.random((H // 6 + 1, W // 40 + 1)).astype(np.float32)
n = np.array(Image.fromarray((n * 255).astype('uint8')).resize((W, H), Image.BICUBIC)) / 255.
clouds = np.clip((n - 0.55) * 3, 0, 1) * np.clip((yy - 40) / 60, 0, 1) * np.clip((140 - yy) / 40, 0, 1)
sky = sky * (1 - 0.25 * clouds[..., None]) + clouds[..., None] * 0.25 * np.array([0.55, 0.30, 0.35])
sky = np.clip(sky, 0, 1)

# ---------- 2. 전체 시간대 보정(해 질 녘 톤) ----------
def evening(x, dark=0.62, warm=(1.10, 0.92, 0.80)):
    x = x * dark
    x = x * np.array(warm)
    # 그림자 쪽은 푸른 보라로 살짝
    l = (x @ np.array([0.299, 0.587, 0.114]))[..., None]
    shadow = np.clip(1 - l / 0.35, 0, 1)
    x = x * (1 - 0.25 * shadow) + 0.25 * shadow * l * np.array([0.85, 0.80, 1.25])
    return np.clip(x, 0, 1)

graded = evening(img)
# 원경(산·도시)은 노을 안개에 묻히게: 지평선 근처일수록 금빛 헤이즈
haze = np.clip(1 - np.abs(yy - 150) / 45, 0, 1)[..., None] * (1 - sky_a[..., None])
graded = graded * (1 - 0.35 * haze) + 0.35 * haze * np.array([0.85, 0.55, 0.40])
# 지면에 낮게 깔리는 역광: 해 방향에서 멀어질수록 어둡게
falloff = np.clip(1 - (yy - 150) / 400, 0.55, 1)[..., None]
graded = graded * np.where(yy[..., None] > 150, falloff, 1)

# ---------- 3. 수면: 노을 반사 + 잔물결 완화 ----------
water_m = np.maximum(mask('02_왼쪽수면'), mask('03_오른쪽수면'))
# 왼쪽 마스크에 섞인 나무(초록) 제외: 초록이 파랑보다 확실히 크면 물이 아님
not_tree = np.clip(1 - (g - b - 0.02) / 0.06, 0, 1)
not_tree = np.array(Image.fromarray((not_tree * 255).astype('uint8')).filter(ImageFilter.GaussianBlur(1.5))) / 255.
water_a = water_m * not_tree
# 반사색: 수면 위쪽(먼 곳)은 지평선 금빛, 가까울수록 위쪽 하늘 색
ref_t = np.clip(1 - (yy - 165) / 110, 0, 1)[..., None]
refl = np.array([0.95, 0.62, 0.42]) * ref_t + np.array([0.55, 0.36, 0.48]) * (1 - ref_t)
# 해 반사 기둥(해 바로 아래 세로 띠)
col = np.exp(-((xx - sx) / 55.0) ** 2)[..., None]
refl = refl + col * np.array([0.25, 0.15, 0.03])
# 원본 수면 질감을 강하게 흐려 잔잔하게(세부 결만 약하게 남김)
smooth = np.array(Image.fromarray((lum * 255).astype('uint8')).filter(ImageFilter.GaussianBlur(6))) / 255.
detail = (lum - smooth)
water = np.clip(refl * 0.85 + detail[..., None] * 0.25, 0, 1)

# ---------- 합성 ----------
res = graded
res = res * (1 - water_a[..., None]) + water * water_a[..., None]
res = res * (1 - sky_a[..., None]) + sky * sky_a[..., None]
Image.fromarray((np.clip(res, 0, 1) * 255 + 0.5).astype('uint8')).save(out)
print('saved', out)
