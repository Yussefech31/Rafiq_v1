"""Document generation: Word template filling + PDF export."""

import logging
import os
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from backend.config import get_settings

logger = logging.getLogger(__name__)


def render_docx(
    question: str,
    answer: str,
    objet: str = "",
    date: str = None,
    signature: str = "Le Directeur",
) -> str:
    """Fill the Word template and return the file path."""
    from docxtpl import DocxTemplate

    settings = get_settings()
    template_path = Path(settings.template_path)
    if not template_path.exists():
        logger.error(f"Word template not found at {template_path}")
        raise FileNotFoundError(f"Word template not found at {template_path}")

    # Ensure output directory exists
    output_dir = Path(settings.documents_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Prepare Context
    context = {
        'en_tete': 'Ministère de la Transition Numérique',
        'objet': objet or "Réponse officielle",
        'question': question,
        'corps': answer,
        'date': date or datetime.now().strftime('%d/%m/%Y'),
        'signature': signature,
    }

    logger.info(f"Rendering Word template {template_path}...")
    doc = DocxTemplate(str(template_path))
    doc.render(context)

    # Save output file
    filename = f"reponse_{datetime.now():%Y%m%d_%H%M%S}.docx"
    output_path = output_dir / filename
    doc.save(str(output_path))
    logger.info(f"Word document saved to {output_path}")

    return str(output_path)


def convert_to_pdf(docx_path: str) -> str:
    """Convert docx to PDF via LibreOffice headless.

    If LibreOffice is not installed, throws FileNotFoundError so caller can handle gracefully.
    """
    settings = get_settings()
    docx_file = Path(docx_path)
    if not docx_file.exists():
        raise FileNotFoundError(f"Source DOCX file not found: {docx_path}")

    # Locate soffice
    soffice_path = shutil.which("soffice")
    if not soffice_path:
        # Check standard Windows installation path
        std_path = r"C:\Program Files\LibreOffice\program\soffice.exe"
        if Path(std_path).exists():
            soffice_path = std_path

    if not soffice_path:
        logger.warning("LibreOffice (soffice) not found on PATH or typical paths. PDF conversion is unavailable.")
        raise FileNotFoundError("LibreOffice (soffice) not found. PDF conversion is not available.")

    output_dir = docx_file.parent

    # Execute LibreOffice Headless
    cmd = [
        soffice_path,
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(output_dir),
        str(docx_file)
    ]

    logger.info(f"Running LibreOffice PDF conversion: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=30  # Don't hang forever
        )
        logger.info("LibreOffice conversion output: " + result.stdout.decode('utf-8', errors='replace'))
    except subprocess.TimeoutExpired as e:
        logger.error("LibreOffice conversion timed out after 30 seconds.")
        raise RuntimeError("LibreOffice PDF conversion timed out.") from e
    except subprocess.CalledProcessError as e:
        err_msg = e.stderr.decode('utf-8', errors='replace')
        logger.error(f"LibreOffice conversion failed: {err_msg}")
        raise RuntimeError(f"LibreOffice conversion failed: {err_msg}") from e

    pdf_path = docx_file.with_suffix(".pdf")
    if pdf_path.exists():
        logger.info(f"PDF document created at {pdf_path}")
        return str(pdf_path)
    else:
        logger.error("PDF file was not created by LibreOffice.")
        raise FileNotFoundError("PDF file was not created by LibreOffice conversion.")
