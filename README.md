# iAqualink Heat Pump — Home Assistant Integration

> ⚠️ **Unofficial.** This is **NOT** an official integration. It is not affiliated with, endorsed by, or supported by Zodiac, Fluidra, iAquaLink, or Home Assistant. Use at your own risk. The iAquaLink cloud API may change or break this integration at any time without notice.

A community-built Home Assistant custom integration for Zodiac / Fluidra heat pumps (device types `zs500` and `hpm`) connected via the iAquaLink cloud.

This first release is **read-only**: it polls the device shadow and dynamically exposes every leaf value as a sensor. Climate control (mode, target temperature) will follow once the shadow schema is mapped.

## Features

- UI-based setup (config flow) — no YAML
- Auto-discovers the first heat pump on your iAquaLink account
- Auto-creates a sensor entity for every value in the device shadow
- Heuristic unit inference for temperature / pressure / percentage sensors
- Polls every 60 seconds via cloud (`iot_class: cloud_polling`)

## Installation

<img width="337" height="539" alt="image" src="https://github.com/user-attachments/assets/c016eb17-87aa-4ea0-bb18-46f95bbc62d2" />


### Via HACS (custom repository)

1. In HACS → Integrations → ⋮ → **Custom repositories**, add:
   - Repository: `https://github.com/peterwenzelnet/iAqualink-Heat-Pump-Home-Assistant-Integration`
   - Category: **Integration**
2. Install **iAqualink Heat Pump (Unofficial)**.
3. Restart Home Assistant.
4. Settings → Devices & Services → **Add integration** → search for *iAqualink Heat Pump*.
5. Enter your iAquaLink email and password.

### Manual

Copy `custom_components/iaqualink_heat_pump/` into your Home Assistant `config/custom_components/` directory, restart, and add the integration from the UI.

## Notes

- The integration uses the same public mobile-app API key and secret as the iAquaLink Android app. Only your email and password are stored in Home Assistant's encrypted config entry.
- Authentication tokens are refreshed automatically on expiry.
- If the entity names produced from your shadow look odd, share a sample shadow JSON and the unit / device-class mapping can be made explicit instead of heuristic.

## Roadmap

- Climate entity (mode + target temperature) once shadow keys are confirmed
- Binary sensors for boolean shadow values
- Reauth flow on credential change
- Diagnostics download

## Disclaimer

This project is an independent, community-built integration. It is **not** an official product of Zodiac, Fluidra, iAquaLink, or Home Assistant, and is **not** endorsed by or affiliated with any of them. All trademarks are property of their respective owners. Use at your own risk.
