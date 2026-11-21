Table 2 | Patient-level functional agreement for the frozen CAMUS baseline.

The first block compares predicted EDV, ESV, SV and LVEF with expert ED/ES contours processed using the same 20-disk biplane geometry and shorter long axis. These references are not independent clinical volume standards. The second block compares predicted LVEF separately with CAMUS Info.cfg clinical EF labels. Each row includes all 82 test patients, without outlier exclusion or imputation. MAE is reported with its previously frozen percentile 95% confidence interval from 2,000 patient bootstrap resamples (seed 2026); intervals were not recomputed or selected in this batch. RMSE, signed bias, descriptive 95% limits of agreement (LOA), Pearson r and predictive R² are calculated from the original paired values. Bias is prediction minus reference; LOA are bias +/- 1.96 times the sample standard deviation of differences, not confidence intervals or clinical acceptance limits. Predictive R² is 1 - SSE/SST relative to the reference mean and differs from squared correlation. EF errors are percentage points (pp). The existing proxy-axis coverage mismatch and potential cancellation of reference and prediction biases remain unresolved. HR and CO are unavailable, not zero, because complete-cycle/reliable reference HR and independent CO evidence are absent. No hypothesis tests, recalibration, new inference or wearable-acquisition claims are made.

| Metric (error unit) | n | MAE [95% CI] | RMSE | Bias | 95% LOA | Pearson r | Predictive R² |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Expert contours + same biplane geometry (not an independent clinical volume standard)** |  |  |  |  |  |  |  |
| EDV (mL) | 82 | 8.15 [6.66, 9.75] | 10.79 | -0.87 | [-22.09, 20.34] | 0.908 | 0.823 |
| ESV (mL) | 82 | 5.82 [4.89, 6.88] | 7.34 | +2.55 | [-11.03, 16.13] | 0.951 | 0.890 |
| SV (mL) | 82 | 8.03 [6.74, 9.46] | 10.24 | -3.43 | [-22.45, 15.60] | 0.612 | -0.002 |
| LVEF (pp) | 82 | 9.27 [7.56, 11.07] | 12.48 | -5.81 | [-27.60, 15.97] | 0.659 | -0.041 |
| **CAMUS dataset EF clinical label (Info.cfg); separate reference** |  |  |  |  |  |  |  |
| LVEF (pp) | 82 | 9.03 [7.63, 10.48] | 11.12 | +1.56 | [-20.15, 23.28] | 0.663 | 0.189 |

One pair per test patient; all 82 patients retained per row. Expert ED/ES phases; 20 disks, shorter axis.
MAE intervals: frozen patient bootstrap, 2,000 resamples, seed 2026. EF errors use percentage points (pp).
Bias = prediction - reference; 95% LOA = bias +/- 1.96 sample SD, not a confidence or acceptability interval.
Predictive R² = 1 - SSE/SST against the reference; it is not Pearson r². No significance tests were used.
Current proxy-axis geometry has a coverage mismatch. Shared geometry is not an independent gold standard.
HR/CO: null, n = 0; no complete cycle/reliable reference HR or independent CO. No patch acquisition.
Single-plane and automatic-phase results have different n and remain separate for Supplementary Table 1.
