"""Constants for the Tado X integration."""
from typing import Final

DOMAIN: Final = "tado_x"

# API URLs
TADO_AUTH_URL: Final = "https://login.tado.com/oauth2/device_authorize"
TADO_TOKEN_URL: Final = "https://login.tado.com/oauth2/token"
TADO_HOPS_API_URL: Final = "https://hops.tado.com"
TADO_MY_API_URL: Final = "https://my.tado.com/api/v2"
TADO_EIQ_API_URL: Final = "https://energy-insights.tado.com/api"

# OAuth2 Client ID (public client for device linking)
TADO_CLIENT_ID: Final = "1bb50063-6b0c-4d11-bd99-387f4a91cc46"

# Config keys
CONF_HOME_ID: Final = "home_id"
CONF_HOME_NAME: Final = "home_name"
CONF_ACCESS_TOKEN: Final = "access_token"
CONF_REFRESH_TOKEN: Final = "refresh_token"
CONF_TOKEN_EXPIRY: Final = "token_expiry"
CONF_API_CALLS_TODAY: Final = "api_calls_today"
CONF_API_RESET_TIME: Final = "api_reset_time"
CONF_HAS_AUTO_ASSIST: Final = "has_auto_assist"

# Update intervals (in seconds)
# Free tier: 100 req/day ÷ 3 req/update = 33 updates max → 45 min interval = 32 updates × 3 = 96 req/day
SCAN_INTERVAL_FREE_TIER: Final = 2700  # 45 minutes - stays under 100 req/day quota
SCAN_INTERVAL_AUTO_ASSIST: Final = 30  # 30 seconds - for 20k req/day quota
DEFAULT_SCAN_INTERVAL: Final = 30  # seconds (legacy, use tier-specific)

# API Rate Limits
API_QUOTA_FREE_TIER: Final = 100  # requests per day without Auto-Assist
API_QUOTA_PREMIUM: Final = 20000  # requests per day with Auto-Assist
API_CALLS_PER_UPDATE: Final = 3  # get_rooms + get_rooms_and_devices + get_home_state

# Config keys for options
CONF_SCAN_INTERVAL: Final = "scan_interval"

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
PLATFORMS: Final = ["climate", "sensor", "binary_sensor", "switch"]
