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

## License

MIT License - see [LICENSE](LICENSE) file for details.
