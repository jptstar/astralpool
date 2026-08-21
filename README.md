# AstralPool for Home Assistant

Local Modbus integration for supported AstralPool pool equipment.

This repository combines Smart Next and Pro Elyo Touch support under a single Home Assistant domain: `astralpool`.

**Stable baseline:** version 1.0.1.

> **Unofficial project** — This is an independent community integration. It is not developed, approved, endorsed, or maintained by AstralPool or Fluidra. AstralPool, Fluidra and their product names and trademarks remain the property of their respective owners.

## Supported devices

| Device | Default Modbus Unit ID | Home Assistant platforms |
| --- | ---: | --- |
| AstralPool Smart Next | 2 | Sensors, binary sensors, numbers, selects, switches, buttons |
| AstralPool Pro Elyo Touch | 9 | Climate, sensors, binary sensors, time controls |

Pro Elyo Touch exposes the selected Silent / Smart / Turbo inverter preset, the real active inverter feedback, and the documented MODEL_Serie identification as the Home Assistant device serial number when the controller provides it.

Both devices use Modbus RTU and require an external Modbus RTU-to-TCP gateway. The integration polls locally and does not require a cloud account.
