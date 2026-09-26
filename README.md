# AstralPool for Home Assistant

Local Modbus integration for supported AstralPool pool equipment.

This repository combines Smart Next and Pro Elyo Touch support under a single Home Assistant domain: `astralpool`.

**Stable baseline:** version 1.0.11.

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

Only procedures validated on real Smart Next hardware are exposed as guided workflows. Version 1.0.9 adds guided **pH Fast**, **pH Standard two-point**, **Redox / ORP 470 mV**, plus factory calibration reset for pH and ORP. Salinity calibration remains available only through the raw `Calibration TEST` entities until its exact sequence is validated.

### Shared calibration state machine

The hardware-validated pH/ORP state machine uses:

- `0x201` to enter calibration mode and stop treatment/dosing;
- `0x203`, while `0x201` is active, to clear the shared calibration response;
- input register `0x22` for the result: `0` no response, `1` OK, `2` E2, `3` E3, `4` unavailable, `5` initializing and `16` first point of a two-point calibration accepted.

Entering `0x201` was also observed to clear `IR 0x22` by itself, but the guided pH/ORP workflows intentionally send `0x203` after `0x201` for a deterministic fresh session.

A terminal success or error can make the Smart Next release `0x201` automatically. A successful ORP test also showed that re-entering calibration mode after completion is not safe to assume: an early guided implementation that re-armed `0x201` during probe restoration was followed by an implausible `999 mV` ORP reading. Version 1.0.9 therefore **does not automatically re-arm `0x201` after a terminal result**. A new `0x201` session is started only for an explicit retry or a deliberately chained calibration of the other probe.

### Safety architecture for probe-removal procedures

pH Standard and Redox / ORP require physical probe removal. The guided workflow therefore uses several independent barriers instead of relying on calibration mode alone.

Before any valve or probe manipulation, AstralPool:

1. saves the previous electrolysis, flow-supervision and pH Pump Stop settings;
2. forces **pH Pump Stop ON** as an additional controller safeguard;
3. keeps flow supervision active during the physical preparation;
4. disables known electrolysis production overrides (Boost, cover production, external chlorine control and internal ORP production control when active);
5. forces normal electrolysis production to `0 %`;
6. verifies **production = 0**, **cell current = 0** and **electrolysis not running**.

`Pump Stop` is deliberately **not** treated as an immediate pump-off command. The Modbus setting enables the Smart Next Pump Stop function; before the hydraulic circuit may be opened, the workflow additionally verifies the real pH dosing-pump output at `IR 0x58` is **0 %**.

Calibration mode is not entered during the slow physical preparation. Once the probe has been cleaned, placed in its reference solution and stabilized for the mandatory delay, Home Assistant enters `0x201`, verifies treatment is halted, then temporarily disables the logical flow inputs, sends `0x203`, and triggers the actual calibration command.

As soon as a terminal pH/ORP result is captured, AstralPool **immediately restores the saved flow-sensor configuration** and verifies the real pH pump output remains `0 %`. Electrolysis stays independently forced to `0 %` until the entire hydraulic circuit has been restored and real circulation is confirmed.

### Exact hydraulic preparation — pH Standard and ORP

The same physical preparation is presented one confirmation at a time:

1. with filtration still running and all valves in their normal position, let AstralPool establish the software protections described above;
2. switch the filtration pump **OFF**, physically verify that it is stopped, and validate — Home Assistant then verifies `IR 0x58 = 0 %` for the pH dosing pump;
3. fully **OPEN** the electrolyzer bypass valve;
4. **CLOSE** the upstream/inlet valve on the probe side;
5. **CLOSE** the downstream/outlet valve;
6. slightly unscrew the probe that will be removed without removing it completely;
7. very slightly open the downstream/outlet valve for **no more than 2 seconds** so a small amount of air enters and the water level drops, then close it again immediately;
8. remove, rinse/clean and immerse the target probe in the appropriate reference solution;
9. start the mandatory **60-second stabilization period** and confirm that the displayed measurement is stable after the full minute;
10. only then does Home Assistant enter `0x201`, verify treatment halted, temporarily disable the flow inputs, clear `IR 0x22` with `0x203`, and trigger calibration.

