# Tado X Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/exabird/ha-tado-x)](https://github.com/exabird/ha-tado-x/releases)

A Home Assistant custom integration for **Tado X** devices (the new generation of Tado smart thermostats and radiator valves).

> **Note:** This integration is specifically designed for Tado X devices. For older Tado devices (V3+ and earlier), use the [official Tado integration](https://www.home-assistant.io/integrations/tado/).

---

## Quick Installation (HACS)

### Step 1: Add the repository
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=exabird&repository=ha-tado-x&category=integration)

**Or manually:**
1. Open HACS in Home Assistant
2. Click **⋮** (top right) → **Custom repositories**
3. Add `https://github.com/exabird/ha-tado-x` as **Integration**

### Step 2: Install & Restart
1. Search "Tado X" in HACS → **Download**
2. **Restart Home Assistant**

### Step 3: Configure
1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search "Tado X" and follow the authentication flow

---

## Features

| Entity Type | Features |
|-------------|----------|
| **Climate** | Temperature control, HVAC modes (Heat/Off/Auto), Preset modes (Schedule/Boost) |
| **Sensors** | Temperature, Humidity, Heating power, Battery status |
| **Binary Sensors** | Window open, Heating active, Manual control, Connectivity, Low battery |

## Supported Devices

| Model | Device |
|-------|--------|
| VA04 | Radiator Valve X |
| SU04 | Temperature Sensor X |
| TR04 | Thermostat X |
| IB02 | Bridge X |

## API Rate Limits

| Subscription | Daily Limit |
|--------------|-------------|
| Without Auto-Assist | 100 requests/day |
| With Auto-Assist | 20,000 requests/day |

The integration polls every 30 seconds (~2,880 requests/day). Without Auto-Assist, consider increasing the polling interval.

## Troubleshooting

**Authentication issues:** Go to Settings → Devices & Services → Tado X → **⋮** → Reconfigure

**Rate limiting:** If entities become unavailable, you may have exceeded the daily limit. Wait until the next day or get Auto-Assist subscription.

## Manual Installation

1. Download `custom_components/tado_x` from this repository
2. Copy to your `config/custom_components/` directory
3. Restart Home Assistant

---

## Contributing

This is a community-maintained integration for Tado X devices. Contributions are welcome!

### Reporting Issues

Found a bug or have a feature request? Please use our issue templates:
- [Report a Bug](https://github.com/exabird/ha-tado-x/issues/new?template=bug_report.md)
- [Request a Feature](https://github.com/exabird/ha-tado-x/issues/new?template=feature_request.md)

### Development

Want to contribute code? Great! Here's how to get started:

1. Fork this repository
2. Create a branch for your feature: `git checkout -b feature/my-feature`
3. Make your changes
4. Test thoroughly with your Tado X setup
5. Submit a pull request

### Roadmap

Planned features based on community feedback:
- [ ] Away preset (geofencing) - [Issue #2](https://github.com/exabird/ha-tado-x/issues/2)
- [ ] Temperature offset adjustment service
- [ ] Open window detection toggle
- [ ] Child lock control

See [all feature requests](https://github.com/exabird/ha-tado-x/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement) for the full list.

## Why This Integration Exists

Tado X devices use a different API than previous Tado generations. While Tado recommends using Matter integration, many users experience issues with Matter setup (greyed-out pairing buttons, requiring full device resets).

This integration uses Tado's official API to provide reliable Home Assistant integration for Tado X users who:
- Cannot get Matter integration working
- Prefer cloud-based API control
- Need features not available through Matter
- Want full Home Assistant integration capabilities

## Support

- **Community Forum:** Discuss on [Home Assistant Community](https://community.home-assistant.io/)
- **Issues:** Report bugs or request features on [GitHub Issues](https://github.com/exabird/ha-tado-x/issues)
- **Hardware Support:** For Tado device issues, contact [Tado Support](https://support.tado.com/)

## License

MIT License - see [LICENSE](LICENSE) file for details.
