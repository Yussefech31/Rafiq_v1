"""Load raw Excel data files for RAFIQ ingestion pipeline."""
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from backend.ingestion.normalize_ar import normalize_arabic

logger = logging.getLogger(__name__)


def load_bd_idarati(filepath: str) -> list[dict]:
    """
    Load BD_idarati_consolidée Excel file.

    Reads sheet 'BD brute' with key columns:
    id, title, admin ar, admin fr, Section docs, description, delay, price,
    publication_status, committee_decision.

    The 'Section docs' column contains pipe-||-separated lists of
    required documents (in Arabic).

    Args:
        filepath: Path to the Excel file.

    Returns:
        List of procedure record dicts.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        logger.warning(f"BD idarati file not found: {filepath}")
        return []

    records = []

    # Try 'BD brute' sheet first, fallback to first sheet
    try:
        df = pd.read_excel(filepath, sheet_name='BD brute', engine='openpyxl')
        logger.info(f"Loaded 'BD brute' sheet: {len(df)} rows, {len(df.columns)} cols")
    except (ValueError, KeyError):
        try:
            df = pd.read_excel(filepath, sheet_name=0, engine='openpyxl')
            logger.info(f"Loaded first sheet (fallback): {len(df)} rows, {len(df.columns)} cols")
        except Exception as e:
            logger.error(f"Failed to read BD idarati: {e}")
            return []

    # Normalize column names (lowercase, strip)
    df.columns = [str(c).strip().lower() for c in df.columns]

    for idx, row in df.iterrows():
        record = {
            'id': str(row.get('id', idx)),
            'title': _safe_str(row.get('title', row.get('titre', ''))),
            'admin_ar': _safe_str(row.get('admin ar', row.get('admin_ar', ''))),
            'admin_fr': _safe_str(row.get('admin fr', row.get('admin_fr', ''))),
            'section_docs': _safe_str(row.get('section docs', row.get('section_docs', ''))),
            'description': _safe_str(row.get('description', '')),
            'delay': _safe_str(row.get('delay', row.get('délai', ''))),
            'price': _safe_str(row.get('price', row.get('prix', ''))),
            'publication_status': _safe_str(row.get('publication_status', '')),
            'committee_decision': _safe_str(row.get('committee_decision', '')),
            '_source_file': filepath.name,
            '_source_sheet': 'BD brute',
        }
        records.append(record)

    # Also try to load 'source' sheet for reference data
    try:
        df_source = pd.read_excel(filepath, sheet_name='source', engine='openpyxl')
        logger.info(f"Loaded 'source' sheet: {len(df_source)} rows")
        # Attach source metadata where id matches
        df_source.columns = [str(c).strip().lower() for c in df_source.columns]
    except Exception:
        logger.info("No 'source' sheet found or failed to load")

    logger.info(f"Loaded {len(records)} procedure records from BD idarati")
    return records


def load_split_data(filepath: str) -> list[dict]:
    """
    Load pre-split data Excel file (data_apres_split.xlsx).

    Columns: procedure_id, title, id_document, document_title,
    document_canonical, is_alternative.

    This is already-chunked data — treat as reference for output schema.

    Args:
        filepath: Path to the Excel file.

    Returns:
        List of document record dicts.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        logger.warning(f"Split data file not found: {filepath}")
        return []

    try:
        df = pd.read_excel(filepath, engine='openpyxl')
    except Exception as e:
        logger.error(f"Failed to read split data: {e}")
        return []

    # Normalize column names
    df.columns = [str(c).strip().lower() for c in df.columns]

    records = []
    for idx, row in df.iterrows():
        record = {
            'procedure_id': _safe_str(row.get('procedure_id', row.get('id_procedure', ''))),
            'title': _safe_str(row.get('title', row.get('titre', ''))),
            'id_document': _safe_str(row.get('id_document', '')),
            'document_title': _safe_str(row.get('document_title', row.get('titre_document', ''))),
            'document_canonical': _safe_str(row.get('document_canonical', '')),
            'is_alternative': bool(row.get('is_alternative', False)),
            '_source_file': filepath.name,
        }
        records.append(record)

    logger.info(f"Loaded {len(records)} document records from split data")
    return records


def load_all_raw_data(raw_dir: str) -> dict:
    """
    Find and load all xlsx files in the raw data directory.

    Returns:
        Dict with keys 'bd_idarati' and 'split_data', each a list[dict].
    """
    raw_path = Path(raw_dir)
    raw_path.mkdir(parents=True, exist_ok=True)

    result = {
        'bd_idarati': [],
        'split_data': [],
    }

    for xlsx_file in raw_path.glob('*.xlsx'):
        name_lower = xlsx_file.name.lower()

        if 'idarati' in name_lower or 'consolid' in name_lower or 'bd_' in name_lower:
            logger.info(f"Loading as BD idarati: {xlsx_file.name}")
            result['bd_idarati'].extend(load_bd_idarati(str(xlsx_file)))

        elif 'split' in name_lower or 'apres' in name_lower:
            logger.info(f"Loading as split data: {xlsx_file.name}")
            result['split_data'].extend(load_split_data(str(xlsx_file)))

        else:
            # Try split data format first (simpler schema)
            logger.info(f"Unknown file {xlsx_file.name}, trying split data format")
            records = load_split_data(str(xlsx_file))
            if records:
                result['split_data'].extend(records)
            else:
                records = load_bd_idarati(str(xlsx_file))
                result['bd_idarati'].extend(records)

    total = len(result['bd_idarati']) + len(result['split_data'])
    logger.info(f"Total raw records loaded: {total} "
                f"(bd_idarati: {len(result['bd_idarati'])}, "
                f"split_data: {len(result['split_data'])})")
    return result


def _safe_str(value) -> str:
    """Convert a value to string safely, handling NaN and None."""
    if pd.isna(value) or value is None:
        return ""
    return str(value).strip()
