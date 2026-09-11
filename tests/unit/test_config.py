from app.config import get_settings


def test_settings_load_with_defaults():
    get_settings.cache_clear()
    settings = get_settings()

    assert settings.application.name == "agent-operator"
    assert settings.database.url.startswith("postgresql+asyncpg://")
    assert settings.limits.max_iterations > 0
    assert settings.model_routing.default_provider == "litellm"


def test_settings_is_cached():
    get_settings.cache_clear()
    assert get_settings() is get_settings()
