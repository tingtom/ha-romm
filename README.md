# RomM for Home Assistant

A Home Assistant custom integration for [RomM](https://github.com/rommapp/romm), the
self-hosted ROM manager. It surfaces your library, your play history and your
RetroAchievements progress as native entities.

## Entities

### Library

| Entity | Description |
| --- | --- |
| `sensor.romm_games` | Number of games in the library |
| `sensor.romm_platforms` | Number of platforms |
| `sensor.romm_library_size` | Total size of the library (GB) |
| `sensor.romm_saves` | Save files |
| `sensor.romm_states` | Save states |
| `sensor.romm_screenshots` | Screenshots |

### Play activity

| Entity | Description |
| --- | --- |
| `sensor.romm_last_played` | The most recently played game, with platform, cover, completion and status as attributes |
| `sensor.romm_recently_played` | Count of the last 10 games played — the games themselves are in the `games` attribute |
| `sensor.romm_recently_added` | Count of the last 10 games added — games in the `games` attribute |
| `sensor.romm_games_played` | Games that have ever been played |
| `sensor.romm_games_finished` | Games marked *finished* |
| `sensor.romm_games_completed` | Games marked *100% completed* |

### RetroAchievements

| Entity | Description |
| --- | --- |
| `sensor.romm_achievements_earned` | Achievements unlocked (softcore) |
| `sensor.romm_achievements_possible` | Achievements available across tracked games |
| `sensor.romm_achievement_completion` | Unlocked / available, in percent |
| `sensor.romm_ra_games` | Games with RetroAchievements data; per-game breakdown in the `games` attribute |

### Connectivity

`binary_sensor.romm_server` reports whether RomM answered the last poll.

## Installation

### HACS (custom repository)

1. HACS → **Integrations** → ⋮ → **Custom repositories**
2. Add `https://github.com/tingtom/ha-romm` with category **Integration**
3. Search for **RomM** in HACS and install it
4. Restart Home Assistant
5. **Settings → Devices & Services → Add Integration → RomM**

### Manual

Copy `custom_components/romm` into your Home Assistant `config/custom_components`
directory and restart Home Assistant.

## Configuration

The config flow asks for:

- **Server URL** — e.g. `http://192.168.1.28:8085` (a trailing `/api` is stripped)
- **API token** *(optional)* — a RomM client token (`rmm_…`). Create one in RomM under
  **Settings → Client tokens**, granting at least the read scopes
  (`me.read`, `roms.read`, `roms.user.read`, `platforms.read`, `assets.read`,
  `collections.read`, `users.read`).
- **Username / Password** — used with HTTP Basic auth if no token is given.

Polling defaults to every 5 minutes and is configurable under the integration's
**Configure** dialog.

## Notes

- Only read scopes are required; the integration never writes to RomM.
- `sensor.romm_games_finished` and `sensor.romm_games_completed` reflect RomM's
  per-user status values (`finished` and `completed_100`).
- Cover URLs come from RomM's own assets or the metadata provider, so cards show
  artwork without extra configuration.

## License

MIT
