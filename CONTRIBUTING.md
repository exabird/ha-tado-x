# Contributing to Tado X Integration

Thank you for your interest in contributing to the Tado X integration for Home Assistant!

## How to Contribute

### Reporting Issues

Before creating a new issue, please:
1. Search [existing issues](https://github.com/exabird/ha-tado-x/issues) to avoid duplicates
2. Use the appropriate template:
   - [Bug Report](https://github.com/exabird/ha-tado-x/issues/new?template=bug_report.md) for bugs
   - [Feature Request](https://github.com/exabird/ha-tado-x/issues/new?template=feature_request.md) for new features
3. Include as much detail as possible

### Submitting Code

1. **Fork** this repository
2. **Create a branch** for your feature:
   ```bash
   git checkout -b feature/my-feature
   ```
3. **Make your changes** following the code style guidelines below
4. **Test thoroughly** with real Tado X hardware
5. **Commit** with clear, descriptive messages
6. **Push** to your fork and create a Pull Request

## Development Setup

### Requirements

- Home Assistant development environment
- Tado X hardware for testing
- Python 3.11+
- Git

### Local Development

1. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/ha-tado-x.git
   cd ha-tado-x
   ```

2. Link to your Home Assistant installation:
   ```bash
   ln -s $(pwd)/custom_components/tado_x ~/.homeassistant/custom_components/tado_x
   ```

3. Restart Home Assistant to load the integration

4. Enable debug logging in `configuration.yaml`:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.tado_x: debug
   ```

### Testing

- Test all changes with real Tado X devices
- Verify all device types work (VA04, SU04, TR04, IB02)
- Check logs for errors or warnings
- Test edge cases (network issues, auth failures, etc.)

## Code Style Guidelines

### Python Code

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use type hints for function parameters and return values
- Add docstrings for all public functions and classes
- Keep functions focused and single-purpose
- Use meaningful variable names

### Example:

```python
async def set_temperature_offset(
    self,
    device_id: str,
    offset: float,
) -> None:
    """Set the temperature offset for a device.

    Args:
        device_id: Serial number of the device
        offset: Temperature offset in °C (-9.9 to +9.9)

    Raises:
        TadoXApiError: If the API request fails
    """
    if not self._home_id:
        raise TadoXApiError("Home ID not set")

    await self._request(
        "PATCH",
        f"{TADO_HOPS_API_URL}/homes/{self._home_id}/devices/{device_id}",
        json_data={"temperatureOffset": offset},
    )
```

### Commit Messages

Use clear, descriptive commit messages:

```
Add temperature offset adjustment service

- Implement set_temperature_offset in TadoXApi
- Add tado_x.set_temperature_offset service
- Update services.yaml with new service definition
- Add tests for temperature offset functionality

Closes #3
```

## Architecture Overview

### Key Files

- `__init__.py` - Integration setup and platform loading
- `api.py` - Tado X API client
- `coordinator.py` - Data update coordinator and data models
- `config_flow.py` - Configuration flow (OAuth2)
- `climate.py` - Climate entity (room control)
- `sensor.py` - Sensor entities
- `binary_sensor.py` - Binary sensor entities
- `const.py` - Constants and configuration

### Adding a New Feature

1. **API Client** (`api.py`): Add API method if needed
2. **Coordinator** (`coordinator.py`): Update data models if needed
3. **Entity Platform**: Add/modify entities as needed
4. **Services** (`services.yaml`): Define service if adding control
5. **Strings** (`strings.json`): Add localized strings
6. **Tests**: Add or update tests

### Example: Adding a Service

1. Add API method in `api.py`:
   ```python
   async def set_temperature_offset(self, device_id: str, offset: float) -> None:
       """Set temperature offset for a device."""
       # Implementation
   ```

2. Add service definition in `services.yaml`:
   ```yaml
   set_temperature_offset:
     name: Set Temperature Offset
     description: Adjust the temperature offset for a Tado X device
     fields:
       device_id:
         description: Device serial number
         required: true
         selector:
           text:
       offset:
         description: Temperature offset in °C
         required: true
         selector:
           number:
             min: -9.9
             max: 9.9
             step: 0.1
   ```

3. Register service in `__init__.py`:
   ```python
   async def async_setup_entry(hass, entry):
       # ... existing code ...

       async def handle_set_temperature_offset(call):
           """Handle set temperature offset service."""
           device_id = call.data["device_id"]
           offset = call.data["offset"]
           await api.set_temperature_offset(device_id, offset)

       hass.services.async_register(
           DOMAIN,
           "set_temperature_offset",
           handle_set_temperature_offset,
       )
   ```

## Feature Roadmap

Current priorities based on user requests:

1. **Away preset** (Issue #2) - Geofencing support
2. **Temperature offset service** (Issue #3) - Device calibration
3. **Open window detection toggle** - Per-room control
4. **Child lock control** - Device safety settings

## Questions?

- **Technical questions:** Open a discussion on GitHub
- **Bug reports:** Use the [bug report template](https://github.com/exabird/ha-tado-x/issues/new?template=bug_report.md)
- **Feature ideas:** Use the [feature request template](https://github.com/exabird/ha-tado-x/issues/new?template=feature_request.md)

Thank you for contributing! 🏠
