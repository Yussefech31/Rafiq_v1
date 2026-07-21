"""Rule-based chunking for RAFIQ ingestion pipeline (Phase 1)."""
import logging
import re
from typing import Optional

from backend.config import Chunk
from backend.ingestion.normalize_ar import normalize_arabic
from backend.ingestion.load_excel import load_all_raw_data

logger = logging.getLogger(__name__)

# Max approximate tokens per chunk (rough: 1 token ≈ 4 chars for Arabic)
MAX_CHUNK_CHARS = 2000  # ~500 tokens

# Delimiter for Section docs field
SECTION_DOCS_DELIMITER = '||'

# Patterns for splitting on bullets/numbered lists
_BULLET_RE = re.compile(r'(?:^|\n)\s*(?:[-•●◦▪]\s+|\d+[.)]\s+|\*\s+)', re.MULTILINE)


def chunk_procedures(records: list[dict]) -> list[Chunk]:
    """
    Chunk BD idarati procedure records into indexable chunks.

    Strategy:
    1. Split 'section_docs' on '||' delimiter into individual document chunks.
    2. Create a chunk for the procedure description.
    3. Create a chunk for admin info (admin_ar, admin_fr).
    4. Split long texts on paragraph/bullet boundaries.
    5. Apply Arabic normalization.

    Args:
        records: List of procedure dicts from load_bd_idarati().

    Returns:
        List of Chunk objects ready for embedding.
    """
    chunks = []

    for record in records:
        source_id = record.get('id', 'unknown')
        title = record.get('title', '')
        chunk_idx = 0

        # 1. Section docs — split on ||
        section_docs = record.get('section_docs', '')
        if section_docs:
            doc_items = [d.strip() for d in section_docs.split(SECTION_DOCS_DELIMITER) if d.strip()]
            for doc_item in doc_items:
                normalized = normalize_arabic(doc_item)
                if normalized:
                    chunks.append(Chunk(
                        chunk_id=f"{source_id}_doc_{chunk_idx}",
                        text=normalized,
                        source_id=source_id,
                        title=title,
                        metadata={
                            'field': 'section_docs',
                            'source_file': record.get('_source_file', ''),
                        }
                    ))
                    chunk_idx += 1

        # 2. Description
        description = record.get('description', '')
        if description:
            desc_chunks = _split_long_text(
                normalize_arabic(description),
                max_chars=MAX_CHUNK_CHARS
            )
            for text_part in desc_chunks:
                chunks.append(Chunk(
                    chunk_id=f"{source_id}_desc_{chunk_idx}",
                    text=text_part,
                    source_id=source_id,
                    title=title,
                    metadata={
                        'field': 'description',
                        'source_file': record.get('_source_file', ''),
                    }
                ))
                chunk_idx += 1

        # 3. Admin info (combined ar + fr)
        admin_ar = record.get('admin_ar', '')
        admin_fr = record.get('admin_fr', '')
        admin_text = _combine_admin_info(admin_ar, admin_fr, title)
        if admin_text:
            admin_chunks = _split_long_text(admin_text, max_chars=MAX_CHUNK_CHARS)
            for text_part in admin_chunks:
                chunks.append(Chunk(
                    chunk_id=f"{source_id}_admin_{chunk_idx}",
                    text=text_part,
                    source_id=source_id,
                    title=title,
                    metadata={
                        'field': 'admin_info',
                        'source_file': record.get('_source_file', ''),
                    }
                ))
                chunk_idx += 1

        # 4. Delay + Price (combined as a small chunk)
        delay = record.get('delay', '')
        price = record.get('price', '')
        if delay or price:
            info_parts = []
            if title:
                info_parts.append(f"Procédure: {title}")
            if delay:
                info_parts.append(f"Délai: {delay}")
            if price:
                info_parts.append(f"Prix: {price}")
            info_text = ' | '.join(info_parts)
            chunks.append(Chunk(
                chunk_id=f"{source_id}_info_{chunk_idx}",
                text=info_text,
                source_id=source_id,
                title=title,
                metadata={
                    'field': 'delay_price',
                    'source_file': record.get('_source_file', ''),
                }
            ))
            chunk_idx += 1

    logger.info(f"Chunked {len(records)} procedures into {len(chunks)} chunks")
    return chunks


