from pathlib import Path
import time
import numpy as np
from PIL import Image, ImageDraw
from .common import read_json, write_json, write_csv, provenance, sha256
from .preprocess import Transform
from .geometry import mask_features, biplane_volume, functional, infer_landmarks
from .metrics import segmentation_metrics, landmark_errors, mae_summary
from .temporal import quality_flags, smooth_curve, detect_beats


def overlay(frame, mask, points=None):
    a = np.repeat(frame[:, :, None], 3, 2).astype(np.uint8)
    a[mask.astype(bool)] = (a[mask.astype(bool)] * .6 + np.array([20,220,80]) * .4).astype(np.uint8)
    image = Image.fromarray(a)
    draw = ImageDraw.Draw(image)
    if points:
        for key in ("apex", "base_left", "base_right"):
            x,y = points[key]
            draw.ellipse((x-2,y-2,x+2,y+2), fill=(255,90,20))
    return image


def evaluate(processed, weights, output, split="test", normalization=None, device="cuda", limit=None,
             temporal=False, gate=False, references=None, manual_landmarks=None):
    from .model import load_checkpoint, predict
    root, out = Path(processed), Path(output)
    out.mkdir(parents=True, exist_ok=True)
    model, ckpt = load_checkpoint(weights, device)
    norm = read_json(normalization) if normalization else ckpt
    if norm.get("mean") is None or norm.get("std") is None:
        raise ValueError("checkpoint has no normalization: supply reviewed --normalization JSON")
    mean, std = norm["mean"], norm["std"]
    if np.asarray(mean).shape != (3,) or np.asarray(std).shape != (3,) or min(std) <= 0:
        raise ValueError("normalization requires three means and three positive standard deviations")
    cases = [x for x in read_json(root / "manifest.json")["cases"] if x["split"] == split]
    if limit:
        cases = cases[:limit]
    refs = read_json(references) if references else {}
    manual = read_json(manual_landmarks) if manual_landmarks else {}
    structures, frame_rows, functional_rows, beat_rows, failures = [], [], [], [], []
    biplane = {}
    started = time.perf_counter()
    for case in cases:
        key, pid, view = case["case_id"], case["patient_id"], case["view"]
        try:
            meta = read_json(root / (key+".json"))
            with np.load(root / (key+".npz")) as data:
                frames = data["frames"]
                labeled = data["labeled"]
                gt_original = {int(i): g for i,g in zip(data["original_gt_indices"], data["original_gt"])}
            probabilities = predict(model, frames, mean, std, device)
            pred = probabilities >= .5
            np.savez_compressed(out/(key+"_pred.npz"), masks=pred.astype(np.uint8))
            tr = meta["audit"]["transform"]
            transform = Transform(tuple(tr["original_hw"]), tuple(tr["crop_xyxy"]), tuple(tr["output_hw"]))
            spacing = meta["audit"]["spacing_xy_mm"]
            times = meta["audit"]["timestamps_s"]
            features, truth_features = {}, {}
            valid, values = [], []
            for index, small in enumerate(pred):
                original = transform.restore_mask(small)
                # Manual landmarks only used for evaluation, never fed into prediction geometry.
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
                        # QA has predicted overlay and reference overlay side by side.
                        reference_small = transform.image(gt, label=True)
                        canvas = Image.new("RGB", (frames.shape[2]*2, frames.shape[1]+20), "white")
                        canvas.paste(overlay(frames[index], small), (0,20))
                        canvas.paste(overlay(frames[index], reference_small), (frames.shape[2],20))
                        ImageDraw.Draw(canvas).text((2,2), key+f" frame {index}", fill="black")
                        canvas.save(out/(key+f"_{index}_overlay.png"))
            curve = smooth_curve(values, valid) if temporal else np.asarray(values)
            for row, volume in zip(frame_rows[-len(frames):],curve):
                row["analysis_volume_ml"] = float(volume) if np.isfinite(volume) else None
                row["temporal_filtered"] = temporal
            phases = meta.get("phases", {})
            if "ED" in phases and "ES" in phases:
                ed,es = phases["ED"],phases["ES"]
                hr = refs.get(pid,{}).get("HR")
                edv = float(curve[ed]) if valid[ed] and np.isfinite(curve[ed]) else None
                esv = float(curve[es]) if valid[es] and np.isfinite(curve[es]) else None
                f = functional(edv,esv,hr)
                # GT-contour derived targets are explicitly separated from independent clinical labels.
                tf = functional(truth_features.get(ed,{}).get("volume_ml"), truth_features.get(es,{}).get("volume_ml"))
                fr = {"patient_id":pid,"view":view,"method":"single_plane_area_length", **{k:v for k,v in f.items() if k!='issues'},
                      "issues":";".join(f['issues']), "reference_scope":"same_geometry_from_expert_ED_ES_contours"}
                fr.update({"ref_"+k:tf[k] for k in ("EDV","ESV","SV","EF","CO")})
                functional_rows.append(fr)
                for phase, index in phases.items():
                    biplane.setdefault(pid,{}).setdefault(phase,{})[view] = {
                        "pred": features[index] if valid[index] else {}, "truth":truth_features.get(index,{})}
            if meta.get("sequence_type") == "sequence":
                for beat in detect_beats(curve,times,valid):
                    beat_rows.append({"patient_id":pid,"case_id":key,"view":view,**{k:v for k,v in beat.items() if k!='issues'}})
            if len(cases) <= 10 or (cases.index(case)+1)%20==0:
                print(f"evaluated {key}",flush=True)
        except Exception as e:
            failures.append({"case_id":key,"error":str(e)})
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
             "issues":";".join(f['issues']),"reference_scope":"same_geometry_from_expert_ED_ES_contours"}
        row.update({"ref_"+k:tf[k] for k in ('EDV','ESV','SV','EF','CO')})
        functional_rows.append(row)
        # Independent supplied references have their own metrics group, including CO when available.
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
    def mean_available(key, unit=None):
        # Average frames within patient then patients; explicit unit filter.
        groups={}
        for row in structures:
            if row.get(key) is not None and (unit is None or row['distance_unit']==unit):
                groups.setdefault(row['patient_id'],[]).append(row[key])
        return float(np.mean([np.mean(a) for a in groups.values()])) if groups else None
    summary={**provenance(),"split":split,"weights_sha256":sha256(weights),"normalization":{"mean":mean,"std":std},
             "cases_attempted":len(cases),"cases_failed":len(failures),"labeled_frames":len(structures),
             "patients":len(set(x['patient_id'] for x in structures)),"failures":failures,
             "dice_patient_mean":mean_available('dice'),"assd_mm":mean_available('assd','mm'),
             "hd95_mm":mean_available('hd95','mm'),"assd_pixel":mean_available('assd','pixel'),
             "hd95_pixel":mean_available('hd95','pixel'),
             "manual_keypoint_error":mean_available('manual_keypoint_error'),
             "contour_derived_keypoint_error":mean_available('contour_derived_keypoint_error'),
             "keypoint_scope":"manual_when_sidecar_available_else_contour_derived_proxy_only",
             "function":summaries,"frames":len(frame_rows),"beats":len(beat_rows),
             "valid_frame_fraction":float(np.mean([x['valid'] for x in frame_rows])) if frame_rows else None,
             "timing_seconds":duration,"end_to_end_fps":len(frame_rows)/duration,
             "temporal":temporal,"gate":gate,
             "experiment_type":ckpt.get('run',{}).get('experiment_type','external_checkpoint_cross_dataset')}
    for name, rows in [('frames',frame_rows),('structure',structures),('function',functional_rows),('beats',beat_rows)]:
        write_csv(out/(name+'.csv'),rows)
    write_json(out/'summary.json',summary)
    return summary
