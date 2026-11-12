"""超声图像、左室掩膜与关键点叠加。"""
import numpy as np
from PIL import Image, ImageDraw


def overlay(frame, mask, points=None):
    """生成叠加分割掩膜与可选关键点的质量检查图。"""
    a = np.repeat(frame[:, :, None], 3, 2).astype(np.uint8)
    a[mask.astype(bool)] = (a[mask.astype(bool)] * .6 + np.array([20,220,80]) * .4).astype(np.uint8)
    image = Image.fromarray(a)
    draw = ImageDraw.Draw(image)
    if points:
        for key in ("apex", "base_left", "base_right"):
            x,y = points[key]
            draw.ellipse((x-2,y-2,x+2,y+2), fill=(255,90,20))
        apex=np.array(points['apex'])
        base=(np.array(points['base_left'])+np.array(points['base_right']))/2
        draw.line([tuple(apex),tuple(base)],fill=(255,180,30),width=1)
        draw.line([tuple(points['base_left']),tuple(points['base_right'])],fill=(255,180,30),width=1)
    return image
