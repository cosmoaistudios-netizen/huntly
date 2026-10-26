from __future__ import annotations
import tempfile
from pathlib import Path
import yaml
from huntly.config.settings import Settings
from huntly.core.analyzer import JobAnalyzer


def test_analyzer_model_parameter_preserved():
    analyzer = JobAnalyzer(
        api_key="test-key",
        model="llama3.2",
        base_url="http://localhost:11434/v1",
    )
    assert analyzer.model == "llama3.2"
    assert analyzer.base_url == "http://localhost:11434/v1"


def test_settings_provider_resolution():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_file = Path(tmpdir) / "config.yaml"
        # Test ollama config
        with open(cfg_file, "w") as f:
            yaml.safe_dump({
                "ai": {
                    "provider": "ollama",
                    "model": "mistral",
                }
            }, f)

        settings = Settings(config_path=cfg_file)
        assert settings.ai_provider == "ollama"
        assert settings.ai_model == "mistral"
        assert settings.ai_base_url == "http://localhost:11434/v1"
        assert settings.ai_api_key == "ollama"
