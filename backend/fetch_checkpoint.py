"""Download a private, checksum-pinned ONNX model before cloud startup."""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .app.model_spec import sha256

MAX_BYTES = 64 * 1024 * 1024


class HTTPSRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme != "https":
            raise ValueError("model redirect requires HTTPS")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch():
    target = Path(os.environ["ECHO_INFERENCE_CHECKPOINT"])
    expected = os.environ["ECHO_INFERENCE_SHA256"].strip().lower()
    if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
        raise ValueError("invalid expected SHA-256")
    if target.is_file() and sha256(target) == expected:
        return
    url = os.environ["ECHO_CHECKPOINT_URL"]
    if urlsplit(url).scheme != "https":
        raise ValueError("private model source requires HTTPS")
    request = Request(url, headers={"Accept": "application/octet-stream", "User-Agent": "EchoLab-Render"})
    token = os.getenv("ECHO_CHECKPOINT_TOKEN")
    if token:
        request.add_unredirected_header("Authorization", f"Bearer {token}")
    target.parent.mkdir(parents=True, exist_ok=True)
    pending = None
    try:
        with build_opener(HTTPSRedirect()).open(request, timeout=45) as response, NamedTemporaryFile(
            dir=target.parent, delete=False,
        ) as file:
            pending = Path(file.name)
            size = 0
            for block in iter(lambda: response.read(1024 * 1024), b""):
                size += len(block)
                if size > MAX_BYTES:
                    raise ValueError("private model download exceeds limit")
                file.write(block)
        if sha256(pending) != expected:
            raise ValueError("private model SHA-256 mismatch")
        pending.replace(target)
    finally:
        if pending is not None:
            pending.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        fetch()
    except (OSError, ValueError, KeyError) as exc:
        raise SystemExit(f"Private model setup failed ({type(exc).__name__}). Check the Render model source and SHA-256.") from None
