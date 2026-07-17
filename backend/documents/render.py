"""Document generation: Word template filling + PDF export. Phase 3 implementation."""

from pathlib import Path
from datetime import datetime
from backend.config import get_settings


def render_docx(
    question: str,
    answer: str,
    objet: str = "",
    date: str = None,
    signature: str = "Le Directeur",
) -> str:
    """Fill the Word template and return the file path. Phase 1: stub.

    Phase 3 will:
      - Load reponse_template.docx via docxtpl
      - Render with context variables
      - Save to output directory
    """
    # TODO Phase 3: Use docxtpl to fill template
    # from docxtpl import DocxTemplate
    # settings = get_settings()
    # doc = DocxTemplate(settings.template_path)
    # context = {
    #     'en_tete': 'Ministère de la Transition Numérique',
    #     'objet': objet,
    #     'question': question,
    #     'corps': answer,
    #     'date': date or datetime.now().strftime('%d/%m/%Y'),
    #     'signature': signature,
    # }
    # doc.render(context)
    # output_path = Path(settings.documents_dir) / f"reponse_{datetime.now():%Y%m%d_%H%M%S}.docx"
    # output_path.parent.mkdir(parents=True, exist_ok=True)
    # doc.save(str(output_path))
    # return str(output_path)
    raise NotImplementedError("Document generation is not yet implemented (Phase 3).")


def convert_to_pdf(docx_path: str) -> str:
    """Convert docx to PDF via LibreOffice headless. Phase 1: stub.

    Phase 3 will:
      - Run LibreOffice in headless mode
      - Convert the docx to PDF
      - Return the PDF path
    """
    # TODO Phase 3: subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', docx_path])
    raise NotImplementedError("PDF conversion is not yet implemented (Phase 3).")
