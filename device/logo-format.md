# The MediaTek `logo.img` container, as it is on `vienna`

Reverse engineered from the stock `logo` partition of the Motorola Edge 60 Neo, build
`W1UIS36H.39-17-8`. [`../tools/mtk-logo.py`](../tools/mtk-logo.py) implements it.

## Container

A sequence of blocks. Each block starts with a **512 byte MTK header**: magic `0x58881688`
(little endian, so `88 16 88 58` on disk) followed by the block name.

On this device there are **9 blocks**, in this order:

```
logo1  cert1  cert2
logo2  cert1  cert2
logo3  cert1  cert2
```

The `cert*` blocks are **Motorola's signature material**. A tool that repacks this file must pass
them through **untouched**, byte for byte.

## Body of a `logoN` block

```
uint32   blocknum              number of images in this block
uint32   total                 total size of the body
uint32   offsets[blocknum]     offset of each image, relative to the start of the body
bytes    zlib streams          one per image, in order
```

Each image decompresses to raw **RGBA8888**, at the panel's width by height.

## 🪤 The alignment that is easy to miss

Every block is padded with `0x00` up to the next **16 byte** boundary. This was measured on the
original file, where the gaps are 13, 7, 3, 12 and so on, rather than assumed from the format.

Repacking without honouring that alignment produces a file that parsers still read back correctly,
which is exactly why it is a trap: it looks fine, and whether the bootloader still accepts it is
unproven. Keep the alignment.

## Why you would touch this

Replacing the images is the cosmetic way to deal with the unlocked bootloader warning screen. It
does **not** require touching `lk`, and you should not touch `lk` on this device: a bad `lk` bricks
it, and there is no BROM recovery path.

The stock `logo` partition image is published in the
[stock images release](https://github.com/VD171/vienna-kernel-build/releases/tag/stock-MMI-W1UIS36H.39-17-8),
so you can extract your own frames with the tool rather than getting them from anyone.
