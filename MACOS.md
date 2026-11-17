# macOS build, launch and verification

## Requirements

- Apple Silicon ARM64 Mac, macOS 26 or later. The currently verified machine is an Apple M4,
  16 GB MacBook Air running macOS 26.5.1 (25F80).
- Apple Command Line Tools. Verified compiler: Apple Clang 17 / SDK 26.1; Swift 6.2.1 for the launcher.
  Full Xcode is not required. The verified Python is Apple Python 3.9.6.
- Internet for pinned open-source dependencies and Python packages during first preparation.
- Approximately 5 GB free working space is a practical starting allowance; requirements vary
  with the ISO, retained failed attempts and dependency caches. Imports check free space.
- Your own original English Version 1 PC executable and complete `_data` assets, normally from an ISO.

The exact supported executable SHA-256 is
`117c111d8de6ce6179c70b2ff88f74766a3417b9997e83b186e1c56fca873198`,
SHA-1 `1dd65fa89381a1aecdeb9f52f372b36b233d7732`, size 6,406,196 bytes.
The runtime also checks that hash before loading the executable.

## Public launcher versus private game build

`python3 tools/macos/build_launcher.py --zip` creates the **public launcher** in `dist/`.
It contains a native SwiftUI application plus allowlisted open-source source files. It does not
contain a translated game executable, game assets or generated game C code.

The launcher’s preparation worker extracts a user-selected ISO (or reads an installed folder),
creates a private engine workspace, bootstraps dependencies, audits and translates Version 1,
compiles ARM64, performs an offscreen 1800-frame menu startup check, then makes a private local
runtime bundle. Only then does it replace the ready record. Failed attempts do not replace a
previously prepared game or personal saves. Stop Preparation terminates the worker and compiler
process group; partial private work may remain for diagnostics.

The launcher library is `~/Library/Application Support/LEGOIsland2Mac/`:

- `Imports/`: locally extracted original assets and their original notices.
- `Engines/`: source workspaces, pinned tools, dependency caches, generated game C and objects.
- `Prepared/`: private locally built game bundles. Do not redistribute these.
- `Profiles/en-v1/`: ordinary game saves, settings and `last-run.log`.
- `Checks/`: separate startup-check profiles, never installed over personal saves.
- `Logs/`: preparation logs, which may contain local paths; review before sharing.
- `prepared.json`: location of the active prepared game and source fingerprint.

A changed launcher source fingerprint requires a fresh preparation. Existing saves are retained.
This library is separate from the earlier command-line port’s `~/Library/Application Support/li2-native/`.
No automatic save migration or deletion is performed. Optional installed-folder imports must remain
at their selected path. ISO imports can play from the extracted copy after the original ISO moves.

Public preview builds are ad-hoc signed. Developer ID signing/notarization and clean-machine
Gatekeeper testing remain release work; an Apple Development certificate does not substitute for
Developer ID. The runtime bundle generated locally is also ad-hoc signed.

## Command-line setup and import

Run from the checkout root:

```sh
python3 tools/macos/bootstrap.py
python3 tools/macos/import_iso.py '/absolute/path/to/your.iso'
python3 tools/macos/check_game.py work/imported-disc/Game
python3 tools/macos/build.py work/imported-disc/Game
build/li2 --play --window --game "$PWD/work/imported-disc/Game" \
  --user "$PWD/work/manual-test-user" --option display=window
```

The importer refuses to overwrite its destination. Use `--destination /another/new/folder`
for a subsequent import. It reads ISO/CAB contents with macOS libarchive and the pinned unshield
library without executing the Windows installer. Relative traversal, links and special archive
members are rejected. The supported layout is `LEGO Island 2/data1.cab`, InstallShield Game group.
Game extraction streams 3,126 files on the tested discs. Core filename checks are not a complete
asset manifest or a guarantee that every area will work.

Optional movies are read from `Movies/` or `fmv/`: `LegoSoftware.mpg`, `SdLogo.mpg`, `IntroFmv.mpg`,
`outroFmv.mpg`. The importer links the disc’s Movies directory into the private installed folder.
Optional user-provided `gm.dls` or the disc redistributable’s `gm16.dls` supply General MIDI
instruments. If `directx8/directx.cab` contains `gm16.dls` and `gmreadme.txt`, the importer retains
both privately with the game files. The MIDI bank has its own restrictive proprietary terms;
its inclusion on a disc does not grant unrestricted reuse. No bank is included in source/releases.
Missing banks can leave some instruments silent. Other game DLS collections remain in `_data`.

Dependencies are local, never installed with Homebrew: SDL3 3.4.18, SIMDe 0.8.2, Vulkan Headers
1.4.350.1, MoltenVK 1.4.2 and unshield 1.6.2. Sources are SHA-256 pinned in
`tools/macos/dependencies.lock.json`; Python versions are pinned in `requirements.txt`.
The original vendored dmusic, dr_mp3 and pl_mpeg are reused. unshield uses its internal MD5 implementation.

`build.py` validates the input, audits active Version 1 addresses, explicitly regenerates game C
(to avoid stale output when changing games), and compiles with four jobs. `make` defaults to
Version 1 on macOS; an explicit equivalent is:

```sh
make BUILD_CFG=builds/en_v1.py GAME='/absolute/installed/game' JOBS=4
```

