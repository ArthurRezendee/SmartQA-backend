from sqlalchemy.orm import Session
from sqlalchemy import func

from app.shared.controller import BaseController
from app.modules.documentation.model.documentation_model import Documentation
from app.modules.qa_analysis.model.qa_analysis_model import QaAnalysis
from fastapi.responses import StreamingResponse
import io
from app.modules.export.service.pdf_service import PDFService


class DocumentationsController(BaseController):

    # ============================
    # GETs
    # ============================

    def get_by_analysis(self, db: Session, analysis_id: int):
        docs = (
            db.query(Documentation)
            .filter(Documentation.qa_analysis_id == analysis_id)
            .order_by(Documentation.version.desc())
            .all()
        )

        return {
            "status": True,
            "data": [
                {
                    "id": d.id,
                    "analysis_id": d.qa_analysis_id,
                    "title": d.title,
                    "version": d.version,
                    "status": d.status,
                    "content_format": d.content_format,
                    "generated_by": d.generated_by,
                    "generator_model": d.generator_model,
                    "created_at": d.created_at,
                }
                for d in docs
            ],
        }

    def get_latest_by_analysis(self, db: Session, analysis_id: int):
        doc = (
            db.query(Documentation)
            .filter(Documentation.qa_analysis_id == analysis_id)
            .order_by(Documentation.version.desc())
            .first()
        )

        if not doc:
            return None

        return {
            "status": True,
            "data": {
                "id": doc.id,
                "analysis_id": doc.qa_analysis_id,
                "title": doc.title,
                "version": doc.version,
                "status": doc.status,
                "content": doc.content,
                "content_format": doc.content_format,
                "generated_by": doc.generated_by,
                "generator_model": doc.generator_model,
                "created_at": doc.created_at,
            },
        }

    # ============================
    # PUT – atualizar documentação
    # ============================

    def update(self, db: Session, analysis_id: int, payload: dict):
        documentation = (
            db.query(Documentation)
            .filter(Documentation.qa_analysis_id == analysis_id)
            .order_by(Documentation.version.desc())
            .first()
        )

        if not documentation:
            return {
                "status": False,
                "message": "Documentação não encontrada",
            }

        editable_fields = [
            "title",
            "content",
            "status",
            "content_format",
        ]

        for field in editable_fields:
            if field in payload:
                setattr(documentation, field, payload[field])

        documentation.version += 1  
        
        # marcou como edição manual
        documentation.generated_by = "user"

        db.commit()
        db.refresh(documentation)

        return {
            "status": True,
            "message": "Documentação atualizada com sucesso",
            "data": {
                "id": documentation.id,
                "analysis_id": documentation.qa_analysis_id,
                "version": documentation.version,
                "status": documentation.status,
                "content": documentation.content,
            },
        }
        
    def export(self, db: Session, documentation_id: int):

        documentation = (
            db.query(Documentation)
            .filter(Documentation.id == documentation_id)
            .first()
        )

        if not documentation:
            return {
                "status": False,
                "message": "Documentação não encontrada",
            }

        content = documentation.content

        pdf_service = PDFService()

        pdf_bytes = pdf_service.generate_pdf(
            content=content,
            format_type="md" 
        )

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=documentation_{documentation.id}.pdf"
            }
        )