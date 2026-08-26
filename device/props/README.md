# `prop.default` / `build.prop` from this device's boot partitions

Extracted from the stock partitions of the Motorola Edge 60 Neo (`vienna`, XT2509-1),
build `W1UIS36H.39-17-8`. Plain text on purpose, so search engines and GitHub code search
index them. Nothing here is device specific: no serial, IMEI, eSIM id, MAC or unlock code.
The only id present is `ro.mot.build.guid`, which is a per **build** value baked into the
firmware image, identical on every unit of this build.

| File | Source | Notes |
|---|---|---|
| [`bootimage--W1UIS36H.39-17-8--build.prop`](bootimage--W1UIS36H.39-17-8--build.prop) | `system/etc/ramdisk/build.prop` inside `init_boot` (and `boot`) | 🪤 identifies itself as `ro.bootimage.build.id=W1UIS36`**`M`**`.39-17-8` (with **M**, not the **H** of the overall build) and `ro.product.bootimage.model=motorola edge 50 neo`, the shared codename written into the partition |
| [`vendor_boot-ramdisk--W1UIS36H.39-17-8--prop.default`](vendor_boot-ramdisk--W1UIS36H.39-17-8--prop.default) | the normal vendor ramdisk (`ramdisk_`) of `vendor_boot` | the vendor `prop.default`, `vienna_g_hal` |
| [`vendor_boot-recovery-ramdisk--W1UIS36H.39-17-8--prop.default`](vendor_boot-recovery-ramdisk--W1UIS36H.39-17-8--prop.default) | the recovery vendor ramdisk (`ramdisk_recovery`) of `vendor_boot` | the recovery `prop.default`, `vienna_g_vext` |

The KernelSU LKM patch does not touch `build.prop`: the stock and patched ramdisk carry the
same one. These are firmware facts, redistributed to help identify and work with this build.
