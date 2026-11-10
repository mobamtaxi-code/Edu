# 과정정리_양식.pptx의 배치(도형 위치·크기·색)를 그대로 두고 텍스트만 바꾸고, 이미지 칸에 실제 중간 결과를 넣음
import sys, os
from pptx import Presentation
from pptx.util import Pt, Emu
from PIL import Image

base, out = sys.argv[1], sys.argv[2]
W = f'{base}/작업'
tmpdir = os.path.dirname(out)
prs = Presentation(f'{base}/과정정리_양식.pptx')
slide = prs.slides[0]
shapes = {sh.name: sh for sh in slide.shapes}

def set_text(name, lines, size=None):
    tf = shapes[name].text_frame
    paras = tf.paragraphs
    for i, para in enumerate(paras):
        runs = para.runs
        txt = lines[i] if i < len(lines) else ''
        runs[0].text = txt
        for r in runs[1:]:
            r._r.getparent().remove(r._r)
        if size:
            runs[0].font.size = Pt(size)

set_text('person', ['정성택 · 4학년'])
set_text('intent', ['[의도] 저녁 산책하는 시민이 노을빛에 빛나는 외피와 고요한 수면을 느끼게 한다'], 17)
set_text('criteria', ['[확인 기준] ① 외피: 해 쪽 면에 노을빛 반사광이 맺히는가   ② 수면: 노을색이 비치며 잔잔해 보이는가'], 14.5)

steps = [
    dict(title='1. 시간대를 저녁으로', flow='00_원본.png → v01.png',
         op=['하늘 노을·수면 반사·전체 저녁 톤', '마스크 01~03 + Python 색 보정'],
         dec=['채택', '이미지는 그대로, 마스크로 보정'],
         img='v01.png', crop=(0, 0, 658, 316)),
    dict(title='2. 중정·전경 밝히기', flow='v01.png → v02.png',
         op=['밝기 +30%, 가로등 12, 사람 19', '마스크 06·07 + Python 그리기'],
         dec=['채택', '산책·휴식하는 모습이 보이게'],
         img='v02.png', crop=(80, 188, 600, 438)),
    dict(title='3. 외피 반사광+그림자', flow='v02.png → v03.png',
         op=['해 쪽 주황 반사광, 외피 그림자 옅게', '마스크 04 + Python 색 보정'],
         dec=['기각', '그림자를 옅게 하니 입체감 사라짐'],
         img='v03.png', crop=(170, 165, 555, 350)),
    dict(title='4. 반사광+저녁 그림자', flow='v02.png → v02-2.png',
         op=['외피 반사광만, 그림자 저녁 방향으로', '마스크 04 + 그림자 투영(Python)'],
         dec=['채택 (최종)', '입체감 유지, 빛·그림자 방향 일치'],
         img='v02-2.png', crop=(100, 180, 620, 430)),
]

for i, st in enumerate(steps, 1):
    set_text(f'step{i}_title', [st['title']], 14.5)
    set_text(f'step{i}_flow', [st['flow']], 11.5)
    set_text(f'step{i}_operation', st['op'], 10.5)
    set_text(f'step{i}_decision', st['dec'], 10.5)
    # 이미지 칸: 칸 비율에 맞춰 같은 부분을 잘라 넣음
    box = shapes[f'step{i}_image']
    set_text(f'step{i}_image', ['', ''])
    # 모든 단계를 같은 시점(전체 이미지)으로: 칸 안에 비율을 유지해 가운데 맞춤
    im = Image.open(f'{W}/{st["img"]}')
    p = os.path.join(tmpdir, f'step{i}.png'); im.save(p)
    bw, bh = box.width, box.height
    ih = bh; iw = int(bh * im.width / im.height)
    if iw > bw: iw = bw; ih = int(bw * im.height / im.width)
    slide.shapes.add_picture(p, box.left + (bw - iw) // 2, box.top + (bh - ih) // 2, iw, ih)

set_text('key_decision', ['[핵심 판단] 처음에는 외피 그림자도 옅게 했지만(v03), 입체감이 사라져 v02로 돌아가 반사광만 넣고 그림자를 저녁 방향으로 바꿨다.'], 13)
set_text('result', ['[결과] 한낮 사진이 노을 하늘·잔잔한 반사 수면·해 쪽이 빛나는 외피·가로등 아래 산책하는 사람이 있는 저녁 장면이 됐다.'], 12.5)
set_text('limitation', ['[한계] 그림자는 건물 윤곽을 늘인 근사치(실제 높이 계산 아님), 사람은 저해상도라 단순한 형상, 원본 워터마크가 남아 있음.'], 11.5)

prs.save(out)
print('saved', out)
