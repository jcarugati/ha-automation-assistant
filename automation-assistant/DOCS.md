# Automation Assistant

Create Home Assistant automations using natural language, powered by Claude AI.

## Overview

This add-on allows you to describe what you want your automation to do in plain English, and it will generate the corresponding YAML configuration. The add-on fetches context from your Home Assistant instance (entities, devices, areas, and services) to generate accurate and relevant automations.

## Installation

1. Add this repository to your Home Assistant add-on store:
   - Go to **Settings** > **Add-ons** > **Add-on Store**
   - Click the menu (three dots) in the top right
   - Select **Repositories**
   - Add the repository URL

2. Find "Automation Assistant" in the add-on store and click **Install**

3. Configure your Claude API key in the add-on settings

4. Start the add-on

5. Click **Open Web UI** to access the interface

## Configuration

### Claude API Key (Required)

You need an Anthropic API key to use this add-on. Get one at [console.anthropic.com](https://console.anthropic.com/).

1. Create an account or sign in
2. Go to API Keys
3. Create a new key
4. Copy the key and paste it in the add-on configuration

### Model (Optional)

The Claude model to use for generation. Default is `claude-sonnet-4-20250514`.

Available models:
- `claude-sonnet-4-20250514` - Fast and capable (recommended)
- `claude-3-opus-20240229` - Most capable, slower

### Log Level (Optional)

Set the logging verbosity. Options: `debug`, `info`, `warning`, `error`. Default is `info`.

## Usage

1. Open the add-on web interface from the sidebar

2. Click **Show Context** to verify your Home Assistant data is being loaded correctly

3. Enter a natural language description of your automation, for example:
   - "Turn on the living room lights when motion is detected after sunset"
   - "Send me a notification when the garage door has been open for more than 10 minutes"
   - "Set the thermostat to 72 degrees at 6am on weekdays"

4. Click **Generate Automation**

5. Review the generated YAML and explanation

6. Click **Validate** to check the YAML syntax

7. Click **Copy** to copy the YAML to your clipboard

8. Paste the YAML into your Home Assistant automations:
   - Go to **Settings** > **Automations & Scenes** > **Automations**
   - Click the menu (three dots) and select **Traces**
   - Or edit `automations.yaml` directly

## Tips for Better Results

- Be specific about which entities you want to use
- Mention time-based conditions (e.g., "after sunset", "on weekdays", "at 8am")
- Describe the desired state changes clearly
- Use area names if you've organized your entities by area

## Troubleshooting

### "API key not configured"

Make sure you've entered your Claude API key in the add-on configuration and restarted the add-on.

### "Failed to fetch context"

The add-on may not have access to the Home Assistant API. Ensure:
- The add-on is properly installed
- Home Assistant API access is enabled in the add-on configuration
- The add-on has been restarted after installation

### Generated YAML has validation errors

The AI may occasionally generate YAML with minor issues. Review the validation errors and make manual corrections as needed. You can use Home Assistant's automation editor to help fix issues.

### The add-on doesn't appear in the sidebar

After installation and starting the add-on:
1. Refresh your browser
2. Check that the add-on is running
3. Try stopping and starting the add-on again

## Privacy & Security

- Your API key is stored securely in Home Assistant's add-on configuration
- Entity and device information is sent to Claude's API to provide context
- No data is stored outside your Home Assistant instance
- The add-on communicates with Anthropic's API using HTTPS

## Support

For issues and feature requests, please visit the GitHub repository.
