"""Ingestion script for CivicPulse municipal knowledge base.

Usage:
    python -m rag.ingest [--yes]
"""
import os
import re
import sys
import argparse
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from collections import Counter, defaultdict
from typing import Dict, Any, List, Tuple

from dotenv import load_dotenv

load_dotenv()

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_postgres import PGVector

from .embeddings import CivicPulseEmbeddings
from .service import get_connection_url, COLLECTION_NAME

EXEMPT_SOURCE_URL_PREFIXES = (
    "platform_", "guide_", "example_", "playbook_", "admin_"
)

PREFIX_TYPE_MAP = [
    ("dept_", "department"),
    ("sop_", "sop"),
    ("rti_", "legal"),
    ("escalation_", "legal"),
    ("legal_", "legal"),
    ("scheme_", "scheme"),
    ("portal_", "portal"),
    ("disaster_", "disaster"),
    ("health_", "health"),
    ("infra_", "infra"),
    ("seasonal_", "seasonal"),
    ("platform_", "platform"),
    ("guide_", "guide"),
    ("glossary_", "glossary"),
    ("playbook_", "playbook"),
    ("service_", "service"),
    ("governance_", "governance"),
    ("util_", "util"),
    ("env_", "env"),
    ("safety_", "safety"),
    ("city_", "city"),
    ("admin_", "admin"),
    ("example_", "example"),
]


def infer_type_from_filename(stem: str) -> str:
    """Infer document type from filename prefix."""
    stem_lower = stem.lower()
    for prefix, doc_type in PREFIX_TYPE_MAP:
        if stem_lower.startswith(prefix):
            return doc_type
    return "general"


def parse_front_matter(content: str) -> Tuple[Dict[str, Any], str]:
    """Extract YAML-style front matter if present between leading triple-dashes.

    Returns:
        (metadata_dict, remaining_body_text)
    """
    metadata: Dict[str, Any] = {}
    content_stripped = content.strip()

    if content_stripped.startswith("---"):
        parts = content_stripped.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1].strip()
            body_text = parts[2].strip()

            for line in fm_text.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or ":" not in line:
                    continue
                key, val = line.split(":", 1)
                key = key.strip().lower()
                val = val.strip().strip('"').strip("'")

                if val.lower() == "true":
                    val_parsed = True
                elif val.lower() == "false":
                    val_parsed = False
                else:
                    val_parsed = val

                metadata[key] = val_parsed

            return metadata, body_text

    return metadata, content


