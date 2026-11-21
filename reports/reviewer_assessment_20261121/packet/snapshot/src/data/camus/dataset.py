"""CAMUS 处理后病例适配器与专家 ED/ES 标注帧 Dataset。"""
from ..base import AnnotatedFrameDataset, PreparedDatasetAdapter


class CamusAdapter(PreparedDatasetAdapter):
    """读取独立病例清单和处理后 NPZ，不在训练中解析原始文件。"""


class CamusDataset(AnnotatedFrameDataset):
    """只把 labeled=True 的 ED/ES 专家帧用于监督训练，标签为左室腔。"""
