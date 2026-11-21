"""评估流水线：执行分割推理，导出逐帧特征、结构误差、功能和时序结果。"""
from pathlib import Path
import time
import numpy as np
from PIL import Image, ImageDraw
from ..visualization.overlay import overlay
from ..utils.io import read_json, write_json, write_csv
from ..utils.hash import provenance, sha256
from ..data.transforms import Transform
from ..geometry.mask_features import mask_features, infer_landmarks
from ..geometry.volume import biplane_volume
from ..geometry.functional import functional
from ..metrics.segmentation import segmentation_metrics, landmark_errors
from ..metrics.cardiac import mae_summary
from ..metrics.temporal import phase_errors
from ..temporal.quality_gate import quality_flags
from ..temporal.smoothing import smooth_curve
from ..temporal.beat_detection import detect_beats
from ..data.base import build_adapter


def evaluate(test_path, weights, output, split="test", normalization=None, device="cuda", limit=None,
             temporal=False, gate=False, references=None, manual_landmarks=None,
             model_config=None, adapter='camus'):
    """运行分割评估并导出结构、功能、时间指标及中间特征。

    test_path 提供 scripts/prepare_data.py 生成的固定测试集清单，weights 提供模型和归一化参数。
    temporal 开启曲线平滑，gate 开启质量筛选；参考值与人工关键点由可选
    JSON 文件提供。输出逐帧特征、掩膜、CSV、summary.json 和 HTML 报告。
    """
    from ..models.build import load_checkpoint, predict
    source = build_adapter(test_path, split, adapter)
    cases = source.cases
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    model, ckpt = load_checkpoint(weights, device, model_config) if model_config is not None else load_checkpoint(weights, device)
    norm = read_json(normalization) if normalization else ckpt
    if norm.get("mean") is None or norm.get("std") is None:
        raise ValueError("checkpoint has no normalization: supply reviewed --normalization JSON")
    mean, std = norm["mean"], norm["std"]
    if np.asarray(mean).shape != (3,) or np.asarray(std).shape != (3,) or min(std) <= 0:
        raise ValueError("normalization requires three means and three positive standard deviations")
    if limit:
        cases = cases[:limit]
    refs = read_json(references) if references else {}
    manual = read_json(manual_landmarks) if manual_landmarks else {}
    structures, frame_rows, functional_rows, beat_rows, failures = [], [], [], [], []
    biplane = {}
    camus_ef = {}
    started = time.perf_counter()
    for case in cases:
        key, pid, view = case["case_id"], case["patient_id"], case["view"]
        checkpoint_lengths=[len(x) for x in (structures,frame_rows,functional_rows,beat_rows)]
        try:
            data, meta = source.load_case(case)
            frames = data['frames']
            gt_original = {int(i): g for i,g in zip(data['original_gt_indices'], data['original_gt'])}
            probabilities = predict(model, frames, mean, std, device)
            pred = probabilities >= .5
            # 固定 0.5 阈值生成掩膜；先恢复原图再按原始像素间距测量。
            np.savez_compressed(out/(key+"_pred.npz"), masks=pred.astype(np.uint8))
            tr = meta["audit"]["transform"]
            transform = Transform(tuple(tr["original_hw"]), tuple(tr["crop_xyxy"]), tuple(tr["output_hw"]))
            spacing = meta["audit"]["spacing_xy_mm"]
            times = meta["audit"]["timestamps_s"]
            if times is not None and len(times)!=len(frames):
                raise ValueError('preprocessed timestamps do not match frames; regenerate processed data')
            features, truth_features = {}, {}
            valid, values = [], []
            for index, small in enumerate(pred):
                original = transform.restore_mask(small)
                # 人工关键点只用于评价，不参与预测侧几何特征提取。
                f = mask_features(original, spacing)
                features[index] = f
                confidence = float(probabilities[index][small].mean()) if small.any() else 0.
                flags = quality_flags(f, meta["audit"]["roi_reviewed"], confidence)
                valid.append(f.get("valid", False) and (not gate or not flags))
                values.append(f.get("volume_ml") if f.get("volume_ml") is not None else np.nan)
                lp = f.get("landmarks_xy")
                row = {"case_id": key, "patient_id": pid, "view": view, "frame": index,
                       "time_s": times[index] if times is not None else None,
                       "volume_ml": f.get("volume_ml"), "area_mm2": f.get("area_mm2"),
                       "long_axis_mm": f.get("long_axis_mm"), "valid": valid[-1],
                       "confidence": confidence, "quality_flags": ";".join(flags)}
                if lp:
                    for name in ("apex", "base_left", "base_right"):
                        xy = lp[name]
                        row[name+"_x_original"],row[name+"_y_original"] = xy
                frame_rows.append(row)
                if index in gt_original:
                    gt = gt_original[index]
                    tf = mask_features(gt, spacing)
                    truth_features[index] = tf
                    m = segmentation_metrics(original, gt, spacing)
                    derived = landmark_errors(lp, infer_landmarks(gt, spacing or [1.,1.]), spacing)
                    manual_ref = manual.get(key, {}).get(str(index))
                    actual = landmark_errors(lp, manual_ref, spacing)
                    sr = {"case_id": key, "patient_id": pid, "view": view, "frame": index, **m,
                          "manual_keypoint_error": float(np.mean(list(actual.values()))) if actual else None,
                          "contour_derived_keypoint_error": float(np.mean(list(derived.values()))) if derived else None,
                          "keypoint_unit": "mm" if spacing is not None else "pixel"}
                    if derived:
                        sr.update({"contour_"+k+"_error":v for k,v in derived.items()})
                    if actual:
                        sr.update({"manual_"+k+"_error":v for k,v in actual.items()})
                    structures.append(sr)
                    if len(structures) <= 16:
                        # 质量检查图左侧为预测，右侧为专家参考；点位转换到显示坐标。
                        reference_small = transform.image(gt, label=True)
                        canvas = Image.new("RGB", (frames.shape[2]*2, frames.shape[1]+20), "white")
                        def processed_points(points):
                            """将原图坐标关键点转换到预处理图坐标供叠图显示。"""
                            return {name:transform.points(np.array([points[name]]))[0].tolist()
                                    for name in ('apex','base_left','base_right')} if points else None
                        canvas.paste(overlay(frames[index], small,processed_points(lp)), (0,20))
                        canvas.paste(overlay(frames[index], reference_small,processed_points(tf.get('landmarks_xy'))), (frames.shape[2],20))
                        ImageDraw.Draw(canvas).text((2,2), key+f" frame {index}", fill="black")
                        canvas.save(out/(key+f"_{index}_overlay.png"))
            curve = smooth_curve(values, valid) if temporal else np.asarray(values)
            for row, volume in zip(frame_rows[-len(frames):],curve):
                row["analysis_volume_ml"] = float(volume) if np.isfinite(volume) else None
                row["temporal_filtered"] = temporal
            phases = meta.get("phases", {})
            reported_ef=meta.get('config',{}).get('EF')
            if reported_ef is not None:
                camus_ef[pid]=float(reported_ef)
            write_json(out/(key+'_features.json'), {'metadata':meta,'frames':features})
            if "ED" in phases and "ES" in phases:
                ed,es = phases["ED"],phases["ES"]
                hr = refs.get(pid,{}).get("HR")
                edv = float(curve[ed]) if valid[ed] and np.isfinite(curve[ed]) else None
                esv = float(curve[es]) if valid[es] and np.isfinite(curve[es]) else None
                f = functional(edv,esv,hr)
                # 同一几何法从专家轮廓计算的参考量，单独命名，不能称为独立临床真值。
                tf = functional(truth_features.get(ed,{}).get("volume_ml"), truth_features.get(es,{}).get("volume_ml"))
                fr = {"patient_id":pid,"view":view,"method":"single_plane_area_length", **{k:v for k,v in f.items() if k!='issues'},
                      "issues":";".join(f['issues']), "reference_scope":"same_geometry_from_expert_ED_ES_contours",
                      "phase_selection":"reference_ED_ES_for_segmentation_error_isolation"}
                fr.update({"ref_"+k:tf[k] for k in ("EDV","ESV","SV","EF","CO")})
                functional_rows.append(fr)
                # 分别记录参考 ED/ES 帧上的分割误差和预测曲线自动选相位的结果。
                valid_indices=np.flatnonzero(np.asarray(valid)&np.isfinite(curve))
                if len(valid_indices)>=2:
                    auto_ed=int(valid_indices[np.argmax(curve[valid_indices])])
                    after=valid_indices[valid_indices>auto_ed]
                    if len(after):
                        auto_es=int(after[np.argmin(curve[after])])
                        af=functional(float(curve[auto_ed]),float(curve[auto_es]),hr)
                        ar={**fr,**{k:v for k,v in af.items() if k!='issues'},
                            "method":"single_plane_auto_extrema_"+view,
                            "phase_selection":"predicted_ED_then_ES_within_available_sequence",
                            "ed_frame":auto_ed,"es_frame":auto_es,
                            **phase_errors(auto_ed, auto_es, ed, es, times),
                            "issues":";".join(af['issues'])}
                        functional_rows.append(ar)
                for phase, index in phases.items():
                    biplane.setdefault(pid,{}).setdefault(phase,{})[view] = {
                        "pred": features[index] if valid[index] else {}, "truth":truth_features.get(index,{})}
            if meta.get("sequence_type") == "sequence":
                for beat in detect_beats(curve,times,valid):
                    beat_rows.append({"patient_id":pid,"case_id":key,"view":view,**{k:v for k,v in beat.items() if k!='issues'}})
            if len(cases) <= 10 or (cases.index(case)+1)%20==0:
                print(f"evaluated {key}",flush=True)
        except Exception as e:
            import traceback
            # 病例失败时撤销该病例已追加的结果，避免半成品混入汇总。
            for collection,length in zip((structures,frame_rows,functional_rows,beat_rows),checkpoint_lengths):
                del collection[length:]
            for phase in biplane.get(pid,{}).values():
                phase.pop(view,None)
            failures.append({"case_id":key,"error":str(e),'traceback':traceback.format_exc()})
    for pid, phases in biplane.items():
        if not all(phase in phases and all(view in phases[phase] for view in ('2CH','4CH')) for phase in ('ED','ES')):
            continue
        predv, refv = {}, {}
        for phase in ('ED','ES'):
            a,b = phases[phase]['2CH'],phases[phase]['4CH']
            predv[phase] = biplane_volume(a['pred'],b['pred'])
            refv[phase] = biplane_volume(a['truth'],b['truth'])
        f = functional(predv['ED'],predv['ES'],refs.get(pid,{}).get('HR'))
        tf = functional(refv['ED'],refv['ES'])
        row={"patient_id":pid,"view":"biplane","method":"20_disks_shorter_axis",**{k:v for k,v in f.items() if k!='issues'},
             "issues":";".join(f['issues']),"reference_scope":"same_geometry_from_expert_ED_ES_contours",
             "phase_selection":"reference_ED_ES_for_segmentation_error_isolation"}
        row.update({"ref_"+k:tf[k] for k in ('EDV','ESV','SV','EF','CO')})
        functional_rows.append(row)
        if pid in camus_ef:
            reported={**row,"method":"biplane_vs_CAMUS_reported_EF","reference_scope":"CAMUS_Info_cfg_EF"}
            for k in ('EDV','ESV','SV','EF','CO'):
                reported['ref_'+k]=camus_ef[pid] if k=='EF' else None
            functional_rows.append(reported)
        # 外部独立参考单独汇总；CO 仅在参考文件提供时才能得到对应误差。
        if pid in refs:
            ext={**row,"method":"biplane_vs_supplied_reference","reference_scope":"external_reference_sidecar"}
            for k in ('EDV','ESV','SV','EF','CO'):
                ext['ref_'+k]=refs[pid].get(k)
            functional_rows.append(ext)
    duration=time.perf_counter()-started
    summaries={}
    for method in sorted(set(x['method'] for x in functional_rows)):
        if method=='single_plane_area_length':
            for view in ('2CH','4CH'):
                summaries[method+'_'+view]=mae_summary([x for x in functional_rows if x['method']==method and x['view']==view])
        else:
            summaries[method]=mae_summary([x for x in functional_rows if x['method']==method])
    attempted_patients=len(set(x['patient_id'] for x in cases))
    for method,metrics in summaries.items():
        for metric in metrics.values():
            metric['coverage_of_attempted_patients']=metric['n_patients']/attempted_patients if attempted_patients else 0.
    def mean_available(key, unit=None):
        """先求患者内均值再跨患者汇总，且可按距离单位筛选。"""
        # 先在患者内平均再跨患者平均，避免帧数多的患者获得额外权重。
        groups={}
        for row in structures:
            if row.get(key) is not None and (unit is None or row['distance_unit']==unit):
                groups.setdefault(row['patient_id'],[]).append(row[key])
        return float(np.mean([np.mean(a) for a in groups.values()])) if groups else None
    summary={**provenance(),"split":split,"weights_sha256":sha256(weights),"normalization":{"mean":mean,"std":std},
             "cases_attempted":len(cases),"cases_failed":len(failures),"labeled_frames":len(structures),
             "patients_attempted":attempted_patients,
             "patients":len(set(x['patient_id'] for x in structures)),"failures":failures,
             "dice_patient_mean":mean_available('dice'),"assd_mm":mean_available('assd','mm'),
             "hd95_mm":mean_available('hd95','mm'),"assd_pixel":mean_available('assd','pixel'),
             "hd95_pixel":mean_available('hd95','pixel'),
             "manual_keypoint_error":mean_available('manual_keypoint_error'),
             "contour_derived_keypoint_error":mean_available('contour_derived_keypoint_error'),
             "keypoint_distance_unit":'mm' if structures and all(x['keypoint_unit']=='mm' for x in structures) else 'pixel_or_mixed_review',
             "keypoint_scope":"manual_when_sidecar_available_else_contour_derived_proxy_only",
             "manual_keypoint_labeled_frames":sum(x['manual_keypoint_error'] is not None for x in structures),
             "contour_proxy_valid_frames":sum(x['contour_derived_keypoint_error'] is not None for x in structures),
             "reference_file_sha256":sha256(references) if references else None,
             "manual_landmark_file_sha256":sha256(manual_landmarks) if manual_landmarks else None,
             "function":summaries,"frames":len(frame_rows),"beats":len(beat_rows),
             "valid_frame_fraction":float(np.mean([x['valid'] for x in frame_rows])) if frame_rows else None,
             "timing_seconds":duration,"end_to_end_fps":len(frame_rows)/duration,
             "temporal":temporal,"gate":gate,
             "experiment_type":ckpt.get('run',{}).get('experiment_type','external_checkpoint_cross_dataset')}
    for name, rows in [('frames',frame_rows),('structure',structures),('function',functional_rows),('beats',beat_rows)]:
        write_csv(out/(name+'.csv'),rows)
    write_json(out/'summary.json',summary)
    from ..visualization.report import build_report
    build_report(out)
    return summary
