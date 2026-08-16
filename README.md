# AstralPool for Home Assistant

Local Modbus integration for supported AstralPool pool equipment.

This repository combines the former Smart Next and Pro Elyo Touch integrations under a single Home Assistant domain: `astralpool`.

## Supported devices

| Device | Default Modbus Unit ID | Home Assistant platforms |
| --- | ---: | --- |
| AstralPool Smart Next | 2 | Sensors, binary sensors, numbers, selects, switches, buttons |
| AstralPool Pro Elyo Touch | 9 | Climate, sensors, binary sensors, time controls |

Both devices use Modbus RTU and require an external Modbus RTU-to-TCP gateway. The integration polls locally and does not require a cloud account.

## Setup

1. Install the repository as a custom integration with HACS.
2. Restart Home Assistant.
3. Open **Settings → Devices & services → Add integration → AstralPool**.
4. Choose **Smart Next** or **Pro Elyo Touch**.
5. Enter the gateway IP address, TCP port and Modbus Unit ID.
6. The integration validates the selected device with a real Modbus read before creating the config entry.

The device type is selected for every config entry, so one Home Assistant installation can contain several Smart Next and Pro Elyo Touch devices at the same time.

## Architecture

The Home Assistant domain is `astralpool`. Device-specific Modbus maps remain isolated under:

- `custom_components/astralpool/devices/smartnext`
- `custom_components/astralpool/devices/elyo_touch`

The common config flow and setup layer select the appropriate driver and only load the platforms supported by that device.

## Migration from the separate integrations

The previous integrations used the domains `smartnext` and `elyo_touch`. Home Assistant cannot automatically move a config entry from one domain to another. Before switching to this combined integration, note any entity IDs used by automations, remove the old custom integrations, restart Home Assistant, install AstralPool, and add each device again.

After re-adding a device, verify entity IDs referenced by automations and dashboards.

## Communication defaults

- TCP port: `502`
- Timeout: `5 s`
- Reconnect delay: `10 s`
- Polling interval: `5 s`
- Smart Next Unit ID: `2`
- Pro Elyo Touch Unit ID: `9`

These values can be adjusted from the integration options where applicable.

## Requirements

- Home Assistant with custom integrations enabled
- `pymodbus==3.13.1` (installed automatically from the manifest)
- A correctly configured Modbus RTU-to-TCP gateway

## License

MIT
