"""Prepared patch-session adapter with explicit evidence-contract checks."""

from copy import deepcopy

from .base import PreparedDatasetAdapter
from ..patch.contract import validate_patch_record


class PatchAdapter(PreparedDatasetAdapter):
    """Read prepared B-mode patch cases without inventing acquisition metadata."""

    def load_case(self, case):
        arrays, metadata = super().load_case(case)
        record = metadata.get("patch_record") or metadata.get("acquisition")
        if record is not None:
            report = validate_patch_record(record)
            if not report["valid"]:
                raise ValueError(f"invalid patch acquisition record: {report['errors']}")
            metadata = deepcopy(metadata)
            metadata["patch_contract"] = report
        return arrays, metadata
