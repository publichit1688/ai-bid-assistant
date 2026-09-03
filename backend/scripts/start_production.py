import argparse
import os
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import uvicorn

from app.config import (
    get_app_host,
    get_app_log_level,
    get_app_port,
    get_app_workers,
)
from app.services.runtime_checks import prepare_and_validate_runtime


def main():
    parser = argparse.ArgumentParser(description="AI Bid Assistant production server")
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate database and storage, then exit",
    )
    args = parser.parse_args()

    # Keep relative local defaults anchored to backend/ even when this script is
    # launched from the repository root or by an external service manager.
    os.chdir(BACKEND_ROOT)
    report = prepare_and_validate_runtime()
    print("启动检查通过:", ", ".join(report["checks"]))
    if args.check:
        return 0

    uvicorn.run(
        "app.main:app",
        host=get_app_host(),
        port=get_app_port(),
        workers=get_app_workers(),
        log_level=get_app_log_level(),
        reload=False,
        access_log=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
