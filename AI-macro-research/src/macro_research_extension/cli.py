from __future__ import annotations

import argparse
import sys
from pathlib import Path

from macro_research_extension.config import get_settings
from macro_research_extension.workflow import DynamicMacroResearchWorkflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="macro-research-extension",
        description="Discover dynamic macro themes, infer regimes, and generate research reports.",
    )
    parser.add_argument("query", nargs="?", help="Macro research question or mandate.")
    parser.add_argument("--max-articles", type=int, default=None)
    parser.add_argument("--feed-url", action="append", default=[])
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--format", choices=["markdown", "json", "both"], default="both")
    parser.add_argument(
        "--embedding-provider",
        choices=["hashing", "sentence-transformer"],
        default=None,
    )
    parser.add_argument("--no-history", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    query = args.query or input("What macro topic do you want to research? ").strip()
    if not query:
        print("A non-empty query is required.", file=sys.stderr)
        return 2

    try:
        settings = get_settings()
        if args.embedding_provider:
            settings = settings.model_copy(
                update={"embedding_provider": args.embedding_provider}
            )
        workflow = DynamicMacroResearchWorkflow(settings)
        report, paths = workflow.run_and_save(
            query,
            feed_urls=args.feed_url,
            max_articles=args.max_articles,
            use_history=not args.no_history,
            output_dir=args.output_dir,
            output_format=args.format,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Regime: {report.regime.name} ({report.regime.confidence:.2f})")
    print(f"Dynamic themes: {len(report.themes)} | Events: {len(report.events)}")
    for path in paths:
        print(f"Wrote: {path}")
    return 0

