# README mask comparison figures

These qualitative examples compare existing baseline predictions in a fixed test
patient. They do not establish a new model ranking or change the repeated-run
metrics. The five models use their existing seed-2026 representative runs.

## Selection and image integrity

- The patient remains patient0015, the patient used by the previous README video.
  No test metric was used to choose a replacement patient or a favorable frame.
- The 2-by-3 plate shows B-mode input followed by UNet, Attention-UNet, UNet++,
  UNet-mini and VGG16-UNet. The static example is frame 10 of 20 (zero-based).
  The GIF and MP4 include all 20 frames, including 18 frames without labels.
- The dual-view plate contains all four labeled phases for this patient:

  | View | Phase | Original frame index | Expert mask |
  |---|---|---:|---|
  | A4C / 4CH | ED | 26 | Available |
  | A4C / 4CH | ES | 0 | Available |
  | A2C / 2CH | ED | 0 | Available |
  | A2C / 2CH | ES | 19 | Available |

- Each dual-view row contains the B-mode input, original expert mask and all five
  predictions for that same frame. Phase indices come from the view's metadata,
  rather than assuming that both sequences begin at ED. The sequences are
  separate acquisitions; this is not a synchronized biplane measurement.
- B-mode images use the existing prepared model inputs without new intensity
  normalization, contrast adjustment or cropping. Original aspect ratio is
  restored for display, with black letterboxing. Binary masks use nearest-neighbor
  resizing. No component filtering, smoothing, hole filling or shape repair is
  applied. The original data, annotations and saved predictions are unchanged.
- The two display plates are 182.88 mm wide. PNG previews are 300 dpi; PDF/SVG
  retain editable text. Display resizing does not increase the source resolution.

## Rendered checks

| Artifact | Panels inspected | Geometry | Minimum PDF text | Collisions |
|---|---:|---|---:|---|
| Five-model grid | All 6 | PASS, 1.5 pt tolerance | 7.2 pt | 0 failures, 0 warnings |
| A4C/A2C comparison | All 28 | PASS, 1.5 pt tolerance | 6.2 pt | 0 failures, 0 warnings |

Every model name, view, phase and frame label was checked against its source.
The grid's six contained text overlays are the intentional labels in black bands
below the image pixels. The dual-view labels are outside the image areas. The
observed holes and irregular edges in UNet-mini outputs are preserved.

Source preflight: 19 passed, 0 failures. Its two advisory warnings concern PNG
rather than TIFF and 300 rather than 600 dpi; PNG is the intended README format,
with editable PDF/SVG alternatives provided. This is not a journal submission
package. Rendered alignment and collision reports accompany each plate.

The full asset export completed successfully and all 16 project tests passed.
