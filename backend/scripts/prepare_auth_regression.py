import argparse
import json
import os
from pathlib import Path
import sys

import fitz


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def create_pdf(path, text):
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    document.save(path)
    document.close()


def main():
    parser = argparse.ArgumentParser(
        description="Prepare isolated, synthetic fixtures for auth regression."
    )
    parser.add_argument("root", type=Path)
    args = parser.parse_args()

    root = args.root.resolve()
    if root.exists():
        raise RuntimeError(f"Refusing to overwrite existing regression root: {root}")

    upload_dir = root / "uploads"
    report_dir = root / "reports"
    upload_dir.mkdir(parents=True)
    report_dir.mkdir()

    os.environ["DATABASE_URL"] = f"sqlite:///{(root / 'bid.db').as_posix()}"
    os.environ["UPLOAD_DIR"] = str(upload_dir)
    os.environ["REPORT_DIR"] = str(report_dir)

    from app.database import Base, SessionLocal, engine
    from app.models import BidFile

    pdf_path = upload_dir / "auth-sample.pdf"
    create_pdf(pdf_path, "AUTH REGRESSION PDF PREVIEW")

    word_path = upload_dir / "auth-word-sample.docx"
    word_path.write_bytes(b"synthetic-auth-regression-placeholder")
    create_pdf(
        upload_dir / "auth-word-sample.docx.preview.pdf",
        "AUTH WORD PREVIEW",
    )

    analysis = json.dumps(
        {
            "project_name": "Auth Regression",
            "tender_company": "Synthetic Test",
            "deadline": "N/A",
            "deposit": "N/A",
            "risk": [],
        }
    )
    Base.metadata.create_all(engine)
    session = SessionLocal()
    try:
        session.add_all(
            [
                BidFile(
                    filename=pdf_path.name,
                    filepath=str(pdf_path),
                    project_name="Auth PDF Project",
                    analysis=analysis,
                    risk="[]",
                    status="analyzed",
                ),
                BidFile(
                    filename=word_path.name,
                    filepath=str(word_path),
                    project_name="Auth Word Project",
                    analysis=analysis,
                    risk="[]",
                    status="analyzed",
                ),
            ]
        )
        session.commit()
    finally:
        session.close()
        engine.dispose()

    print("Synthetic auth regression fixtures are ready.")


if __name__ == "__main__":
    main()
