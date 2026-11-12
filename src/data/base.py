"""数据集适配器接口；共享处理后 NPZ 协议与具体数据集解耦。"""
from abc import ABC, abstractmethod
import numpy as np

from .manifests import read_split_manifest
from ..utils.io import read_json


class DatasetAdapter(ABC):
    """适配器负责读取病例，训练/评价引擎不解析数据集原始文件名。"""

    def __init__(self, manifest, split):
        self.root, self.cases = read_split_manifest(manifest, split)

    @abstractmethod
    def load_case(self, case):
        """返回 (数组字典, 元数据字典)。"""


class PreparedDatasetAdapter(DatasetAdapter):
    """任何满足 frames/masks/labeled/original_gt 协议的数据均可复用。"""

    def load_case(self, case):
        key = case['case_id']
        with np.load(self.root / (key + '.npz'), allow_pickle=False) as archive:
            arrays = {name: archive[name] for name in archive.files}
        return arrays, read_json(self.root / (key + '.json'))


class AnnotatedFrameDataset:
    """PyTorch DataLoader 可读取的数据集；仅加载专家实际标注的帧。"""

    def __init__(self, adapter, cases=None, description='Load annotated frames'):
        from tqdm import tqdm
        images, masks = [], []
        rows = adapter.cases if cases is None else cases
        for case in tqdm(rows, desc=description, unit='view'):
            arrays, _ = adapter.load_case(case)
            labeled = np.asarray(arrays['labeled'], dtype=bool)
            images.extend(arrays['frames'][labeled])
            masks.extend(arrays['masks'][labeled])
        self.frames, self.masks = np.asarray(images), np.asarray(masks)
        if not len(self.frames):
            raise ValueError('清单中没有专家标注帧。')
        self.mean = self.std = None

    def set_normalization(self, mean, std):
        """验证与测试必须复用训练集统计量，不能各自重新计算。"""
        self.mean, self.std = mean, std

    def __len__(self):
        return len(self.frames)

    def __getitem__(self, index):
        import torch
        from .transforms import normalize
        if self.mean is None:
            raise ValueError('必须先设置训练集归一化统计量。')
        image = normalize(self.frames[index:index + 1], self.mean, self.std)[0]
        target = torch.from_numpy(self.masks[index].astype(np.float32))[None]
        return image, target


def build_dataset(adapter, cases=None, description='Load annotated frames'):
    """数据格式与训练引擎解耦；新适配器可以复用通用标注帧协议。"""
    from .camus.dataset import CamusAdapter, CamusDataset
    dataset_class = CamusDataset if isinstance(adapter, CamusAdapter) else AnnotatedFrameDataset
    return dataset_class(adapter, cases, description)


def build_adapter(manifest, split, name='camus'):
    """按配置创建病例适配器；新数据集可继承 DatasetAdapter 接入。"""
    if name == 'camus':
        from .camus.dataset import CamusAdapter
        return CamusAdapter(manifest, split)
    if name == 'prepared':
        return PreparedDatasetAdapter(manifest, split)
    raise ValueError(f'不支持的数据适配器：{name}')
