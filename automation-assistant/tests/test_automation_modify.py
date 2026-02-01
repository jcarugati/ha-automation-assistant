import asyncio
from pathlib import Path
import sys

import yaml

sys.path.append(str(Path(__file__).resolve().parents[1]))

import app.automation as automation
from app.automation import AutomationGenerator, extract_yaml_from_response


class StubLLMClient:
    def __init__(self, response: str):
        self.response = response

    async def generate_automation(self, _system_prompt: str, _user_prompt: str) -> str:
        return self.response


def test_extract_yaml_code_block_list_normalized():
    response = (
        "Here is the updated automation:\n"
        "```yaml\n"
        "- alias: Vacuum Notify\n"
        "  description: Notify when vacuum starts\n"
        "  trigger: []\n"
        "  action: []\n"
        "  mode: single\n"
        "```\n"
    )
    yaml_content = extract_yaml_from_response(response)
    assert yaml_content is not None

    parsed = yaml.safe_load(yaml_content)
    assert isinstance(parsed, dict)
    assert parsed["alias"] == "Vacuum Notify"


def test_extract_yaml_fallback_plain_text():
    response = (
        "Updated automation details:\n"
        "alias: Vacuum Notify\n"
        "description: Notify when vacuum starts\n"
        "trigger: []\n"
        "action: []\n"
        "mode: single\n"
    )
    yaml_content = extract_yaml_from_response(response)
    assert yaml_content is not None

    parsed = yaml.safe_load(yaml_content)
    assert parsed.get("alias") == "Vacuum Notify"


def test_modify_merges_action_only_response(monkeypatch):
    existing_yaml = (
        "alias: Vacuum Automation\n"
        "description: Notify when vacuum starts\n"
        "id: test-id\n"
        "trigger:\n"
        "  - platform: state\n"
        "    entity_id: vacuum.my_vacuum\n"
        "    to: \"cleaning\"\n"
        "action:\n"
        "  - service: notify.notify\n"
        "    data:\n"
        "      message: \"Old message\"\n"
        "mode: single\n"
    )
    llm_response = (
        "```yaml\n"
        "- service: notify.notify\n"
        "  data:\n"
        "    message: \"Vacuum started :broom:\"\n"
        "```\n"
    )

    generator = AutomationGenerator()
    generator.llm_client = StubLLMClient(llm_response)

    async def fake_context():
        return {"states": [], "services": [], "areas": [], "devices": []}

    monkeypatch.setattr(automation.ha_client, "get_full_context", fake_context)

    result = asyncio.run(generator.modify(existing_yaml, "Notify on vacuum start"))
    assert result.success is True
    assert result.yaml_content is not None

    parsed = yaml.safe_load(result.yaml_content)
    assert parsed["id"] == "test-id"
    assert parsed["trigger"]
    assert parsed["action"][0]["service"] == "notify.notify"


def test_modify_fails_when_no_yaml(monkeypatch):
    existing_yaml = (
        "alias: Vacuum Automation\n"
        "description: Notify when vacuum starts\n"
        "id: test-id\n"
        "trigger: []\n"
        "action: []\n"
        "mode: single\n"
    )

    generator = AutomationGenerator()
    generator.llm_client = StubLLMClient("No YAML here")

    async def fake_context():
        return {"states": [], "services": [], "areas": [], "devices": []}

    monkeypatch.setattr(automation.ha_client, "get_full_context", fake_context)

    result = asyncio.run(generator.modify(existing_yaml, "Notify on vacuum start"))
    assert result.success is False
    assert result.error
