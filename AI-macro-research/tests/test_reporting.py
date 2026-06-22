from datetime import UTC, datetime

from macro_research_extension.reporting import report_to_markdown
from macro_research_extension.schemas import (
    DynamicResearchReport,
    MacroAxisVector,
    MacroRegime,
)


def test_markdown_contains_dynamic_sections():
    report = DynamicResearchReport(
        query="US inflation",
        generated_at=datetime(2026, 6, 21, tzinfo=UTC),
        executive_summary="Inflation narratives remain prominent.",
        key_findings=["Inflation attention increased."],
        risks_to_watch=["The sample is small."],
        regime=MacroRegime(
            name="policy_tightening",
            state=MacroAxisVector(inflation=0.5, policy=0.4),
            confidence=0.6,
        ),
    )

    markdown = report_to_markdown(report)

    assert "## Macro State" in markdown
    assert "## Dynamic Themes" in markdown
    assert "## Cross-Asset Research Mapping" in markdown
    assert "## Disclaimer" in markdown

