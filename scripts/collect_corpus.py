"""Real-World Corpus Collector Script.

Stages open-access scientific paper excerpts and abstracts into datasets/real/documents/
and computes deterministic SHA-256 content hashes for provenance verification.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict

ROOT_DIR = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT_DIR / "datasets" / "real" / "manifest.json"
DOCS_DIR = ROOT_DIR / "datasets" / "real" / "documents"


def collect_corpus() -> Dict[str, Any]:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Manifest not found: {MANIFEST_PATH}")

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    papers = manifest.get("papers", [])
    print(f"Staging {len(papers)} open-access scientific papers...")

    hashes = {}

    for p in papers:
        pid = p["paper_id"]
        title = p["title"]
        authors = ", ".join(p["authors"])
        venue = p["venue"]
        year = p["year"]
        abstract = p["abstract"]
        url = p["open_access_url"]

        content = (
            f"Title: {title}\n"
            f"Authors: {authors}\n"
            f"Venue: {venue} ({year})\n"
            f"Open Access URL: {url}\n\n"
            f"Abstract:\n{abstract}\n\n"
            f"Summary Notes:\n"
            f"This paper introduces {p['key_entities'][0]} developed by {p['key_entities'][-1]} in {year}. "
            f"It addresses foundational machine intelligence architectures.\n"
        )

        out_path = ROOT_DIR / p["file_path"]
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with open(out_path, "w", encoding="utf-8") as pf:
            pf.write(content)

        sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        hashes[pid] = {
            "title": title,
            "path": str(out_path.relative_to(ROOT_DIR)),
            "sha256": sha,
            "bytes": len(content.encode("utf-8")),
        }
        print(f" - [{pid}] {title} ({sha[:12]}...) -> {out_path.name}")

    hash_manifest_path = ROOT_DIR / "datasets" / "real" / "checksums.json"
    with open(hash_manifest_path, "w", encoding="utf-8") as hf:
        json.dump(hashes, hf, indent=2)

    print(f"\nAll papers staged successfully. Checksums saved to {hash_manifest_path}")
    return hashes


if __name__ == "__main__":
    collect_corpus()
