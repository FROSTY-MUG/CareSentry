"""Unit tests for Adapter Shims (Contract C-05 and C-02)."""

import json
from pathlib import Path
import pytest
import jsonschema

from caresentry_plus.adapters.runner_shim import ModelRunnerShim
from caresentry_plus.adapters.probe_shim import ProbeShim

CONTRACT_SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "contracts" / "attention_trace.v1.schema.json"


def test_runner_shim_simulation_fallback():
    """Test runner shim in simulation / fallback mode."""
    shim = ModelRunnerShim(fallback_mode=True)
    _, tokens = shim.tokenize("Patient has documented allergy to Augmentin.")
    assert len(tokens) >= 5
    assert "allergy" in [t.lower() for t in tokens]

    telemetry = shim.forward("Patient prompt", needle="Augmentin")
    assert telemetry.seq_len > 0
    assert telemetry.is_simulated is True

    gen = shim.generate("Generate summary")
    assert isinstance(gen, str)
    assert len(gen) > 0


def test_probe_shim_emits_valid_c02_schema():
    """F-06 / C-02: ProbeShim trace dump must validate against attention_trace.v1.schema.json."""
    assert CONTRACT_SCHEMA_PATH.exists()
    with open(CONTRACT_SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)

    probe = ProbeShim(fallback_mode=True)
    trace_dto = probe.probe(
        prompt="Patient has documented severe allergy to Penicillin and Amoxicillin. Prescribe safe medication.",
        needle="severe allergy to Penicillin and Amoxicillin",
        apply_mitigation=True,
    )
    trace_dict = trace_dto.to_dict()

    # Validate against frozen JSON Schema
    jsonschema.validate(instance=trace_dict, schema=schema)

    assert trace_dict["schema"] == "attention_trace.v1"
    assert trace_dict["classification"] in ["attended", "neutral", "neglected", "SUFFICIENTLY_ATTENDED"]
    assert len(trace_dict["control_spans"]) == 20
    assert trace_dict["z_score"] > 0.0  # Mitigated
