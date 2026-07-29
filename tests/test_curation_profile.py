from types import SimpleNamespace

from src.ai.analyzer import ContentAnalyzer
from src.ai.enricher import ContentEnricher


def test_analyzer_appends_configured_curation_profile():
    client = SimpleNamespace(
        config=SimpleNamespace(curation_profile="儿童 AI 教育家长受众")
    )

    prompt = ContentAnalyzer(client)._get_system_prompt()

    assert "儿童 AI 教育家长受众" in prompt


def test_enricher_appends_configured_curation_profile():
    client = SimpleNamespace(
        config=SimpleNamespace(curation_profile="区分来源事实与编辑推断")
    )

    prompt = ContentEnricher(client)._get_enrichment_system_prompt()

    assert "区分来源事实与编辑推断" in prompt


def test_empty_profile_preserves_default_prompts():
    client = SimpleNamespace(config=SimpleNamespace(curation_profile=None))

    assert "Audience-specific curation profile" not in (
        ContentAnalyzer(client)._get_system_prompt()
    )
    assert "Audience-specific editorial profile" not in (
        ContentEnricher(client)._get_enrichment_system_prompt()
    )

