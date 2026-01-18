# Automation Assistant

A Home Assistant add-on that generates automations from natural language using Claude AI.

## Features

- **Natural Language Input**: Describe automations in plain English
- **Context-Aware**: Uses your Home Assistant entities, devices, and areas to generate accurate YAML
- **Save & Manage**: Save generated automations for later access and editing
- **Validation**: Validate generated YAML before using it
- **Dark Theme UI**: Clean interface that matches Home Assistant's style

## Installation

1. Add this repository to your Home Assistant add-on store
2. Install the "Automation Assistant" add-on
3. Configure your Claude API key in the add-on settings
4. Start the add-on and open the web UI

## Configuration

| Option | Description | Default |
|--------|-------------|---------|
| `claude_api_key` | Your Anthropic API key (required) | - |
| `model` | Claude model to use | `claude-sonnet-4-20250514` |
| `log_level` | Logging level | `info` |

## Usage

1. Open Automation Assistant from the Home Assistant sidebar
2. Describe the automation you want (e.g., "Turn on the living room lights when motion is detected after sunset")
3. Click **Generate Automation**
4. Review the explanation and generated YAML
5. Click **Validate** to check syntax, **Copy** to clipboard, or **Save** to store for later

## Saved Automations

- Click the menu icon to open the sidebar with saved automations
- Click a saved automation to load it
- Modify and save to update, or generate fresh automations

## Requirements

- Home Assistant OS or Supervised installation
- Claude API key from [Anthropic](https://console.anthropic.com/)

## License

MIT
