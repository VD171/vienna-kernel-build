# vienna-kernel-build

[🇬🇧 English](README.md) · 🇧🇷 Português

Build do kernel do **Motorola Edge 60 Neo** (`vienna`, MT6878 / Dimensity 7400) por GitHub Actions.

> ⚠️ **Para a maioria, você NÃO precisa disto para ter root.** O root do Edge 60 Neo se faz com
> **KernelSU LKM patchado no `init_boot`**, que não precisa de build nenhum. O workflow padrão aqui
> compila o **kernel GKI stock** (sem KernelSU) e existe para provar que a receita é byte a byte.
>
> 🆕 **Fase 2 (root built-in) funciona.** Um segundo workflow compila o **KernelSU-Next dentro do
> kernel** (não LKM), mantendo a `Linux version` do stock byte a byte. Um kernel com KSU built-in feito
> por esta receita **bootou num aparelho real** e carregou todos os device modules stock. A variante
> atual (KernelSU-Next OFICIAL, sem SUSFS) compila e passa o gate pré-flash; a validação no aparelho
> dessa build específica está pendente. Ver [Fase 2](#fase-2-ksu-next-built-in-a-parte-que-deu-mais-trabalho) abaixo.

## Status

| O quê | Estado |
|---|---|
| O `Image` stock compila | ✅ 34 MB, em **36 min** num runner comum (2 cores, 7,8 GB) |
| `Linux version` do stock | ✅ reproduzida **byte a byte** vs a build de fábrica |
| Device modules | ✅ **reusa o `vendor_dlkm` stock** (GKI/KMI, mesmo vermagic); compilá-los da fonte é barrado pelo `vendor/mediatek` proprietário, e não é preciso |
| Fase 2: um kernel com **KSU built-in** boota | ✅ medido no aparelho: subiu o Android, **424 device modules carregados, 0 erro de vermagic**, `lsmod` sem kernelsu (é built-in, não LKM) |
| Fase 2: **KSU-Next OFICIAL, sem SUSFS** | 🟡 compila e passa o gate pré-flash (versão byte a byte, config bate com o aparelho). **Ainda não validado no aparelho** |
| Boota no aparelho | ✅ validado no aparelho do mantenedor (stock e Fase 2) |

## O que este repo responde

Uma pergunta só: **o alvo GKI compila sem o `vendor/mediatek`?**

O `bazel_mgk_rules` da MediaTek declara `mgk_internal` e `mgk_ko` apontando para `../vendor/mediatek`, árvore **proprietária**, que nem a Motorola nem a MediaTek publicam. Ela barra os *device modules*.
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
Perseguir os repositórios que "faltam" é caçar o sintoma, a causa é a revisão.

## Fase 2: KSU-Next built-in (a parte que deu mais trabalho)

A fase 1 é stock. A fase 2 compila o **KernelSU-Next OFICIAL** (do `KernelSU-Next/KernelSU-Next`, o
projeto do rifsxd) **dentro do kernel**, então `lsmod | grep kernelsu` fica vazio e o driver anda
dentro do `vmlinux`. Workflow: **`build-gki-ksu.yml`**. Mantém a `Linux version` do stock byte a byte
para os `vendor_dlkm` de fábrica continuarem carregando.

### 🪤 A armadilha que custou dias: um `Image` que compila não é um kernel que boota

Todo build de KSU + kernel que fizemos na **árvore da MediaTek** compilava limpo, reproduzia a
`Linux version` exata, e **panicava no 1º `execve` do init**, no page allocator (`clear_page` num
endereço poison, determinístico). Provamos que **não** era o KSU, **não** era o SUSFS, **não** era a
config e **não** era o tamanho de página, por bisecção:

| Build | KSU | SUSFS | Resultado |
|---|---|---|---|
| Fase 2 (completa) | sim | sim | panic no init |
| sem os manual hooks | sim | sim | **mesmo** panic |
| stock, sem KSU/SUSFS, árvore MTK | não | não | **mesmo** panic |

Mesmo panic com zero KSU e zero SUSFS = a causa é a **árvore de build**, não o que adicionamos. O
`.config` embutido do nosso `Image` batia com o `/proc/config.gz` do aparelho em ~100% (um símbolo
irrelevante), então também não era a config. A única variável fora do padrão que sobrava era a
**`WORKSPACE` da MediaTek** (`bazel_mgk_rules` sobrescrevendo a do AOSP).

### ✅ A correção: compilar o GKI `common` puro do AOSP, não a árvore MTK

Dar checkout no `common` na tag exata do stock e compilar com a **`WORKSPACE` padrão do AOSP**, alvo
`//common:kernel_aarch64_dist`:

```bash
cd common
git fetch --depth=1 https://android.googlesource.com/kernel/common refs/tags/android14-6.1-2025-07_r11
git checkout FETCH_HEAD   # SUBLEVEL=141, o ponto exato do kernel stock
```

O `common` puro **bootou**. Depois `common` + KSU-Next built-in **bootou**, chegou ao Android e
**424 device modules carregaram com 0 erro de vermagic**, que é o de-risk real do KMI: o
`vendor_dlkm` stock aceita o nosso kernel. Bônus: nesse caminho o vermagic sai natural do
`git describe`, então o hack do `.scmversion` que a receita do stock exige fica desnecessário.

### Por que sem SUSFS

O mantenedor escolheu **sem SUSFS**, de propósito, para manter a stack **100% oficial** (a cola do
KernelSU-Next com SUSFS só existe em forks de terceiro, e o manager tem de ficar alinhado com o
driver no release mais recente). Sem SUSFS o build é KSU-Next oficial puro, e a ocultação no nível de
app que ele agregaria é em boa parte inócua, porque o SELinux já nega ao `untrusted_app` o acesso a
`/proc/modules`. A ocultação de runtime fica no userspace.

### 🤖 Autobuild

O `ksun-autobuild.yml` roda diariamente. Quando o KernelSU-Next publica um release novo ele bumpa o
ref pinado e rebuilda o kernel built-in automaticamente (só o artefato, nunca flasha nada).

## O que tem aqui

| Caminho | O quê |
|---|---|
| `.github/workflows/` | os builds: stock e KernelSU-Next OFICIAL built-in (mais o autobuild) |
| [`flash-recipe/`](flash-recipe/) | **como de fato flashar um kernel custom neste aparelho.** `fastboot boot` não existe aqui e o `flash boot` é preflash-checado contra o vbmeta on-device, então exige um patch cirúrgico do vbmeta. Leia o README de lá antes de rodar |
| [`tools/check-gate.py`](tools/check-gate.py) | provar que o `Image` compilado combina com o aparelho (string de versão, config embutido × `/proc/config.gz`, marcadores KSU/SUSFS) **antes** de flashar |
| [`tools/mtk-logo.py`](tools/mtk-logo.py) | desempacota/reempacota o `logo.img` da MediaTek, preservando os blocos de assinatura da Motorola |
| [`device/`](device/) | **fatos medidos do aparelho**: a config do kernel stock vinda do `/proc/config.gz` (a referência que o `check-gate.py` compara), o `fastboot getvar all` redigido, e o formato do `logo.img` |

As **fontes do kernel** em si estão espelhadas, extraídas e navegáveis, uma branch por tag de build, em
**[VD171/vienna-kernel-source](https://github.com/VD171/vienna-kernel-source)**. Diffar duas branches
de lá mostra o que a Motorola mudou entre duas ROMs.

## Fontes de kernel publicadas (catálogo)

Todas as tags do **vienna** que a Motorola já liberou, da mais nova para a mais antiga. Os repos
`kernel-mtk` e `kernel-kernel_device_modules-6.1` usam **os mesmos nomes de tag**, então uma
consulta serve para os dois.

| Tag | Android | Notas |
|---|---|---|
| [`MMI-W1UIS36H.39-17-8`](https://github.com/MotorolaMobilityLLC/kernel-mtk/releases/tag/MMI-W1UIS36H.39-17-8) | 16 | **atual**, é a que este workflow compila |
| [`MMI-V2UIS35.43-12-4-1`](https://github.com/MotorolaMobilityLLC/kernel-mtk/releases/tag/MMI-V2UIS35.43-12-4-1) | 15 |  |
| [`MMI-V1UIS35H.11-39-28-5`](https://github.com/MotorolaMobilityLLC/kernel-mtk/releases/tag/MMI-V1UIS35H.11-39-28-5) | 15 |  |
| [`MMI-V1UIS35H.11-39-16-5`](https://github.com/MotorolaMobilityLLC/kernel-mtk/releases/tag/MMI-V1UIS35H.11-39-16-5) | 15 |  |
| [`MMI-V1UIS35H.11-39-16-2`](https://github.com/MotorolaMobilityLLC/kernel-mtk/releases/tag/MMI-V1UIS35H.11-39-16-2) | 15 |  |
| [`MMI-V1UI35H.11-39-16`](https://github.com/MotorolaMobilityLLC/kernel-mtk/releases/tag/MMI-V1UI35H.11-39-16) | 15 |  |
| [`MMI-U4UI34.8-28-1`](https://github.com/MotorolaMobilityLLC/kernel-mtk/releases/tag/MMI-U4UI34.8-28-1) | 14 |  |
| [`MMI-U4UI34.8-22-7`](https://github.com/MotorolaMobilityLLC/kernel-mtk/releases/tag/MMI-U4UI34.8-22-7) | 14 |  |

Repare no token de aparelho **`UI`** em todo Build ID: é ele que identifica a plataforma, e é por
isso que procurar por "XT2509" não acha nada.

**Falta a sua?** Abra uma issue em
[MotorolaMobilityLLC/kernel-mtk](https://github.com/MotorolaMobilityLLC/kernel-mtk/issues) com o
**Build ID** e o **Build fingerprint** (uma build por issue). A minha foi atendida em **2 dias**.
Esta lista é mantida conforme surgem tags novas.

## Links

| Onde | O quê |
|---|---|
| 💬 [t.me/Edge60Neo](https://t.me/Edge60Neo) | Telegram, Edge 60 Neo |
| 💬 [t.me/MotorolaEdge60Neo](https://t.me/MotorolaEdge60Neo) | Telegram, Motorola Edge 60 Neo |
| 💬 [t.me/Motorola_Edge_60_Neo](https://t.me/Motorola_Edge_60_Neo) | Telegram, Motorola Edge 60 Neo |
| 🧵 [Thread no XDA](https://xdaforums.com/t/guide-rooting-how-to-root-motorola-60-edge-neo-5g-xt2509-1-vienna.4798267/) | `[GUIDE][ROOTING]` XT2509-1 (vienna) |
| 🛠 [VD171/vienna-kernel-build](https://github.com/VD171/vienna-kernel-build) | este repo |
| 📦 [VD171/vienna-kernel-source](https://github.com/VD171/vienna-kernel-source) | as fontes do kernel, extraídas, uma branch por tag |
| 🐧 [MotorolaMobilityLLC, `MMI-W1UIS36H.39-17-8`](https://github.com/MotorolaMobilityLLC/kernel-mtk/releases/tag/MMI-W1UIS36H.39-17-8) | o release GPL da própria Motorola para esta build |
| 💾 [stockrom.net, Edge 60 Neo 5G](https://www.stockrom.net/category/motorola/edge-60-neo-5g) | pacotes de firmware stock, úteis se você precisar da ROM inteira em vez de partições soltas |

## Licença

[MIT](LICENSE). Este repo apenas **automatiza** a montagem e o build.
As fontes do kernel são **GPL-2.0**, da [MotorolaMobilityLLC](https://github.com/MotorolaMobilityLLC),
e aqui não são redistribuídas nem relicenciadas.

## Contato

| Canal | Endereço |
|---|---|
| Telegram | [@VD_Priv8](https://t.me/VD_Priv8) |
| E-mail | `vd.priv8 [at] pm.me` |
| XDA | [VD171](https://xdaforums.com/m/vd171.4699873/) |
| GitHub | [VD171](https://github.com/VD171) |
