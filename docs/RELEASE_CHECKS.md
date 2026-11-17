# Preview 0.2 release checks

Verified locally on Apple M4 / macOS 26.5.1, 2026-11-17:

- Nine asset-free unit checks pass: traversal/link rejection, selected-file extraction/no-overwrite,
  unsupported executable rejection, source boundary, document-versus-engine fingerprint changes,
  child timeout, and failed ISO preparation preserving a previous ready record and save files.
- New libarchive/libunshield importer extracted 3,126 files from the user-provided English PC ISO.
  The executable matches the supported original Version 1 SHA-256. The original ISO was not modified.
- Native SwiftUI launcher opens without game assets, accepts an ISO through the native file picker,
  and displays progress, optional details, local logs, upstream credits and license access.
- Stop Preparation cancels the worker/compiler process group. Retrying resumes dependency setup.
- Full first-run flow passed in a fresh engine workspace under Application Support (paths with spaces):
  pinned dependency setup, local ISO extraction, seven address checks, full Version 1 translation,
  native ARM64 compilation, offscreen 1800-frame menu check, private bundle/signature verification,
  and ready-record creation. No generated game output is written into the public launcher.
- Play launched the locally generated game. Main menu, New Game, opening town dialogue and playable
  town with Pepper/HUD were visually inspected. Native keyboard menu input and movement were exercised.
  Quitting returned the launcher to its enabled Play state.
- The earlier linker bug with unquoted absolute Application Support paths was fixed using
  executable-relative dependency paths. The final first-run flow verified the fix.
- Runtime cleanup was followed by passing memory/ARM helper, offscreen and native-window probes;
  44 fixture runtime C files and 23 music-engine C files compiled.
- Source publication audit passes for the original upstream history and allowlisted source tree.
  Public launcher contents match a per-file SHA-256 manifest; no original assets or translated
  game output are included. The launcher executable contains no absolute home paths.

Final clean-source packaging, launcher restart, ZIP verification and hosted CI are checked during
publication. CI performs asset-free tests and builds only the public launcher; it cannot verify
actual gameplay because it never receives game files.

Remaining limitations:

- Developer ID/notarization: not performed. Only an Apple Development identity is available locally;
  ad-hoc preview signing is used. No clean-machine Gatekeeper result is claimed.
- Cross-Mac coverage: not performed; no Intel support or older macOS compatibility is claimed.
- Full-game/late-island compatibility, hardware controllers and audible sound quality remain
  unverified; see MACOS.md. Successful menu or initial town tests do not establish a complete port.
- Generated game bundles, memory snapshots, original assets and game-derived screenshots remain
  private local outputs and are not release artifacts.
