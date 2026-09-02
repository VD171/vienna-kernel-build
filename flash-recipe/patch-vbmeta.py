#!/usr/bin/env python3
"""Surgically swap the `boot` hash descriptor inside a stock vbmeta image.

Why this exists
---------------
On the Motorola Edge 60 Neo (`vienna`) you cannot just flash a custom boot image:

  * `fastboot boot` (boot from RAM) does not exist on this bootloader;
  * `fastboot flash boot` runs a PREFLASH check that compares the image against the
    `boot` hash descriptor of the vbmeta ALREADY ON THE DEVICE, and refuses on mismatch;
  * `fastboot --disable-verification flash vbmeta` writes, but `boot` stays refused;
  * a MINIMAL vbmeta (only the boot descriptor) flashes, but then the device says
    "cannot load android system / data corrupt", because fs_mgr needs the hashtree
    descriptors for system/vendor/product/... that you just dropped.

So the only thing that works is a COMPLETE vbmeta (every stock descriptor intact) with
ONLY the `boot` descriptor updated. That is what this script does. The AVB signature
becomes invalid, which is fine on an unlocked (orange) bootloader: AVB does not enforce.

What it changes
---------------
Inside the `boot` hash descriptor, only two fixed-length fields:
  * image_size (8 bytes, big endian)
  * digest     (digest_len bytes)
The salt is left untouched, so lengths never move. Feed `make-boot.sh` the same salt
(it reads it from here with --print-salt) and the digest is the only real change.

Usage
-----
  ./patch-vbmeta.py --print-salt  vbmeta_stock.img
  ./patch-vbmeta.py vbmeta_stock.img boot-new.img vbmeta-patched.img
"""
import argparse
import hashlib
import struct
import sys

AVB_MAGIC = b"AVB0"
HEADER_SIZE = 256
TAG_HASH_DESCRIPTOR = 2


def _read_header(blob):
    if blob[:4] != AVB_MAGIC:
        sys.exit("not an AVB vbmeta image (bad magic)")
    # AvbVBMetaImageHeader (big-endian), fixed offsets in the 256-byte header:
    #   +12 authentication_data_block_size (u64)
    #   +20 auxiliary_data_block_size      (u64)
    #   +96 descriptors_offset             (u64, relative to the start of the aux block)
    #  +104 descriptors_size               (u64)
    # (fix 2026-09-02: liam-se auth/aux em 24/32 -> nunca se achava o descritor.)
    auth_size = struct.unpack_from(">Q", blob, 12)[0]
    aux_size = struct.unpack_from(">Q", blob, 20)[0]
    desc_off = struct.unpack_from(">Q", blob, 96)[0]
    desc_size = struct.unpack_from(">Q", blob, 104)[0]
    return auth_size, aux_size, desc_off, desc_size


def find_boot_descriptor(blob, partition=b"boot"):
    """Return (abs_offset_of_payload, parsed fields) for the hash descriptor of `partition`."""
    auth_size, aux_size, desc_off, desc_size = _read_header(blob)
    off = HEADER_SIZE + auth_size + desc_off
    end = off + desc_size
    while off < end:
        tag, num_following = struct.unpack_from(">QQ", blob, off)
        payload = off + 16
        if tag == TAG_HASH_DESCRIPTOR:
            image_size = struct.unpack_from(">Q", blob, payload)[0]
            hash_algo = blob[payload + 8:payload + 40].rstrip(b"\0")
            name_len, salt_len, digest_len = struct.unpack_from(">III", blob, payload + 40)
            strings = payload + 116  # +8(image_size)+32(hash_algo)+12(3xu32)+4(flags)+60(reserved)
            name = blob[strings:strings + name_len]
            salt = blob[strings + name_len:strings + name_len + salt_len]
            digest_off = strings + name_len + salt_len
            digest = blob[digest_off:digest_off + digest_len]
            if name == partition:
                return {
                    "image_size_off": payload,
                    "image_size": image_size,
                    "hash_algo": hash_algo.decode(),
                    "salt": salt,
                    "digest_off": digest_off,
                    "digest_len": digest_len,
                    "digest": digest,
                }
        off = payload + num_following
    sys.exit(f"no hash descriptor for partition {partition.decode()!r} in this vbmeta")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("vbmeta_stock")
    ap.add_argument("boot_new", nargs="?")
    ap.add_argument("vbmeta_out", nargs="?")
    ap.add_argument("--print-salt", action="store_true",
                    help="print the stock boot salt (hex) and exit; feed it to make-boot.sh")
    args = ap.parse_args()

    blob = bytearray(open(args.vbmeta_stock, "rb").read())
    d = find_boot_descriptor(blob)

    if args.print_salt:
        print(d["salt"].hex())
        return

    if not (args.boot_new and args.vbmeta_out):
        ap.error("boot_new and vbmeta_out are required unless --print-salt is used")

    new_img = open(args.boot_new, "rb").read()
    # add_hash_footer appends a footer; the hash covers only the original image bytes.
    # Trust the caller: pass the image BEFORE the footer, or pass image_size explicitly.
    algo = d["hash_algo"] or "sha256"
    h = hashlib.new(algo)
    h.update(d["salt"])
    h.update(new_img)
    new_digest = h.digest()

    if len(new_digest) != d["digest_len"]:
        sys.exit(f"digest length mismatch: stock={d['digest_len']} new={len(new_digest)}")

    print(f"partition   : boot")
    print(f"hash algo   : {algo}")
    print(f"image_size  : {d['image_size']} -> {len(new_img)}")
    print(f"digest      : {d['digest'].hex()[:24]}... -> {new_digest.hex()[:24]}...")
    print(f"salt        : unchanged ({len(d['salt'])} bytes)")

    struct.pack_into(">Q", blob, d["image_size_off"], len(new_img))
    blob[d["digest_off"]:d["digest_off"] + d["digest_len"]] = new_digest

    open(args.vbmeta_out, "wb").write(blob)
    print(f"\nwrote {args.vbmeta_out} ({len(blob)} bytes, all other descriptors untouched)")
    print("the AVB signature is now invalid; that is expected and fine on an unlocked bootloader")


if __name__ == "__main__":
    main()
