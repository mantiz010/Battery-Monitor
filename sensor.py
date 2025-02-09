
import logging
import voluptuous as vol
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.components.http import HomeAssistantView
from homeassistant.components.persistent_notification import async_create as persist_notify
from homeassistant.const import STATE_UNKNOWN, STATE_UNAVAILABLE
import aiohttp.web

_LOGGER = logging.getLogger(__name__)

DOMAIN = "battery_monitor"

# Configuration Keys
CONF_SENSORS = "sensors"
CONF_LOW_THRESHOLD = "low_threshold"
CONF_MAX_VOLTAGE = "max_voltage"
CONF_MIN_VOLTAGE = "min_voltage"
CONF_NAME = "name"
CONF_SENSOR_TYPE = "sensor_type"  # "voltage" (default) or "percentage"

# Schema for each sensor configuration.
SENSOR_SCHEMA = vol.Schema({
    vol.Required("entity_id"): cv.entity_id,
    vol.Optional(CONF_SENSOR_TYPE, default="voltage"): vol.In(["voltage", "percentage"]),
    vol.Optional(CONF_MAX_VOLTAGE): vol.Coerce(float),
    vol.Optional(CONF_MIN_VOLTAGE, default=0.0): vol.Coerce(float),
})

# Overall platform schema.
PLATFORM_SCHEMA = vol.Schema({
    vol.Required(CONF_SENSORS): vol.All(cv.ensure_list, [SENSOR_SCHEMA]),
    vol.Optional(CONF_NAME, default="Battery Monitor"): cv.string,
    vol.Optional(CONF_LOW_THRESHOLD, default=25.0): vol.Coerce(float),
}, extra=vol.ALLOW_EXTRA)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Battery Monitor sensor platform."""
    sensors_config = config[CONF_SENSORS]
    name_prefix = config.get(CONF_NAME)
    low_threshold = config.get(CONF_LOW_THRESHOLD)

    _LOGGER.info("Setting up Battery Monitor for sensors with low_threshold=%.1f", low_threshold)

    sensors = []
    for sensor_conf in sensors_config:
        entity_id = sensor_conf["entity_id"]
        sensor_type = sensor_conf.get(CONF_SENSOR_TYPE, "voltage")
        max_voltage = sensor_conf.get(CONF_MAX_VOLTAGE)  # May be None for percentage sensors.
        min_voltage = sensor_conf.get(CONF_MIN_VOLTAGE, 0.0)
        sensor_name = f"{name_prefix} {entity_id.split('.')[-1]}"
        sensor = BatteryMonitorSensor(
            hass,
            entity_id,
            sensor_name,
            sensor_type,
            max_voltage,
            min_voltage,
            low_threshold
        )
        sensors.append(sensor)

    add_entities(sensors, True)

    # Register the HTTP endpoint for battery data.
    register_http_routes(hass, sensors)


class BatteryMonitorSensor(SensorEntity):
    """A sensor that computes battery percentage from a voltage sensor or uses the state directly for percentage sensors.
    
    The entity always returns a numeric value (and its string representation) so that template filters work without error.
    It defines a unique_id to avoid duplicates and sends a persistent notification when battery is low.
    """

    def __init__(self, hass, target_entity_id, name, sensor_type, max_voltage, min_voltage, low_threshold):
        self._hass = hass
        self._target_entity_id = target_entity_id
        self._name = name
        self._sensor_type = sensor_type  # "voltage" or "percentage"
        self._max_voltage = max_voltage
        self._min_voltage = min_voltage
        self._low_threshold = low_threshold
        self._state = 0.0  # Always numeric.
        self._icon = "mdi:battery"
        self._notified = False  # To prevent repeated notifications.
        self._unique_id = f"{DOMAIN}_{target_entity_id.replace('.', '_')}"

    async def async_added_to_hass(self):
        """Register state change listener using async_track_state_change_event."""
        @callback
        def _state_listener(event):
            new_state = event.data.get("new_state")
            self._update_state(new_state)
        async_track_state_change_event(self._hass, [self._target_entity_id], _state_listener)
        init_state = self._hass.states.get(self._target_entity_id)
        self._update_state(init_state)

    def _update_state(self, new_state):
        """Update our sensor’s state and icon based on the new state."""
        if not new_state or new_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            _LOGGER.debug("State for %s is unavailable; defaulting to 0.0", self._target_entity_id)
            self._state = 0.0
            self._icon = "mdi:battery-off"
        else:
            try:
                if self._sensor_type == "percentage":
                    self._state = float(new_state.state)
                else:
                    voltage = float(new_state.state)
                    if self._max_voltage is None:
                        _LOGGER.error("Sensor %s is set to voltage type but no max_voltage provided", self._target_entity_id)
                        self._state = 0.0
                    else:
                        percentage = ((voltage - self._min_voltage) / (self._max_voltage - self._min_voltage)) * 100
                        percentage = max(0, min(100, percentage))
                        self._state = round(percentage, 1)
                self._icon = self._get_icon(self._state)
                if self._state < self._low_threshold and not self._notified:
                    self._notify_low_battery(self._state)
                    self._notified = True
                elif self._state >= self._low_threshold:
                    self._notified = False
            except ValueError:
                _LOGGER.warning("Non-numeric value for %s: %s", self._target_entity_id, new_state.state)
                self._state = 0.0
                self._icon = "mdi:battery-unknown"
        self.async_write_ha_state()

    def _get_icon(self, percentage):
        """Return an appropriate icon based on battery percentage."""
        if percentage > 60:
            return "mdi:battery"
        elif percentage > 30:
            return "mdi:battery-medium"
        else:
            return "mdi:battery-low"

    def _notify_low_battery(self, percentage):
        """Send a persistent notification for low battery."""
        title = f"Low Battery Alert: {self._name}"
        message = f"Battery level for {self._target_entity_id} is low: {percentage:.1f}%.\nThreshold: {self._low_threshold}%."
        _LOGGER.warning(message)
        self._hass.async_create_task(
            persist_notify(self._hass, message, title=title, notification_id=f"battery_low_{self._target_entity_id}")
        )

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def native_value(self):
        return self._state

    @property
    def state(self):
        return str(self.native_value)

    @property
    def icon(self):
        return self._icon

    @property
    def available(self):
        return True

    @property
    def unit_of_measurement(self):
        return "%"


class BatteryMonitorDataView(HomeAssistantView):
    """HTTP view to return battery data as JSON."""
    url = "/battery_monitor/data"
    name = "battery_monitor_data"
    requires_auth = False

    def __init__(self, sensors):
        self.sensors = sensors

    async def get(self, request):
        hass = request.app["hass"]
        battery_data = []
        for sensor in self.sensors:
            sensor_state = hass.states.get(sensor._target_entity_id)
            voltage_display = sensor_state.state if sensor_state and sensor._sensor_type == "voltage" else "N/A"
            battery_data.append({
                "name": sensor.name,
                "voltage": voltage_display,
                "percentage": sensor.native_value,
            })
        _LOGGER.debug("Battery data returned: %s", battery_data)
        return aiohttp.web.json_response(battery_data)


def register_http_routes(hass, sensors):
    hass.http.register_view(BatteryMonitorDataView(sensors))