The two-second outlet-valve pulse is a manual operation. The UI explicitly requires confirmation that the valve has been reclosed.

### Guided pH Fast calibration

Fast calibration keeps the pH probe installed in normal circulation. The user enters a trusted reference pH and Home Assistant performs the validated sequence:

1. `0x201 = ON`;
2. `0x203` clears `IR 0x22`;
3. write the reference value multiplied by 100 to holding register `0x22` — for example `7.20 → 720`;
4. trigger Fast calibration `0x50F`;
5. read `IR 0x22` and show the exact result.

A successful Fast calibration returns `IR 0x22 = 1` and the controller normally releases `0x201` automatically. Because the probe remains installed and normal circulation continues, the physical bypass workflow is not used for Fast calibration.

### Guided pH Standard calibration

The validated two-point sequence is:

1. immerse the cleaned probe in fresh **pH 7** solution;
2. wait **at least 60 seconds** and confirm the displayed measurement is stable;
3. Home Assistant starts `0x201`, disables flow supervision only after treatment halt is confirmed, sends `0x203`, then triggers `0x50D`;
4. `IR 0x22 = 16` confirms the first point and the same calibration session remains active;
5. rinse/clean the probe and immerse it in fresh **pH 4** solution;
6. wait another **at least 60 seconds** and confirm stability;
7. trigger `0x50E`;
8. `IR 0x22 = 1` confirms success and the Smart Next normally releases `0x201`;
9. flow supervision is restored immediately and the pH pump output is verified at `0 %`; electrolysis remains forced to `0 %`.

If a terminal error is returned, the same immediate flow-sensor restoration is attempted. The assistant does not silently re-enter calibration mode. **Retry** starts a new session from pH 7 after a fresh 60-second stabilization.

### Guided Redox / ORP calibration

ORP calibration uses a **470 mV reference solution**, ideally around **25 °C**:

1. remove, clean and immerse the probe in fresh 470 mV solution;
2. wait **at least 60 seconds** and confirm the displayed ORP measurement is stable;
3. Home Assistant enters `0x201`, verifies treatment halt, temporarily disables the flow inputs, sends `0x203`, and triggers `0x80F`;
4. `IR 0x22 = 1` means success;
5. `IR 0x22 = 2` is E2, observed when the measured value is too far from the expected 470 mV value;
6. after any terminal result, flow supervision is restored immediately, the pH dosing-pump output is checked at `0 %`, and electrolysis remains forced to `0 %`.

Other documented response codes are displayed without requiring them to be intentionally reproduced during testing.

### Calibrate both probes in one hydraulic intervention

After a successful pH Standard calibration, the assistant asks whether the user also wants to calibrate **Redox / ORP**. After a successful ORP calibration, it likewise offers **pH Standard**.

When the second calibration is accepted, the workflow does not ask the user to reopen the entire hydraulic circuit and isolate it again. Instead:

1. flow supervision has already been restored immediately after the first terminal result;
2. electrolysis remains locked at `0 %` and Pump Stop remains forced ON;
3. the first calibrated probe must be reinstalled and tightened before the other probe is removed;
4. the second probe is cleaned and immersed in its reference solution;
5. a fresh mandatory **60-second stabilization** is required;
6. Home Assistant starts a fresh `0x201 → 0x203` calibration session for the second probe;
7. after the second terminal result, flow supervision is again restored immediately and the normal hydraulic restoration continues.

This avoids repeating the bypass/isolation sequence while never allowing both probes to remain removed at the same time.

### Exact hydraulic restoration — pH Standard and ORP

After the final probe calibration or after choosing not to calibrate the second probe:

