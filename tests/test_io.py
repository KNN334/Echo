import importlib.util
import numpy as np
import pytest
from cardiac.io import echonet_traces


def test_echonet_trace_polygon_frame_identity(tmp_path):
    path=tmp_path/'VolumeTracings.csv'
    path.write_text('FileName,X1,Y1,X2,Y2,Frame\nx.avi,10,1,10,18,3\nx.avi,6,3,14,3,3\nx.avi,4,8,16,8,3\nx.avi,6,15,14,15,3\n')
    masks,known=echonet_traces(path,'x.avi',6,(20,20))
    assert np.flatnonzero(known).tolist()==[3]
    assert masks[3,8,10]==1 and masks[0].sum()==0


@pytest.mark.skipif(importlib.util.find_spec('SimpleITK') is None,reason='optional medical dependency')
def test_camus_phases_and_fps_not_nifti_third_axis(tmp_path,monkeypatch):
    import SimpleITK as sitk
    from cardiac.io import read_camus
    # NIfTI's Windows backend can reject legacy MAX_PATH absolute names.
    monkeypatch.chdir(tmp_path)
    from pathlib import Path
    folder=Path('patient0001');folder.mkdir()
    seq=np.ones((5,30,20),np.uint8)*80
    im=sitk.GetImageFromArray(seq);im.SetSpacing((.4,.7,1.))
    sitk.WriteImage(im,str(folder/'patient0001_4CH_half_sequence.nii.gz'))
    gt=np.zeros((1,30,20),np.uint8);gt[:,5:20,5:15]=1
    for phase in ('ED','ES'):
        im=sitk.GetImageFromArray(gt);im.SetSpacing((.4,.7,1.))
        sitk.WriteImage(im,str(folder/f'patient0001_4CH_{phase}_gt.nii.gz'))
    (folder/'Info_4CH.cfg').write_text('ED: 1\nES: 5\nNbFrame: 5\nFrameRate: 50\n')
    frames,masks,known,meta=read_camus(folder,'4CH')
    assert np.flatnonzero(known).tolist()==[0,4]
    assert meta['fps']==50 and np.allclose(meta['spacing_xy_mm'],[.4,.7])
    assert meta['sequence_type']=='half_sequence' and frames.shape==seq.shape
