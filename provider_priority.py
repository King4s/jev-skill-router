"""Order decision makers by model-matched measured accuracy, then measured cost."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

from decision_providers import ProviderError

DEFAULT_PROFILE = Path(__file__).resolve().parent / "provider-priority.json"
DEFAULT_ORDER = ("perplexity", "jev")


def provider_order(models: dict, profile_path=None) -> dict:
    """Read local evidence; never run a paid measurement while choosing a provider."""
    path = Path(profile_path or os.environ.get("SKILL_ROUTER_PRIORITY_PROFILE") or DEFAULT_PROFILE)
    try:
        if path.stat().st_size > 65536:
            raise ProviderError("The priority profile exceeds 64 KiB.")
        profile = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, UnicodeError, RecursionError):
        raise ProviderError("Cannot read a valid decision-provider priority profile.") from None
    allowed = {"schema_version", "source", "providers", "notes", "measurement"}
    if not isinstance(profile, dict) or set(profile) - allowed or type(profile.get("schema_version")) is not int or profile["schema_version"] != 1:
        raise ProviderError("Invalid priority profile schema.")
    records = profile.get("providers")
    if not isinstance(records, dict) or not records or set(records) - set(DEFAULT_ORDER):
        raise ProviderError("Invalid priority profile providers.")
    source = profile.get("source", "User-supplied measurements")
    if not isinstance(source, str) or len(source) > 500:
        raise ProviderError("Invalid priority profile source.")
    metrics = {}
    for name in DEFAULT_ORDER:
        record = records.get(name)
        if record is None:
            metrics[name] = {"accuracy": None, "cost_per_candidate_usd": None, "model_matches": False}
            continue
        if not isinstance(record, dict) or set(record) != {"models", "accuracy", "cost_per_candidate_usd"}:
            raise ProviderError("Invalid priority profile measurement fields.")
        supported = record["models"]
        if not isinstance(supported, list) or not supported or not all(isinstance(model, str) and model.strip() and len(model) <= 200 for model in supported):
            raise ProviderError("Invalid priority profile model list.")
        for field in ("accuracy", "cost_per_candidate_usd"):
            value = record[field]
            if value is not None:
                try:
                    valid = type(value) in (int, float) and math.isfinite(value) and value >= 0
                except OverflowError:
                    valid = False
                if not valid or (field == "accuracy" and value > 1):
                    raise ProviderError(f"Invalid priority profile {field}.")
        matches = models.get(name) in supported
        metrics[name] = {"accuracy": record["accuracy"] if matches else None,
                         "cost_per_candidate_usd": record["cost_per_candidate_usd"] if matches else None,
                         "model_matches": matches}
    def rank(name):
        quality = metrics[name]["accuracy"]
        cost = metrics[name]["cost_per_candidate_usd"]
        return (quality is None, -(quality or 0), cost is None, cost or 0, DEFAULT_ORDER.index(name))
    order = sorted(DEFAULT_ORDER, key=rank)
    coverage = sum(row["accuracy"] is not None for row in metrics.values())
    basis = "measured_accuracy_then_measured_cost" if coverage == len(DEFAULT_ORDER) else "provisional_order_incomplete_quality_evidence" if coverage else "provisional_order_quality_unavailable"
    return {"order": order, "basis": basis,
            "source": source, "metrics": metrics}
