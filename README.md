# AstralPool for Home Assistant

Local Modbus integration for supported AstralPool pool equipment.

This repository combines Smart Next and Pro Elyo Touch support under a single Home Assistant domain: `astralpool`.

**Stable baseline:** version 1.0.8.

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

## Smart Next maintenance

Open **Settings → Devices & services → AstralPool → Configure → Smart Next maintenance**.

Maintenance is separated into three guided families:

- **Restart Smart Next**
- **Calibrate a sensor**
- **Restore factory calibration**

Only procedures validated on real Smart Next hardware are exposed in the guided calibration menus. At present, **Temperature** is the only guided sensor calibration. pH, ORP and salinity remain available through the raw `Calibration TEST` entities while their exact hardware sequences are investigated.

### Guided temperature calibration

The temperature workflow has been validated directly on real hardware.

To apply a new reference temperature, Home Assistant:

1. writes the requested temperature multiplied by 10 to holding register `0x22`;
2. triggers temperature calibration coil `0xB0F`;
3. waits **5 seconds** for the Smart Next to apply the new calibration;
4. refreshes the device data.

Example: entering `29.0 °C` writes `290` to holding register `0x22` before triggering `0xB0F`.

To restore the factory temperature calibration, Home Assistant:

1. triggers reset coil `0xB0D`;
2. waits **2 seconds**;
3. refreshes the device data.

These temperature procedures intentionally do not enter the generic `Calibration_Mode` or manipulate flow/electrolysis settings because that is not part of the physically validated temperature sequence.

### Raw calibration test entities

Version 1.0.8 expands the raw calibration diagnostics so the exact Smart Next state machine can be reconstructed on real hardware before pH, ORP and salinity are automated.

The device exposes:

- switch: calibration mode `0x201`
- switch + button: clear calibration response `0x203`
- binary sensor: treatment halted `0x202`
- number: raw calibration value holding register `0x22`
- sensor: raw calibration response input register `0x22`
- pH switches + buttons: reset `0x50C`, pH 7 point `0x50D`, pH 4 point `0x50E`, fast calibration `0x50F`
- ORP switches + buttons: reset `0x80C`, 470 mV calibration `0x80F`
- temperature switches + buttons: reset `0xB0D`, calibration `0xB0F`
- salinity switches + buttons: reset `0xC0D`, calibration `0xC0F`

All raw test names start with **Calibration TEST** and include the Modbus address. The switches are true read/write entities: their state is refreshed from the actual Smart Next coil and they can explicitly force `OFF` then `ON`. This makes it possible to identify commands that remain latched instead of auto-clearing.

The raw command buttons remain available and intentionally write only `1` to their documented volatile coil. They do **not** add an automatic release, calibration mode transition, delay or response handling.

The raw response sensor reports the numeric `rsp_calibrado` code and adds its documented meaning as an entity attribute: `0` no response, `1` OK, `2` E2, `3` E3, `4` unavailable, `5` device initializing and `16` first calibration point OK.

The restart procedure is intentionally guided rather than exposed as an entity. Home Assistant first closes the maintenance options flow and starts the restart as a background task; this avoids unloading the integration while its own configuration request is still active. The background task verifies that `Watchdog_config` is the documented restart mode, fully unloads AstralPool so normal polling is stopped, then uses a dedicated Modbus client to arm the minimum 60-second watchdog and closes immediately. After a 70-second communication-silence period, the integration reconnects, restores the previous watchdog timeout and reloads normal polling. Expect the full procedure to take roughly 70–100 seconds.

The operational **pH · Pump Stop · rearm** action remains available as a normal Home Assistant button.

No undocumented global factory reset is exposed.

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

Unit ID, timeout, reconnect delay and polling interval can be adjusted from **Settings → Devices & services → AstralPool → Configure → Communication settings**.

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
- guided Smart Next maintenance procedure tests
- HACS validation
- Home Assistant hassfest

## License

MIT
