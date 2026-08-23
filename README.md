# vienna-kernel-build

🇬🇧 English · [🇧🇷 Português](README.pt-BR.md)

Reproducible **kernel build for the Motorola Edge 60 Neo** (`vienna`, MT6878 / Dimensity 7400)
on GitHub Actions, straight from Motorola's GPL release.

> ⚠️ **This does NOT give you root.** It builds the **stock GKI kernel** from source. There is no
> KernelSU in it. It exists to prove the build recipe works — rooting the Edge 60 Neo is done with
> **LKM patched into `init_boot`**, which needs no kernel build at all.

## Status

| | |
|---|---|
| `Image` builds | ✅ 34 MB, in **36 min** on a stock runner (2 cores, 7.8 GB RAM) |
| Device modules | ❌ blocked by MediaTek's proprietary `vendor/mediatek` |
| Boots on device | ❓ **never tested** — a built `Image` proves the recipe, not the boot |

## The one thing this repo is worth reading for

Motorola publishes a `MMI-<build>.txt` with defconfig, overlays and Bazel targets. **It is not a
complete procedure** — it documents the *device delta* and assumes a tree obtained with `repo`.
Two things it never says:

1. where `build/kernel` and `build/bazel_mgk_rules` come from, and
2. **at which revision**.

### 🪤 The trap that costs days

**Do not `git clone` `build/kernel` at its default branch.**

| `build/kernel` at | Kleaf style | `external/` repos required |
|---|---|---|
| `main-kernel-build-2023` (what the manifest pins) | `WORKSPACE` | **0** |
| default / HEAD | `bzlmod` (Bazel 8) | **32** |

Cloning HEAD makes Bazel demand ~32 repositories that **are not actually missing**. The symptom is
`"repository X not found"`, one at a time, which sends you hunting the wrong thing. The cause is the
**revision**.

➜ The fix is to let the manifest pin everything:

```bash
repo init -u https://android.googlesource.com/kernel/manifest -b common-android14-6.1 --depth=1
repo sync -c -j$(nproc)
```

That is 18 projects, and `tools/bazel` + `WORKSPACE` come **ready** — no symlink hacks needed.

### 🔑 `vendor/mediatek` does not block the GKI kernel

MediaTek's `WORKSPACE` declares `mgk_internal` / `mgk_ko` pointing at `../vendor/mediatek`, a
**proprietary tree** nobody publishes. Create it **empty** and the GKI target still builds. Only the
*device modules* are blocked.

## Usage

Actions → **build vienna kernel** → *Run workflow*. Inputs: MMI tag, manifest branch, Bazel target.
The `Image` comes out as an artifact.

## Credits & license

Kernel sources: [MotorolaMobilityLLC](https://github.com/MotorolaMobilityLLC) (GPL-2.0).
This repo only automates assembling and building them.
