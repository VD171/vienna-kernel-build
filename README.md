# vienna-kernel-build

🇬🇧 English · [🇧🇷 Português](README.pt-BR.md)

Reproducible **kernel build for the Motorola Edge 60 Neo** (`vienna`, MT6878 / Dimensity 7400)
on GitHub Actions, straight from Motorola's GPL release.

> ⚠️ **For most people, you do NOT need this to get root.** Rooting the Edge 60 Neo is done with
> **KernelSU LKM patched into `init_boot`**, which needs no kernel build at all. The default workflow
> here builds the **stock GKI kernel** (no KernelSU) and exists to prove the recipe is byte exact.
>
> 🆕 **Phase 2 (built-in root) works.** A second workflow builds **KernelSU-Next compiled into the
> kernel** (not an LKM), keeping the stock `Linux version` byte for byte. A built-in KSU kernel from
> this recipe **booted on a real device** and loaded every stock vendor module. The current variant
> (KernelSU-Next OFFICIAL, no SUSFS) builds and passes the pre-flash gate; device validation of that
> exact build is pending. See [Phase 2](#phase-2-built-in-ksu-next-the-part-that-took-the-most-work) below.

## Status

| What | Status |
|---|---|
| Stock `Image` builds | ✅ 34 MB, in **36 min** on a stock runner (2 cores, 7.8 GB RAM) |
| Stock `Linux version` | ✅ reproduced **byte for byte** vs the factory build |
| Device modules | ✅ **stock `vendor_dlkm` reused** (GKI/KMI, same vermagic); building them from source is blocked by the proprietary `vendor/mediatek`, and is not needed |
| Phase 2: a **built-in KSU** kernel boots | ✅ measured on device: booted to Android, **424 vendor modules loaded, 0 vermagic errors**, `lsmod` shows no kernelsu (it is built in, not an LKM) |
| Phase 2: **KSU-Next OFFICIAL, no SUSFS** | 🟡 builds, and passes the pre-flash gate (byte exact version, config matches the device). **Not yet validated on device** |
| Boots on device | ✅ validated on the maintainer's device (stock and Phase 2) |

## The one thing this repo is worth reading for

Motorola publishes a `MMI-<build>.txt` with defconfig, overlays and Bazel targets. **It is not a
complete procedure**: it documents the *device delta* and assumes a tree obtained with `repo`.
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

That is 18 projects, and `tools/bazel` + `WORKSPACE` come **ready**, with no symlink hacks needed.

### 🔑 `vendor/mediatek` does not block the GKI kernel

MediaTek's `WORKSPACE` declares `mgk_internal` / `mgk_ko` pointing at `../vendor/mediatek`, a
**proprietary tree** nobody publishes. Create it **empty** and the GKI target still builds. Only the
*device modules* are blocked.

## Phase 2: built-in KSU-Next (the part that took the most work)

Phase 1 is stock. Phase 2 compiles **KernelSU-Next OFFICIAL** (from `KernelSU-Next/KernelSU-Next`,
the rifsxd project) **into the kernel**, so `lsmod | grep kernelsu` is empty and the driver rides
inside `vmlinux`. Workflow: **`build-gki-ksu.yml`**. It keeps the byte exact stock `Linux version`
so the factory `vendor_dlkm` modules still load.

### 🪤 The trap that cost days: a booting `Image` is not a booting kernel

Every KSU + kernel build we made on the **MediaTek tree** compiled clean, reproduced the exact
`Linux version`, and then **panicked at the first `execve` of init**, in the page allocator
(`clear_page` hitting a poison address, deterministic). We proved it was **not** KSU, **not** SUSFS,
**not** the config, and **not** the page size, by bisecting:

| Build | KSU | SUSFS | Result |
|---|---|---|---|
| Phase 2 (full) | yes | yes | panic at init |
| minus manual hooks | yes | yes | **same** panic |
| stock, no KSU/SUSFS, MTK tree | no | no | **same** panic |

Same panic with zero KSU and zero SUSFS meant the cause was the **build tree**, not what we added.
The embedded `.config` of our `Image` matched the device's `/proc/config.gz` to ~100% (one
irrelevant symbol), so it was not the config either. The one non standard variable left was the
**MediaTek `WORKSPACE`** (`bazel_mgk_rules` overriding the AOSP one).

