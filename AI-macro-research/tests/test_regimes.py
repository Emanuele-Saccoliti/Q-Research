from macro_research_extension.mapping import CrossAssetMapper
from macro_research_extension.regimes import RegimeInferer
from macro_research_extension.schemas import DynamicTheme, MacroAxisVector, ThemeMetrics


def _stagflation_theme() -> DynamicTheme:
    return DynamicTheme(
        theme_id="theme-test",
        label="Sticky inflation and weaker growth",
        event_ids=[0, 1],
        representative_summaries=["Inflation rose while growth weakened."],
        metrics=ThemeMetrics(
            attention=1.0,
            momentum_zscore=1.0,
            breadth=1.0,
            novelty=0.5,
            persistence=0.8,
            source_count=3,
            article_count=2,
        ),
        macro_vector=MacroAxisVector(
            growth=-0.6,
            inflation=0.8,
            policy=0.5,
            liquidity=-0.2,
            risk_sentiment=-0.3,
        ),
        mapping_confidence=0.9,
    )


def test_regime_and_cross_asset_mapping():
    regime = RegimeInferer().infer([_stagflation_theme()])
    implications = CrossAssetMapper().map(regime)
    by_asset = {item.asset_class: item for item in implications}

    assert regime.name == "stagflation_pressure"
    assert by_asset["Long-duration government bonds (price)"].direction == "negative"
    assert by_asset["US dollar"].direction == "positive"

