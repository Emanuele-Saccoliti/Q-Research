from __future__ import annotations

import json
import re
from pathlib import Path

from macro_research_assistant.schemas import MacroResearchReport


def slugify(value: str, max_length: int = 72) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return (slug or "macro-research")[:max_length].strip("-")


def report_to_markdown(report: MacroResearchReport) -> str:
    lines: list[str] = [
        f"# Macro Research Report: {report.query}",
        "",
        f"Generated: {report.generated_at.isoformat()}",
        f"Sources: {report.source_count}",
        "",
        "## Executive Summary",
        "",
        report.executive_summary,
        "",
        "## Key Themes",
        "",
    ]

    lines.extend(f"- {theme}" for theme in report.key_themes)
    lines.extend(["", "## Research Signals", ""])

    for signal in report.signals:
        lines.extend(
            [
                f"### {signal.theme}",
                "",
                f"- Direction: `{signal.direction}`",
                f"- Time horizon: `{signal.time_horizon}`",
                f"- Confidence: `{signal.confidence:.2f}`",
                f"- Affected assets: {', '.join(signal.affected_assets) or 'n/a'}",
                f"- Research note: {signal.research_note}",
                "- Evidence:",
            ]
        )
        lines.extend(f"  - {item}" for item in signal.evidence)
        lines.append("")

    lines.extend(["## Market Implications", ""])
    lines.extend(f"- {item}" for item in report.market_implications)

    lines.extend(["", "## Risks To Watch", ""])
    lines.extend(f"- {item}" for item in report.risks_to_watch)

    lines.extend(["", "## Sources", ""])
    lines.extend(f"- {source}" for source in report.sources)

    lines.extend(["", "## Retrieved Context", ""])
    for item in report.news_items:
        url = f" - {item.url}" if item.url else ""
        lines.append(f"- {item.title} ({item.source}){url}")

    return "\n".join(lines).strip() + "\n"


def save_report(
    report: MacroResearchReport,
    output_dir: Path,
    output_format: str = "both",
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = report.generated_at.strftime("%Y%m%d-%H%M%S")
    base_name = f"{timestamp}-{slugify(report.query)}"
    written: list[Path] = []

    if output_format in {"markdown", "both"}:
        markdown_path = output_dir / f"{base_name}.md"
        markdown_path.write_text(report_to_markdown(report), encoding="utf-8")
        written.append(markdown_path)

    if output_format in {"json", "both"}:
        json_path = output_dir / f"{base_name}.json"
        json_path.write_text(
            json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        written.append(json_path)

    return written
