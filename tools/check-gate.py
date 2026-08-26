#!/usr/bin/env python3
"""Prove a built kernel Image matches the device it is meant for, BEFORE flashing it.

Three questions, answered from the binary itself instead of from hope:

  1. Is the `Linux version` string byte for byte what the stock kernel reports?
  2. Is the config compiled into the Image the same config the device is running?
  3. Which markers are actually in there (KernelSU built in? SUSFS? neither?)

(2) is the one that matters. The Image embeds its own config (CONFIG_IKCONFIG), and the
device hands you its running config from /proc/config.gz. Comparing the two is the only
honest way to know the thing you built is the thing the device wants. A build that
differs in one memory management symbol will compile fine and panic at init.

  # on the device
  adb shell 'zcat /proc/config.gz' > device-config.txt
  # or, if you rooted it and adb is off, over ssh

  ./check-gate.py Image device-config.txt

Anything reported under "unexpected" is a reason not to flash.
"""
import argparse
import gzip
import io
import re
import sys
import zlib

EXPECTED_PREFIXES = ("CONFIG_KSU", "CONFIG_KSU_SUSFS")


def embedded_config(path):
    """Pull the IKCONFIG blob out of a kernel Image by scanning for gzip streams."""
    blob = open(path, "rb").read()
    start = 0
    while True:
        i = blob.find(b"\x1f\x8b\x08", start)
        if i < 0:
            return None
        try:
            text = zlib.decompressobj(31).decompress(blob[i:]).decode("utf-8", "replace")
            if "CONFIG_" in text and "\n" in text:
                return text
        except Exception:
            pass
        start = i + 3


def parse(text):
    out = {}
    for line in text.splitlines():
        m = re.match(r"(CONFIG_\w+)=(.*)", line)
        if m:
            out[m.group(1)] = m.group(2)
            continue
        m = re.match(r"# (CONFIG_\w+) is not set", line)
        if m:
            out[m.group(1)] = "<not set>"
    return out


def version_string(path):
    blob = open(path, "rb").read()
    m = re.search(rb"Linux version [\x20-\x7e]{20,300}", blob)
    return m.group(0).decode() if m else None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", help="the built kernel Image (uncompressed)")
    ap.add_argument("device_config", help="the device's config, from /proc/config.gz")
    ap.add_argument("--expect-version", help="fail unless the version string equals this exactly")
    args = ap.parse_args()

    failures = []

    print("== Linux version ==")
    ver = version_string(args.image)
    print(f"  {ver}")
    if args.expect_version:
        if ver == args.expect_version:
            print("  matches --expect-version exactly")
        else:
            failures.append("version string does not match --expect-version")

    print("\n== markers ==")
    blob = open(args.image, "rb").read()
    for name, needle in (("KernelSU", b"KernelSU"), ("SUSFS", b"susfs")):
        print(f"  {name:9}: {'present' if needle in blob else 'absent'}")

    print("\n== config: Image vs device ==")
    raw = embedded_config(args.image)
    if raw is None:
        print("  no embedded config found (CONFIG_IKCONFIG not enabled?)")
        sys.exit(2)
    ours = parse(raw)
    theirs = parse(open(args.device_config, encoding="utf-8", errors="replace").read())
    print(f"  Image: {len(ours)} symbols | device: {len(theirs)} symbols")

    diffs = [(k, theirs.get(k, "<absent>"), ours.get(k, "<absent>"))
             for k in sorted(set(ours) | set(theirs))
             if ours.get(k, "<absent>") != theirs.get(k, "<absent>")]
    expected = [d for d in diffs if d[0].startswith(EXPECTED_PREFIXES)]
    unexpected = [d for d in diffs if d not in expected]

    print(f"  total diffs: {len(diffs)} | expected (KSU/SUSFS): {len(expected)} | "
          f"unexpected: {len(unexpected)}")

    if expected:
        print("\n  expected, these are what you added:")
        for k, dev, our in expected:
            print(f"    {k}: device={dev} | image={our}")
    if unexpected:
        failures.append(f"{len(unexpected)} config symbols differ from the device")
        print("\n  UNEXPECTED, do not flash until you understand these:")
        for k, dev, our in unexpected:
            print(f"    {k}: device={dev} | image={our}")

    print()
    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        sys.exit(1)
    print("PASS: the Image agrees with the device")


if __name__ == "__main__":
    main()
