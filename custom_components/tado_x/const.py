"""Constants for the Tado X integration."""
from typing import Final

DOMAIN: Final = "tado_x"

# API URLs
TADO_AUTH_URL: Final = "https://login.tado.com/oauth2/device_authorize"
TADO_TOKEN_URL: Final = "https://login.tado.com/oauth2/token"
TADO_HOPS_API_URL: Final = "https://hops.tado.com"
TADO_MY_API_URL: Final = "https://my.tado.com/api/v2"

# OAuth2 Client ID (public client for device linking)
TADO_CLIENT_ID: Final = "1bb50063-6b0c-4d11-bd99-387f4a91cc46"

# Config keys
CONF_HOME_ID: Final = "home_id"
CONF_HOME_NAME: Final = "home_name"
CONF_ACCESS_TOKEN: Final = "access_token"
CONF_REFRESH_TOKEN: Final = "refresh_token"
CONF_TOKEN_EXPIRY: Final = "token_expiry"

# Update intervals
DEFAULT_SCAN_INTERVAL: Final = 30  # seconds

# API Rate Limits
API_QUOTA_FREE_TIER: Final = 100  # requests per day without Auto-Assist
API_QUOTA_PREMIUM: Final = 20000  # requests per day with Auto-Assist

# Device types
DEVICE_TYPE_VALVE: Final = "VA04"  # Tado X Radiator Valve
DEVICE_TYPE_THERMOSTAT: Final = "TR04"  # Tado X Thermostat
DEVICE_TYPE_BRIDGE: Final = "IB02"  # Tado X Bridge
DEVICE_TYPE_SENSOR: Final = "SU04"  # Tado X Temperature Sensor

# Termination types
TERMINATION_MANUAL: Final = "MANUAL"
TERMINATION_TIMER: Final = "TIMER"
TERMINATION_NEXT_TIME_BLOCK: Final = "NEXT_TIME_BLOCK"

# Default timer duration (30 minutes)
DEFAULT_TIMER_DURATION: Final = 1800

# Temperature limits
MIN_TEMP: Final = 5.0
MAX_TEMP: Final = 25.0
TEMP_STEP: Final = 0.5

# Battery states
BATTERY_STATE_NORMAL: Final = "NORMAL"
BATTERY_STATE_LOW: Final = "LOW"

# Connection states
CONNECTION_STATE_CONNECTED: Final = "CONNECTED"
CONNECTION_STATE_DISCONNECTED: Final = "DISCONNECTED"

# Platforms
PLATFORMS: Final = ["climate", "sensor", "binary_sensor"]