1. reinstall and tighten the removed probe while filtration remains OFF and both isolation valves are closed;
2. fully **OPEN** the upstream/inlet valve;
3. fully **OPEN** the downstream/outlet valve;
4. **CLOSE** the electrolyzer bypass valve so the normal path again passes through the electrolyzer;
5. switch filtration **ON** and verify real water circulation through the electrolyzer;
6. Home Assistant verifies Smart Next flow;
7. only then are the saved electrolysis settings and the user's original Pump Stop configuration restored.

Flow supervision has already been restored immediately after the terminal calibration result. If normal flow is not confirmed at the final step, electrolysis production remains at `0 %`.

### Guided pH / ORP factory calibration reset

The factory calibration reset sequence is also validated on real hardware and does not require probe removal or hydraulic bypass.

For pH (`0x50C`) and ORP (`0x80C`), Home Assistant executes:

1. `0x201 = ON`;
2. `0x203` to clear `IR 0x22`;
3. verify `IR 0x22 = 0`;
4. trigger the relevant reset coil;
5. read `IR 0x22` — `1` confirms success;
6. the Smart Next normally releases `0x201` automatically after the terminal result.

Errors `2`, `3`, `4` and `5` are shown to the user instead of being hidden.

### Guided temperature calibration

The temperature workflow has been validated directly on real hardware.

To apply a new reference temperature, Home Assistant:

1. writes the requested temperature multiplied by 10 to holding register `0x22`;
2. triggers temperature calibration coil `0xB0F`;
3. waits **5 seconds** for the Smart Next to apply the new calibration;
4. refreshes the device data.

Example: entering `29.0 °C` writes `290` to holding register `0x22` before triggering `0xB0F`.

To restore the factory temperature calibration, Home Assistant triggers reset coil `0xB0D`, waits **2 seconds**, then refreshes the device data.

Temperature calibration intentionally does not enter generic `Calibration_Mode` because that is not part of the physically validated temperature sequence.

### Raw calibration test entities

The raw calibration diagnostics remain exposed so protocol work can continue without hiding controller behavior.

Available entities include:

- switch: calibration mode `0x201`
- switch + button: clear calibration response `0x203`
- binary sensor: treatment halted `0x202`
- number: raw calibration value holding register `0x22`
- sensor: raw calibration response input register `0x22`
- pH switches + buttons: reset `0x50C`, pH 7 point `0x50D`, pH 4 point `0x50E`, fast calibration `0x50F`
- ORP switches + buttons: reset `0x80C`, 470 mV calibration `0x80F`
- temperature switches + buttons: reset `0xB0D`, calibration `0xB0F`
- salinity switches + buttons: reset `0xC0D`, calibration `0xC0F`

All raw test names start with **Calibration TEST** and include the Modbus address. The switches read the real Smart Next coil state and can explicitly force `OFF` then `ON`. The buttons intentionally write only `1` and add no hidden sequence.

The restart procedure remains guided. Home Assistant closes the options flow, stops normal polling, arms the documented watchdog restart, waits for the controller to reboot, restores the previous watchdog timeout and reloads the integration.

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
7. If the test fails, disable/remove the AstralPool entry and re-enable the former integration.

Because the old entities are still registered during a side-by-side test, Home Assistant may temporarily give the new entities IDs ending in `_2`. This is expected.

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

### Shared gateway behaviour

Version 1.0.10 serializes all AstralPool requests that use the same gateway host
and TCP port, including requests for different Modbus Unit IDs. This is important
for TCP-to-RTU gateways, which commonly have a single serial bus. After a failed
transaction the affected TCP connection is closed, so a delayed response cannot
be mistaken for the following request. Do not run another Modbus integration
against the same gateway at the same time; it cannot participate in this lock.

Version 1.0.11 also detects Smart Next firmware that does not support reading
the optional ECO HMI coil (`0x230B`). After the first failed probe, the ECO
switch is unavailable for that connection and the integration no longer retries
the unsupported read during every polling cycle.


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
