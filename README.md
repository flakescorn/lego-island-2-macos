# LEGO Island 2 for macOS

An **experimental native Apple Silicon port and ISO-import launcher** for the original PC
version of LEGO Island 2: The Brickster’s Revenge. Based on
[AntAir267/li2-recompiled](https://github.com/AntAir267/li2-recompiled), which supplies the
static recompiler and SDL3/Vulkan Windows/DirectX runtime. This fork adds macOS support,
English Version 1 support and a native setup/play interface, developed with AI assistance.

**Bring your own game.** No game executable, assets, movies, sound banks, saves, translated
game C code or playable game binary is included in this repository or the public launcher.
Your copy is extracted, translated and compiled on your Mac. Game files are never uploaded.

[Download the experimental launcher](https://github.com/flakescorn/lego-island-2-macos/releases/tag/v0.2.0-preview) · [Verification notes](docs/RELEASE_CHECKS.md)

## Use the launcher

1. Open **LEGO Island 2 Launcher.app** on an Apple Silicon Mac running **macOS 26 or later**.
2. Click **Choose ISO…** and select your own English Version 1 PC disc image.
3. If needed, install Apple’s Command Line Tools using the guided setup. Full Xcode is not required.
4. Click **Prepare Game**. Initial preparation needs internet, several minutes and disk space.
5. Click **Play**. Later launches use the locally prepared game without recompiling it.

An installed folder containing the executable and `_data` is an optional alternative to an ISO.
Your original ISO is not modified. Imported files, compiled game code, saves and logs stay in
`~/Library/Application Support/LEGOIsland2Mac/`. Keep that library in place.

**Preview distribution:** local builds use ad-hoc signatures, not Developer ID/notarization.
macOS may block an internet download. This is an early developer preview, not a signed consumer
release. Never disable Gatekeeper globally; source builds are available below.

## Compatibility and limitations

The launcher targets the original **English Version 1**, identified by:

```text
LEGO Island 2.exe — 6,406,196 bytes
SHA-256 117c111d8de6ce6179c70b2ff88f74766a3417b9997e83b186e1c56fca873198
```

The game also needs its complete installed asset tree. The importer handles the InstallShield
`LEGO Island 2/data1.cab` Game group layout tested with the supplied English discs. Other layouts,
languages and modified executables may not work. The retained Version 2 build configuration is
not offered by the launcher because its macOS gameplay has not been tested.

Verified on Apple M4 / macOS 26.5.1: native build, menu, initial town gameplay, movement, jumping,
pause, saving and loading in a fresh process. Movies decode; non-silent audio output is observed,
but audible quality has not been independently verified. A full playthrough, later islands,
minigames and hardware gamepads remain unverified. ARM x87 numerical fidelity is experimental.

Initial gameplay stays at 30 fps with original 640×480 rendering scaled to the display. Version 2’s
optional widescreen, camera and high-frame-rate patches have not been retargeted to Version 1.
See [MACOS.md](MACOS.md) for build instructions and detailed verification boundaries.

## Build the public launcher

Requires Apple Silicon, macOS 26+, Apple Command Line Tools (including Swift and Python 3).
No game files are needed to build this launcher:

```sh
git clone https://github.com/flakescorn/lego-island-2-macos.git
cd lego-island-2-macos
python3 -m unittest discover -s tests -p 'test_launcher.py' -v
python3 tools/macos/audit_public.py --history
python3 tools/macos/build_launcher.py --zip
open 'dist/LEGO Island 2 Launcher.app'
```

The build refuses to overwrite an existing app/archive; move it aside before rebuilding.
The launcher contains a SwiftUI interface and allowlisted open-source engine/build sources.
It never packages `build/li2`, `gen/`, `work/`, installed dependencies or any user game files.

For the engine/dependency build and command-line game import, see [MACOS.md](MACOS.md).
For contributing and the source/publication boundary, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits and licensing

The original game is by Silicon Dreams, published by LEGO Media (2001).
The translator/runtime foundation is by **AntAir267**, with earlier work in their 1NSANE and
L.A. Rush ports. This project builds on that work; it does not claim to have created the
translator or original game. The [original upstream README](docs/UPSTREAM_README.md) is retained.

Translator/runtime/launcher code is under the [Unlicense](LICENSE), with separate licenses for
third-party components. Preserve [CREDITS.md](CREDITS.md),
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and their referenced notices.
The original game and external MIDI banks retain their proprietary terms.

LEGO and LEGO Island are trademarks of the LEGO Group. This unofficial project is not affiliated
with, endorsed by, or supported by the LEGO Group or Silicon Dreams.
