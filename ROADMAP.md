# Roadmap

This document tracks planned features and enhancements for the Tado X Home Assistant integration.

## Planned Features

### P2 - High Priority

*None currently - all P2 items completed in v1.7.0*

### P3 - Medium Priority

- **Historic Data** - Historical temperature, humidity, and heating data
- **Schedule Management** - Read and modify heating schedules from Home Assistant

### P4 - Low Priority

- **Flow Temperature Optimization** - Boiler flow temperature control for energy savings
- **Away Radius Configuration** - Configure geofencing radius for presence detection

---

## Completed

See [CHANGELOG](https://github.com/exabird/ha-tado-x/releases) for completed features by version.

**Recent highlights:**
- v1.7.0 - Home presence sensors, select entity, set_climate_timer service, graceful 429 rate limit handling
- v1.6.7 - Weather sensor fix (all states supported)
- v1.6.6 - Fix HVAC mode OFF vs AUTO detection
- v1.6.5 - Temperature offset sensor
- v1.6.4 - Fix OptionsFlow for HA 2024.x
- v1.6.0 - Weather sensors, air comfort, mobile tracking, heating time
- v1.5.0 - Quick actions, Energy IQ tariff management
- v1.4.0 - Child lock, open window controls
- v1.3.0 - API usage monitoring, smart polling

---

## Won't Implement

*None currently*

---

## How to Request Features

Open an issue using the [Feature Request template](https://github.com/exabird/ha-tado-x/issues/new?template=feature_request.md).