def process_knowledge_directory(knowledge_dir: Path) -> Tuple[List[Document], List[str], Dict[str, List[str]]]:
    """Read knowledge documents, parse front matter, drop VERIFY lines, check warnings, and split."""
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("##", "section")],
        strip_headers=False
    )
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=700,
        chunk_overlap=100
    )

    documents: List[Document] = []
    warnings: List[str] = []
    verify_records: Dict[str, List[Tuple[str, str]]] = defaultdict(list)  # filename -> list of (line, source_url)

    supported_extensions = {".md", ".txt"}
    files = sorted([
        f for f in knowledge_dir.rglob("*")
        if f.suffix.lower() in supported_extensions
        and not any(part.startswith("_") for part in f.relative_to(knowledge_dir).parts)
        and "rates" not in f.parts
    ])

    if not files:
        print(f"No valid .md or .txt files found in {knowledge_dir}")
        return [], warnings, verify_records

    print(f"\nProcessing {len(files)} knowledge files from {knowledge_dir}...")
    today = datetime.now()

    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                raw_text = fh.read()

            fm, body = parse_front_matter(raw_text)

            # Metadata resolution
            filename = f.name
            stem = f.stem
            doc_type = fm.get("type") or infer_type_from_filename(stem)
            title = fm.get("title") or stem.replace("_", " ").title()
            city = fm.get("city", "Pune")
            language = fm.get("language", "en")
            source_url = fm.get("source_url", "")
            last_verified = str(fm.get("last_verified", "")).strip()
            synthetic = bool(fm.get("synthetic", False) or doc_type == "example")

            # Warnings check
            is_exempt_url = any(f.name.lower().startswith(p) for p in EXEMPT_SOURCE_URL_PREFIXES)
            source_type = str(fm.get("source_type", "")).strip().lower()
            if not source_url and not is_exempt_url and doc_type != "general" and source_type != "general_knowledge" and fm.get("status") != "unsourced":
                warnings.append(f"[MISSING SOURCE_URL] {filename}")

            if last_verified:
                try:
                    dt = datetime.strptime(last_verified, "%Y-%m-%d")
                    days_old = (today - dt).days
                    if days_old > 365:
                        warnings.append(f"[OUTDATED > 365 DAYS] {filename} (verified on {last_verified}, {days_old} days ago)")
                except Exception:
                    pass

            # Word count warning
            word_count = len(body.split())
            if word_count < 80:
                warnings.append(f"[SHORT CONTENT < 80 WORDS] {filename} ({word_count} words)")

            # Line-by-line VERIFY filtering
            clean_lines = []
            dropped_verify_count = 0
            for line in body.splitlines():
                if "VERIFY" in line:
                    dropped_verify_count += 1
                    verify_records[filename].append((line.strip(), source_url))
                else:
                    clean_lines.append(line)

            if dropped_verify_count > 0:
                print(f"  - {filename}: dropped {dropped_verify_count} line(s) containing 'VERIFY'")

            clean_text = "\n".join(clean_lines).strip()
            if not clean_text:
                continue

            # Two-stage splitting
            header_docs = header_splitter.split_text(clean_text)
            for hdoc in header_docs:
                section_title = hdoc.metadata.get("section", "").strip()
                chunks = char_splitter.split_text(hdoc.page_content)

                for chunk in chunks:
                    prefix = f"{title} > {section_title}" if section_title else f"{title}"
                    prefixed_content = f"{prefix}\n\n{chunk.strip()}"

                    chunk_meta = {
                        "source": filename,
                        "title": title,
                        "type": doc_type,
                        "city": city,
                        "language": language,
                        "source_url": source_url,
                        "last_verified": last_verified,
                        "synthetic": synthetic,
                        "section": section_title
                    }

                    if doc_type == "department":
                        dept_clean = stem.replace("dept_", "").replace("_", " ").title()
                        chunk_meta["department"] = dept_clean
                    elif doc_type == "sop":
                        cat_clean = stem.replace("sop_", "").replace("_", " ").title()
                        chunk_meta["category"] = cat_clean

                    documents.append(Document(
                        page_content=prefixed_content,
                        metadata=chunk_meta
                    ))

        except Exception as e:
            print(f"  ! Error processing {f.name}: {e}")

    # Generate knowledge/_REVIEW.md
    write_review_file(knowledge_dir, verify_records, warnings)

    return documents, warnings, verify_records


