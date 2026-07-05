from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _run(command: list[str]) -> int:
    print(f"$ {' '.join(command)}", flush=True)
    return subprocess.run(command, cwd=BACKEND_ROOT).returncode


def main() -> int:
    """Run the deck extractor stack checks that are relevant to this stack.

    Do not use blanket `unittest discover -s tests` here: the repository also
    contains pytest-only and product-wide tests that are validated by other jobs.
    Importing all of them in this lightweight stack job creates unrelated failures
    and hides extractor/Smart Deck contract regressions.
    """
    checks = [
        [sys.executable, "-m", "unittest", "tests.test_smart_deck_quality_eval_service"],
        [sys.executable, "scripts/check_deck_extractor_runtime.py", "--strict-app"],
        [
            sys.executable,
            "-m",
            "compileall",
            "app/api/routes/deck_intake.py",
            "app/api/routes/slides.py",
            "app/services/agent_telemetry_service.py",
            "app/services/admin_operations_service.py",
            "app/services/deck_file_service.py",
            "app/services/deck_extractors",
            "app/services/pdf_deck_extraction_service.py",
            "app/services/deck_structure_service.py",
            "app/services/slide_thumbnail_service.py",
            "app/services/smart_deck_quality_eval_service.py",
            "app/schemas/deck_structure.py",
            "tests/test_smart_deck_quality_eval_service.py",
            "scripts/check_deck_extractor_runtime.py",
            "scripts/smoke_deck_extraction_api.py",
            "scripts/smoke_due_diligence_api.py",
        ],
    ]

    for command in checks:
        result = _run(command)
        if result != 0:
            return result
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
