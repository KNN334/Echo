"""读取测试：检查 EchoNet 轨迹仍对应原始标注帧号。"""
import numpy as np
from src.data.medical_io import echonet_traces


def test_echonet_trace_polygon_frame_identity(tmp_path):
    """验证 EchoNet 轨迹转换后仍对应 CSV 标注帧编号。"""
    path=tmp_path/'VolumeTracings.csv'
    path.write_text('FileName,X1,Y1,X2,Y2,Frame\nx.avi,10,1,10,18,3\nx.avi,6,3,14,3,3\nx.avi,4,8,16,8,3\nx.avi,6,15,14,15,3\n')
    masks,known=echonet_traces(path,'x.avi',6,(20,20))
    assert np.flatnonzero(known).tolist()==[3]
    assert masks[3,8,10]==1 and masks[0].sum()==0
