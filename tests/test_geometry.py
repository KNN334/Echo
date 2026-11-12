"""几何测试：检查容积标定、功能公式、边界指标和时序异常情形。"""
import numpy as np
import pytest
from src.geometry.mask_features import mask_features
from src.geometry.functional import functional
from src.geometry.volume import biplane_volume
from src.metrics.segmentation import segmentation_metrics, landmark_errors
from src.metrics.cardiac import mae_summary
from src.temporal.beat_detection import detect_beats
from src.temporal.smoothing import smooth_curve


def test_volume_scales_cubically_and_no_fake_milliliters():
    """验证像素间距缩放对容积的三次影响且未标定时不伪报毫升。"""
    y,x=np.ogrid[:200,:150]
    mask=((x-75)/35)**2+((y-100)/70)**2 <= 1
    a=mask_features(mask,[.5,.5])
    b=mask_features(mask,[1.,1.])
    assert b['volume_ml'] == pytest.approx(a['volume_ml']*8, rel=.02)
    assert mask_features(mask)['volume_ml'] is None
    assert biplane_volume(a,a) > 0


def test_exact_functional_formula():
    """验证 SV、EF、CO 公式及缺少心率时 CO 保持缺失。"""
    a=functional(120,50,60)
    assert a['SV']==70 and a['EF']==pytest.approx(58.3333333) and a['CO']==4.2
    assert functional(120,50)['CO'] is None
    assert functional(50,120)['EF'] is None


def test_boundary_metrics_anisotropic_and_empty():
    """验证各向异性间距下的边界距离单位和空掩膜处理。"""
    a=np.zeros((20,20),bool);a[5:15,5:15]=True
    b=np.roll(a,1,axis=1)
    m=segmentation_metrics(a,b,[2.,1.])
    assert 0<m['dice']<1 and m['hd_max']==2
    assert segmentation_metrics(a,a)['dice']==1
    assert segmentation_metrics(a,np.zeros_like(a))['dice']==0
    assert segmentation_metrics(a,np.zeros_like(a))['hd95'] is None


def test_cycles_and_gap_not_imputed():
    """验证周期识别遵循时间戳且不会跨无效间断补造周期。"""
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
    """验证 MAE 忽略缺失参考并按患者而非帧数统计。"""
    rows=[{'patient_id':'a','EF':50,'ref_EF':55}]*5+[{'patient_id':'b','EF':70,'ref_EF':69}]
    a=mae_summary(rows)
    assert a['EF']['mae']==3 and a['EF']['n_patients']==2
    assert a['CO']['mae'] is None
