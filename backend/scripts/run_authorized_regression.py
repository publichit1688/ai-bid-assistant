import contextlib
import argparse
import io
import json
import os
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
SAMPLE_ROOT = PROJECT_ROOT / "regression_samples"


def load_local_configuration():
    load_dotenv(BACKEND_DIR / ".env")
    load_dotenv(PROJECT_ROOT / ".env")
    if not os.getenv("DEEPSEEK_API_KEY"):
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")


def authorized_samples():
    samples = []
    for expected_path in sorted(SAMPLE_ROOT.glob("*/expected.local.json")):
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        if expected.get("authorization", {}).get("status") != "已确认":
            continue
        sources = [
            path
            for path in expected_path.parent.iterdir()
            if path.name.startswith("source.") and path.is_file()
        ]
        if len(sources) != 1:
            raise RuntimeError(
                f"{expected.get('sample_id', expected_path.parent.name)} must have one source"
            )
        samples.append((expected, sources[0], expected_path.parent))
    return samples


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sample-id",
        action="append",
        dest="sample_ids",
        help="Run only the authorized sample id; may be repeated.",
    )
    parser.add_argument("--validate-only", action="store_true")
    return parser.parse_args()


def run():
    args = parse_args()
    load_local_configuration()
    samples = authorized_samples()
    if args.sample_ids:
        requested = set(args.sample_ids)
        samples = [
            sample
            for sample in samples
            if (sample[0].get("sample_id") or sample[2].name) in requested
        ]
        found = {
            sample[0].get("sample_id") or sample[2].name
            for sample in samples
        }
        missing = requested - found
        if missing:
            raise RuntimeError(
                "Authorized regression sample ids not found: "
                + ", ".join(sorted(missing))
            )
    if not samples:
        raise RuntimeError("No authorized local regression samples")

    sys.path.insert(0, str(BACKEND_DIR))
    with tempfile.TemporaryDirectory(prefix="ai-bid-real-regression-") as temp_dir:
        runtime_dir = Path(temp_dir)
        (runtime_dir / "uploads").mkdir()
        (runtime_dir / "reports").mkdir()
        previous_dir = Path.cwd()
        os.chdir(runtime_dir)
        try:
            # Import only after changing directory so SQLite and generated files
            # remain isolated from the user's working database and uploads.
            with contextlib.redirect_stdout(io.StringIO()):
                from fastapi.testclient import TestClient
                from app.database import engine
                from app.main import app

            if args.validate_only:
                print(json.dumps({"authorized_samples": len(samples), "validated": True}))
            else:
                with TestClient(app) as client:
                    for expected, source, sample_dir in samples:
                        run_sample(client, expected, source, sample_dir)
        finally:
            if "engine" in locals():
                engine.dispose()
            os.chdir(previous_dir)


def run_sample(client, expected, source, sample_dir):
                    sample_id = expected.get("sample_id") or sample_dir.name
                    with source.open("rb") as stream:
                        # Parser and LLM currently emit document/model details to stdout.
                        # Capture them so real content never enters terminal logs.
                        with contextlib.redirect_stdout(io.StringIO()):
                            response = client.post(
                                "/api/upload",
                                files={
                                    "file": (
                                        source.name,
                                        stream,
                                        "application/octet-stream",
                                    )
                                },
                            )

                    try:
                        payload = response.json()
                    except ValueError:
                        payload = {"error": "non-json response"}

                    local_result = {
                        "sample_id": sample_id,
                        "http_status": response.status_code,
                        "result": payload,
                    }
                    (sample_dir / "actual.local.json").write_text(
                        json.dumps(local_result, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )

                    safe_summary = {
                        "sample_id": sample_id,
                        "http_status": response.status_code,
                        "success": response.status_code == 200,
                        "score": payload.get("score") if isinstance(payload, dict) else None,
                        "risk_count": (
                            payload.get("risk_count") if isinstance(payload, dict) else None
                        ),
                        "high_count": (
                            payload.get("high_count") if isinstance(payload, dict) else None
                        ),
                    }
                    print(json.dumps(safe_summary, ensure_ascii=False))


if __name__ == "__main__":
    run()
