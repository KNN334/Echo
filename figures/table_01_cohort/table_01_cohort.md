Table 1 | CAMUS cohort, patient partitions and available reference evidence.

The table summarizes all 500 patients and 1,000 two- and four-chamber view sequences in the local prepared cohort. Age, sex and dataset EF labels were checked for agreement between both views before retaining one record per patient. Counts, medians and interquartile boundaries are derived from the fixed patient split and original metadata, with no exclusions or imputation. Image-quality categories are provided by CAMUS and counted per view sequence. Sequence duration is the observed ED-to-ES interval, (frame count minus one)/FPS. Original pixel spacing and the spacing of the 112-by-112 processed raster are reported separately. Unavailable reference and acquisition evidence is described in the notes rather than listed as zero-valued cohort characteristics. This concerns available project assets, not measurements that may have been obtained during the original clinical examination. Expert ED/ES contours support geometry-derived reference volumes, but no independent clinical volume standard, manually annotated anatomical points, complete cardiac cycles, independent HR/CO reference or project wearable acquisition is available. All ROIs retain their unreviewed status. No between-split hypothesis tests were performed. CAMUS: Leclerc et al., IEEE TMI (2019), doi:10.1109/TMI.2019.2900516; data license: CC BY-NC-SA 4.0.

| Characteristic | Train | Validation | Test | Total |
| --- | --- | --- | --- | --- |
| **Patient-level characteristics** |  |  |  |  |
| Patients, n | 347 | 71 | 82 | 500 |
| Age, years; median [IQR] | 68.0 [56.0, 76.0] | 65.0 [52.0, 74.0] | 65.0 [55.0, 76.0] | 67.0 [55.8, 76.0] |
| Female, n (%) | 116 (33.4) | 29 (40.8) | 25 (30.5) | 170 (34.0) |
| Male, n (%) | 231 (66.6) | 42 (59.2) | 57 (69.5) | 330 (66.0) |
| CAMUS EF label, %; median [IQR] | 45.0 [37.0, 52.0] | 48.0 [38.0, 52.5] | 47.5 [38.2, 54.8] | 46.0 [37.0, 52.0] |
| CAMUS EF label coverage, patients | 347 / 347 | 71 / 71 | 82 / 82 | 500 / 500 |
| **View-sequence and frame-level characteristics** |  |  |  |  |
| View sequences, n | 694 | 142 | 164 | 1,000 |
| 2CH / 4CH sequences, n | 347 / 347 | 71 / 71 | 82 / 82 | 500 / 500 |
| Observed frames, n | 13,415 | 2,650 | 3,167 | 19,232 |
| Expert ED / ES frames, n | 694 / 694 | 142 / 142 | 164 / 164 | 1,000 / 1,000 |
| Image quality - Good, n (%) | 345 (49.7) | 72 (50.7) | 88 (53.7) | 505 (50.5) |
| Image quality - Medium, n (%) | 262 (37.8) | 55 (38.7) | 62 (37.8) | 379 (37.9) |
| Image quality - Poor, n (%) | 87 (12.5) | 15 (10.6) | 14 (8.5) | 116 (11.6) |
| Frames per sequence; median [IQR] | 19 [17, 22] | 18 [17, 20] | 19 [17, 21] | 19 [17, 21] |
| Frame rate, FPS; median [IQR] | 56.5 [55.4, 56.5] | 56.0 [54.2, 56.5] | 56.5 [54.2, 56.5] | 56.5 [55.4, 56.5] |
| ED-ES duration, s; median [IQR] | 0.325 [0.283, 0.372] | 0.319 [0.285, 0.353] | 0.320 [0.283, 0.361] | 0.323 [0.283, 0.368] |
| **Spatial sampling (one value per sequence)** |  |  |  |  |
| Processed raster, height x width; pixels | 112 x 112 | 112 x 112 | 112 x 112 | 112 x 112 |
| Original height, pixels; range | 292-714 | 292-973 | 292-649 | 292-973 |
| Original width, pixels; range | 323-915 | 354-1181 | 355-869 | 323-1181 |
| Original x / y spacing, mm | 0.308 / 0.308 | 0.308 / 0.308 | 0.308 / 0.308 | 0.308 / 0.308 |
| Processed x spacing, mm; median [IQR] | 1.625 [1.485, 1.840] | 1.625 [1.408, 1.840] | 1.625 [1.408, 1.836] | 1.625 [1.408, 1.840] |
| Processed y spacing, mm; median [IQR] | 1.339 [1.160, 1.515] | 1.339 [1.160, 1.517] | 1.339 [1.160, 1.449] | 1.339 [1.160, 1.515] |

Patient statistics use one record per patient; quality and sampling statistics use view sequences.
Values are n (%), median [25th, 75th percentiles], or ranges; IQR boundaries use linear quantiles.
Custom patient split; both views stay together. All data are CAMUS transthoracic ED-ES half-sequences.
Time is derived from FPS, not acquisition timestamps. Original and processed spacing are distinct.
Expert-contour-derived volumes are available but are not independent clinical volume standards.
Independent volume, manual point and HR/CO references, full cycles and project patch recordings are unavailable.
All ROIs retain their unreviewed status. Missing evidence is stated here, not listed as cohort characteristics.
