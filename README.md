# AstralPool for Home Assistant

Local Modbus integration for supported AstralPool pool equipment.

This repository combines Smart Next and Pro Elyo Touch support under a single Home Assistant domain: `astralpool`.

**Stable baseline:** version 1.0.2.

> **Unofficial project** — This is an independent community integration. It is not developed, approved, endorsed, or maintained by AstralPool or Fluidra. AstralPool, Fluidra and their product names and trademarks remain the property of their respective owners.

## Supported devices

| Device | Default Modbus Unit ID | Home Assistant platforms |
| --- | ---: | --- |
| AstralPool Smart Next | 2 | Sensors, binary sensors, numbers, selects, switches, buttons |
| AstralPool Pro Elyo Touch | 9 | Climate, sensors, binary sensors, time controls |

Pro Elyo Touch exposes the selected Silent / Smart / Turbo inverter preset, the real active inverter feedback, and the documented MODEL_Serie identification as the Home Assistant device serial number when the controller provides it.

Both devices use Modbus RTU and require an external Modbus RTU-to-TCP gateway. The integration polls locally and does not require a cloud account.

## Smart Next parameters

Smart Next exposes the verified operating values, alarms and user configuration through Home Assistant. Configuration entities are enabled by default.

Current controls include:

- normal and cover electrolysis production
- Boost mode and remaining Boost time
- polarity reversal period
- Flow Cell and Flow configuration
- cover control
- Cl mV auto and Cl EXT auto
- pH setpoint, initialization time, intelligent dosing and Pump Stop
- ORP setpoint
- temperature low/high alarm limits and alarm enable switches
- conductivity/salinity low/high alarm limits and alarm enable switches
- Bio pool mode
- ECO mode when the controller exposes the corresponding HMI Modbus point

The integration also exposes the measured pH, ORP, temperature, salinity/conductivity, electrolysis current/voltage/production, hour counters, pH/ORP alarm limits and the documented alarm/status bits.

For Smart Next software 2.00, the conductivity alarm thresholds use the verified `0xC1` / `0xC2` mapping. Older v1.70 controllers use the historical `0xC2` / `0xC3` mapping. The integration detects the active layout from the controller registers before reading or writing these limits.

Calibration and maintenance/factory-reset commands are intentionally not exposed yet. They will only be added after the complete calibration workflow and result handling are verified.

## Installation

### HACS

1. Add `jptstar/astralpool` as a custom repository in HACS with category **Integration**.
2. Install **AstralPool**.
3. Restart Home Assistant.
4. Open **Settings → Devices & services → Add integration → AstralPool**.
5. Choose **Smart Next** or **Pro Elyo Touch**.
6. Enter the gateway IP address, TCP port and Modbus Unit ID.

The integration validates the selected device with a real Modbus read before creating the config entry.

The device type is selected for every config entry, so one Home Assistant installation can contain several Smart Next and Pro Elyo Touch devices at the same time.

## Architecture

The Home Assistant domain is `astralpool`. Device-specific Modbus maps remain isolated under:

- `custom_components/astralpool/devices/smartnext`
- `custom_components/astralpool/devices/elyo_touch`

The common config flow and setup layer select the appropriate driver and only load the platforms supported by that device.

## Safe migration from the separate integrations

The former custom integrations use the domains `smartnext` and `elyo_touch`. Home Assistant does not automatically move config entries between integration domains, so each device must be added again through **AstralPool**.

### Recommended reversible test

Do **not** remove the existing integrations before the first test.

1. Create a Home Assistant backup.
2. Install **AstralPool**.
3. Restart Home Assistant.
4. Temporarily **disable** the existing Smart Next or Pro Elyo Touch config entry before enabling the matching AstralPool entry. This avoids two integrations polling the same Modbus RTU device at the same time.
5. Add **AstralPool** and choose the device type.
6. Verify measurements, controls, alarms, climate functions and diagnostics.
7. If the test fails, disable/remove the AstralPool entry and re-enable the former integration. No old config entry needs to be deleted for this rollback.

Because the old entities are still registered during a side-by-side test, Home Assistant may temporarily give the new entities IDs ending in `_2`. This is expected and does not indicate a protocol problem.

### Final migration

Once the new AstralPool entry has been validated:

1. Note the entity IDs referenced by automations, scripts and dashboards.
2. Remove the old `smartnext` / `elyo_touch` config entries and custom integration folders.
3. Restart Home Assistant.
4. Keep or rename the new AstralPool entity IDs as required by your automations.

## Communication defaults

- TCP port: `502`
- Timeout: `5 s`
- Reconnect delay: `10 s`
- Polling interval: `5 s`
- Smart Next Unit ID: `2`
- Pro Elyo Touch Unit ID: `9`

Unit ID, timeout, reconnect delay and polling interval can be adjusted from the integration options.

The gateway host/IP, TCP port and all Modbus communication parameters can also be changed later with **Settings → Devices & services → AstralPool → Reconfigure**. The new connection is validated before it is saved.

## Requirements

- Home Assistant with custom integrations enabled
- `pymodbus==3.13.1` (installed automatically from the manifest)
- A correctly configured Modbus RTU-to-TCP gateway

## Validation

The GitHub workflow checks:

- Python compilation
- JSON syntax
- unit tests for both protocol implementations
- HACS validation
- Home Assistant hassfest

## License

MIT
