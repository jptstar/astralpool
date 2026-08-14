# SmartNext for Home Assistant

[![GitHub Release](https://img.shields.io/github/v/release/jptstar/astralpool_smartnext)](https://github.com/jptstar/astralpool_smartnext/releases)

> **Unofficial project** — This independent community integration was created for fun and for my own Home Assistant installation. It is not developed, approved, endorsed, or maintained by AstralPool or Fluidra, and is not affiliated with either company. AstralPool, Fluidra, Smart Next, and their product names and trademarks remain the property of their respective owners. Support requests for this integration must be directed to its author through GitHub, not to AstralPool or Fluidra.

Custom Home Assistant integration for an **AstralPool Smart Next** pool controller over **Modbus TCP**.

The register map in version 0.2.6 has been reconciled against the supplied **Modbus protocol v1.70** spreadsheet.

## About this project

I originally developed this integration for fun and for my own Home Assistant installation. I am sharing it so other Smart Next owners can benefit from local access to their controller. This remains a personal hobby project, so support and updates are provided on a best-effort basis.

## Configuration

Configuration is done from the Home Assistant UI:

- IP address / host
- TCP port (default `502`)
- Modbus Unit ID (default `2`)
- timeout
- reconnect delay
- polling interval

After setup, Unit ID, timeout, reconnect delay and polling interval can be changed from the integration's **Configure** dialog.

## Verified Modbus v1.70 mapping

### Measurements

| Entity | Modbus point | Conversion |
|---|---:|---:|
| Water temperature | Input `0xB1` | signed INT16 / 10 |
| Salt | Input `0xC1` | / 100 ppt |
| pH | Input `0x51` | / 100 |
| ORP | Input `0x81` | mV |
| pH dosage elapsed time | Input `0x57` | minutes |
| pH pump output | Input `0x58` | % |
| Electrolysis functional target | Input `0x41` | % |
| Electrolysis production | Input `0x42` | % |
| Electrolysis current | Input `0x43` | / 100 A |
| Electrolysis voltage | Input `0x44` | / 100 V |
| Chlorine production | Input `0x45` | g/h |

### Writable settings

| Entity | Holding register | Range / conversion |
|---|---:|---:|
| Electrolysis normal production | `0x41` | 0-100 % |
| Electrolysis cover production | `0x42` | 10-90 % |
| pH initialization time | `0x55` | 0 / 60 / 120 / 240 s |
| pH setpoint | `0x57` | x100 on write |
| pH dosage time limit | `0x58` | minutes |
| ORP setpoint | `0x87` | mV |
| Low temperature threshold | `0xB2` | x10 on write |
| High temperature threshold | `0xB3` | x10 on write |

### Standard / Biopool setpoint ranges

The integration reads Holding Register `0x0D`, bit 9 (`0x0D9`) to detect Biopool mode
and dynamically applies the protocol-valid setpoint ranges:

- pH standard mode: `7.00` to `7.80`
- pH Biopool mode: `6.50` to `8.50`
- ORP standard mode: `600` to `850 mV`
- ORP Biopool mode: `300` to `850 mV`

The current Biopool state is also exposed as a binary sensor.

### Read-only salt thresholds

Protocol v1.70 moved the salt thresholds to:

- Low salt threshold: Holding `0xC2`
- High salt threshold: Holding `0xC3`

They are documented as **not editable via Modbus**, so the integration exposes them as sensors only.

### Alarm and status inputs

The integration exposes the documented alarm groups for flow, electrolysis, pH, ORP, temperature and salt, plus measurement-quality states, electrolysis running/polarity, cover status and pH dosing status.

Important corrections from the verified table:

- `0x242` is the external/inductive flow-switch alarm.
- `0x250`, `0x251`, `0x252` are Check Cell, Low Conductivity and High Conductivity.
- Coil `0x56D` rearms the pH pump-stop; it is not a global alarm-reset coil.

## Installation with HACS

[![Add SmartNext to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=jptstar&repository=astralpool_smartnext&category=integration)

1. Add `https://github.com/jptstar/astralpool_smartnext` to HACS as a custom **Integration** repository.
2. Install **SmartNext**.
3. Restart Home Assistant.
4. Settings → Devices & services → Add integration → **SmartNext**.

## Default communication settings

- Port: `502`
- Unit ID: `2`
- Timeout: `5 s`
- Reconnect delay: `10 s`
- Polling interval: `5 s`

## Entity language

Entity names are intentionally kept in **English**, including when Home Assistant itself is configured in French. Configuration-flow labels can still be localized.

## Support and trademarks

Use the [GitHub issue tracker](https://github.com/jptstar/astralpool_smartnext/issues) for integration support. Do not contact AstralPool or Fluidra about this software.

The license covers only this independent implementation. It grants no rights to AstralPool or Fluidra trademarks, logos, software, documentation, or products. This project remains unofficial and unaffiliated with AstralPool and Fluidra.
