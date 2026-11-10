# 저녁 그림자: 해(건물 뒤 지평선, x≈430)의 반대쪽 = 보는 사람 쪽(화면 아래, 약간 왼쪽)으로 길고 부드럽게
import sys, numpy as np
from PIL import Image, ImageFilter

base, src, out = sys.argv[1], sys.argv[2], sys.argv[3]
img = np.array(Image.open(src).convert('RGB')).astype(np.float32) / 255.
H, W, _ = img.shape
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

def m(name):
    return np.array(Image.open(f'{base}/영역마스크/{name}.png').convert('L')).astype(np.float32) / 255.
def blur(a, r):
    return np.array(Image.fromarray(np.clip(a * 255, 0, 255).astype('uint8')).filter(ImageFilter.GaussianBlur(r))).astype(np.float32) / 255.

bld = np.clip(m('04_건물외피') + m('05_유리면') + m('06_중정'), 0, 1)
# 건물 바닥(그릇 모양 아래쪽) 부분만 그림자의 출발점으로: 외피 마스크의 아래쪽 절반
ys = np.where(bld.max(1) > 0.5)[0]
mid = (ys.min() + ys.max()) / 2
src_sil = bld * (yy > mid - 10)

# 그림자 방향(화면 기준): 해에서 건물을 지나 앞쪽으로. 낮은 해라 길게.
DX, DY, STEPS = -38.0, 105.0, 60
shadow = np.zeros((H, W), np.float32)
for i in range(STEPS + 1):
    k = i / STEPS
    dx, dy = int(round(DX * k)), int(round(DY * k))
    sh = np.roll(np.roll(src_sil, dy, axis=0), dx, axis=1)
    if dy > 0: sh[:dy] = 0
    if dx < 0: sh[:, dx:] = 0
    # 멀어질수록 옅고 흐릿하게(해 질 녘 긴 그림자의 반그림자)
    shadow = np.maximum(shadow, sh * (1 - 0.35 * k))
shadow = blur(shadow, 3)

# 그림자가 떨어질 수 있는 곳: 지면(연못·데크·잔디·산책로). 건물 자체·하늘·강은 제외
ground = (yy > 250).astype(np.float32) * (1 - bld) * (1 - m('03_오른쪽수면')) * (1 - m('02_왼쪽수면'))
ground = blur(ground, 1)
s = shadow * ground

# 새 그림자 안에서는 밝기를 하나의 '그림자 밝기'로 맞춤 -> 한낮 그림자 경계(밝은 연못/어두운 연못)가 사라짐
lum = img @ np.array([0.299, 0.587, 0.114], np.float32)
lsm = blur(lum, 3)
# 재질별로 그림자 밝기를 맞춤
#  - 연못·데크(어두운 면): 한낮 그림자 쪽(아주 어두움)과 햇빛 받던 쪽(밝음)을 같은 밝기 T로 -> 옛 경계 제거
#  - 잔디(초록): 질감 유지하며 일정 비율로만 어둡게
r_, g_, b_ = img[..., 0], img[..., 1], img[..., 2]
grass = blur(np.clip((g_ - (r_ + b_) / 2 - 0.02) / 0.05, 0, 1), 2)
T = 0.075
fac_pool = np.clip(T / np.maximum(blur(lum, 4), 1e-3), 0.12, 2.5)
fac = fac_pool * (1 - grass) + 0.62 * grass
w = np.clip(s * 1.9, 0, 1)[..., None]
cool = np.array([0.88, 0.90, 1.05])                   # 그림자 속은 하늘빛을 받아 약간 푸른 보라
shaded = img * fac[..., None] * cool
res = img * (1 - w) + shaded * w
Image.fromarray((np.clip(res, 0, 1) * 255 + 0.5).astype('uint8')).save(out)
Image.fromarray((np.clip(s, 0, 1) * 255).astype('uint8')).save(out.replace('.png', '_mask.png'))
print('saved', out)
