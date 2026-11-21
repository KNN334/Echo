Supplementary Table 2 | Patient-level LV segmentation performance by view and reference phase on CAMUS.
The frozen DeepLabV3–ResNet50 baseline was evaluated in all 82 test patients (164 view sequences; 328 expert-labeled frames). Each cell reports the mean ± sample standard deviation across patient means within the stated stratum. Overall values average four frames per patient; view-only and phase-only values average two; view–phase values use one. The strata overlap and do not constitute independent cohorts. Dice and intersection-over-union (IoU) were calculated from the binary predictions restored to original image coordinates and the original expert masks. IoU was computed per frame from intersection and union pixel counts before patient aggregation, rather than by transforming an averaged Dice. Average symmetric surface distance (ASSD), 95th-percentile Hausdorff distance (HD95) and maximum Hausdorff distance (HDmax) retain the original frozen metrics, evaluated using original pixel spacing in millimetres. The overall Dice/ASSD/HD95 patient values match Figure 2. No patient, frame or outlier was removed; no imputation, confidence intervals or hypothesis tests were used. ED and ES denote expert end-diastole and end-systole; 2CH/4CH denote independently acquired two-/four-chamber views. Intermediate frames have no expert reference. These are public CAMUS transthoracic half-sequences with 112 × 112 image caches, not wearable patch acquisitions. CAMUS: Leclerc et al., IEEE TMI (2019), doi:10.1109/TMI.2019.2900516; CC BY-NC-SA 4.0.

| Stratum | Patients n | Frames n | Dice | IoU | ASSD (mm) | HD95 (mm) | HDmax (mm) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Overall | 82 | 328 | 0.912 ± 0.032 | 0.842 ± 0.049 | 1.96 ± 0.64 | 4.81 ± 1.86 | 6.22 ± 2.08 |
| 2CH, ED + ES | 82 | 164 | 0.907 ± 0.043 | 0.835 ± 0.062 | 2.07 ± 0.83 | 5.12 ± 2.81 | 6.58 ± 3.01 |
| 4CH, ED + ES | 82 | 164 | 0.917 ± 0.034 | 0.849 ± 0.056 | 1.86 ± 0.75 | 4.51 ± 1.85 | 5.85 ± 2.20 |
| ED, 2CH + 4CH | 82 | 164 | 0.929 ± 0.024 | 0.869 ± 0.041 | 1.87 ± 0.65 | 4.60 ± 1.85 | 5.98 ± 2.32 |
| ES, 2CH + 4CH | 82 | 164 | 0.895 ± 0.049 | 0.814 ± 0.071 | 2.06 ± 0.83 | 5.03 ± 2.80 | 6.45 ± 3.03 |
| 2CH, ED | 82 | 82 | 0.926 ± 0.030 | 0.863 ± 0.050 | 1.96 ± 0.81 | 4.71 ± 1.92 | 6.14 ± 2.40 |
| 2CH, ES | 82 | 82 | 0.889 ± 0.072 | 0.806 ± 0.098 | 2.18 ± 1.22 | 5.53 ± 5.01 | 7.03 ± 5.28 |
| 4CH, ED | 82 | 82 | 0.932 ± 0.032 | 0.875 ± 0.053 | 1.77 ± 0.83 | 4.49 ± 2.42 | 5.83 ± 2.85 |
| 4CH, ES | 82 | 82 | 0.901 ± 0.047 | 0.823 ± 0.074 | 1.94 ± 0.86 | 4.52 ± 1.86 | 5.88 ± 2.32 |

Values: mean ± sample SD of patient means within each stratum (n = 82); frames are repeated observations.
Dice/IoU are dimensionless. ASSD/HD95/HDmax use original image coordinates and spatial calibration.
IoU was calculated directly for each restored binary mask, then averaged per patient, not from mean Dice.
Strata overlap; counts must not be added. No patients/frames were excluded; no imputation or significance tests.
2CH/4CH: two-/four-chamber; ED/ES: end-diastole/end-systole. Expert labels are available only at ED/ES.
Public CAMUS half-sequences (CC BY-NC-SA 4.0); 112 × 112 caches; not wearable patch recordings.
