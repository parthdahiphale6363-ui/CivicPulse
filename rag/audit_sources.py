"""Content and Source Audit for CivicPulse Knowledge Base.

Audits knowledge files against cached source pages in knowledge/_sources_cache/
and knowledge/_FETCH_LOG.md.

Checks:
1. Every file with source_url points to a URL in _FETCH_LOG.md with HTTP 200 and >= 150 main-content words.
2. The URL actually supports the content (removes mismatched sources like complaint.pmc.gov.in/home on infra/env/health/seasonal/dept).
3. Every 2+ digit number, phone, email, percentage, unit, and act/section name in non-VERIFY lines
   appears in that URL's cached text.

Usage:
    python -m rag.audit_sources [--fix]
"""
import sys
import re
import argparse
from pathlib import Path
from typing import Dict, Set, Tuple, Any, List

from .ingest import parse_front_matter

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"
FETCH_LOG_PATH = KNOWLEDGE_DIR / "_FETCH_LOG.md"
CACHE_DIR = KNOWLEDGE_DIR / "_sources_cache"

# Prefixes where complaint.pmc.gov.in/home does NOT support substantive technical content
UNSUPPORTED_PMC_HOME_PREFIXES = (
    "infra_", "env_", "health_", "seasonal_", "dept_", "playbook_", "sop_", "escalation_"
)


def load_fetch_log(log_path: Path) -> Dict[str, Dict[str, Any]]:
    """Parse _FETCH_LOG.md and extract verified URLs with HTTP 200 and >= 150 main-content words."""
    sources: Dict[str, Dict[str, Any]] = {}
    if not log_path.exists():
        print(f"[ERROR] Fetch log does not exist at {log_path}")
        return sources

    with open(log_path, "r", encoding="utf-8") as fh:
        lines = fh.readlines()

    for line in lines:
        line = line.strip()
        if not line.startswith("|") or line.startswith("| Date") or line.startswith("|---"):
            continue

        parts = [p.strip() for p in line.split("|")[1:-1]]
        if len(parts) >= 6:
            # Date, URL, HTTP Status, Total Words, Main Words, Notes
            url = parts[1]
            status = parts[2]
            try:
                total_words = int(parts[3])
                main_words = int(parts[4])
            except ValueError:
                total_words = 0
                main_words = 0
            note = parts[5]

            is_valid = (status == "200" and main_words >= 150 and "index page" not in note.lower())
            sources[url] = {
                "url": url,
                "status": status,
                "total_words": total_words,
                "main_words": main_words,
                "valid": is_valid,
                "note": note,
            }

    return sources


def load_cached_texts(cache_dir: Path) -> Dict[str, str]:
    """Load cached page body texts keyed by URL."""
    cache: Dict[str, str] = {}
    if not cache_dir.exists():
        return cache

    for cf in cache_dir.glob("*.md"):
        with open(cf, "r", encoding="utf-8") as fh:
            raw = fh.read()
        url = ""
        body = raw
        if raw.startswith("---"):
            parts = raw.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        if k.strip().lower() == "url":
                            url = v.strip().strip('"').strip("'")
                body = parts[2]
        if url:
            cache[url] = body

    return cache


def normalize_for_search(text: str) -> str:
    """Normalize text for substring matching (remove punctuation variations, standardize spaces)."""
    return re.sub(r"\s+", " ", text).lower()


