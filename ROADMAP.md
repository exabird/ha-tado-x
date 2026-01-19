# Roadmap

This document tracks planned features and enhancements for the Tado X Home Assistant integration.

## Planned Features

### P2 - High Priority

- **Set Climate Timer Service** - Service call to set temperature with duration (like original Tado integration)
  - Requested by: @jelmerkk
  - Issue: [#19](https://github.com/exabird/ha-tado-x/issues/19)
  - Date: 2026-01-19
  - Notes: Implement `tado_x.set_temperature_timer` service with temperature + duration parameters

- **Home Presence Sensor & Select Entity** - Central sensor showing Home/Away state with manual override capability
  - Requested by: @Orishas
  - Issue: [#20](https://github.com/exabird/ha-tado-x/issues/20)
  - Date: 2026-01-19
  - Notes: Create `sensor.tado_presence_mode` and `select.tado_presence_override` to track and control geofencing state

### P3 - Medium Priority

- **Historic Data** - Historical temperature, humidity, and heating data
- **Schedule Management** - Read and modify heating schedules from Home Assistant
- **Graceful Rate Limit Handling** - Show "Rate Limited" state when 429 received and auto-suspend polling until reset

### P4 - Low Priority

- **Flow Temperature Optimization** - Boiler flow temperature control for energy savings
- **Away Radius Configuration** - Configure geofencing radius for presence detection

---

## Completed

See [CHANGELOG](https://github.com/exabird/ha-tado-x/releases) for completed features by version.

**Recent highlights:**
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
