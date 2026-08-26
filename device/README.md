# Measured facts about this device

Things that are true of the Motorola Edge 60 Neo (`vienna`, XT2509-1) on build
`W1UIS36H.39-17-8`, taken off the device itself rather than copied from a spec sheet. Everything
here is unit agnostic: serial, IMEI, eSIM id, `uid`, `chipid` and the board part number are
redacted, because those identify one phone and nothing here needs them.

| File | What it is | Why you may want it |
|---|---|---|
| [`kernel-config-stock--W1UIS36H.39-17-8.txt`](kernel-config-stock--W1UIS36H.39-17-8.txt) | the **running** kernel config, from `/proc/config.gz` on the stock kernel (7550 lines) | this is the config that is known to boot on this hardware. It is also the reference input for [`../tools/check-gate.py`](../tools/check-gate.py), so you can check a kernel you built **without** already having root on the device |
| [`fastboot-getvar--vienna.txt`](fastboot-getvar--vienna.txt) | full `fastboot getvar all`, redacted | UFS and RAM parts, `MT6878`, panel and slot layout, baseband, bootloader version, `securestate` semantics |
| [`logo-format.md`](logo-format.md) | the `logo.img` container, reverse engineered | if you want to change the boot logo without touching `lk` |
| [`props/`](props/) | the `build.prop` / `prop.default` from init_boot and vendor_boot, as plain text | build fingerprints, ids, vendor and RIL config; good for searching, no device identity |

## The one that matters most

The stock kernel config is the thing people usually cannot get, and it is what turns "my build
compiles" into "my build agrees with the device". A kernel that differs from it in a single memory
management symbol will compile perfectly and then panic at init. That happened here, repeatedly,
and comparing against this file is how it was ruled out. See the
[main README](../README.md#phase-2-built-in-ksu-next-the-part-that-took-the-most-work).
