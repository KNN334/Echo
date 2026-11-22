"""Render explanatory views of the checked reconstruction (requires Pillow)."""

import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'hardware/kicad/orthogonal88'
DATA=json.loads((OUT/'geometry.json').read_text(encoding='utf-8'))
COLORS=['#ff8585','#51d3ad','#6eafff','#c59bff']
BG='#0d1728';FG='#edf3fb';MUTED='#b0bfd1'


def font(size):return ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',size)


def render():
    im=Image.new('RGB',(1800,1400),BG);d=ImageDraw.Draw(im)
    d.text((60,36),'论文正交电极 · 88 通道重建',font=font(46),fill=FG)
    d.text((62,105),'四臂 13 × 6 子阵元 + 中央 6 × 6 独立子阵元；四种颜色表示四个信号层',font=font(24),fill=MUTED)
    xy=lambda p:(520+p[0]*32,750+p[1]*32)
    d.rectangle([xy((-14,-18)),xy((14,14))],outline='#40516a',width=2)
    for c in DATA['channels']:
        color=COLORS[c['layer']-1]
        paths=[c['route']]
        if c['kind']=='arm':paths.append(c['sites'])
        for path in paths:d.line([xy(p) for p in path],fill=color,width=2)
        for p in c['sites']:
            r=.22/math.sqrt(2)
            d.polygon([xy((p[0]+x,p[1]+y)) for x,y in [(0,-r),(r,0),(0,r),(-r,0)]],fill=color)
        d.polygon([xy(p) for p in c['tail_corners']],fill=color)
    d.text((85,1220),'总图：隐藏 RETURN / SHIELD，以便看清信号引线',font=font(22),fill=MUTED)
    d.text((85,1260),'不同信号层之间允许交叉；每张单层图独立检查',font=font(22),fill=MUTED)
    d.text((1060,185),'中央 36 路（展开到 U / V 坐标）',font=font(26),fill=FG)
    for c in DATA['channels']:
        if c['kind']!='center':continue
        x=1115+(c['column']-1)*90;y=300+(c['row']-1)*90
        d.rounded_rectangle((x-33,y-33,x+33,y+33),radius=5,fill=COLORS[c['layer']-1])
        d.text((x,y),f'R{c["row"]}C{c["column"]}',font=font(15),fill=BG,anchor='mm')
    d.text((1065,812),'中心间距 0.4 mm；中央各格独立寻址',font=font(23),fill=MUTED)
    d.text((1065,854),'行 / 列仅在采集时成组控制，不能硬短接',font=font(23),fill=MUTED)
    for i,(arm,color) in enumerate(zip(['U_NEG','V_POS','U_POS','V_NEG'],COLORS),1):
        y=945+(i-1)*53
        d.rectangle((1065,y+5,1090,y+30),fill=color)
        d.text((1110,y),f'E{i}  {arm}：13 臂通道 + 9 中央通道',font=font(21),fill=FG)
    d.text((1065,1190),'拓扑与节距依据论文；层分配、接点、',font=font(22),fill=MUTED)
    d.text((1065,1226),'出线、端子和外形为本次工程重建。',font=font(22),fill=MUTED)
    d.text((62,1340),'可编辑电极掩模与连接拓扑 · 未完成层间开窗 / 材料堆叠与加工验证',font=font(23),fill='#efc67a')
    im.save(OUT/'exports/orthogonal88_preview.png')
    grid=Image.new('RGB',(1800,1400),'white');g=ImageDraw.Draw(grid)
    g.text((55,25),'E1 - E4 单层信号掩模（同一方向、同一比例）',font=font(32),fill='#132844')
    for layer in range(1,5):
        ox=80+((layer-1)%2)*875;oy=110+((layer-1)//2)*630
        transform=lambda p:(ox+390+p[0]*19,oy+365+p[1]*19)
        g.text((ox+30,oy),f'E{layer} / 22 通道 / 87 个接点',font=font(24),fill='#132844')
        for c in DATA['channels']:
            if c['layer']!=layer:continue
            paths=[c['route']]+([c['sites']] if c['kind']=='arm' else [])
            for path in paths:g.line([transform(p) for p in path],fill='#203e62',width=2)
            for p in c['sites']:
                r=.22/math.sqrt(2)
                g.polygon([transform((p[0]+x,p[1]+y)) for x,y in [(0,-r),(r,0),(0,r),(-r,0)]],fill='#203e62')
            g.polygon([transform(p) for p in c['tail_corners']],fill='#203e62')
    grid.save(OUT/'exports/signal_layers_preview.png')


if __name__=='__main__':render()
