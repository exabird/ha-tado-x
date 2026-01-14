# Claude Code Instructions

## Project: Tado X Home Assistant Integration

Custom Home Assistant integration for Tado X (next generation) devices.

## Communication Rules

- **All GitHub communications must be in English** (issues, comments, PR descriptions, commit messages)
- Code comments can be in English
- User-facing strings in `strings.json` are in English

## Tech Stack

- Python 3.11+
- Home Assistant Core
- aiohttp for async HTTP requests
- OAuth2 Device Flow for authentication

## Key Files

- `custom_components/tado_x/api.py` - Tado API client
- `custom_components/tado_x/coordinator.py` - Data update coordinator
- `custom_components/tado_x/config_flow.py` - Configuration flow & options
- `custom_components/tado_x/const.py` - Constants and configuration keys

## API Quotas

- Free tier: 100 requests/day
- Auto-Assist subscription: 20,000 requests/day
