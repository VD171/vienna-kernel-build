#!/usr/bin/env bash
#
# gen-changelog.sh - regenerate CHANGELOG.md from the root-lkm-* GitHub releases.
#
# The CHANGELOG is fully derivable from the releases, so it is rebuilt from
# scratch on every run instead of appended to: one line per root-lkm-* release,
# most recent on top. Every field comes from the release itself, which keeps the
# releases the single source of truth:
#
#   identifier (bold)  <- the tag versionCode, else the body "driver `<n>`",
#                         else the KSU-Next version in the body
#   ROM                <- the tag  (root-lkm-<versionCode>-MMI-<rom>)
#   date               <- published_at
#   KSU-Next ref       <- the release body: a dev commit ("(commit `<hex>`)") on
#                         modern builds, or the KSU-Next version on the earliest
#                         releases that predate the commit-in-body convention
#   (current) marker   <- the release flagged "latest" on GitHub
#
# The single release currently flagged latest is marked (current); every other
# entry is left plain, so the marker self-heals whenever a release is published
# or the latest flag is moved.
#
# Deterministic and idempotent: same releases -> byte-identical output.
#
# Usage: gen-changelog.sh [output-file]   (default: CHANGELOG.md)
# Env:   REPO (default VD171/vienna-kernel-build), GH_TOKEN for gh.

set -euo pipefail

REPO="${REPO:-VD171/vienna-kernel-build}"
OUT="${1:-CHANGELOG.md}"
# Field separator: US (0x1f), a non-whitespace control char. A whitespace IFS
# (tab/space) makes `read` collapse runs of separators and drop empty fields,
# which shifts every column right when a release has no commit/driver; US does
# not. No captured token (tag/date/hex/version/digits) ever contains it.
US="$(printf '\037')"

# The release currently flagged latest on GitHub; only a root-lkm-* tag is
# eligible for the (current) marker (the repo also holds stock-* releases).
latest_tag="$(gh api "repos/$REPO/releases/latest" --jq '.tag_name' 2>/dev/null || true)"
case "$latest_tag" in root-lkm-*) ;; *) latest_tag="" ;; esac

# tag <tab> published_at <tab> commit <tab> ksu_version <tab> driver, for every
# root-lkm-* release. Missing fields come back empty and are handled below.
records="$(gh api --paginate "repos/$REPO/releases" --jq '
  .[]
  | select(.tag_name | startswith("root-lkm-"))
  | [ .tag_name,
      .published_at,
      ((.body // "") | (capture("commit `(?<c>[0-9a-f]{7,40})`") // {c:""}).c),
      ((.body // "") | (capture("KernelSU[-_ ]Next[-_ ]v?(?<v>[0-9]+(\\.[0-9]+)+)") // {v:""}).v),
      ((.body // "") | (capture("driver `(?<d>[0-9]+)`") // {d:""}).d)
    ] | map(tostring) | join("\u001f")')"

tmp="$(mktemp)"; trap 'rm -f "$tmp"' EXIT
{
  printf '# Changelog - vienna-kernel-build (root-lkm)\n\n'
  printf 'One entry per auto-published LKM release, most recent on top. Each entry links its GitHub release and its tag. The release currently flagged latest on GitHub is marked **(current)**.\n\n'

  # Newest first (ISO-8601 timestamps sort lexically).
  printf '%s\n' "$records" | sort -t "$US" -k2,2r | while IFS="$US" read -r tag pub commit ksuver driver; do
    [ -n "$tag" ] || continue
    rest="${tag#root-lkm-}"
    case "$rest" in
      *-MMI-*) vc="${rest%%-MMI-*}"; rom="${rest#*-MMI-}" ;;
      MMI-*)   vc="";               rom="${rest#MMI-}"    ;;
      *)       vc="$rest";          rom=""                ;;
    esac
    case "$vc" in ''|*[!0-9]*) vc="" ;; esac   # keep vc only when it is the numeric versionCode

    # Leading identifier: versionCode, else driver number, else KSU-Next version.
    ident="$vc"; [ -n "$ident" ] || ident="$driver"; [ -n "$ident" ] || ident="$ksuver"
    [ -n "$ident" ] || ident="$tag"

    # KSU-Next reference: a dev commit when present, otherwise the version (but
    # not when it would just repeat the leading identifier).
    if [ -n "$commit" ]; then
      ksu=" - KSU-Next commit \`$commit\`"
    elif [ -n "$ksuver" ] && [ "$ksuver" != "$ident" ]; then
      ksu=" - KSU-Next \`$ksuver\`"
    else
      ksu=""
    fi

    rompart=""; [ -n "$rom" ] && rompart=" - ROM $rom"
    mark=""; [ "$tag" = "$latest_tag" ] && mark=" (current)"
    date="$(date -u -d "$pub" '+%Y-%m-%d %H:%M UTC')"

    printf -- '- **%s** - %s%s%s%s - [release](https://github.com/%s/releases/tag/%s) - [tag](https://github.com/%s/tree/%s)\n' \
      "$ident" "$date" "$rompart" "$mark" "$ksu" "$REPO" "$tag" "$REPO" "$tag"
  done
} > "$tmp"

mv "$tmp" "$OUT"
trap - EXIT