Do not switch configurations using only stale objects/generated files. The retained Version 2
configuration requires its exact original executable and is not macOS-gameplay verified.

## Controls

Arrows move; **Option/Alt jumps**, Control uses the skateboard when available, Shift talks,
Space throws and Escape pauses. Menus use arrows and Return. Option+Return switches fullscreen.
The launcher exposes fullscreen and startup-movie toggles. Additional original game bindings
can be changed in the game. Hardware gamepad and mouse/camera feel still require hands-on checks.

Keep 30 fps for now: Version 1 does not use Version 2’s high-frame-rate gameplay patches.
The image is originally 640×480, scaled to the display. Generic renderer options in upstream
files are not evidence that Version 1 supports all their corresponding game hooks.

## Verification boundaries

Verified during local port development on M4/macOS 26.5.1:

| Stage | Result |
|---|---|
| Dependencies/runtime | Native SDL build; direct MoltenVK works; 44 asset-free fixture runtime C files and 23 music-engine files compile |
| Memory/ARM helpers | High-address guest mapping, unaligned access, zero-on-free, heap operations, guard page and selected floating-point/80-bit memory helpers pass |
| Graphics | Offscreen triangle RGB readback and native Retina Cocoa/Metal swapchain probes pass |
| Translation | 4,501 Version 1 functions, 1,117,134 instructions, zero discovery errors; approximately 2.9 million generated C lines |
| Active addresses | Seven Version 1 hook/directory/movie/state-table checks pass against the exact original executable |
| Menu/gameplay | Menu and New Game into town rendered; initial run reached 10,000 frames |
| Controls | Scripted movement and Option/Alt jump inspected; native Return enters gameplay; fullscreen toggle observed |
| Save/load | Ordinary Save menu confirmation writes 334,988-byte Save00.lgo; fresh-process Load restores the saved hillside position |
| Private game app | Native app launch verified; relocated bundle loads SDL/MoltenVK from its own Frameworks directory |
| Movies | Startup logos decoded and inspected; IntroFMV began; full intro/outro completion unverified |
| Audio | Normal 44,100 Hz output submits non-silent samples; this is not a human listening test |

Launcher/import/publication verification is recorded in [docs/RELEASE_CHECKS.md](docs/RELEASE_CHECKS.md).
Game-derived screenshots, memory dumps and local test saves are private, not repository fixtures.

Repeat source/launcher boundary tests without game files:

```sh
python3 -m unittest discover -s tests -p 'test_launcher.py' -v
python3 tools/macos/audit_public.py --history
python3 tools/macos/verify.py  # after dependency bootstrap; includes native window probe
```

Game checks need a private installed folder. The script’s default is the original local development
extraction; pass your own folder explicitly:

```sh
.venv/bin/python tools/macos/audit_v1.py work/imported-disc/Game
python3 tools/macos/playtest.py town --game work/imported-disc/Game
python3 tools/macos/playtest.py jump --game work/imported-disc/Game
python3 tools/macos/playtest.py save --game work/imported-disc/Game
python3 tools/macos/playtest.py load --game work/imported-disc/Game
```

These use isolated `work/v1-test-user` saves and virtual 30 fps, skipping movies and real-time audio.
Also test normal windowed play. `LI2_AUDIO_STATS=1` logs submitted stereo frames and peak magnitude
at exit, without recording a microphone. It establishes output signal, not audible quality.

## Port design and remaining work

Guest addresses are 32-bit offsets into a reserved 4 GB host address range; macOS cannot use the
Linux low-address identity mapping. This reserves virtual space, not 4 GB of immediate physical RAM.
All guest-pointer conversion uses `GP`. Host guard pages account for Apple Silicon’s 16 KB pages;
Darwin decommit explicitly zeroes ranges. No MAP_FIXED mapping may overwrite host allocations.

SIMDe maps generated Intel SIMD operations to ARM. ARM spin waits, sleeps, profiler contexts and
Linux-only diagnostics are adapted. dmusic uses POSIX threads; DirectInput event signaling has a
real definition for Darwin linking. The renderer enables Vulkan portability extensions as advertised
and uses direct MoltenVK, preserving the existing Vulkan/Direct3D translation paths.

Version 1 uses `builds/en_v1.py` and `runtime/game_v1.c`; original translated gameplay handles menus,
physics, skinning and controls. Version 2’s optional game/menu/native/skinning optimizations and
per-instruction timing fixes are excluded. Only the verified CD/movie paths and loading-present hook
are active. A common address shift had exceptions, so no blanket offset was accepted as verified.
The Version 1 music filename `Lego Town Bridge.sgt` resolves to the disc’s `Town Bridge.sgt`.

**Numerical fidelity is experimental:** ARM64 long double has a 53-bit significand versus x87’s 64.
Ten-byte values are safely converted, but exact extended arithmetic, precision-control behavior,
independent x87/SSE rounding, FTZ/DAZ, denormal/C1 flags and transcendental approximations are incomplete.
Upstream’s x86-specific Unicorn function-check harness has not been ported into a trusted reference
for this ARM build. Local repeatable tests are not proof of equivalence to the original Windows game.

Later islands, vehicles, minigames, ending, long sessions and a full playthrough remain unverified.
Higher resolution/widescreen, reliable 60 fps, full controller integration, signed distribution and
additional Mac/macOS coverage are future work. Initial town success is not a complete compatibility claim.
