# vienna-kernel-build

[🇬🇧 English](README.md) · 🇧🇷 Português

Build do kernel do **Motorola Edge 60 Neo** (`vienna`, MT6878 / Dimensity 7400) por GitHub Actions.

> ⚠️ **Isto NÃO dá root.** Compila o **kernel GKI stock** a partir da fonte; não tem KernelSU
> dentro. Existe para provar que a receita de build funciona — o root do Edge 60 Neo se faz com
> **LKM patchado no `init_boot`**, que não precisa de build nenhum.

## Status

| | |
|---|---|
| O `Image` compila | ✅ 34 MB, em **36 min** num runner comum (2 cores, 7,8 GB) |
| Device modules | ❌ barrados pelo `vendor/mediatek` proprietário da MediaTek |
| Boota no aparelho | ❓ **nunca testado** — `Image` prova a receita, não o boot |

## O que este repo responde

Uma pergunta só: **o alvo GKI compila sem o `vendor/mediatek`?**

O `bazel_mgk_rules` da MediaTek declara `mgk_internal` e `mgk_ko` apontando para `../vendor/mediatek`
— árvore **proprietária**, que nem a Motorola nem a MediaTek publicam. Ela barra os *device modules*.
A dúvida é se barra também o **`Image`** do GKI.

- ✅ se compilar → há caminho para kernel próprio com o que é público
- ❌ se não → o teto é o `vendor/mediatek`, e o caminho é **LKM sobre o kernel de fábrica**

## Como montar a árvore (o que a receita da Motorola não diz)

A Motorola publica um `MMI-<build>.txt` com defconfig/overlays/alvos, mas ele documenta **o delta do
aparelho** e pressupõe uma árvore obtida por `repo`. Faltam nele:

| Peça | Onde está |
|---|---|
| `build/kernel` (Kleaf) | vem do manifesto AOSP |
| `build/bazel_mgk_rules` | `MotorolaMobilityLLC/kernel-build-bazel_mgk_rules`, **na mesma tag `MMI-*`** |
| revisão de tudo | `<default revision="main-kernel-build-2023">` no manifesto |

🪤 **Não clone `build/kernel` no branch default.** O HEAD é da era bzlmod/Bazel 8 e passa a exigir
**32** repositórios em `external/`; a revisão que o manifesto fixa é WORKSPACE-based e exige **0**.
Perseguir os repositórios que "faltam" é caçar o sintoma — a causa é a revisão.

## Links

| Onde | O quê |
|---|---|
| 💬 [t.me/Edge60Neo](https://t.me/Edge60Neo) | Telegram — Edge 60 Neo |
| 💬 [t.me/MotorolaEdge60Neo](https://t.me/MotorolaEdge60Neo) | Telegram — Motorola Edge 60 Neo |
| 🧵 [Thread no XDA](https://xdaforums.com/t/guide-rooting-how-to-root-motorola-60-edge-neo-5g-xt2509-1-vienna.4798267/) | `[GUIDE][ROOTING]` XT2509-1 (vienna) |
| 🛠 [VD171/vienna-kernel-build](https://github.com/VD171/vienna-kernel-build) | este repo |

## Licença

[MIT](LICENSE) — este repo apenas **automatiza** a montagem e o build.
As fontes do kernel são **GPL-2.0**, da [MotorolaMobilityLLC](https://github.com/MotorolaMobilityLLC),
e aqui não são redistribuídas nem relicenciadas.

## Contato

| | |
|---|---|
| Telegram | [@VD_Priv8](https://t.me/VD_Priv8) |
| E-mail | `vd.priv8 [at] pm.me` |
| XDA | [VD171](https://xdaforums.com/m/vd171.4699873/) |
| GitHub | [VD171](https://github.com/VD171) |