def write_review_file(knowledge_dir: Path, verify_records: Dict[str, List[Tuple[str, str]]], warnings: List[str]):
    """Generate knowledge/_REVIEW.md listing all dropped VERIFY lines and validation warnings."""
    review_path = knowledge_dir / "_REVIEW.md"
    total_verify = sum(len(lines) for lines in verify_records.values())

    lines = [
        "# Knowledge Base Quality & Verification Review",
        f"\nGenerated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"\n**Total Dropped VERIFY Lines:** {total_verify}",
        f"**Files With VERIFY Lines:** {len(verify_records)}",
        f"**Validation Warnings:** {len(warnings)}",
        "\n---",
        "\n## 1. Lines Dropped for Verification (`VERIFY` token)",
        "The following lines were excluded from embedding indexing to prevent hallucinations:\n"
    ]

    if not verify_records:
        lines.append("_No VERIFY lines found._\n")
    else:
        for fname, items in sorted(verify_records.items()):
            lines.append(f"### `{fname}`")
            source_url = items[0][1] if items else ""
            if source_url:
                lines.append(f"- **Source URL:** {source_url}")
            lines.append("- **Flagged Lines:**")
            for item, _ in items:
                lines.append(f"  - `{item}`")
            lines.append("")

    lines.append("\n---")
    lines.append("\n## 2. Validation Warnings")
    if not warnings:
        lines.append("_No validation warnings._\n")
    else:
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    lines.append("\n---")
    lines.append("\n## 3. Human Review Checklist")
    lines.append("- [ ] Verify all official phone numbers and contact emails via PMC official portal (.gov.in / .nic.in).")
    lines.append("- [ ] Have a native Marathi speaker review all Marathi translations (`language: mr`).")
    lines.append("- [ ] Have a native Hindi speaker review all Hindi translations (`language: hi`).")
    lines.append("- [ ] Replace `VERIFY` placeholders with verified citations once confirmed.\n")

    with open(review_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n[INFO] Generated review file: {review_path}")


def main():
    parser = argparse.ArgumentParser(description="Ingest knowledge files into PGVector.")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip interactive confirmation.")
    args = parser.parse_args()

    lock_file = Path(__file__).resolve().parent / ".ingest.lock"
    if lock_file.exists():
        print(f"\n[FATAL ERROR] Ingestion lock file exists at {lock_file}.")
        print("Another ingestion may be running, or a previous run was killed. Remove the lock file if safe.")
        sys.exit(1)

    try:
        with open(lock_file, "w", encoding="utf-8") as lf:
            lf.write(f"PID: {os.getpid()}\nStarted: {datetime.now().isoformat()}\n")

        conn_url = get_connection_url()
        if not conn_url:
            print("\n[ERROR] SUPABASE_DB_URL is not set or empty in environment. Ingestion aborted.")
            sys.exit(1)

        parsed = urlparse(conn_url)
        db_host = parsed.hostname or "unknown-host"
        db_port = parsed.port or 5432
        db_name = parsed.path.lstrip("/") or "postgres"

        print("\n=======================================================")
        print(" CIVICPULSE MUNICIPAL KNOWLEDGE BASE INGESTOR")
        print("=======================================================")
        print(f"Target Database Host: {db_host}")
        print(f"Target Port         : {db_port}")
        print(f"Target Database     : {db_name}")
        print(f"Collection Name     : {COLLECTION_NAME}")
        print("=======================================================")

        knowledge_dir = Path(__file__).resolve().parent.parent / "knowledge"
        if not knowledge_dir.exists():
            print(f"[ERROR] Knowledge directory does not exist: {knowledge_dir}")
            sys.exit(1)

        docs, warnings, verify_records = process_knowledge_directory(knowledge_dir)
        if not docs:
            print("No documents generated. Ingestion finished.")
            return

        type_counts = Counter(d.metadata.get("type", "general") for d in docs)
        print("\nChunk counts per type (local):")
        for doc_type, count in sorted(type_counts.items()):
            print(f"  - {doc_type:15}: {count} chunk(s)")
        print(f"  Total chunks    : {len(docs)}")

        if warnings:
            print(f"\n[WARNING] {len(warnings)} validation warning(s) logged to _REVIEW.md")

        if not args.yes:
            confirmation = input(f"\nProceed with recreating collection '{COLLECTION_NAME}' and adding documents? [y/N]: ").strip().lower()
            if confirmation != "y":
                print("Aborted by user.")
                sys.exit(0)

        print("\nInitializing vector store connection...")
        embeddings = CivicPulseEmbeddings()
        vectorstore = PGVector(
            embeddings=embeddings,
            collection_name=COLLECTION_NAME,
            connection=conn_url,
            use_jsonb=True,
            create_extension=False
        )

        try:
            print(f"Deleting existing collection '{COLLECTION_NAME}' (if any)...")
            vectorstore.delete_collection()
        except Exception as e:
            print(f"Note on delete_collection: {e}")

        try:
            print(f"Creating collection '{COLLECTION_NAME}'...")
            vectorstore.create_collection()
        except Exception as e:
            print(f"Note on create_collection: {e}")

        print(f"Indexing {len(docs)} document chunks...")
        vectorstore.add_documents(docs)

        # Database chunk count verification
        print("\nQuerying database to verify chunk counts per type...")
        raw_url = os.environ.get("SUPABASE_DB_URL", "") or conn_url
        raw_url = raw_url.replace("postgresql+psycopg://", "postgresql://", 1)

        import psycopg
        with psycopg.connect(raw_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT e.cmetadata->>'type' AS doc_type, count(*)
                    FROM langchain_pg_embedding e
                    JOIN langchain_pg_collection c ON e.collection_id = c.uuid
                    WHERE c.name = %s
                    GROUP BY doc_type
                    ORDER BY doc_type
                """, (COLLECTION_NAME,))
                db_counts = dict(cur.fetchall())

        print("\nDatabase chunk counts per type:")
        mismatches = []
        for doc_type, local_cnt in sorted(type_counts.items()):
            db_cnt = db_counts.get(doc_type, 0)
            print(f"  - {doc_type:15}: Local={local_cnt} | DB={db_cnt}")
            if local_cnt != db_cnt:
                mismatches.append((doc_type, local_cnt, db_cnt))

        for db_type, db_cnt in sorted(db_counts.items()):
            if db_type not in type_counts:
                print(f"  - [EXTRA IN DB] {db_type:15}: DB={db_cnt} | Local=0")
                mismatches.append((db_type, 0, db_cnt))

        if mismatches:
            print(f"\n[FATAL ERROR] Chunk count mismatch between local documents and database: {mismatches}")
            sys.exit(1)

        print(f"\n[VERIFIED] Database contains exactly {sum(db_counts.values())} chunks matching all local categories.")
        print("[SUCCESS] Ingestion completed successfully!")

    finally:
        if lock_file.exists():
            try:
                lock_file.unlink()
            except Exception:
                pass


if __name__ == "__main__":
    main()
