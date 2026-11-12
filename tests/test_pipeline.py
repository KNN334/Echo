"""流水线测试：验证端到端评估产物以及缺失参考量的明确处理。"""
import importlib.util
import json
import numpy as np
import pytest


@pytest.mark.skipif(importlib.util.find_spec('torch') is None,reason='optional model dependency')
def test_end_to_end_export_and_missing_co(tmp_path,monkeypatch):
    """验证评估端到端产物，并确保缺失心率时 CO 为空。"""
    from src.utils.io import write_json
    from src.models import build as model
    from src.engine.evaluator import evaluate
    from src.data.transforms import Transform
    root=tmp_path/'processed';root.mkdir()
    key='patient0001_4CH'
    frames=np.zeros((4,64,64),np.uint8)
    y,x=np.ogrid[:64,:64]
    labels=np.stack([(((x-32)/r)**2+((y-30)/24)**2<1).astype(np.uint8) for r in (17,15,12,10)])
    frames[labels.astype(bool)]=100
    transform=Transform((64,64),(0,0,64,64),(64,64))
    audit={'transform':transform.record([1.,1.]),'spacing_xy_mm':[1.,1.],
           'fps':50,'timestamps_s':[0.,.02,.04,.06],'roi_reviewed':True,
           'n_frames':4,'issues':[]}
    np.savez_compressed(root/(key+'.npz'),frames=frames,masks=labels,labeled=[True,False,False,True],
                         original_gt=labels[[0,3]],original_gt_indices=[0,3])
    write_json(root/(key+'.json'),{'audit':audit,'phases':{'ED':0,'ES':3},'sequence_type':'half_sequence','config':{'EF':'60'}})
    case={'case_id':key,'patient_id':'patient0001','view':'4CH','split':'test'}
    write_json(root/'manifest.json',{'cases':[case]})
    test_manifest=root/'test.json'
    write_json(test_manifest,{'schema_version':1,'split':'test','dataset_root':'.',
                              'cases':[case],'patients':['patient0001']})
    weights=tmp_path/'checkpoint';weights.write_text('stubbed model predictions for integration test')
    monkeypatch.setattr(model,'load_checkpoint',lambda *a:(None,{'mean':[0]*3,'std':[1]*3}))
    monkeypatch.setattr(model,'predict',lambda *a:labels*.98+.01)
    out=tmp_path/'results'
    result=evaluate(test_manifest,weights,out,device='cpu')
    assert result['cases_failed']==0 and result['labeled_frames']==2
    assert result['dice_patient_mean']==1
    assert result['manual_keypoint_error'] is None and result['beats']==0
    assert result['function']['single_plane_area_length_4CH']['CO']['mae'] is None
    assert (out/'report.html').exists() and (out/(key+'_features.json')).exists()
