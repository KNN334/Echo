"""Summarize measured results and missing labels without inventing clinical references."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import shutil
import numpy as np


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--run',default='runs/full_baseline')
    p.add_argument('--checkpoint',default='checkpoints/camus_full')
    p.add_argument('--processed',default='data/processed/camus')
    p.add_argument('--output',default='reports/full_baseline')
    a=p.parse_args()
    root,out=Path(a.processed),Path(a.output)
    out.mkdir(parents=True,exist_ok=True)
    summary=json.loads((Path(a.run)/'summary.json').read_text())
    training=json.loads((Path(a.checkpoint)/'run.json').read_text())
    manifest=json.loads((root/'manifest.json').read_text())
    audit_rows=[]
    for case in manifest['cases']:
        meta=json.loads((root/(case['case_id']+'.json')).read_text())
        audit=meta['audit']
        audit_rows.append({'patient_id':case['patient_id'],'view':case['view'],'split':case['split'],
                           'frames':case['frames'],'labeled_frames':case['labeled_frames'],
                           'fps':audit['fps'],'spacing_x_mm':audit['spacing_xy_mm'][0],
                           'spacing_y_mm':audit['spacing_xy_mm'][1],
                           'timestamp_source':audit['timestamp_source'],
                           'image_quality':meta.get('config',{}).get('ImageQuality'),
                           'retained_pixel_fraction':audit.get('retained_pixel_fraction'),
                           'removed_foreground_pixels':audit.get('removed_foreground_label_pixels'),
                           'image_support_excludes_reference_foreground_pixels':audit.get('image_support_excludes_reference_foreground_pixels',0),
                           'roi_reviewed':audit['roi_reviewed'],'sequence_type':meta['sequence_type']})
    with (out/'preprocessing_audit.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(audit_rows[0]));w.writeheader();w.writerows(audit_rows)
    audit_summary={'patients':len(set(x['patient_id'] for x in audit_rows)),'views':len(audit_rows),
                   'frames':sum(x['frames'] for x in audit_rows),'expert_frames':sum(x['labeled_frames'] for x in audit_rows),
                   'fps_range':[min(x['fps'] for x in audit_rows),max(x['fps'] for x in audit_rows)],
                   'splits_patients':dict(Counter(next(x['split'] for x in audit_rows if x['patient_id']==pid)
                                   for pid in set(x['patient_id'] for x in audit_rows))),
                   'sequence_types':dict(Counter(x['sequence_type'] for x in audit_rows)),
                   'roi_removes_foreground_cases':sum(bool(x['removed_foreground_pixels']) for x in audit_rows)}
    audit_summary['image_support_exclusion_review_cases']=sum(bool(x['image_support_excludes_reference_foreground_pixels']) for x in audit_rows)
    (out/'preprocessing_summary.json').write_text(json.dumps(audit_summary,indent=2))
    for name in ('summary.json','function.csv','structure.csv','frames.csv','beats.csv'):
        shutil.copyfile(Path(a.run)/name,out/name)
    shutil.copyfile(Path(a.checkpoint)/'run.json',out/'training_run.json')
    shutil.copyfile(Path(a.checkpoint)/'training.csv',out/'training_history.csv')
    with (Path(a.run)/'function.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    primary=[x for x in rows if x['method']=='20_disks_shorter_axis']
    if primary:
        with (out/'patient_features.csv').open('w',encoding='utf-8-sig',newline='') as f:
            keys=['patient_id','EDV','ESV','SV','EF','HR','CO','ref_EDV','ref_ESV','ref_SV','ref_EF','ref_CO','issues','reference_scope','phase_selection']
            w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');w.writeheader();w.writerows(primary)
    def fmt(value):return '不可计算' if value is None else f'{value:.4f}'
    lines=['# CAMUS / EchoNet 全量基线实测报告','',
           f"代码提交：`{summary['git_commit']}`；权重 SHA256：`{summary['weights_sha256']}`。",'',
           f"预处理 {audit_summary['patients']} 名患者 / {audit_summary['views']} 个切面 / {audit_summary['frames']} 帧；ED/ES 专家标注 {audit_summary['expert_frames']} 帧。",'',
           f"训练/验证/测试患者：{len(training['train_patients'])}/{len(training['val_patients'])}/{len(training['test_patients'])}。测试尝试 {summary['patients_attempted']} 名患者、{summary['cases_attempted']} 个切面，失败 {summary['cases_failed']} 个切面。",'',
           '## 结构误差','',
           '| 指标 | 实测值 |','|---|---:|',
           f"| 患者均值 Dice | {fmt(summary['dice_patient_mean'])} |",
           f"| ASSD (mm) | {fmt(summary['assd_mm'])} |",
           f"| HD95 (mm) | {fmt(summary['hd95_mm'])} |",
           f"| 轮廓派生关键点代理误差 (mm) | {fmt(summary['contour_derived_keypoint_error'])} |",
           f"| 人工解剖关键点误差 | {fmt(summary['manual_keypoint_error'])} |",'',
           '代理关键点来自对预测/专家轮廓使用相同几何算法；没有独立人工解剖点标签，因此不能将代理误差解释为真实解剖定位精度。','',
           '## 功能 MAE','',
           '| 计算与参考口径 | 指标 | MAE | 单位 | 有效患者 |','|---|---|---:|---|---:|']
    for method,metrics in summary['function'].items():
        for key,value in metrics.items():
            lines.append(f"| {method} | {key} | {fmt(value['mae'])} | {value['unit']} | {value['n_patients']} |")
    lines+=['','EDV/ESV/SV 的主要参考为专家轮廓经同一几何方法计算，不能冒充独立临床金标准。`biplane_vs_CAMUS_reported_EF` 才是与数据集 `Info.cfg` EF 标签的比较。参考相位和自动极值选相位结果分开报告。','',
            'CAMUS 仅提供 ED→ES 半周期，不能由此可靠推导完整周期心率；没有独立 CO 真值，因此 CO 及其 MAE 为不可计算，绝不按双倍收缩时间伪造。','',
            '## 可用性与限制','',
            f"原始基线几何有效帧占比：{fmt(summary['valid_frame_fraction'])}，属于研究性几何可计算率，不是经人工验证的临床有效覆盖率。",'',
            '默认 ROI 尚未逐病例人工审阅；自动最大声窗可去除分离文字，但与声窗相连的文字仍需人工排除。门控和平滑接口已实现，不能把未验证的阈值称为已证实有效的质量分类器。','',
            f"实测端到端处理速度：{fmt(summary['end_to_end_fps'])} FPS（本机、本次输入及当前实现，不宣称通用实时性能）。",'',
            '训练为 EchoNet 官方架构/权重上的 CAMUS 适配（AdamW、mean BCE、训练集归一化、冻结 BN 运行统计），不是官方 EchoNet 论文实验逐项复现。采用固定自定义患者划分，不是 CAMUS 官方排行榜分数。','',
            '详细中间特征：`patient_features.csv`、`frames.csv`；完整参考口径与置信区间：`summary.json`；每病例几何与坐标转换见运行目录 `*_features.json`。']
    (out/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(audit_summary,indent=2))


if __name__=='__main__':main()