def chunk_split_data(records: list[dict]) -> list[Chunk]:
    """
    Convert pre-split data (data_apres_split.xlsx) into Chunk objects.

    This data is already split — each record becomes one chunk.

    Args:
        records: List of document dicts from load_split_data().

    Returns:
        List of Chunk objects.
    """
    chunks = []

    for record in records:
        proc_id = record.get('procedure_id', 'unknown')
        doc_id = record.get('id_document', '')
        title = record.get('title', '')
        doc_title = record.get('document_title', '')
        canonical = record.get('document_canonical', '')

        # Combine available text fields
        text_parts = []
        if title:
            text_parts.append(f"Procédure: {normalize_arabic(title)}")
        if doc_title:
            text_parts.append(f"Document: {normalize_arabic(doc_title)}")
        if canonical:
            text_parts.append(normalize_arabic(canonical))

        text = '\n'.join(text_parts)
        if not text.strip():
            continue

        chunk_id = f"{proc_id}_{doc_id}" if doc_id else f"{proc_id}_{len(chunks)}"

        chunks.append(Chunk(
            chunk_id=chunk_id,
            text=text,
            source_id=proc_id,
            title=title or doc_title,
            metadata={
                'document_id': doc_id,
                'document_title': doc_title,
                'is_alternative': record.get('is_alternative', False),
                'source_file': record.get('_source_file', ''),
                'field': 'split_data',
            }
        ))

    logger.info(f"Converted {len(records)} split records into {len(chunks)} chunks")
    return chunks


def chunk_all(raw_dir: str) -> list[Chunk]:
    """
    Convenience function: load all raw data and chunk everything.

    Args:
        raw_dir: Path to the raw data directory.

    Returns:
        Combined list of all Chunk objects.
    """
    raw_data = load_all_raw_data(raw_dir)

    all_chunks = []

    if raw_data['bd_idarati']:
        all_chunks.extend(chunk_procedures(raw_data['bd_idarati']))

    if raw_data['split_data']:
        all_chunks.extend(chunk_split_data(raw_data['split_data']))

    # Deduplicate by chunk_id
    seen = set()
    deduped = []
    for chunk in all_chunks:
        if chunk.chunk_id not in seen:
            seen.add(chunk.chunk_id)
            deduped.append(chunk)

    logger.info(f"Total chunks after dedup: {len(deduped)} (from {len(all_chunks)})")
    return deduped


def _split_long_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """
    Split a long text into smaller chunks on paragraph/bullet boundaries.

    Tries to split on:
    1. Double newlines (paragraphs)
    2. Bullet points / numbered lists
    3. Single newlines
    4. Hard split at max_chars as last resort
    """
    if not text or len(text) <= max_chars:
        return [text] if text else []

    # Try paragraph splits first
    paragraphs = re.split(r'\n\s*\n', text)
    if len(paragraphs) > 1:
        return _merge_small_chunks(paragraphs, max_chars)

    # Try bullet/list splits
    parts = _BULLET_RE.split(text)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) > 1:
        return _merge_small_chunks(parts, max_chars)

    # Try newline splits
    lines = text.split('\n')
    if len(lines) > 1:
        return _merge_small_chunks(lines, max_chars)

    # Hard split as last resort
    result = []
    for i in range(0, len(text), max_chars):
        result.append(text[i:i + max_chars])
    return result


def _merge_small_chunks(parts: list[str], max_chars: int) -> list[str]:
    """Merge small adjacent parts to avoid too-small chunks."""
    merged = []
    current = ""

    for part in parts:
        part = part.strip()
        if not part:
            continue

        if current and len(current) + len(part) + 1 > max_chars:
            merged.append(current.strip())
            current = part
        else:
            current = f"{current}\n{part}" if current else part

    if current.strip():
        merged.append(current.strip())

    return merged if merged else ['\n'.join(parts)]


def _combine_admin_info(admin_ar: str, admin_fr: str, title: str) -> str:
    """Combine Arabic and French admin info into a single text."""
    parts = []
    if title:
        parts.append(f"Procédure: {normalize_arabic(title)}")
    if admin_ar:
        parts.append(f"المسطرة الإدارية: {normalize_arabic(admin_ar)}")
    if admin_fr:
        parts.append(f"Administration: {admin_fr.strip()}")

    return '\n'.join(parts) if parts else ""
