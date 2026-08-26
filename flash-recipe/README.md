# Flashing a custom kernel on the Edge 60 Neo (`vienna`)

> ⚠️ **Read this whole file first.** This is a record of what worked on **my** device, not a
> one-click tool. It writes to `vbmeta` and `boot`. If you flash the wrong thing you get a
> bootloop, and you recover with `fastboot` and the stock images (grab them from the
> [stock release](https://github.com/VD171/vienna-kernel-build/releases)). Keep a copy of your own
> stock `boot` and `vbmeta` **before** you start. Your bootloader must be unlocked.
> It never touches `lk`, which is the partition that actually bricks this device.

## The problem

You built a kernel. You cannot flash it:

| What you try | What happens |
|---|---|
| `fastboot boot boot.img` | **the command does not exist** on this bootloader |
| `fastboot flash boot boot.img` | **refused at preflash** |
| pad the image to the exact partition size, retry | still refused |
| `fastboot --disable-verification flash vbmeta` | writes, `boot` still refused |
| flash a minimal vbmeta (boot descriptor only) | flashes, then **"cannot load android system / data corrupt"** |

The preflash check compares your image against the `boot` **hash descriptor of the vbmeta already on
the device**. It is not checking the size, and `--disable-verification` does not turn it off. It is
checking the hash, against a copy of the truth that lives on the phone.

The minimal vbmeta fails for a different reason: `fs_mgr` needs the **hashtree** descriptors for
`system` / `vendor` / `product` / `vendor_dlkm` / `system_dlkm`. Drop them and the system will not
mount, even though `boot` was accepted.

## What works

Give the device a **complete** vbmeta, every stock descriptor intact, with **only** the `boot`
descriptor updated to describe your image.

```bash
# 1. boot.img (header v4) + AVB footer sized for the real 64 MiB partition
./make-boot.sh Image.gz vbmeta_stock.img out/

# 2. splice your image's size and digest into the stock vbmeta, touching nothing else
python3 patch-vbmeta.py vbmeta_stock.img out/boot-raw.img out/vbmeta-new.img

# 3. flash, vbmeta first
fastboot flash vbmeta out/vbmeta-new.img
fastboot flash boot   out/boot-new.img
```

Note step 2 hashes `boot-raw.img`, the image **before** the footer is added. The AVB hash covers the
image, not the footer.

The patched vbmeta's signature is now invalid. That is expected: on an unlocked (orange) bootloader
AVB reports but does not enforce, so it boots. On a locked device none of this applies, and you
should not be here.

## Things that cost me time

- **`init_boot` is not preflash checked**, only `boot` is. That is why LKM root (which patches
  `init_boot`) works with no vbmeta surgery at all. If you only want root, you do not need any of
  this: patch `init_boot` with the KernelSU manager and stop reading.
- **A booting `Image` is not a booting kernel.** See the
  [main README](../README.md#phase-2-built-in-ksu-next-the-part-that-took-the-most-work) for the
  build tree that compiled clean, reproduced the exact version string, and panicked at init anyway.
- **"It booted" can be a lie.** If the flash silently failed, the device reboots into the stock
  kernel and looks perfectly healthy. Verify what is actually running (`uname -r`, and whether
  KernelSU is a module or built in) instead of trusting that the screen came up.
- **`fastboot getvar securestate`** is the real answer for the lock state. `getprop` values can be
  spoofed at runtime and tell you what the userspace wants you to hear.
