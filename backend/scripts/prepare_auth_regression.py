import argparse
import json
import os
from pathlib import Path
import sys

import fitz


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def create_pdf(path, *page_texts):
    document = fitz.open()
    for text in page_texts:
        page = document.new_page()
        page.insert_text((72, 72), text)
    document.save(path)
    document.close()


def main():
    parser = argparse.ArgumentParser(
        description="Prepare isolated, synthetic fixtures for auth and workbench regression."
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
    from app.models import (
        BidFile,
        BidWorkspace,
        OutlineSection,
        ScoringCriterion,
        SourceReference,
        WorkspaceRevision,
    )

    pdf_path = upload_dir / "auth-sample.pdf"
    create_pdf(
        pdf_path,
        "AUTH REGRESSION PDF PAGE 1",
        "AUTH REGRESSION PDF RISK PAGE 2",
    )

    word_path = upload_dir / "auth-word-sample.docx"
    word_path.write_bytes(b"synthetic-auth-regression-placeholder")
    create_pdf(
        upload_dir / "auth-word-sample.docx.preview.pdf",
        "AUTH WORD PREVIEW PAGE 1",
        "AUTH WORD RISK PAGE 2",
    )

    pdf_risks = [
        {
            "level": "高风险",
            "deduction": 20,
            "category": "合成资格条件",
            "reason": "纯合成回归风险，用于验证Dashboard预警穿透。",
            "suggestion": "仅用于本地自动化验证。",
            "page": 2,
            "quote": "AUTH REGRESSION PDF RISK PAGE 2",
            "highlight_words": ["PDF RISK PAGE 2"],
            "keywords": ["PDF RISK"],
            "ocr_highlight_boxes": [
                {"x": 0.1, "y": 0.08, "width": 0.48, "height": 0.05}
            ],
        }
    ]
    word_risks = [
        {
            "level": "中风险",
            "deduction": 8,
            "category": "合成Word页码",
            "reason": "纯合成回归风险，用于验证Word渲染页映射。",
            "suggestion": "仅用于本地自动化验证。",
            "page": 1,
            "quote": "AUTH WORD RISK PAGE 2",
            "highlight_words": ["WORD RISK PAGE 2"],
            "keywords": ["WORD RISK"],
        }
    ]

    def analysis_for(risks):
        return json.dumps(
        {
            "project_name": "Auth Regression",
            "tender_company": "Synthetic Test",
            "deadline": "N/A",
            "deposit": "N/A",
            "risk": risks,
        },
        ensure_ascii=False,
        )
    Base.metadata.create_all(engine)
    session = SessionLocal()
    try:
        pdf_file = BidFile(
                    filename=pdf_path.name,
                    filepath=str(pdf_path),
                    project_name="Auth PDF Project",
                    analysis=analysis_for(pdf_risks),
                    risk=json.dumps(pdf_risks, ensure_ascii=False),
                    status="analyzed",
                )
        session.add_all(
            [
                pdf_file,
                BidFile(
                    filename=word_path.name,
                    filepath=str(word_path),
                    project_name="Auth Word Project",
                    analysis=analysis_for(word_risks),
                    risk=json.dumps(word_risks, ensure_ascii=False),
                    status="analyzed",
                ),
            ]
        )
        session.flush()
        workspace = BidWorkspace(
            bid_file_id=pdf_file.id,
            title="Synthetic Workbench",
            status="draft",
            revision=1,
        )
        session.add(workspace)
        session.flush()
        confirmed_source = SourceReference(
            bid_file_id=pdf_file.id,
            page=1,
            quote="AUTH REGRESSION PDF PAGE 1",
            locator=json.dumps({"page": 1}),
            fingerprint="synthetic-confirmed-source",
        )
        suggested_source = SourceReference(
            bid_file_id=pdf_file.id,
            page=1,
            quote="AUTH REGRESSION PDF PAGE 1",
            locator=json.dumps({"page": 1}),
            fingerprint="synthetic-suggested-source",
        )
        session.add_all([confirmed_source, suggested_source])
        session.flush()
        session.add_all(
            [
                OutlineSection(
                    workspace_id=workspace.id,
                    stable_key="synthetic-confirmed-section",
                    title="技术响应方案",
                    sort_order=0,
                    origin="manual",
                    review_status="confirmed",
                ),
                OutlineSection(
                    workspace_id=workspace.id,
                    stable_key="synthetic-suggested-section",
                    title="项目实施计划",
                    sort_order=1,
                    origin="ai",
                    review_status="suggested",
                    source_ref_id=suggested_source.id,
                ),
                ScoringCriterion(
                    workspace_id=workspace.id,
                    stable_key="synthetic-confirmed-criterion",
                    title="技术方案完整性",
                    requirement="提供完整技术实施方案",
                    max_score=10,
                    review_status="confirmed",
                    source_ref_id=confirmed_source.id,
                ),
                ScoringCriterion(
                    workspace_id=workspace.id,
                    stable_key="synthetic-suggested-criterion",
                    title="进度计划合理性",
                    requirement="提供项目进度计划",
                    max_score=5,
                    review_status="suggested",
                    source_ref_id=suggested_source.id,
                ),
                WorkspaceRevision(
                    workspace_id=workspace.id,
                    revision=1,
                    action="workspace_create",
                    snapshot=json.dumps(
                        {"sections": [], "criteria": [], "mappings": [], "materials": []}
                    ),
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
