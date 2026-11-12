"""分割质量标志；不改变人工审阅状态。"""



def quality_flags(features, roi_reviewed, confidence=None):
    """为分割几何质量问题生成标记，不改变人工审核状态。"""
    flags = []
    if not features.get("valid"):
        flags.append(features.get("reason", "invalid_geometry"))
    if features.get("touches_image_edge"):
        flags.append("LV_touches_image_edge")
    if features.get("largest_component_fraction", 1) < .9:
        flags.append("fragmented_segmentation")
    if not roi_reviewed:
        flags.append("roi_not_reviewed")
    if confidence is not None and confidence < .65:
        flags.append("low_segmentation_confidence")
    return flags
