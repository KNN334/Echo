"""Self-contained research dashboard; missing samples create visible gaps."""
import csv
import html
import json
from pathlib import Path
from collections import defaultdict
import numpy as np
from .common import read_json


def build_report(output):
    out=Path(output)
    summary=read_json(out/'summary.json')
    with (out/'frames.csv').open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    groups=defaultdict(list)
    for row in rows:groups[row['case_id']].append(row)
    parts=['<!doctype html><meta charset="utf-8"><title>Echo 研究结果</title>',
           '<style>body{font:16px system-ui;max-width:1080px;margin:32px auto;padding:0 20px;color:#172b3a} section{margin:28px 0} table{border-collapse:collapse;width:100%}th,td{border-bottom:1px solid #ddd;text-align:left;padding:8px}svg{width:100%;height:auto}img{max-width:100%}.note{background:#fff2cf;padding:14px}a{color:#12648c}</style>',
           '<h1>CAMUS / EchoNet 研究结果</h1>',
           '<p class="note">'+html.escape(summary['experiment_type'])+'。人工关键点、独立 CO 参考缺失时不计算其误差。灰色原始容积，蓝色分析曲线；断线表示无效或缺失。</p>',
           f"<p>患者 {summary['patients']}，标注帧 {summary['labeled_frames']}，失败病例 {summary['cases_failed']}，Dice {summary['dice_patient_mean']}，HD95(mm) {summary['hd95_mm']}</p>",
           '<p><a href="frames.csv">逐帧特征</a> · <a href="function.csv">EDV / ESV / SV / EF / CO</a> · <a href="structure.csv">结构误差</a> · <a href="summary.json">完整指标及溯源</a></p>']
    parts.append('<h2>功能指标 MAE（按参考口径分开）</h2><table><tr><th>口径</th><th>指标</th><th>MAE</th><th>单位</th><th>患者数</th></tr>')
    for method,metrics in summary['function'].items():
        for key,value in metrics.items():
            parts.append('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in (method,key,value['mae'],value['unit'],value['n_patients']))+'</tr>')
    parts.append('</table>')
    for key,records in groups.items():
        parts.append('<section><h2>'+html.escape(key)+'</h2>')
        w,h=900,220
        values=[float(r['volume_ml']) for r in records if r['volume_ml']]
        if values:
            low,high=min(values),max(values)
            span=max(high-low,1.)
            parts.append(f'<svg viewBox="0 0 {w} {h+35}" role="img" aria-label="容积曲线，单位毫升"><line x1="50" y1="{h}" x2="880" y2="{h}" stroke="#bbb"/>')
            for name,color in [('volume_ml','#9a9a9a'),('analysis_volume_ml','#12648c')]:
                segment=[]
                def emit():
                    if segment:parts.append('<polyline fill="none" stroke="'+color+'" stroke-width="2" points="'+' '.join(segment)+'"/>')
                for i,r in enumerate(records):
                    if r[name] and (name=='volume_ml' or r['valid']=='True'):
                        x=50+i/max(1,len(records)-1)*830
                        y=h-15-(float(r[name])-low)/span*(h-35)
                        segment.append(f'{x:.1f},{y:.1f}')
                    else:emit();segment=[]
                emit()
            parts.append(f'<text x="3" y="25">{high:.1f}</text><text x="3" y="{h-10}">{low:.1f}</text><text x="4" y="{h+20}">mL</text><text x="400" y="{h+25}">Frame index</text></svg>')
        for image in sorted(out.glob(key+'_*_overlay.png'))[:2]:
            parts.append('<img src="'+html.escape(image.name)+'" alt="左侧预测，右侧专家参考">')
        parts.append('</section>')
    (out/'report.html').write_text('\n'.join(parts),encoding='utf-8')
    return str(out/'report.html')
