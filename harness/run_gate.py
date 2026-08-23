"""STUB — Arm A entry point. Real wiring (read frozen claims, run the Gate,
write deliverables/results.json) lands in T-04.

Runnable today: writes a fixture results.json so `./run.sh gate` exits 0 from minute one.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "deliverables" / "results.json"


def main():
    stub = {
        "pack_version": "0.0.1-STUB",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_layer": "off",
        "claims": [
            {
                "claim_id": "stub00000001",
                "text": "STUB — real claims land after T-02/T-04/T-07.",
                "score": 0,
                "max_score": 5,
                "verdicts": [],
                "pack_version": "0.0.1-STUB",
            }
        ],
        "documents": [],
        "corpus": {"note": "STUB"},
    }
    RESULTS.write_text(json.dumps(stub, indent=2) + "\n")
    print(f"wrote {RESULTS} (STUB — T-04 not yet wired)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
