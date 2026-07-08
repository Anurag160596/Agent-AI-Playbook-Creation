"""
Command-line interface — the glue that runs the whole pipeline end to end.

Usage:
    python -m playbook_forge.cli examples/block_card_sop.txt
    python -m playbook_forge.cli examples/block_card_sop.txt --out build/
    python -m playbook_forge.cli examples/block_card_sop.txt --no-ai   # force offline demo

What it does, in order:
    1. Read the SOP text file.
    2. Extract a structured Playbook (AI if a key is present, else offline demo).
    3. Validate it (compliance + structural checks).
    4. Render it to Markdown + a Mermaid diagram.
    5. Print a summary and, optionally, write the outputs to disk.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playbook_forge.extractor import extract_playbook, _has_credentials
from playbook_forge.renderer import to_markdown, to_mermaid
from playbook_forge.validator import Severity, summarize, validate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Turn an SOP into a compliance-checked playbook.")
    parser.add_argument("sop", help="Path to the SOP text file.")
    parser.add_argument("--out", help="Directory to write playbook.json / .md / .mmd into.")
    parser.add_argument("--no-ai", action="store_true", help="Skip the model and use the offline demo playbook.")
    args = parser.parse_args(argv)

    sop_path = Path(args.sop)
    if not sop_path.exists():
        print(f"error: SOP file not found: {sop_path}", file=sys.stderr)
        return 2

    sop_text = sop_path.read_text()

    # --- 1 & 2: extract -------------------------------------------------------
    mode = "OFFLINE (demo)" if (args.no_ai or not _has_credentials()) else f"LIVE (Claude)"
    print(f"→ Extracting playbook from {sop_path.name}   [mode: {mode}]")
    playbook = extract_playbook(sop_text, source_name=sop_path.stem, use_ai=not args.no_ai)
    print(f"  got '{playbook.intent}' with {len(playbook.steps)} steps")

    # --- 3: validate (pass the SOP text so citations are verified against it) --
    issues = validate(playbook, source_text=sop_text)
    print(f"\n→ Validation: {summarize(issues)}")
    for issue in issues:
        print(f"   {issue}")

    # --- 4: render ------------------------------------------------------------
    markdown = to_markdown(playbook)
    mermaid = to_mermaid(playbook)

    # --- 5: output ------------------------------------------------------------
    if args.out:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{playbook.intent}.json").write_text(playbook.model_dump_json(indent=2))
        (out_dir / f"{playbook.intent}.md").write_text(markdown)
        (out_dir / f"{playbook.intent}.mmd").write_text(mermaid)
        print(f"\n→ Wrote {playbook.intent}.json / .md / .mmd to {out_dir}/")
    else:
        print("\n" + "=" * 70)
        print(markdown)

    # Exit non-zero if there are hard errors — useful in CI / review gates.
    has_errors = any(i.severity == Severity.ERROR for i in issues)
    return 1 if has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
