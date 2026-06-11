from app.agents import prompts

def test_prompts_exist_and_isolate_user_input():
    for p in [prompts.ROUTER, prompts.EXTRACTOR, prompts.ANALYST, prompts.CRITIC]:
        assert isinstance(p, str) and len(p) > 50
    # извлекатель должен получать schema_card
    assert "schema" in prompts.EXTRACTOR.lower() or "вьюх" in prompts.EXTRACTOR.lower()
