# Contributing

This fork builds on AntAir267’s translator/runtime; preserve upstream history, credits and notices.
Describe changes as macOS/Version 1 adaptations or launcher work, not authorship of the original game
or translator. Implementation and verification in this fork were AI-assisted; review changes normally.

## Public source boundary

Never commit original game EXEs, ISOs, CABs, assets, movies, sound banks, saves, memory snapshots,
generated game C (`gen/`), compiled game binaries/bundles, dependency/build caches or local logs.
Do not attach them to issues, Actions artifacts or releases. A playable local game bundle includes
code translated from the original proprietary executable even when its assets are external.

`tools/macos/public_files.py` defines an explicit source allowlist for launcher resources.
`audit_public.py` checks that boundary, disguised binaries, generated game code and obvious credentials.
Run it with `--history` before publication, and `--bundle` against a public launcher before release.
These automated guards supplement human review; they do not prove ownership of arbitrary source.

Use synthetic, asset-free fixtures for automated tests. Users supply their own game for gameplay checks.
Do not invent test results or present a startup/menu check as proof of a full working game.

## Development

Build the native UI with `python3 tools/macos/build_launcher.py`; see MACOS.md for the engine.
Run `python3 -m unittest discover -s tests -p 'test_launcher.py' -v` and the source audit before a PR.
A release must contain only the launcher ZIP produced by this tool, never the private game app.
Preserve failed imports and normal saves; fixes should not overwrite user-owned files.

Initial scope is English Version 1, Apple Silicon and macOS 26+. Add support claims only with evidence.
The original Linux instructions and Version 2 configuration are retained for reference.
