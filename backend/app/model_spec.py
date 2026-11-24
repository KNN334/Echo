import hashlib
from pathlib import Path

SOURCE_SHA256 = "5103390376bbd2db4c75269c7752ad30a43637d9d75a5cb18a955cb415c2f384"
MODEL_HW = (192, 256)
CONTEXT_FRAMES = 3


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
