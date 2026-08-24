# PHASENOX Ableton Export Helper

This optional, separately operated component supports an explicit rendered-WAV
handoff from Ableton Live to the local PHASENOX bridge. It is not a control
surface, Max for Live device, plugin, or DAW automation layer.

The helper:

- connects only to the `127.0.0.1` endpoint in an ephemeral per-user handoff;
- never prints the bearer token;
- watches only the immediate children of one explicit export folder;
- ignores files that existed when it started unless `--include-existing` is
  explicitly supplied;
- submits WAV identities for stable-file validation and deterministic PHASENOX
  analysis;
- does not alter Live preferences, projects, transport, devices, or automation.

Start the host with an existing empty export directory:

```powershell
python tools/ableton/bridge_host.py --export-root C:\path\to\temporary\exports
```

In a second terminal, start the helper:

```powershell
python tools/ableton/export_client.py --daw-version 11.2.7 --project "Disposable Set"
```

Then render a disposable WAV from Ableton into that exact folder. The helper
reports only bounded state/result JSON. Stop both processes with `Ctrl+C`.

Installation for a future release must be an explicit optional action. The
standard Desktop Core installer must not silently install this helper or modify
Ableton directories. Uninstall removes only PHASENOX-owned helper files; it must
not remove Live projects, exports, preferences, or unrelated settings.
