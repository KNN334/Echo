"""数据集无关的可逆裁剪缩放坐标变换，供预处理和原图评价复用。"""
from dataclasses import dataclass, asdict
import numpy as np
from PIL import Image


@dataclass
class Transform:
    """描述裁剪和缩放，并提供图像坐标与原图坐标的双向变换。"""
    original_hw: tuple
    crop_xyxy: tuple
    output_hw: tuple

    def __post_init__(self):
        """校验裁剪边界是否在原图内，以及输出尺寸是否为正。"""
        h, w = self.original_hw
        x0, y0, x1, y1 = self.crop_xyxy
        if not (0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h):
            raise ValueError("crop outside source image")
        if min(self.output_hw) < 1:
            raise ValueError("invalid output size")

    @property
    def matrix(self):
        """返回从原图像素坐标映射到处理后坐标的齐次矩阵。"""
        x0, y0, x1, y1 = self.crop_xyxy
        oh, ow = self.output_hw
        sx, sy = ow / (x1 - x0), oh / (y1 - y0)
        # 缩放按像素中心对齐；半像素偏移与图像 resize 的坐标约定一致。
        return np.array([[sx, 0, sx * (0.5 - x0) - 0.5],
                         [0, sy, sy * (0.5 - y0) - 0.5], [0, 0, 1.]])

    def points(self, xy, inverse=False):
        """变换关键点坐标；设置 inverse 可从处理图映回原图。"""
        a = np.asarray(xy, float)
        matrix = np.linalg.inv(self.matrix) if inverse else self.matrix
        return (np.c_[a.reshape(-1, 2), np.ones(a.size // 2)] @ matrix.T)[:, :2].reshape(a.shape)

    def image(self, image, label=False):
        """对图像或标签应用相同裁剪缩放，标签使用最近邻插值。"""
        x0, y0, x1, y1 = self.crop_xyxy
        oh, ow = self.output_hw
        return np.asarray(Image.fromarray(image[y0:y1, x0:x1]).resize(
            (ow, oh), Image.Resampling.NEAREST if label else Image.Resampling.BILINEAR))

    def restore_mask(self, mask):
        """将处理后掩膜映回原图尺寸及对应像素位置。"""
        x0, y0, x1, y1 = self.crop_xyxy
        out = np.zeros(self.original_hw, np.uint8)
        out[y0:y1, x0:x1] = np.asarray(Image.fromarray(mask.astype(np.uint8)).resize(
            (x1 - x0, y1 - y0), Image.Resampling.NEAREST))
        return out

    def record(self, spacing):
        """导出变换参数及缩放后像素间距，供审计和复现使用。"""
        r = asdict(self)
        r.update(original_to_processed=self.matrix.tolist(), processed_to_original=np.linalg.inv(self.matrix).tolist(),
                 coordinate_convention="integer_pixel_centers_half_pixel_resize")
        if spacing is not None:
            r["processed_spacing_xy_mm"] = [spacing[0] / self.matrix[0, 0], spacing[1] / self.matrix[1, 1]]
        return r


def normalize(frames, mean, std):
    """将灰度帧复制为三通道并按训练集统计量标准化。"""
    import torch
    if np.asarray(mean).shape != (3,) or np.asarray(std).shape != (3,) or not np.all(np.isfinite(mean)) or not np.all(np.isfinite(std)) or min(std) <= 0:
        raise ValueError('归一化需要 3 个有限均值和 3 个有限正标准差。')
    # T×H×W 转成 T×3×H×W；mean/std 均按通道广播。
    x = torch.from_numpy(frames.astype(np.float32))[:, None].repeat(1, 3, 1, 1)
    return (x - torch.tensor(mean, dtype=torch.float32)[None, :, None, None]) / torch.tensor(std, dtype=torch.float32)[None, :, None, None]
