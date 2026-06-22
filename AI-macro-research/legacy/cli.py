from __future__ import annotations

import argparse
import sys
from pathlib import Path

from macro_research_assistant.config import get_settings
from macro_research_assistant.workflow import MacroResearchWorkflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="macro-research",
        description="Retrieve macro/financial news and generate structured research signals.",
    )
    parser.add_argument("query", nargs="?", help="Macro research question or topic.")
    parser.add_argument(
        "--max-articles",
        type=int,
        default=None,
        help="Maximum number of retrieved articles/items to analyze.",
    )
    parser.add_argument(
        "--feed-url",
        action="append",
        default=[],
        help="Optional RSS feed URL. Can be passed multiple times.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory where reports are saved.",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json", "both"],
        default="both",
        help="Report output format.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    query = args.query or input("What macro topic do you want to research? ").strip()

    if not query:
        print("A non-empty query is required.", file=sys.stderr)
        return 2

    try:
        settings = get_settings()
        workflow = MacroResearchWorkflow(settings=settings)
        report, paths = workflow.run_and_save(
            query,
            feed_urls=args.feed_url,
            max_articles=args.max_articles,
            output_dir=args.output_dir,
            output_format=args.format,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Generated report for: {report.query}")
    print(f"Signals: {len(report.signals)} | Sources: {report.source_count}")
    for path in paths:
        print(f"Wrote: {path}")

    return 0
