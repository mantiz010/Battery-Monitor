# Battery Icons Custom Integration

The **Battery Icons** integration creates battery sensor entities in Home Assistant that display battery percentages. It supports two modes:

- **Voltage-Based Mode:**  
  Computes the battery percentage from a voltage reading using configured minimum and maximum voltage values.

- **Percentage-Based Mode:**  
  Uses the sensor’s state directly as the battery percentage (0–100).

_All sensors created by this integration display the unit of measurement as "%" in Home Assistant._

Additionally, the integration sends a persistent notification when:
- A sensor's battery level falls below the configured low threshold.
- A battery stays at `0%` for more than a configurable period, prompting a **battery replacement reminder**.

The integration also includes a dashboard that provides a visual overview of all configured battery sensors.

---

## Features

- **Dual Mode Support:**  
  Configure sensors as either voltage-based or percentage-based.
  
- **Unique Sensor IDs:**  
  Prevents duplicate sensor creation by using unique IDs.

- **Persistent Notifications:**  
  - **Low Battery Notification:** When a sensor’s battery level is below the configured threshold.
  - **Battery Replacement Reminder:** When a battery remains at `0%` for a prolonged period (default is 7 days).

- **Dashboard with Battery Overview:**  
  Accessible at `http://<home_assistant_url>:8123/local/battery_status.html`. Displays real-time battery levels and voltages for all configured sensors.

- **HTTP Endpoint:**  
  Provides a JSON API at `/battery_icons/data` that returns battery data from all sensors.

---

## Installation

1. **Copy Files:**  
   Create a folder in your Home Assistant configuration directory called `custom_components/battery_monitor/` and copy the following files into it:
   - `manifest.json`
   - `__init__.py`
   - `sensor.py`

2. **Add the HTML Dashboard:**  
   Place the `battery_status.html` file in your Home Assistant `www/` folder.  
   If the `www/` folder does not exist, create it under your Home Assistant configuration directory.

   Example path: `config/www/battery_status.html`

3. **Restart Home Assistant:**  
   Restart your Home Assistant instance to load the integration.

---

## Configuration

Add the following configuration to your `configuration.yaml` file under the `sensor:` section.

### Example Configuration (`configuration.yaml`)

```yaml
sensor:
  - platform: battery_icons
    name: "Battery Icons"
    low_threshold: 25
    sensors:
      # Voltage-based sensor
      - entity_id: sensor.hydro_battery_voltage
        sensor_type: voltage
        max_voltage: 12.6
        min_voltage: 10.0

      # Percentage-based sensor
      - entity_id: sensor.solar_battery_percentage
        sensor_type: percentage
```

### Explanation of Configuration Fields

- **name**: The name prefix for all created battery sensors.
- **low_threshold**: The battery percentage threshold for sending a low battery notification.
- **sensors**: Define each battery sensor to be monitored.
  - **entity_id**: The entity ID of the existing sensor in Home Assistant.
  - **sensor_type**: The type of sensor (`voltage` or `percentage`).
  - **max_voltage**: The maximum voltage for `voltage` sensors.
  - **min_voltage**: The minimum voltage for `voltage` sensors.

---

## Dashboard Access

You can access the battery dashboard at the following URL:

```
http://<home_assistant_url>:8123/local/battery_status.html
```

### Dashboard Features
- Displays each battery sensor's name, voltage, and percentage.
- Dynamically updates with real-time data from the `/battery_icons/data` endpoint.

---

This README provides installation, configuration, and dashboard setup instructions for the integration.
