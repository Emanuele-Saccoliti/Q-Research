from __future__ import annotations

import json
import re
from pathlib import Path

from macro_research_extension.schemas import DynamicResearchReport


def slugify(value: str, max_length: int = 72) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return (slug or "dynamic-macro-research")[:max_length].strip("-")


def report_to_markdown(report: DynamicResearchReport) -> str:
    state = report.regime.state
    lines = [
        f"# Dynamic Macro Research Report: {report.query}",
        "",
        f"Generated: {report.generated_at.isoformat()}",
        f"Inferred regime: `{report.regime.name}`",
        f"Regime confidence: `{report.regime.confidence:.2f}`",
        "",
        "## Executive Summary",
        "",
        report.executive_summary,
        "",
        "## Macro State",
        "",
        "| Axis | Score |",
        "| --- | ---: |",
        f"| Growth | {state.growth:+.2f} |",
        f"| Inflation | {state.inflation:+.2f} |",
        f"| Policy | {state.policy:+.2f} |",
        f"| Liquidity | {state.liquidity:+.2f} |",
        f"| Risk sentiment | {state.risk_sentiment:+.2f} |",
        "",
        "## Dynamic Themes",
        "",
    ]

    for theme in report.themes:
        metrics = theme.metrics
        vector = theme.macro_vector
        lines.extend(
            [
                f"### {theme.label}",
                "",
                f"Theme ID: `{theme.theme_id}`",
                "",
                f"- Attention: `{metrics.attention:.2f}`",
                f"- Momentum z-score: `{metrics.momentum_zscore:+.2f}`",
                f"- Breadth: `{metrics.breadth:.2f}`",
                f"- Novelty: `{metrics.novelty:.2f}`",
                f"- Persistence: `{metrics.persistence:.2f}`",
                f"- Sources / articles: `{metrics.source_count}` / `{metrics.article_count}`",
                f"- Mapping confidence: `{theme.mapping_confidence:.2f}`",
                (
                    "- Macro vector: "
                    f"growth `{vector.growth:+.2f}`, inflation `{vector.inflation:+.2f}`, "
                    f"policy `{vector.policy:+.2f}`, liquidity `{vector.liquidity:+.2f}`, "
                    f"risk `{vector.risk_sentiment:+.2f}`"
                ),
                "- Representative summaries:",
            ]
        )
        lines.extend(f"  - {summary}" for summary in theme.representative_summaries)
        lines.append("")

    lines.extend(["## Cross-Asset Research Mapping", ""])
    lines.append("| Asset | Direction | Score | Confidence |")
    lines.append("| --- | --- | ---: | ---: |")
    for implication in report.asset_implications:
        lines.append(
            f"| {implication.asset_class} | {implication.direction} | "
            f"{implication.score:+.2f} | {implication.confidence:.2f} |"
        )

    lines.extend(["", "## Key Findings", ""])
    lines.extend(f"- {item}" for item in report.key_findings)
    lines.extend(["", "## Risks And Limitations", ""])
    lines.extend(f"- {item}" for item in report.risks_to_watch)

    lines.extend(["", "## Normalized Events", ""])
    for event in report.events:
        lines.append(f"- **{event.title}** ({event.source}): {event.summary}")

    lines.extend(["", "## Sources", ""])
    lines.extend(f"- {source}" for source in report.sources)
    lines.extend(
        [
            "",
            "## Disclaimer",
            "",
            (
                "This report is for research and educational purposes only. Dynamic themes, "
                "regimes, and asset mappings are model outputs, not investment advice or "
                "validated trading signals."
            ),
        ]
    )
    return "\n".join(lines).strip() + "\n"


def save_report(
    report: DynamicResearchReport,
    output_dir: Path,
    output_format: str,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = report.generated_at.strftime("%Y%m%d-%H%M%S")
    base_name = f"{timestamp}-{slugify(report.query)}"
    written: list[Path] = []

    if output_format in {"markdown", "both"}:
        path = output_dir / f"{base_name}.md"
        path.write_text(report_to_markdown(report), encoding="utf-8")
        written.append(path)

    if output_format in {"json", "both"}:
        path = output_dir / f"{base_name}.json"
        path.write_text(
            json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        written.append(path)

    return written