### ✅ The fix: build the pure AOSP GKI `common`, not the MTK tree

Check out `common` at the exact stock tag and build it with the **stock AOSP `WORKSPACE`**, target
`//common:kernel_aarch64_dist`:

```bash
cd common
git fetch --depth=1 https://android.googlesource.com/kernel/common refs/tags/android14-6.1-2025-07_r11
git checkout FETCH_HEAD   # SUBLEVEL=141, the stock kernel's exact point
```

The pure `common` **booted**. Then `common` + KSU-Next built-in **booted**, reached Android, and
**424 vendor modules loaded with 0 vermagic error**, which is the real KMI de-risk: the stock
`vendor_dlkm` accepts our kernel. Bonus: on this path the vermagic comes out naturally from
`git describe`, so the `.scmversion` hack the stock recipe needs is unnecessary.

### Why no SUSFS

The maintainer chose **no SUSFS**, on purpose. Rationale: keeping the stack **100% official** (the
KernelSU-Next glue for SUSFS lives only in third party forks, and the manager must stay aligned with
the driver on the latest release). Without SUSFS the build is pure official KSU-Next, and the app
level hiding it would add is largely moot anyway, because SELinux already denies `untrusted_app`
access to `/proc/modules`. Runtime hiding is handled in userspace instead.

### 🤖 Autobuild

`ksun-autobuild.yml` runs daily. When KernelSU-Next publishes a new release it bumps the pinned ref
and rebuilds the built-in kernel automatically (artifact only, it never flashes anything).

## What is in here

| Path | What |
|---|---|
| `.github/workflows/` | the builds: stock, and KernelSU-Next OFFICIAL built in (plus the autobuild) |
| [`flash-recipe/`](flash-recipe/) | **how to actually flash a custom kernel on this device.** `fastboot boot` does not exist here and `flash boot` is preflash checked against the on-device vbmeta, so it takes a surgical vbmeta patch. Read its README before running it |
| [`tools/check-gate.py`](tools/check-gate.py) | prove a built `Image` agrees with the device (version string, embedded config vs `/proc/config.gz`, KSU/SUSFS markers) **before** you flash it |
| [`tools/mtk-logo.py`](tools/mtk-logo.py) | unpack/repack the MediaTek boot `logo.img`, leaving Motorola's signature blocks intact |
| [`device/`](device/) | **measured facts about the device**: the stock kernel config from `/proc/config.gz` (the reference `check-gate.py` compares against), the redacted `fastboot getvar all`, and the `logo.img` format |

