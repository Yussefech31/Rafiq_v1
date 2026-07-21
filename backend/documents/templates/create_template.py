"""Script to create the Word response template for RAFIQ.

Usage:
    python -m backend.documents.templates.create_template
"""
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from pathlib import Path


def create_template():
    """Create reponse_template.docx with docxtpl placeholders."""
    doc = Document()

    # Page margins
    for section in doc.sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)

    # Header block
    header_para = doc.add_paragraph()
    header_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = header_para.add_run('{{ en_tete }}')
    run.font.size = Pt(14)
    run.bold = True

    doc.add_paragraph()  # spacer

    # Objet line
    objet_para = doc.add_paragraph()
    run = objet_para.add_run('Objet : ')
    run.bold = True
    run.font.size = Pt(12)
    objet_para.add_run('{{ objet }}')

    doc.add_paragraph()

    # Question received
    q_para = doc.add_paragraph()
    run = q_para.add_run('Question reçue : ')
    run.bold = True
    run.font.size = Pt(11)
    q_para.add_run('{{ question }}')

    doc.add_paragraph()

    # Corps de réponse
    body_para = doc.add_paragraph()
    body_para.add_run('{{ corps }}')

    doc.add_paragraph()
    doc.add_paragraph()

    # Date (right-aligned)
    date_para = doc.add_paragraph()
    date_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    date_para.add_run('{{ date }}')

    doc.add_paragraph()

    # Signature block (right-aligned)
    sig_para = doc.add_paragraph()
    sig_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = sig_para.add_run('{{ signature }}')
    run.bold = True

    # Save
    output = Path(__file__).parent / 'reponse_template.docx'
    doc.save(str(output))
    print(f'Template created at: {output}')
    return str(output)


if __name__ == '__main__':
    create_template()
