"""可选数据包获取工具，独立于 prepare/train/evaluate 日常流程。"""
from pathlib import Path
import re
import urllib.request
from urllib.parse import urlparse

from ...utils.hash import sha256
from ...utils.io import write_json


def download_archive(url, destination, expected_sha256):
    """获取用户有权访问的 CAMUS 包；必须提供可信来源的 SHA256。

    不绕过原始 CAMUS 的注册/许可，不自动解压或更改患者划分。
    下载前应阅读 docs/data_sources/CAMUS_LICENSE_TERMS.md。
    """
    if urlparse(url).scheme != 'https':
        raise ValueError('数据来源必须为 HTTPS。')
    if not isinstance(expected_sha256, str) or not re.fullmatch(r'[0-9a-fA-F]{64}', expected_sha256):
        raise ValueError('必须提供发布清单中的完整 SHA256。')
    destination = Path(destination)
    if destination.exists():
        if sha256(destination) != expected_sha256.lower():
            raise ValueError('已有数据包校验失败，不覆盖该文件。')
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + '.partial')
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'Echo-research'})
        with urllib.request.urlopen(request, timeout=60) as response, temporary.open('wb') as stream:
            if urlparse(response.geturl()).scheme != 'https':
                raise ValueError('拒绝非 HTTPS 重定向。')
            while block := response.read(1024 * 1024):
                stream.write(block)
        actual = sha256(temporary)
        if actual != expected_sha256.lower():
            raise ValueError('数据包 SHA256 与发布清单不一致。')
        temporary.replace(destination)
        write_json(destination.with_name(destination.name + '.source.json'), {
            'url': url, 'sha256': actual, 'bytes': destination.stat().st_size,
            'license': 'CAMUS CC BY-NC-SA 4.0; see CAMUS_LICENSE_TERMS.md',
            'scope': 'archive_only_not_dataset_completeness_verification',
        })
    finally:
        temporary.unlink(missing_ok=True)
    return destination