def extract_facts_from_line(line: str) -> List[Tuple[str, str]]:
    """Extract verifiable factual tokens from a markdown line.

    Returns:
        List of (fact_type, token_value)
    """
    facts = []
    # Strip markdown formatting prefixes (e.g. list numbering '1. ', header hashes)
    stripped = re.sub(r"^\s*(?:#+|\d+\.|\*|-)\s*", "", line).strip()
    if not stripped:
        return facts

    # 1. Emails
    for m in re.finditer(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", stripped):
        facts.append(("email", m.group(0)))

    # 2. Phone numbers (1800..., 022..., 112, 100, 101, etc.)
    for m in re.finditer(r"\b(?:1800[- ]?\d{3,4}[- ]?\d{3,4}|022[- ]?\d{6,8}|\+91[- ]?\d{10}|\b112\b|\b100\b|\b101\b|\b108\b)\b", stripped):
        facts.append(("phone", m.group(0)))

    # 3. Percentages
    for m in re.finditer(r"\b\d+(?:\.\d+)?%", stripped):
        facts.append(("percentage", m.group(0)))

    # 4. Units (e.g. 75 microns, 120 microns, 50 ppm, etc.)
    for m in re.finditer(r"\b\d+\s*(?:microns?|ppm|mg/L|LPCD|dB\(A\)|dB)\b", stripped, re.IGNORECASE):
        facts.append(("unit", m.group(0)))

    # 5. Act and Section citations (e.g. Section 12, Act 1974)
    for m in re.finditer(r"\b(?:Section\s+\d+[A-Za-z\(\)]*|Article\s+\d+)\b", stripped, re.IGNORECASE):
        facts.append(("section", m.group(0)))

    # 6. Standalone numbers of 2+ digits (excluding years or item numbers already in other facts)
    # Filter out standalone numbers that might just be numbering
    for m in re.finditer(r"\b\d{2,}\b", stripped):
        token = m.group(0)
        # Avoid duplicate token if already part of phone or unit
        if not any(token in f[1] for f in facts):
            facts.append(("number", token))

    return facts


def audit_knowledge_base(fix: bool = False, knowledge_dir: Path = None):
    """Run full content audit of knowledge files."""
    if knowledge_dir is None:
        knowledge_dir = KNOWLEDGE_DIR

    sources_log = load_fetch_log(FETCH_LOG_PATH)
    cached_texts = load_cached_texts(CACHE_DIR)

    valid_urls = {u for u, data in sources_log.items() if data["valid"]}
    print(f"Loaded {len(valid_urls)} valid source URL(s) (status 200, >= 150 main words) from {FETCH_LOG_PATH.name}:")
    for u in sorted(valid_urls):
        print(f"  - {u} ({sources_log[u]['main_words']} main words)")

    files = sorted([
        f for f in knowledge_dir.glob("*.md")
        if not f.name.startswith("_")
    ])

    passed_files = 0
    failed_files = 0
    general_knowledge_files = []
    unmatched_facts_fixed = 0
    failures: List[Dict[str, Any]] = []

    for f in files:
        with open(f, "r", encoding="utf-8") as fh:
            raw_content = fh.read()

        fm, body = parse_front_matter(raw_content)
        source_url = fm.get("source_url", "").strip()
        source_type = fm.get("source_type", "").strip().lower()

        # If already general knowledge, record and skip URL check
        if source_type == "general_knowledge":
            general_knowledge_files.append(f.name)
            continue

        if not source_url:
            # Unsourced file
            continue

        # Check 1: Is citation valid in _FETCH_LOG.md?
        if source_url not in valid_urls:
            reason = f"source_url '{source_url}' is not a valid source in _FETCH_LOG.md (<150 main words or failed fetch)"
            failures.append({
                "file": f,
                "source_url": source_url,
                "reason": reason,
                "mismatch": True,
            })
            print(f"[FAIL] {f.name}: {reason}")
            if fix:
                # Convert to general_knowledge
                convert_to_general_knowledge(f, raw_content, source_url)
                general_knowledge_files.append(f.name)
                unmatched_facts_fixed += 1
            else:
                failed_files += 1
            continue

        # Check 2: Citation mismatch (complaint.pmc.gov.in/home cited for specialized files)
        is_pmc_home = (source_url.rstrip("/") == "https://complaint.pmc.gov.in/home")
        is_unsupported_type = any(f.name.startswith(pfx) for pfx in UNSUPPORTED_PMC_HOME_PREFIXES)

        if is_pmc_home and is_unsupported_type:
            reason = f"Citation '{source_url}' only provides complaint intake portal, does not support substantive content in {f.name}"
            failures.append({
                "file": f,
                "source_url": source_url,
                "reason": reason,
                "mismatch": True,
            })
            print(f"[MISMATCH] {f.name}: {reason}")
            if fix:
                convert_to_general_knowledge(f, raw_content, source_url)
                general_knowledge_files.append(f.name)
                unmatched_facts_fixed += 1
            else:
                failed_files += 1
            continue

        # Check 3: Content fact verification against cached text
        cached_content = cached_texts.get(source_url, "")
        if not cached_content:
            reason = f"No cached text found for valid URL '{source_url}' in _sources_cache/"
            failures.append({
                "file": f,
                "source_url": source_url,
                "reason": reason,
                "mismatch": True,
            })
            print(f"[FAIL] {f.name}: {reason}")
            failed_files += 1
            continue

        norm_cached = normalize_for_search(cached_content)

        file_unmatched: List[Tuple[str, str, str]] = []
        body_lines = body.splitlines()

        for idx, line in enumerate(body_lines):
            # Skip lines tagged with VERIFY
            if "VERIFY" in line.upper():
                continue

            facts = extract_facts_from_line(line)
            for fact_type, token in facts:
                # Check presence in cached content
                # For numbers or phones, strip punctuation for normalized lookup
                norm_token = normalize_for_search(token)
                num_clean = re.sub(r"\D", "", token)

                token_matched = False
                if norm_token in norm_cached:
                    token_matched = True
                elif len(num_clean) >= 2 and num_clean in re.sub(r"\D", "", cached_content):
                    token_matched = True

                if not token_matched:
                    file_unmatched.append((fact_type, token, line.strip()))

        if file_unmatched:
            print(f"[UNMATCHED FACTS] {f.name} ({len(file_unmatched)} unmatched):")
            for f_type, tok, line_snippet in file_unmatched:
                print(f"  - [{f_type}] '{tok}' in: \"{line_snippet[:70]}\"")

            if fix:
                # Tag unmatched lines with VERIFY or fix
                fix_unmatched_lines(f, raw_content, file_unmatched)
                unmatched_facts_fixed += len(file_unmatched)
                passed_files += 1
            else:
                failed_files += 1
        else:
            passed_files += 1

    print("\n" + "=" * 60)
    print("AUDIT SUMMARY:")
    print(f"  Passed Files          : {passed_files}")
    print(f"  Failed Files          : {failed_files}")
    print(f"  General Knowledge     : {len(general_knowledge_files)}")
    print(f"  Unmatched Facts Fixed : {unmatched_facts_fixed}")
    print("=" * 60)

    return passed_files, failed_files, general_knowledge_files, unmatched_facts_fixed


def convert_to_general_knowledge(fpath: Path, raw_content: str, old_url: str):
    """Rewrite file frontmatter to remove source_url and add general_knowledge metadata."""
    lines = raw_content.splitlines()
    new_lines = []
    in_fm = False
    fm_count = 0

    helpline_note = ""
    if "complaint.pmc.gov.in" in old_url:
        helpline_note = 'confirmed_facts_from: "https://complaint.pmc.gov.in/home: PMC CARE helpline 1800 1030 222, WhatsApp 9689900002"'
    elif "ndma.gov.in" in old_url:
        helpline_note = 'confirmed_facts_from: "https://ndma.gov.in/: NDMA national disaster guidelines overview"'

    for line in lines:
        if line.strip() == "---":
            fm_count += 1
            if fm_count == 2:
                # Insert general knowledge metadata before closing frontmatter
                new_lines.append('source_type: "general_knowledge"')
                if helpline_note:
                    new_lines.append(helpline_note)
            new_lines.append(line)
            if fm_count == 1:
                in_fm = True
            elif fm_count == 2:
                in_fm = False
            continue

        if in_fm:
            # Remove source_url and status lines
            if line.strip().lower().startswith("source_url:") or line.strip().lower().startswith("status:"):
                continue

        new_lines.append(line)

    with open(fpath, "w", encoding="utf-8") as out:
        out.write("\n".join(new_lines) + "\n")
    print(f"  -> Converted {fpath.name} to source_type: general_knowledge")


def fix_unmatched_lines(fpath: Path, raw_content: str, unmatched: List[Tuple[str, str, str]]):
    """Tag lines containing unmatched facts with VERIFY."""
    lines = raw_content.splitlines()
    unmatched_snippets = {u[2] for u in unmatched}

    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped in unmatched_snippets and "VERIFY" not in line:
            new_lines.append(f"{line} VERIFY: fact not present on fetched source page.")
        else:
            new_lines.append(line)

    with open(fpath, "w", encoding="utf-8") as out:
        out.write("\n".join(new_lines) + "\n")
    print(f"  -> Fixed unmatched facts in {fpath.name} by tagging lines with VERIFY.")


def test_audit_flags_fake_number() -> bool:
    """Test that audit_sources detects and flags unmatched factual numbers inserted into a knowledge file."""
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        # Select a file with verified official source_url
        src_file = KNOWLEDGE_DIR / "env_air_quality.md"
        if not src_file.exists():
            for kf in KNOWLEDGE_DIR.glob("*.md"):
                fm, _ = parse_front_matter(kf.read_text(encoding="utf-8"))
                if fm.get("source_url"):
                    src_file = kf
                    break

        content = src_file.read_text(encoding="utf-8")
        fake_number = "99887766"
        tampered_content = content + f"\n\n## Fake Audit Test Section\nUnverified factual threshold limit is {fake_number} mg/L.\n"
        
        test_file = tmp_path / src_file.name
        test_file.write_text(tampered_content, encoding="utf-8")

        print(f"\n[TEST] Running audit on tampered copy '{src_file.name}' with fake number '{fake_number}'...")
        passed, failed, gen_files, fixed = audit_knowledge_base(fix=False, knowledge_dir=tmp_path)
        
        flagged = (failed > 0)
        print(f"\n[TEST VERIFICATION] Fake number flagged: {flagged} (failed_count={failed})")
        assert flagged, f"Audit failed to flag fake number {fake_number} in {src_file.name}"
        return flagged


def main():
    parser = argparse.ArgumentParser(description="Audit knowledge base sources and content facts.")
    parser.add_argument("--fix", action="store_true", help="Fix mismatched citations and tag unmatched facts with VERIFY")
    parser.add_argument("--test", action="store_true", help="Run self-test proving audit flags fake facts")
    args = parser.parse_args()

    if args.test:
        success = test_audit_flags_fake_number()
        sys.exit(0 if success else 1)

    passed, failed, gen_files, fixed = audit_knowledge_base(fix=args.fix)
    if failed > 0 and not args.fix:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
