# Tado X Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A Home Assistant custom integration for **Tado X** devices (the new generation of Tado smart thermostats and radiator valves).

> **Note:** This integration is specifically designed for Tado X devices. For older Tado devices (V3+ and earlier), use the [official Tado integration](https://www.home-assistant.io/integrations/tado/).

## Features

- **Climate entities** for each room with:
  - Current and target temperature control
  - HVAC modes: Heat, Off, Auto (schedule)
  - Preset modes: Schedule, Boost
  - Current humidity display
  - Heating power percentage

- **Sensors** for:
  - Room temperature
  - Room humidity
  - Heating power percentage
  - Device battery status
  - Device temperature (measured by each valve)

- **Binary sensors** for:
  - Window open detection
  - Heating active status
  - Manual control (overlay) active
  - Device connectivity
  - Low battery warning

## Supported Devices

- **VA04** - Tado X Radiator Valve
- **SU04** - Tado X Temperature Sensor
- **TR04** - Tado X Thermostat
- **IB02** - Tado X Bridge

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/exabird/ha-tado-x`
6. Select "Integration" as the category
7. Click "Add"
8. Search for "Tado X" and install it
9. Restart Home Assistant

### Manual Installation

1. Download the `custom_components/tado_x` folder from this repository
2. Copy it to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** > **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Tado X"
4. Follow the authentication flow:
   - Click "Submit" to start authentication
   - Visit the provided URL
   - Enter the displayed code
   - Authorize the integration
   - Click "Submit" again after authorizing

## API Rate Limits

Tado has implemented API rate limits:
- **Without Auto-Assist subscription:** 100 requests/day
- **With Auto-Assist subscription:** 20,000 requests/day

This integration polls every 30 seconds by default, which uses approximately 2,880 requests/day. If you don't have an Auto-Assist subscription, you may need to increase the polling interval or the integration may stop working after ~100 updates.

## Known Limitations

- This integration uses the undocumented `hops.tado.com` API which may change without notice
- Some advanced features may not be available compared to the official Tado app

## Troubleshooting

### Authentication Issues

If you see "Authentication failed" errors:
1. Go to Settings > Devices & Services
2. Find the Tado X integration
3. Click the three dots and select "Reconfigure"
4. Follow the authentication flow again

### Rate Limiting

If entities become unavailable or show stale data:
- Check if you've exceeded the daily API limit
- Wait until the next day for the limit to reset
- Consider getting a Tado Auto-Assist subscription for higher limits

## Credits

This integration was created using the reverse-engineered Tado X API. Thanks to the community for documenting the API endpoints.

## License

MIT License - see [LICENSE](LICENSE) file for details.
