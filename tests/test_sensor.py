import asyncio
import sys
from datetime import datetime
from types import ModuleType, SimpleNamespace


def _install_home_assistant_stubs():
    voluptuous = ModuleType("voluptuous")
    voluptuous.Schema = lambda value, **kwargs: value
    voluptuous.Required = lambda key, **kwargs: key
    voluptuous.Optional = lambda key, **kwargs: key
    voluptuous.All = lambda *validators: validators
    voluptuous.Coerce = lambda value: value
    voluptuous.Range = lambda **kwargs: kwargs
    voluptuous.In = lambda values: values
    voluptuous.ALLOW_EXTRA = object()
    sys.modules.setdefault("voluptuous", voluptuous)

    homeassistant = ModuleType("homeassistant")
    components = ModuleType("homeassistant.components")
    sensor_module = ModuleType("homeassistant.components.sensor")
    http_module = ModuleType("homeassistant.components.http")
    notification_module = ModuleType(
        "homeassistant.components.persistent_notification"
    )
    helpers = ModuleType("homeassistant.helpers")
    event_module = ModuleType("homeassistant.helpers.event")
    validation_module = ModuleType("homeassistant.helpers.config_validation")
    restore_state_module = ModuleType("homeassistant.helpers.restore_state")
    core_module = ModuleType("homeassistant.core")
    const_module = ModuleType("homeassistant.const")
    aiohttp_module = ModuleType("aiohttp")
    aiohttp_web_module = ModuleType("aiohttp.web")

    class SensorEntity:
        async def async_added_to_hass(self):
            pass

        def async_on_remove(self, callback):
            self._remove_callback = callback

        def async_write_ha_state(self):
            pass

    class RestoreEntity:
        async def async_get_last_state(self):
            return self._restored_state

    class HomeAssistantView:
        pass

    async def persist_notify(*args, **kwargs):
        pass

    sensor_module.SensorEntity = SensorEntity
    http_module.HomeAssistantView = HomeAssistantView
    notification_module.async_create = persist_notify
    event_module.async_track_state_change_event = lambda *args, **kwargs: lambda: None
    validation_module.entity_id = str
    validation_module.ensure_list = list
    validation_module.string = str
    restore_state_module.RestoreEntity = RestoreEntity
    core_module.callback = lambda function: function
    const_module.STATE_UNKNOWN = "unknown"
    const_module.STATE_UNAVAILABLE = "unavailable"
    aiohttp_web_module.json_response = lambda value: value
    aiohttp_module.web = aiohttp_web_module

    modules = {
        "homeassistant": homeassistant,
        "homeassistant.components": components,
        "homeassistant.components.sensor": sensor_module,
        "homeassistant.components.http": http_module,
        "homeassistant.components.persistent_notification": notification_module,
        "homeassistant.helpers": helpers,
        "homeassistant.helpers.event": event_module,
        "homeassistant.helpers.config_validation": validation_module,
        "homeassistant.helpers.restore_state": restore_state_module,
        "homeassistant.core": core_module,
        "homeassistant.const": const_module,
        "aiohttp": aiohttp_module,
        "aiohttp.web": aiohttp_web_module,
    }
    for name, module in modules.items():
        sys.modules.setdefault(name, module)


_install_home_assistant_stubs()

from sensor import ATTR_LAST_REPLACED, BatteryMonitorSensor


def test_threshold_sets_first_last_replaced_timestamp_from_restored_level():
    hass = SimpleNamespace(
        states=SimpleNamespace(get=lambda entity_id: SimpleNamespace(state="75"))
    )
    monitor = BatteryMonitorSensor(
        hass,
        "sensor.test_battery",
        "Test battery",
        "percentage",
        None,
        0.0,
        25.0,
        25.0,
    )
    monitor._restored_state = SimpleNamespace(state="50", attributes={})

    asyncio.run(monitor.async_added_to_hass())

    last_replaced = monitor.extra_state_attributes[ATTR_LAST_REPLACED]
    assert last_replaced is not None
    assert datetime.fromisoformat(last_replaced).tzinfo is not None
