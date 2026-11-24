DISCLAIMER = "研究基线 · 非临床验证"
UNITS = {"EDV": "mL", "ESV": "mL", "SV": "mL", "EF": "%", "HR": "次/分", "CO": "L/min"}
ERROR_UNITS = {**UNITS, "EF": "百分点"}
MISSING_CYCLE = "缺少可靠时间与完整心动周期，且没有可用参考心率"
MISSING_CO = "缺少独立 CO 参考"
MISSING_LANDMARKS = "缺少独立人工解剖关键点标注"
SAME_GEOMETRY = "专家轮廓经相同几何方法派生的参考"


class ServiceError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail
