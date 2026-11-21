"""选择 CPU/CUDA；明确指定 CUDA 时不会静默退回 CPU。"""



def select_device(requested='auto', cpu_threads=2):
    """按配置选择计算设备；明确要求 CUDA 时不可静默改用 CPU。"""
    import torch
    if requested not in ('auto', 'cpu', 'cuda'):
        raise ValueError('device 只支持 auto、cpu、cuda。')
    if requested == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('当前解释器的 CUDA 不可用，请先修复环境，或将 device 设为 cpu。')
    device = 'cuda' if requested == 'auto' and torch.cuda.is_available() else requested
    if device == 'auto':
        device = 'cpu'
    if device == 'cpu':
        if not isinstance(cpu_threads, int) or isinstance(cpu_threads, bool) or cpu_threads < 1:
            raise ValueError('cpu_threads 必须是正整数。')
        torch.set_num_threads(cpu_threads)
    print(f'计算设备：{device}', flush=True)
    return device
