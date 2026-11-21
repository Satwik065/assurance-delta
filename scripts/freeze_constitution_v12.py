"""Freeze Constitution v1.2 into constitution/constitution_v12.json."""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from constitution import constants as C
from constitution.hashing import sha256_file, sha256_canonical

FROZEN_ARTIFACTS_V12 = [
    "constitution/constants.py",
    "sim/traffic.py",
    "sim/channel.py",
    "sim/scheduler_base.py",
    "sim/engine.py",
    "sim/schedulers_v12.py",
    "proposer/reference/r1_v12.py",
    "oracle/audit.py",
    "oracle/verdict.py",
    "oracle/frozen_regression.py",
    "oracle/cache.py",
    "requirements_model/scope.py",
    "gate/gate.py",
    "gate/measure.py",
    "gate/scope_check.py",
    "gate/tamper.py",
    "ledger/conflict_certificate.py",
]


def main():
    root = Path(__file__).parent.parent
    assert len(C.CALIBRATION_SEEDS) == 20 and len(C.VERDICT_SEED_SET) == 20 and len(C.HOLDOUT_SEEDS) == 20
    assert set(C.CALIBRATION_SEEDS).isdisjoint(set(C.VERDICT_SEED_SET))
    assert set(C.CALIBRATION_SEEDS).isdisjoint(set(C.HOLDOUT_SEEDS))
    assert set(C.VERDICT_SEED_SET).isdisjoint(set(C.HOLDOUT_SEEDS))

    calibrated_data = {
        "r0_control_p99_bound_slots": 8.77,
        "r0_bulk_p99_bound_slots": 46.22,
        "r1_n_devices": C.V12_R1_N_DEVICES,
        "r3_bulk_load_multiplier": C.R3_BULK_WAIVE_MULTIPLIER,
        "r3_bulk_burstiness": 0.0,
    }
    v12_spec = {
        "constitution_version": C.CONSTITUTION_V12_VERSION,
        "oracle_version": C.ORACLE_VERSION,
        "horizon_slots": C.V12_HORIZON_SLOTS,
        "control_buffer_packets": C.SIM_BUFFER_PACKETS_PER_QUEUE,
        "bulk_buffer_packets": C.SIM_BULK_BUFFER_PACKETS_PER_QUEUE,
        "r0": {"n_devices": C.V12_R0_N_DEVICES, "bulk_rate": C.V12_R0_BULK_RATE, "burstiness": 0.0, "rho": 0.688},
        "r1": {"n_devices": C.V12_R1_N_DEVICES, "bulk_rate": C.V12_R1_BULK_RATE, "burstiness": 0.0, "rho": 0.754},
        "r2": {"n_devices": C.V12_R0_N_DEVICES, "bulk_rate": C.V12_R0_BULK_RATE, "burstiness": C.V12_R2_BULK_BURSTINESS, "rho": 0.688},
        "r3": {"n_devices": C.V12_R0_N_DEVICES, "bulk_rate": C.V12_R3_BULK_RATE, "burstiness": 0.0, "rho": 0.896, "waived_bulk_bound": 231.10},
        "r4": {"n_devices": C.V12_R0_N_DEVICES, "bulk_rate": C.V12_R4_BULK_RATE, "burstiness": 0.0, "rho": 2.800},
        "calibration_seeds": [C.CALIBRATION_SEEDS[0], C.CALIBRATION_SEEDS[-1]],
        "verdict_seeds": [C.VERDICT_SEED_SET[0], C.VERDICT_SEED_SET[-1]],
        "holdout_seeds": [C.HOLDOUT_SEEDS[0], C.HOLDOUT_SEEDS[-1]],
        "llm_prompt_policy": "G1_offline_reeval_saved_165_proposals",
    }
    artifact_hashes = {rel: sha256_file(root / rel) for rel in FROZEN_ARTIFACTS_V12}
    output = {
        "schema_version": "1.2",
        "frozen_at": "2026-11-21",
        "supersedes_for_calibration": "constitution/constitution.json (v1.1 preserved intact)",
        "calibrated": calibrated_data,
        "v12_spec": v12_spec,
        "frozen_artifact_hashes": artifact_hashes,
    }
    output["constitution_v12_hash"] = sha256_canonical({
        "calibrated": calibrated_data,
        "v12_spec": v12_spec,
        "frozen_artifact_hashes": artifact_hashes,
    })

    out_path = root / C.CONSTITUTION_V12_JSON_PATH
    out_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Froze {out_path}")
    print(f"  constitution_v12_hash: {output['constitution_v12_hash']}")


if __name__ == "__main__":
    main()
