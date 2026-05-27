def test_config_defaults():
    import config
    assert config.OPENAI_MODEL in ("gpt-4o-mini", "gpt-4o")
    assert isinstance(config.OPENAI_TEMPERATURE, float)
    assert config.ALL_SKILLS == [
        "quick", "screen", "comps", "rental", "neighborhood",
        "mortgage", "market", "commercial", "flip", "invest",
        "analyze", "compare", "listing",
    ]

def test_parallel_skills_subset_of_all():
    import config
    for skill in config.PARALLEL_SKILLS:
        assert skill in config.ALL_SKILLS

def test_skill_labels_covers_all():
    import config
    for skill in config.ALL_SKILLS:
        assert skill in config.SKILL_LABELS
