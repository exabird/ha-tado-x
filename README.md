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
| **Climate** | Temperature control, HVAC modes (Heat/Off/Auto), Preset modes (Schedule/Boost/Home/Away/Auto) |
| **Sensors** | Temperature, Humidity, Heating power, Battery status, **API usage monitoring** (calls today, quota remaining, usage %, reset time) |
| **Binary Sensors** | Window open, Heating active, Manual control, Connectivity, Low battery |
| **Switches** | **Child lock** (per device), **Open window** control (per room) |
| **Services** | Temperature offset calibration, **Meter reading upload** (Energy IQ) |

### Climate Presets

- **Schedule**: Follow the smart schedule
- **Boost**: Quick temperature boost
- **Home**: Manually set presence to Home (override geofencing)
- **Away**: Manually set presence to Away (override geofencing)
- **Auto (Geofencing)**: Enable automatic presence detection

### Services

- **set_temperature_offset**: Calibrate device temperature readings (-9.9°C to +9.9°C)
- **add_meter_reading**: Upload meter readings to Tado Energy IQ (requires Energy IQ subscription)

### API Usage Monitoring

Five sensors help you track API quota usage (values read directly from Tado API headers when available):
- **API calls today**: Number of API requests since midnight
- **API quota remaining**: Remaining requests
- **API quota limit**: Your daily quota (auto-detected from API: 100 free, 20,000 with Auto-Assist)
- **API usage**: Percentage of daily quota used
- **API reset time**: When the quota resets

These sensors use **real values from Tado API response headers** when available, providing accurate quota tracking.

## Supported Devices

| Model | Device |
|-------|--------|
| VA04 | Radiator Valve X |
| SU04 | Temperature Sensor X |
| TR04 | Thermostat X |
| IB02 | Bridge X |

## API Rate Limits & Smart Polling

Tado enforces daily API limits. This integration **automatically adapts** its polling interval based on your subscription:

| Subscription | Daily Limit | Auto Polling Interval | Actual Usage |
|--------------|-------------|----------------------|--------------|
| Without Auto-Assist | 100 requests/day | Every 45 minutes | ~96 req/day ✅ |
| With Auto-Assist | 20,000 requests/day | Every 30 seconds | ~2,880 req/day ✅ |

### Configuration Options

Go to **Settings** → **Devices & Services** → **Tado X** → **⚙️ Configure** to:

- **Enable Auto-Assist**: Toggle if you have an Auto-Assist subscription
- **Custom polling interval**: Override the automatic interval (30s - 3600s)

### API Counter Persistence

The API call counter is **persisted across restarts** - your quota tracking continues accurately even after Home Assistant reboots.

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

**Recently Implemented:**
- [x] Away preset (geofencing) - [Issue #2](https://github.com/exabird/ha-tado-x/issues/2) ✅ v1.1.0
- [x] Temperature offset adjustment service - [Issue #3](https://github.com/exabird/ha-tado-x/issues/3) ✅ v1.1.0
- [x] API usage monitoring sensors - [Issue #4](https://github.com/exabird/ha-tado-x/issues/4) ✅ v1.3.0
- [x] Meter reading service (Energy IQ) - [Issue #5](https://github.com/exabird/ha-tado-x/issues/5) ✅ v1.2.0
- [x] Smart polling based on subscription tier - [Issue #4](https://github.com/exabird/ha-tado-x/issues/4) ✅ v1.3.2
- [x] API counter persistence across restarts ✅ v1.3.2
- [x] Configurable polling interval ✅ v1.3.2
- [x] Real API quota values from response headers ✅ v1.3.3
- [x] Fix meter reading API endpoint - [Issue #7](https://github.com/exabird/ha-tado-x/issues/7) ✅ v1.3.4
- [x] Open window detection toggle ✅ v1.4.0
- [x] Child lock control ✅ v1.4.0

**Planned features based on community feedback:**

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
