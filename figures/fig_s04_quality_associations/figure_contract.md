# Fig.S4 figure contract

- Question: How does the frozen baseline perform across CAMUS image-quality strata, and how closely do spatial and clinical-label EF performance co-vary within patients?
- Claim: Quality-stratified spatial performance and clinical-label EF differences need separate reporting; neither a quality label nor an overlap score establishes functional accuracy.
- Evidence: a, full patient Dice by worst-view quality; b, clinical-label EF absolute difference in the same strata; c/d, patient-level associations with mean Dice/HD95. All 82 fixed test patients remain in every panel.
- Archetype: quantitative grid, 2×2, Python/matplotlib; source/style-only inheritance from existing project figures, no external numerical data.
- Quality is the worse of the two recorded CAMUS view grades, not a new learned or test-optimized label. Patient Dice/HD95 average two views and two phases. Clinical EF reference is Info.cfg, distinct from contour-derived references.
- Raw patient points, group means ± patient sample SD for a/b; c/d are raw associations with Pearson r, no fitted predictor, CI or significance test. Quality groups are observational and unbalanced; no causal/external-generalization claims.
- Export: 183×158 mm, editable PDF, 600 dpi RGB PNG/LZW TIFF, minimum 7 pt; shared style/colors only, source tables, English caption, SHA256 provenance, 1.5 pt comparable-panel alignment and final PDF collision QA.
- No new training/inference, test feedback, outlier removal, imputation, HR/CO or wearable-data claims.
