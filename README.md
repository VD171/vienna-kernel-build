# vienna-kernel-build

Build do kernel do **Motorola Edge 60 Neo** (`vienna`, MT6878 / Dimensity 7400) por GitHub Actions.

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

## Fonte

Levantamento completo, armadilhas e o roteiro em prosa:
`Docs/Android/MOTOROLA_EDGE_60_NEO.md` §6.7 (repo de documentação do dono).
