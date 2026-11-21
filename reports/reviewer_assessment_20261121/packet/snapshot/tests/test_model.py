"""模型测试：检查 EchoNet 分割网络结构和检查点加载兼容性。"""
import importlib.util
import numpy as np
import pytest


@pytest.mark.skipif(importlib.util.find_spec('torch') is None, reason='optional model dependency')
def test_echonet_architecture_and_checkpoint_prefix(tmp_path):
    """验证分割模型输出结构及带 module. 前缀检查点可正常加载。"""
    import torch
    from src.models.build import build_model, load_checkpoint
    torch.set_num_threads(2)
    m=build_model().eval()
    with torch.no_grad():
        assert m(torch.zeros(1,3,64,64))['out'].shape == (1,1,64,64)
    path=tmp_path/'weights.pt'
    torch.save({'state_dict':{'module.'+k:v for k,v in m.state_dict().items()}},path)
    restored,_=load_checkpoint(path)
    assert restored.classifier[-1].out_channels==1
