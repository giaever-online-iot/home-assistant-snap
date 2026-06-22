# core26 Upgrade

Notes and checklist for moving the snap base from `core24` to `core26`
(Ubuntu Core 26 / Ubuntu 26.04 "Resolute Raccoon").

## TL;DR — do the two "hacks" survive core26?

| Hack | Where | Survives core26? |
|------|-------|------------------|
| **HA-core source patch** (`is_snap_env`) | `src/patches/0001-Detect-snap-environment.patch`, applied in `override-build` | **Still required.** It is *not* upstreamed (current HA `dev` `homeassistant/util/package.py` has no `is_snap_env`). core26 changes nothing here — it's HA-side, not base-side. |
| **Interpreter symlink dance** (~55 lines copied from snapcraft's python plugin) | `override-build`, the `# look for a provisioned python interpreter` block | **Probably removable.** It existed because core24's base bundles `python3.12` while we want `python3.14`. From core26 the base bundles **no** Python and the python plugin is built around a staged interpreter, so the manual re-symlink should be unnecessary. **Must be verified by a real build** — see step 4. |

## Why core26 matters for this snap

- **No bundled Python.** From core26 onward the base snap ships no Python interpreter; the snap must stage its own. We already do (`stage-packages: python3.14-venv`, `build-packages: python3.14-dev`), so this is structurally in place.
- **Ubuntu 26.04 ships `python3.14` in its archive**, so the `deadsnakes/ppa` we needed on the core24 (22.04) build base is no longer required. It is commented out in `snapcraft.yaml`, not deleted — restore in one line if a build can't find `python3.14{,-dev,-venv}`.

## Changes already made on this branch

- `snap/snapcraft.yaml`
  - `base: core24` → `base: core26`
  - `deadsnakes/ppa` `package-repositories` commented out (with restore note)
  - App `environment` deduplicated via a YAML anchor (`&python-runtime-env` / `*python-runtime-env`) — was repeated across `home-assistant-snap` and `check-config`
  - `override-build`: added a marker around the interpreter-symlink block flagging it as the core26 simplification candidate, and a clear header around the HA-core patch step (previously buried as the last line)
  - `snapcraft-preload` part: added `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` — 26.04 ships CMake 4.x, which removed compatibility with the pre-3.5 `cmake_minimum_required()` in upstream snapcraft-preload
- `.github/workflows/test-snap-can-build.yml`: removed the meaningless `node-version` build matrix (there is no Node in this project)

## Build-verification procedure (required — not done in CI here)

A full Home Assistant build is large (hundreds of wheels, ffmpeg, etc.). Use LXD on the dev box:

```bash
# from the repo root, on the core26-capable build host
SNAPCRAFT_BUILD_ENVIRONMENT=lxd snapcraft --verbose
```

Checklist:

1. **Toolchain**: `snapcraft --version` supports `core26`; `core26` base snap installed (`snap install core26`).
2. **Python provisioning**: build finds `python3.14`. If it fails on a missing `python3.14*` package, uncomment the deadsnakes block in `snapcraft.yaml`.
3. **Patch applies**: the `patch -p1` step succeeds against the pinned HA tag (`version:` in `snapcraft.yaml`). It currently applies cleanly to `2026.6.4`. Patch drift risk is on *future HA bumps*, not on core26.
4. **Try dropping the interpreter hack**: delete the marked block in `override-build` (everything from `# look for a provisioned python interpreter` down to the `ln -sf …` line) and rebuild. Confirm:
   ```bash
   # inside the built snap / staged part
   $SNAP/bin/python3.14 --version
   $SNAP/bin/hass --version
   ```
   If both resolve, keep it deleted (KISS win). If not, restore the block.
5. **stage-packages parity on 26.04**: a renamed/removed lib fails the `Fetching stage-packages` step (or only surfaces at runtime). Known rename so far:
   - `libturbojpeg` → **`libturbojpeg0`** (noble/24.04 used the unsuffixed name; resolute/26.04 ships the SONAME-suffixed `libturbojpeg0`). Already applied.
   - Verified still valid on 26.04: `libglu1-mesa`, `libpcap0.8`(+`-dev`), `libpulse0`, `python3.14-venv`.
6. **Runtime smoke test**:
   ```bash
   sudo snap install ./home-assistant-snap_*.snap --dangerous
   snap run home-assistant-snap.check-config
   # then confirm the patch took effect:
   # Settings → System → Repairs → System information should show
   # installation_type: "Home Assistant Snap"
   ```
7. **Confinement**: `confinement: strict` still passes `diddlesnaps/snapcraft-review-action`.

## Follow-ups (not blockers)

- **Upstream `is_snap_env` to HA core.** The patch author (`ThyMYthOS` / Manuel Stahl) is already a reviewer on the auto-update workflow. Landing it upstream removes the patch entirely and kills the biggest per-release fragility.
- **Re-enable the `updater` component** (the part is commented out in `snapcraft.yaml` while `README.md` advertises `binary_sensor.updater`). Before shipping it, address the latent bugs noted in the audit (`Tracks.get_latest()` risk/name conflation, `get_risk()` str|int return, the `snap_rev[0] == 'x'` heuristic).
