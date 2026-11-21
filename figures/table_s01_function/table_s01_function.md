Supplementary Table 1 | Complete patient-level functional results across geometric, view, phase-selection and reference scopes.
All 21 existing method–metric groups are reported for the frozen CAMUS baseline. Each row uses one valid prediction–reference pair per patient, with its own effective n out of 82 attempted test patients. Biplane predictions use 20 disks and the shorter long axis; single-plane predictions use area–length geometry. Except for the final block, references are expert ED/ES contours processed with the matching geometry, not independent clinical volume standards. Automatic-extrema predictions remain referenced to expert ED/ES contour-derived measurements. Only the final block compares biplane EF with CAMUS Info.cfg clinical EF labels. MAE, RMSE, prediction-minus-reference bias, descriptive 95% limits of agreement (LOA), Pearson r and predictive R² are calculated from the original pairs. LOA are bias ± 1.96 times the sample standard deviation of differences, not confidence intervals or acceptance limits; predictive R² = 1 − SSE/SST is distinct from squared correlation. Negative R² values are retained. EF errors use percentage points (pp). The five primary results match Table 2, where primary MAE confidence intervals remain available; no new confidence intervals or tests were calculated. Patient0072 has null expert-phase 2CH SV/EF because ESV exceeds EDV. Automatic 4CH results omit patients0068/0203 because the final-frame maximum leaves no later ES under the frozen rule. All 492 patient–scope availability records, 1,712 valid metric pairs and 10 unpaired metric records are supplied. No rule changes, imputation or outlier removal occurred. HR/CO remain unavailable; the proxy-axis coverage limitation persists. Data are public CAMUS transthoracic half-sequences, not wearable recordings (Leclerc et al., IEEE TMI 2019, doi:10.1109/TMI.2019.2900516; CC BY-NC-SA 4.0).

| Metric (error unit) | n | MAE | RMSE | Bias | 95% LOA | Pearson r | Predictive R² |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Expert ED/ES · biplane 20 disks, shorter axis · same-geometry expert reference** |  |  |  |  |  |  |  |
| EDV (mL) | 82 | 8.15 | 10.79 | -0.87 | [-22.09, 20.34] | 0.908 | 0.823 |
| ESV (mL) | 82 | 5.82 | 7.34 | +2.55 | [-11.03, 16.13] | 0.951 | 0.890 |
| SV (mL) | 82 | 8.03 | 10.24 | -3.43 | [-22.45, 15.60] | 0.612 | -0.002 |
| LVEF (pp) | 82 | 9.27 | 12.48 | -5.81 | [-27.60, 15.97] | 0.659 | -0.041 |
| **Expert ED/ES · single plane, area–length · 2CH · same-geometry expert reference** |  |  |  |  |  |  |  |
| EDV (mL) | 82 | 26.50 | 34.27 | -10.62 | [-74.87, 53.63] | 0.907 | 0.803 |
| ESV (mL) | 82 | 15.73 | 23.10 | -3.97 | [-48.84, 40.90] | 0.943 | 0.886 |
| SV (mL) | 81 | 21.48 | 27.54 | -5.67 | [-58.83, 47.48] | 0.705 | 0.175 |
| LVEF (pp) | 81 | 9.93 | 13.04 | -2.25 | [-27.58, 23.08] | 0.670 | 0.289 |
| **Expert ED/ES · single plane, area–length · 4CH · same-geometry expert reference** |  |  |  |  |  |  |  |
| EDV (mL) | 82 | 21.30 | 31.33 | -3.99 | [-65.27, 57.30] | 0.893 | 0.787 |
| ESV (mL) | 82 | 13.29 | 20.77 | -5.54 | [-45.02, 33.93] | 0.954 | 0.877 |
| SV (mL) | 82 | 17.41 | 21.89 | +1.56 | [-41.50, 44.62] | 0.774 | 0.515 |
| LVEF (pp) | 82 | 7.74 | 9.51 | +1.07 | [-17.56, 19.70] | 0.796 | 0.578 |
| **Automatic extrema · single plane, area–length · 2CH · expert ED/ES contour reference** |  |  |  |  |  |  |  |
| EDV (mL) | 82 | 25.03 | 32.16 | -2.62 | [-65.82, 60.58] | 0.910 | 0.827 |
| ESV (mL) | 82 | 17.91 | 27.18 | -6.91 | [-58.75, 44.92] | 0.926 | 0.841 |
| SV (mL) | 82 | 21.17 | 27.60 | +4.29 | [-49.47, 58.05] | 0.675 | 0.161 |
| LVEF (pp) | 82 | 10.16 | 13.03 | +2.29 | [-22.99, 27.58] | 0.625 | 0.282 |
| **Automatic extrema · single plane, area–length · 4CH · expert ED/ES contour reference** |  |  |  |  |  |  |  |
| EDV (mL) | 80 | 20.85 | 28.92 | +1.00 | [-56.01, 58.00] | 0.909 | 0.821 |
| ESV (mL) | 80 | 14.94 | 24.26 | -10.62 | [-53.65, 32.41] | 0.951 | 0.834 |
| SV (mL) | 80 | 18.23 | 23.47 | +11.61 | [-28.61, 51.83] | 0.800 | 0.453 |
| LVEF (pp) | 80 | 8.66 | 11.18 | +6.24 | [-12.04, 24.53] | 0.779 | 0.426 |
| **Expert ED/ES · biplane prediction versus CAMUS clinical EF label (Info.cfg)** |  |  |  |  |  |  |  |
| LVEF (pp) | 82 | 9.03 | 11.12 | +1.56 | [-20.15, 23.28] | 0.663 | 0.189 |

One pair per patient per row. EDV/ESV/SV errors: mL; LVEF errors: percentage points (pp).
Expert contours + matching geometry are derived references, not independent clinical volume standards.
Only the final block uses Info.cfg clinical EF labels. Different reference scopes must not be pooled or ranked.
2CH expert-phase SV/EF: patient0072 invalid (ESV > EDV). Auto 4CH: patient0068/0203 have no ordered extrema.
Bias = prediction - reference; LOA = bias +/- 1.96 sample SD. Predictive R² = 1 - SSE/SST, not squared r.
Point estimates only; primary MAE confidence intervals are in Table 2. No new bootstrap or significance tests.
HR/CO remain null: no complete cycle/reliable reference HR or independent CO. CAMUS half-sequences, not patch data.
Proxy-axis coverage remains unvalidated; the reported agreement does not resolve that limitation.
