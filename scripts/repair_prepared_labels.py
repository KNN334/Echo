"""Restore resized expert labels from retained original annotations; never alter image ROI."""
import json
from pathlib import Path
import numpy as np
from cardiac.preprocess import Transform


def main():
    root=Path('data/processed/camus')
    manifest=json.loads((root/'manifest.json').read_text())
    changed=0
    for case in manifest['cases']:
        key=case['case_id'];path=root/(key+'.npz')
        with np.load(path) as z:arrays={k:z[k] for k in z.files}
        meta_path=root/(key+'.json');meta=json.loads(meta_path.read_text())
        tr=meta['audit']['transform']
        transform=Transform(tuple(tr['original_hw']),tuple(tr['crop_xyxy']),tuple(tr['output_hw']))
        different=False
        for index,gt in zip(arrays['original_gt_indices'],arrays['original_gt']):
            restored=transform.image(gt,label=True)
            if not np.array_equal(arrays['masks'][index],restored):different=True
            arrays['masks'][index]=restored
        if different:
            np.savez_compressed(path,**arrays);changed+=1
        audit=meta['audit']
        old_removed=audit.pop('removed_foreground_label_pixels',0)
        previous=audit.get('image_support_excludes_reference_foreground_pixels',old_removed)
        audit['image_support_excludes_reference_foreground_pixels']=previous
        x0,y0,x1,y1=transform.crop_xyxy
        cropped=sum(int(np.count_nonzero(gt)-np.count_nonzero(gt[y0:y1,x0:x1])) for gt in arrays['original_gt'])
        audit['cropped_reference_foreground_pixels']=cropped
        audit['removed_foreground_label_pixels']=cropped
        audit['issues']=[x.replace('roi_removes_reference_foreground_review_required','image_support_excludes_reference_foreground_review_required')
                        .replace('image_support_excludes_dark_reference_foreground_review_required','image_support_excludes_reference_foreground_review_required') for x in audit['issues']]
        case['issues']=audit['issues']
        meta_path.write_text(json.dumps(meta,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    (root/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    print('Expert labels restored; changed view records:',changed)


if __name__=='__main__':main()
