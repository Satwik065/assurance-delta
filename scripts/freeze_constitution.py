"""Freeze Constitution v1.1 into constitution/constitution.json.

Preserves v1.0 derived bounds (7.80, 985.53) and multipliers (1.5x, 5.0x)
per Errata policy, records v1.1 simulator/oracle parameters, and pins
SHA-256 hashes of all frozen oracle/gate/constitution artifacts.
"""
import sys, json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from constitution import constants as C
from constitution.hashing import sha256_file, sha256_canonical

FROZEN_ARTIFACTS = [
    "constitution/constants.py",
    "sim/traffic.py",
    "sim/channel.py",
    "sim/scheduler_base.py",
    "sim/engine.py",
    "oracle/audit.py",
    "oracle/verdict.py",
    "oracle/frozen_regression.py",
    "requirements_model/scope.py",
    "gate/gate.py",
    "gate/measure.py",
    "gate/scope_check.py",
    "gate/tamper.py",
    "ledger/conflict_certificate.py",
]


def main():
    root = Path(__file__).parent.parent
    # Preserve v1.0 frozen bounds untouched
    calibrated_data = {
        "r0_control_p99_bound_slots": 7.8,
        "r0_bulk_p99_bound_slots": 985.53,
        "r1_n_devices": C.R1_CALIBRATED_N_DEVICES,
        "r3_bulk_load_multiplier": C.R3_BULK_WAIVE_MULTIPLIER,
        "r3_bulk_burstiness": 0.0,
    }
    v11_params = {
        "oracle_version": C.ORACLE_VERSION,
        "horizon_slots": 5000,
        "control_buffer_packets": C.SIM_BUFFER_PACKETS_PER_QUEUE,
        "bulk_buffer_packets": C.SIM_BULK_BUFFER_PACKETS_PER_QUEUE,
        "r0_bulk_rate": 0.02,
        "r1_n_devices": C.R1_CALIBRATED_N_DEVICES,
        "r1_bulk_rate": C.R1_CALIBRATED_BULK_RATE,
        "r3_bulk_rate": C.R3_CALIBRATED_BULK_RATE,
        "horizon_censoring": True,
        "overflow_latency": "inf",
        "empty_latency_list": "inf",
        "control_loss_rule": "BUFFER_OVERFLOW_ONLY",
    }
    artifact_hashes = {rel: sha256_file(root / rel) for rel in FROZEN_ARTIFACTS}
    output = {
        "schema_version": "1.1",
        "frozen_at": "2026-11-21",
        "calibrated": calibrated_data,
        "v11_oracle_spec": v11_params,
        "frozen_artifact_hashes": artifact_hashes,
    }
    output["constitution_v11_hash"] = sha256_canonical({
        "calibrated": calibrated_data,
        "v11_oracle_spec": v11_params,
        "frozen_artifact_hashes": artifact_hashes,
    })

    out_path = root / C.CONSTITUTION_JSON_PATH
    out_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Froze {out_path}")
    print(f"  constitution_v11_hash: {output['constitution_v11_hash']}")
    print(f"  oracle/verdict.py:     {artifact_hashes['oracle/verdict.py']}")
    print(f"  sim/engine.py:         {artifact_hashes['sim/engine.py']}")


if __name__ == "__main__":
    main()
