from app.config import Settings

def test_settings_defaults(monkeypatch):
    monkeypatch.delenv("YC_API_KEY", raising=False)
    s = Settings()
    assert s.llm_model_uri.startswith("gpt://") or s.llm_model_uri.startswith("ds://") or "deepseek" in s.llm_model_uri
    assert s.deadline_simple_sec == 300
    assert s.deadline_analytical_sec == 600
    assert s.sql_row_limit == 5000
    assert s.critic_max_retries == 1
