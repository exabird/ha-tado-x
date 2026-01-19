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
| **Sensors** | Temperature, Humidity, Heating power, Battery status, **API usage monitoring**, **Weather** (outdoor temp, solar intensity), **Air comfort** (freshness, comfort level), **Heating time today** |
| **Binary Sensors** | Window open, Heating active, Manual control, Connectivity, Low battery |
| **Switches** | **Child lock** (per device), **Open window** control (per room) |
| **Buttons** | **Boost All**, **Turn Off All**, **Resume Schedules** (quick actions) |
| **Device Tracker** | **Mobile devices** for geofencing (home/away status) |
| **Services** | Temperature offset, Meter reading, **Energy tariff** (Energy IQ) |

### Climate Presets

- **Schedule**: Follow the smart schedule
- **Boost**: Quick temperature boost
- **Home**: Manually set presence to Home (override geofencing)
- **Away**: Manually set presence to Away (override geofencing)
- **Auto (Geofencing)**: Enable automatic presence detection

### Quick Actions (Buttons)

Home-level controls for managing all zones at once:
- **Boost All**: Activate boost mode on all heating zones simultaneously
- **Turn Off All**: Disable heating in all zones (useful when leaving)
- **Resume Schedules**: Cancel all manual overrides and return to smart schedules

### Services

- **set_temperature_offset**: Calibrate device temperature readings (-9.9°C to +9.9°C)
- **add_meter_reading**: Upload meter readings to Tado Energy IQ
- **set_eiq_tariff**: Set energy tariffs for cost calculations in Energy IQ
  - Supports both m³ (gas) and kWh (electricity) units
  - Define tariff periods with start/end dates
  - Enables accurate cost tracking in Tado's Energy IQ dashboard

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
- **Enable weather sensors**: Outdoor temperature, solar intensity, weather state (+1 API call)
- **Enable mobile device tracking**: Device tracker for geofencing (+1 API call)
- **Enable air comfort sensors**: Air freshness and comfort level per room (+1 API call)
- **Enable heating time sensors**: Daily heating runtime per room (+1 API call)

**Note:** Optional features are disabled by default for free tier users to optimize API usage. Auto-Assist users have all features enabled by default.

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
- [x] Quick actions (Boost All, Turn Off All, Resume Schedules) ✅ v1.5.0
- [x] Energy IQ tariff management ✅ v1.5.0
- [x] Weather sensors (outdoor temp, solar intensity, weather state) ✅ v1.6.0
- [x] Air comfort sensors (freshness, comfort level per room) ✅ v1.6.0
- [x] Mobile device tracking (geofencing home/away) ✅ v1.6.0
- [x] Heating time sensors (daily runtime per room) ✅ v1.6.0
- [x] Configurable feature toggles to optimize API usage ✅ v1.6.0

**Planned features:**

| Feature | Description | Priority |
|---------|-------------|----------|
| **Historic Data** | Historical temperature, humidity, and heating data | Medium |
| **Schedule Management** | Read and modify heating schedules from Home Assistant | Medium |
| **Flow Temperature Optimization** | Boiler flow temperature control for energy savings | Low |
| **Away Radius Configuration** | Configure geofencing radius for presence detection | Low |

See [all feature requests](https://github.com/exabird/ha-tado-x/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement) for the full list and to vote on priorities.

## Why This Integration Exists

Tado X devices use a different API than previous Tado generations. While Tado recommends using Matter integration, many users experience significant issues with Matter setup:

- **Greyed-out pairing buttons** preventing Matter device linking
- **Failed pairing attempts** with cryptic error messages
- **Tado's official solution** requires a [full device reset](https://help.tado.com/en/articles/10264695-how-can-i-fix-matter-device-linking-errors) - impractical for remote installations (vacation homes, rental properties, elderly parents' homes)

This integration uses Tado's official cloud API to provide reliable Home Assistant integration for Tado X users who:
- Cannot get Matter integration working
- Have remote installations where physical device reset isn't feasible
- Prefer cloud-based API control with smart quota management
- Need features not available through Matter (presets, temperature offset, Energy IQ)
- Want full Home Assistant integration capabilities

### A Note to Tado

We appreciate Tado's commitment to smart home standards like Matter. However, the current Matter implementation challenges highlight the importance of **local API access**. Many smart home enthusiasts would welcome a local API on the Tado X Bridge, similar to what other manufacturers provide. This would:
- Eliminate cloud dependency for basic operations
- Improve response times and reliability
- Provide a fallback when Matter pairing fails
- Respect user privacy and data sovereignty

We hope Tado considers this for future firmware updates. The smart home community would be grateful!

## Support the Project

[![Sponsor](https://img.shields.io/badge/Sponsor-%E2%9D%A4-pink?logo=github)](https://github.com/sponsors/exabird)

If you find this integration useful, consider supporting its development! Your sponsorship helps fund:
- New features and improvements
- Bug fixes and compatibility updates
- Documentation and community support

**[Become a Sponsor](https://github.com/sponsors/exabird)**

## Support

- **Community Forum:** Discuss on [Home Assistant Community](https://community.home-assistant.io/)
- **Issues:** Report bugs or request features on [GitHub Issues](https://github.com/exabird/ha-tado-x/issues)
- **Hardware Support:** For Tado device issues, contact [Tado Support](https://support.tado.com/)

## License

MIT License - see [LICENSE](LICENSE) file for details.
