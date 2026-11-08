import numpy as np
import pytest
from cardiac.geometry import mask_features, functional, biplane_volume
from cardiac.metrics import segmentation_metrics, landmark_errors, mae_summary
from cardiac.temporal import detect_beats, smooth_curve


def test_volume_scales_cubically_and_no_fake_milliliters():
    y,x=np.ogrid[:200,:150]
    mask=((x-75)/35)**2+((y-100)/70)**2 <= 1
    a=mask_features(mask,[.5,.5])
    b=mask_features(mask,[1.,1.])
    assert b['volume_ml'] == pytest.approx(a['volume_ml']*8, rel=.02)
    assert mask_features(mask)['volume_ml'] is None
    assert biplane_volume(a,a) > 0


def test_exact_functional_formula():
    a=functional(120,50,60)
    assert a['SV']==70 and a['EF']==pytest.approx(58.3333333) and a['CO']==4.2
    assert functional(120,50)['CO'] is None
    assert functional(50,120)['EF'] is None


def test_boundary_metrics_anisotropic_and_empty():
    a=np.zeros((20,20),bool);a[5:15,5:15]=True
    b=np.roll(a,1,axis=1)
    m=segmentation_metrics(a,b,[2.,1.])
    assert 0<m['dice']<1 and m['hd_max']==2
    assert segmentation_metrics(a,a)['dice']==1
    assert segmentation_metrics(a,np.zeros_like(a))['dice']==0
    assert segmentation_metrics(a,np.zeros_like(a))['hd95'] is None


def test_cycles_and_gap_not_imputed():
    t=np.arange(0,5,.02)
    v=100+25*np.cos(2*np.pi*t)
    good=np.ones(len(t),bool)
    rows=detect_beats(v,t,good)
    assert len(rows)>=2 and rows[0]['HR']==pytest.approx(60)
    good[100:110]=False
    rows=detect_beats(v,t,good)
    assert all(not(r['ed_frame']<105<r['next_ed_frame']) for r in rows)
    v[~good]=np.nan
    assert np.all(np.isnan(smooth_curve(v,good)[~good]))


def test_mae_missing_references_and_patient_count():
    rows=[{'patient_id':'a','EF':50,'ref_EF':55}]*5+[{'patient_id':'b','EF':70,'ref_EF':69}]
    a=mae_summary(rows)
    assert a['EF']['mae']==3 and a['EF']['n_patients']==2
    assert a['CO']['mae'] is None
