"""相位定位误差：帧差始终保留，有可靠时间戳才输出秒误差。"""


def phase_errors(pred_ed, pred_es, ref_ed, ref_es, timestamps=None):
    result = {'ed_frame_error': abs(pred_ed - ref_ed), 'es_frame_error': abs(pred_es - ref_es),
              'ed_time_error_s': None, 'es_time_error_s': None}
    if timestamps is not None:
        result['ed_time_error_s'] = abs(timestamps[pred_ed] - timestamps[ref_ed])
        result['es_time_error_s'] = abs(timestamps[pred_es] - timestamps[ref_es])
    return result
