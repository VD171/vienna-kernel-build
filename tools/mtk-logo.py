#!/usr/bin/env python3
"""Unpack and repack the MediaTek `logo.img` of the Motorola Edge 60 Neo (`vienna`).

This is the boot logo container. Replacing the images inside it is how you deal with the
unlocked-bootloader warning screen cosmetically, without touching `lk` (which is the
partition that bricks this device, so do not touch `lk`).

  ./mtk-logo.py unpack logo.img out/     # PNG per image + a manifest
  ./mtk-logo.py pack   out/ logo-new.img # back into a flashable container

Structure, measured on this device rather than assumed:

  * N blocks, each with a 512 byte MTK header (magic 0x58881688 + name). `vienna` has 9:
    logo1/cert1/cert2, logo2/cert1/cert2, logo3/cert1/cert2. The `cert*` blocks are
    Motorola's signature and are passed through UNTOUCHED.
  * A `logoN` body is: uint32 blocknum, uint32 total, uint32 offsets[blocknum] (relative
    to the body start), then one zlib stream per image (RGBA8888, panel width x height).
  * Every block is padded with 0x00 to the next 16 BYTE boundary. This was measured on the
    original (gaps of 13, 7, 3, 12...). Repacking without that alignment produces a file
    the parser reads back fine, but whose fidelity to what `lk` expects is unproven.

The original Portuguese notes are kept below.
"""

# Notas originais (pt-BR):
# Desempacota e reempacota o `logo.img` da MediaTek — Motorola Edge 60 Neo (`vienna`).
# 
# O container tem N blocos, cada um com um cabecalho MTK de 512 bytes
# (magic 0x58881688 + nome). No `vienna` sao 9: logo1/cert1/cert2, logo2/cert1/cert2,
# logo3/cert1/cert2 — os `cert*` sao a assinatura da Motorola e passam INTACTOS.
# 
# Corpo de um bloco `logoN`:
#     uint32 blocknum
#     uint32 total
#     uint32 offsets[blocknum]     (relativos ao inicio do corpo)
#     streams zlib, um por imagem  (RGBA8888, largura x altura do painel)
# 
# Cada bloco e seguido de padding 0x00 ate a proxima fronteira de 16 BYTES — medido no
# original (folgas de 13, 7, 3, 12...). Reempacotar sem esse alinhamento gera um arquivo
# que o parser le, mas cuja fidelidade ao que o `lk` espera nao esta provada.
# 
# Doc do assunto: Backups/Fedora/Claude/Docs/MotorolaEdge60Neo5G/MOTOROLA_EDGE_60_NEO.md §9.2

import argparse, json, pathlib, struct, sys, zlib

MTK_MAGIC = b"\x88\x16\x88\x58"
CAB = 512


def blocos(d):
    """Lista (nome, offset_do_cabecalho, tamanho_do_corpo) na ordem do arquivo."""
    fora, i = [], 0
    while True:
        i = d.find(MTK_MAGIC, i)
        if i < 0:
            return fora
        size, = struct.unpack_from("<I", d, i + 4)
        nome = d[i + 8:i + 40].split(b"\0")[0].decode("ascii", "replace")
        fora.append((nome, i, size))
        i += 4


def desempacotar(img, destino, largura):
    from PIL import Image
    d = img.read_bytes()
    destino.mkdir(parents=True, exist_ok=True)
    mapa = {"origem": img.name, "bytes": len(d), "largura": largura, "blocos": []}
    for nome, off, size in blocos(d):
        corpo = off + CAB
        if not nome.startswith("logo"):
            # cert1/cert2: guardar cru, e reempacotar sem tocar
            (destino / f"{nome}@{off:08x}.bin").write_bytes(d[off:corpo + size])
            mapa["blocos"].append({"nome": nome, "off": off, "size": size, "tipo": "cru"})
            continue
        blocknum, total = struct.unpack_from("<II", d, corpo)
        offs = list(struct.unpack_from(f"<{blocknum}I", d, corpo + 8))
        b = {"nome": nome, "off": off, "size": size, "tipo": "logo",
             "blocknum": blocknum, "total": total, "imagens": []}
        for k, o in enumerate(offs):
            fim = corpo + (offs[k + 1] if k + 1 < blocknum else total)
            raw = zlib.decompress(d[corpo + o:fim])
            px = len(raw) // 4
            alt = px // largura if px % largura == 0 else 0
            nomef = f"{nome}--{k:02d}.png" if alt else f"{nome}--{k:02d}.bin"
            if alt:
                Image.frombytes("RGBA", (largura, alt), raw).save(destino / nomef)
            else:                       # nao e do painel inteiro: sai cru
                (destino / nomef).write_bytes(raw)
            b["imagens"].append({"i": k, "arquivo": nomef, "bytes": len(raw),
                                 "w": largura if alt else None, "h": alt or None})
        mapa["blocos"].append(b)
    (destino / "logo.json").write_text(json.dumps(mapa, indent=2, ensure_ascii=False))
    n = sum(len(b.get("imagens", [])) for b in mapa["blocos"])
    print(f"{n} imagens em {destino}")


def empacotar(origem, saida):
    from PIL import Image
    mapa = json.loads((origem / "logo.json").read_text())
    largura = mapa["largura"]
    fora = bytearray()
    for b in mapa["blocos"]:
        if b["tipo"] == "cru":
            fora += (origem / f"{b['nome']}@{b['off']:08x}.bin").read_bytes()
            fora += b"\x00" * (-len(fora) % 16)
            continue
        fluxos = []
        for im in b["imagens"]:
            f = origem / im["arquivo"]
            raw = (Image.open(f).convert("RGBA").tobytes()
                   if f.suffix == ".png" else f.read_bytes())
            fluxos.append(zlib.compress(raw, 9))
        n = len(fluxos)
        cab_len = 8 + 4 * n
        offs, cur = [], cab_len
        for f in fluxos:
            offs.append(cur); cur += len(f)
        corpo = struct.pack(f"<II{n}I", n, cur, *offs) + b"".join(fluxos)
        cab = MTK_MAGIC + struct.pack("<I", len(corpo)) + b["nome"].encode().ljust(32, b"\0")
        fora += cab.ljust(CAB, b"\xff") + corpo
        fora += b"\x00" * (-len(fora) % 16)      # alinhamento de 16 bytes do original
    saida.write_bytes(bytes(fora))
    print(f"{saida} — {len(fora)} bytes")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("acao", choices=["desempacotar", "empacotar", "listar"])
    p.add_argument("entrada", type=pathlib.Path)
    p.add_argument("saida", type=pathlib.Path, nargs="?")
    p.add_argument("--largura", type=int, default=1200, help="painel do vienna: 1200")
    a = p.parse_args()
    if a.acao == "listar":
        for nome, off, size in blocos(a.entrada.read_bytes()):
            print(f"  {nome:<8} @0x{off:08x}  {size:>10} bytes")
    elif a.acao == "desempacotar":
        desempacotar(a.entrada, a.saida, a.largura)
    else:
        empacotar(a.entrada, a.saida)
