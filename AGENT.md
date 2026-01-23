# AGENT.md

## Git Commit Guidelines

- Do NOT add `Co-Authored-By` lines to commit messages
- Keep commit messages concise and descriptive
- Follow the existing commit style in this repository

## Version Bumping

- **ALWAYS** bump the version in `automation-assistant/config.yaml` when pushing changes
- Home Assistant add-ons only detect updates when the version number changes
- Without a version bump, the add-on will not be updated even if code changes are pushed
