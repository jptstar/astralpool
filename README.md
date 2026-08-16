# AstralPool for Home Assistant

Local Modbus integration for supported AstralPool pool equipment.

This repository combines the former Smart Next and Pro Elyo Touch integrations under a single Home Assistant domain: `astralpool`.

> **Unofficial project** — This is an independent community integration. It is not developed, approved, endorsed, or maintained by AstralPool or Fluidra. AstralPool, Fluidra and their product names and trademarks remain the property of their respective owners.

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

## Safe migration from the separate integrations

The former custom integrations use the domains `smartnext` and `elyo_touch`. Home Assistant does not automatically move config entries between integration domains, so each device must eventually be added again through **AstralPool**.

### Recommended reversible test

Do **not** remove the existing integrations before the first test.

1. Create a Home Assistant backup.
2. Install the new `custom_components/astralpool` folder.
3. Restart Home Assistant.
4. Temporarily **disable** the existing Smart Next and Pro Elyo Touch config entries before enabling the matching AstralPool entry. This avoids two integrations polling the same Modbus RTU device at the same time.
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

## Testing the merge branch manually

Until the merge is released through HACS, the current integration can be tested from the merge branch.

From the Home Assistant terminal/SSH add-on:

```sh
cd /tmp
curl -L \
  https://github.com/jptstar/astralpool_smartnext/archive/refs/heads/agent/merge-astralpool-integrations.zip \
  -o astralpool-test.zip
unzip -o astralpool-test.zip
mkdir -p /config/custom_components
rm -rf /config/custom_components/astralpool
cp -R \
  astralpool_smartnext-agent-merge-astralpool-integrations/custom_components/astralpool \
  /config/custom_components/astralpool
```

Then restart Home Assistant and add **AstralPool** from **Settings → Devices & services**.

This test only installs the new `astralpool` folder. It does not overwrite `custom_components/smartnext` or `custom_components/elyo_touch`.

## Communication defaults

- TCP port: `502`
- Timeout: `5 s`
- Reconnect delay: `10 s`
- Polling interval: `5 s`
- Smart Next Unit ID: `2`
- Pro Elyo Touch Unit ID: `9`

Unit ID, timeout, reconnect delay and polling interval can be adjusted from the integration options.

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
