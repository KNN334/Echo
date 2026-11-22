"""Conventional segmentation baselines; no project-specific model is included."""

from .architectures import MODEL_NAMES, build_model

__all__ = ["MODEL_NAMES", "build_model"]