The **kernel sources themselves** are mirrored, extracted and browsable, one branch per build tag, in
**[VD171/vienna-kernel-source](https://github.com/VD171/vienna-kernel-source)**. Diffing two branches
there shows what Motorola changed between two ROM releases.

## Usage

Actions → **build vienna kernel** → *Run workflow*. Inputs: MMI tag, manifest branch, Bazel target.
The `Image` comes out as an artifact.

## Published kernel sources (catalogue)

Every **vienna** tag Motorola has released so far, newest first. `kernel-mtk` and
`kernel-kernel_device_modules-6.1` use the **same tag names**, so one lookup serves both.

| Tag | Android | Notes |
|---|---|---|
| [`MMI-W1UIS36H.39-17-8`](https://github.com/MotorolaMobilityLLC/kernel-mtk/releases/tag/MMI-W1UIS36H.39-17-8) | 16 | **current**: what this workflow builds |
| [`MMI-V2UIS35.43-12-4-1`](https://github.com/MotorolaMobilityLLC/kernel-mtk/releases/tag/MMI-V2UIS35.43-12-4-1) | 15 |  |
| [`MMI-V1UIS35H.11-39-28-5`](https://github.com/MotorolaMobilityLLC/kernel-mtk/releases/tag/MMI-V1UIS35H.11-39-28-5) | 15 |  |
| [`MMI-V1UIS35H.11-39-16-5`](https://github.com/MotorolaMobilityLLC/kernel-mtk/releases/tag/MMI-V1UIS35H.11-39-16-5) | 15 |  |
| [`MMI-V1UIS35H.11-39-16-2`](https://github.com/MotorolaMobilityLLC/kernel-mtk/releases/tag/MMI-V1UIS35H.11-39-16-2) | 15 |  |
| [`MMI-V1UI35H.11-39-16`](https://github.com/MotorolaMobilityLLC/kernel-mtk/releases/tag/MMI-V1UI35H.11-39-16) | 15 |  |
| [`MMI-U4UI34.8-28-1`](https://github.com/MotorolaMobilityLLC/kernel-mtk/releases/tag/MMI-U4UI34.8-28-1) | 14 |  |
| [`MMI-U4UI34.8-22-7`](https://github.com/MotorolaMobilityLLC/kernel-mtk/releases/tag/MMI-U4UI34.8-22-7) | 14 |  |

> 💡 Each of these is a tarball. The same sources **extracted into git**, one branch per tag, are at
> [VD171/vienna-kernel-source](https://github.com/VD171/vienna-kernel-source), where you can grep them
> and diff one release against another.

Note the device token **`UI`** in every Build ID: that is what identifies the platform, and it is
why searching for "XT2509" finds nothing.

**Yours missing?** Open an issue at
[MotorolaMobilityLLC/kernel-mtk](https://github.com/MotorolaMobilityLLC/kernel-mtk/issues) with your
**Build ID** and **Build fingerprint** (one build per issue). Mine was answered in **2 days**.
This list is kept updated as new tags appear.

## Links

| Where | What |
|---|---|
| 💬 [t.me/Edge60Neo](https://t.me/Edge60Neo) | Telegram, Edge 60 Neo |
| 💬 [t.me/MotorolaEdge60Neo](https://t.me/MotorolaEdge60Neo) | Telegram, Motorola Edge 60 Neo |
| 💬 [t.me/Motorola_Edge_60_Neo](https://t.me/Motorola_Edge_60_Neo) | Telegram, Motorola Edge 60 Neo |
| 🧵 [XDA thread](https://xdaforums.com/t/guide-rooting-how-to-root-motorola-60-edge-neo-5g-xt2509-1-vienna.4798267/) | `[GUIDE][ROOTING]` XT2509-1 (vienna) |
| 🛠 [VD171/vienna-kernel-build](https://github.com/VD171/vienna-kernel-build) | this repo |
| 📦 [VD171/vienna-kernel-source](https://github.com/VD171/vienna-kernel-source) | the kernel sources, extracted, one branch per tag |
| 🐧 [MotorolaMobilityLLC, `MMI-W1UIS36H.39-17-8`](https://github.com/MotorolaMobilityLLC/kernel-mtk/releases/tag/MMI-W1UIS36H.39-17-8) | Motorola's own GPL source release for this build |
| 💾 [stockrom.net, Edge 60 Neo 5G](https://www.stockrom.net/category/motorola/edge-60-neo-5g) | stock firmware packages, useful if you need a full ROM rather than single partitions |

## License

[MIT](LICENSE). This repo only **automates** assembling and building.
The kernel sources are **GPL-2.0**, from [MotorolaMobilityLLC](https://github.com/MotorolaMobilityLLC),
and are neither redistributed nor relicensed here.

## Contact

| Channel | Address |
|---|---|
| Telegram | [@VD_Priv8](https://t.me/VD_Priv8) |
| E-mail | `vd.priv8 [at] pm.me` |
| XDA | [VD171](https://xdaforums.com/m/vd171.4699873/) |
| GitHub | [VD171](https://github.com/VD171) |
