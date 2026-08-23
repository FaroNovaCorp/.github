# Claude Instructions — .github

Repo especial de GitHub para la organización FaroNovaCorp: perfil público de la org (`profile/README.md`) y workflows reusables (`.github/workflows/`) que otros repos FaroNova invocan — dependabot-automerge, secret-scan, update-docs.

No es un repo de producto; los cambios aquí afectan a toda la organización.

<!-- BEGIN snippet:agrupar-prs hash:d1b2e0b6fd8b2ca280fbd20679e817e6 -->
## Agrupar PRs — reducir el número, no el trabajo

> Bloque **generado y propagado** desde [`recursos-compartidos/snippets/agrupar-prs.md`](https://github.com/FaroNovaCorp/recursos-compartidos/blob/main/snippets/agrupar-prs.md).
> **No lo edites aquí** — el cambio se hace en ese source y se re-propaga con
> `recursos-compartidos/scripts/propagar.sh`.

**Lo que no requiera desplegarse ya mismo se acumula en un solo PR, para reducir el número de PRs.**

**Por qué esto es dinero, no burocracia:** cada PR que entra a la Merge Queue dispara una corrida completa de CI (además del CI del propio PR). Un PR de tres cambios triviales cuesta lo mismo en minutos de Actions que uno de tres cambios grandes — el costo es por PR, no por tamaño del cambio. Reducir el número de PRs es la palanca que más ahorra sin cambiar el flujo del equipo: el consumo de la organización bajó **-61 %** cuando se atacó justo esta clase de derroche (ver `reportes/COST1-consumo-actions-post-arreglo.md`).

**Qué NO se agrupa** — una regla sin su excepción se aplica mal el día que importa:
- Un fix de producción.
- Un cambio de seguridad.
- Algo que desbloquea a otra persona.

Eso sale ya, en su propio PR, sin esperar a nada.
<!-- END snippet:agrupar-prs -->

<!-- BEGIN snippet:documentacion-estandar hash:05e5a3e38d352d0f127f7d5b6a4a33df -->
## Estándar de documentación del repo

> Bloque **generado y propagado** desde [`recursos-compartidos/snippets/documentacion-estandar.md`](https://github.com/FaroNovaDevs/recursos-compartidos/blob/main/snippets/documentacion-estandar.md).
> **No lo edites aquí** — el cambio se hace en ese source y se re-propaga con
> `recursos-compartidos/scripts/propagar.sh`.

La documentación técnica de este repo sigue la convención del ecosistema FaroNova:

- **Estructura:** la doc técnica vive bajo `docs/`, en las subcarpetas que apliquen — `docs/adr/`, `docs/arquitectura/`, `docs/estandares/`, `docs/datos/`. Cada una con su `README.md` índice. Convención completa: [`recursos-compartidos/docs/estandares/documentacion.md`](https://github.com/FaroNovaDevs/recursos-compartidos/blob/main/docs/estandares/documentacion.md).
- **ADRs:** una decisión por archivo en `docs/adr/`, numeración secuencial **por repo** (empieza en `ADR-001`, independiente de la transversal). Estándar: [`recursos-compartidos/adr/estandar-adr.md`](https://github.com/FaroNovaDevs/recursos-compartidos/blob/main/adr/estandar-adr.md). Plantilla lista para copiar: `templates/adr-template.md` (propagada a este repo).
- **Diagramas:** **Mermaid** embebido en el `.md` (C4 `C4Context`/`C4Container`/`C4Component`/`C4Deployment`, red con `flowchart`, datos con `erDiagram`). Renderiza en GitHub y en el sitio MkDocs.
- **Front-matter:** los docs nuevos llevan YAML front-matter (`title`, `repo`, `seccion`, `generado`) que consume el sitio agregador. Los docs **generados desde código** llevan `generado: true` y **no se editan a mano**.
<!-- END snippet:documentacion-estandar -->

<!-- BEGIN snippet:estandar-costos-ci hash:1da28c038b7895b04e3824703c96a1ad -->
## Estándar de costo de CI (GitHub Actions)

> Bloque **generado y propagado** desde [`recursos-compartidos/snippets/estandar-costos-ci.md`](https://github.com/FaroNovaDevs/recursos-compartidos/blob/main/snippets/estandar-costos-ci.md).
> **No lo edites aquí** — el cambio se hace en ese source y se re-propaga con
> `recursos-compartidos/scripts/propagar.sh`.

GitHub Team factura **cada job redondeado hacia arriba al minuto entero** (un job de 12s paga 1 min completo), y cada job corre en su propia VM. La optimización de costo es la **inversa** de la de velocidad: **consolidar**, no paralelizar. Reglas para repos nuevos y al tocar workflows:

- **Consolidá checks afines en UN job con steps nombrados**, no muchos jobs cortos en paralelo (cada job = piso de 1 min + checkout/setup repetidos). Conservás la granularidad de reporte con `- name:` por step.
- **Secret scan: solo `pull_request` + `concurrency` (`cancel-in-progress`).** NO `push:[main]` — ese run corre post-merge, no gatea ningún merge y duplica el del PR. *Excepción:* si el caller no tiene trigger `pull_request`, el `push` ES el scan de PR (vía push a la rama del feature) → **no lo cortes**. *Excepción:* con merge queue (`merge_group`), `cancel-in-progress` debe excluir ese evento.
- **`ci.yml` reusable (`workflow_call`-only) embebido en `deploy.yml`**, no además standalone en `pull_request` → evita el double-run de tests. Verificá que los required checks salgan del run embebido (`test / *`) antes de quitar el standalone.
- **Workflows docs-only:** `paths-ignore` en los pesados + **gemelo passthrough** que emite los required checks como stubs (sin él, un required que no dispara por path deja el PR docs-only colgado).
- **`timeout-minutes` por job** (cap holgado sobre normal+cold-cache; **nunca** el default de 6h: un step de red colgado factura hasta 360 min). **Pinneá la versión de las tools** (uv, node, etc.) y poné **retry con timeout** en los steps de descarga (los CDNs se cuelgan intermitentemente). **NO** le pongas timeout a `terraform apply` — cancelarlo a mitad corrompe el state.
- **`concurrency` con `cancel-in-progress: true`** en workflows no-deploy; en el job de `terraform apply`, `cancel-in-progress: false` por diseño.

Métricas, palancas verificadas y casos de borde: plan vivo `agente-de-monitoreo:docs/planes-de-trabajo/pendientes/reduccion-costos-github-actions-transversal/`.
<!-- END snippet:estandar-costos-ci -->

<!-- BEGIN snippet:flujo-merges hash:678457d260696adab8ec97d467f5bc44 -->
## Flujo de merges

> Bloque **generado y propagado** desde [`recursos-compartidos/snippets/flujo-merges.md`](https://github.com/FaroNovaCorp/recursos-compartidos/blob/main/snippets/flujo-merges.md).
> **No lo edites aquí** — el cambio se hace en ese source y se re-propaga con
> `recursos-compartidos/scripts/propagar.sh`.

Merges: PR en verde → `gh pr merge <N> --merge` (encola donde hay Merge Queue, mergea directo donde no; verificar que quedó **MERGED**, no solo encolado). Expulsión de cola → `/mi-merge` y re-encolar. Detalle completo: [`docs/estandares/flujo-merges.md`](https://github.com/FaroNovaCorp/recursos-compartidos/blob/main/docs/estandares/flujo-merges.md).
<!-- END snippet:flujo-merges -->

<!-- BEGIN snippet:flujo-secretos hash:87a62d1e8e2e151a05ed52aba1bdd710 -->
## Flujo de entrega de secretos a una sesión de Claude Code

> Bloque **generado y propagado** desde [`recursos-compartidos/snippets/flujo-secretos.md`](https://github.com/FaroNovaCorp/recursos-compartidos/blob/main/snippets/flujo-secretos.md).
> **No lo edites aquí** — el cambio se hace en ese source y se re-propaga con
> `recursos-compartidos/scripts/propagar.sh`.

Un secreto (código MFA, PAT, API key, credencial) **nunca se pega en el chat de una sesión** — ni como texto, ni citado, ni "solo para verificar". Elige el patrón según el tipo:

**1. TOTP / código MFA (vive ~30 s, no se almacena):** se teclea directo en una ventana de Claude Code dedicada y ociosa, lanzada solo para eso. Nunca por relay de otra sesión.

**2. Secreto persistente (PAT, API key, credencial de larga vida):** va a AWS Secrets Manager, ejecutado por el developer con su prefijo `!`, del portapapeles al comando sin escribirse jamás:

```bash
! rtk proxy bash -c 'aws secretsmanager create-secret --name <ruta> --secret-string "$(pbpaste)" --region us-east-1'
```

Requiere admin (`assume-role` con MFA desde el profile **BASE**, nunca desde el rol ya asumido — ver "Elevar a admin desde Claude Code" en este mismo `CLAUDE.md`). Verificado: `$(pbpaste)` entre comillas simples de `bash -c` no se expande en el texto visible del comando (lo que queda en `zsh_history`/scrollback es literalmente `$(pbpaste)`) y `create-secret` no ecoa el secreto en su respuesta (solo `ARN`/`Name`/`VersionId`).

**3. Un comando LARGO que el developer tiene que ejecutar** (varios pasos encadenados — p. ej. `assume-role` + exportar credenciales + llamar a una API): nunca se le pide pegar eso completo. La sesión lo escribe a un script (`/tmp/<propósito>.sh`, con `set -euo pipefail`, validado con `bash -n`), y el developer ejecuta una sola línea corta: `! bash /tmp/<propósito>.sh <arg-corto>`. Reglas: solo argumentos cortos y efímeros (un código MFA sí, un secreto persistente jamás — ese entra por `$(pbpaste)` dentro del script); las credenciales temporales del `assume-role` viven solo dentro del script y mueren con él; el script solo imprime resultados no sensibles (ARN, `OK`).

**4. Higiene del portapapeles:** macOS mantiene un historial en disco (`~/Library/Metadata/CoreSpotlight/PasteboardHistory/`, protegido por TCC/SIP). Por eso, siempre, después de sembrar cualquier secreto: **copiar cualquier otra cosa** para desalojarlo del portapapeles.
<!-- END snippet:flujo-secretos -->

<!-- BEGIN snippet:merge-only hash:28e2619bcd6675d8bc56000b9384059e -->
## Política de merge: solo merge commit

> Bloque **generado y propagado** desde [`recursos-compartidos/snippets/merge-only.md`](https://github.com/FaroNovaDevs/recursos-compartidos/blob/main/snippets/merge-only.md).
> **No lo edites aquí** — el cambio se hace en ese source y se re-propaga con
> `recursos-compartidos/scripts/propagar.sh`.

- **Merge commit es la única estrategia permitida.** Squash y rebase están deshabilitados a nivel de API en todos los repos FaroNova. Comando: `gh pr merge <N> --merge`. Las flags `--squash` y `--rebase` fallan. El branch del remoto se borra automáticamente (`delete_branch_on_merge=true`); el worktree y branch local los limpia el developer. Detalle: `recursos-compartidos/desarrollo/flujo-de-trabajo.md` §5.
- **En los repos con Merge Queue ese mismo comando ENCOLA, no mergea.** `gh pr merge <N> --merge` mete el PR en la cola, que valida el grupo y mergea sola. **No uses el botón "Merge pull request" de la web** — ahí dice "Merge when ready", y cualquier merge directo lo rechaza GitHub con `HTTP 405 "Changes must be made through the merge queue"`. Ese 405 es lo esperado, no un error: nadie salta la cola, ni siquiera admins.
- **No memorices qué repos tienen cola — consultá el allowlist.** La lista se movió dos veces en una semana y cualquier copia en prosa se pudre. La fuente mantenida es `QUEUE_REPOS` en [`hooks/block-direct-merge.sh`](https://github.com/FaroNovaCorp/recursos-compartidos/blob/main/hooks/block-direct-merge.sh); la autoridad real es GitHub: `gh api repos/<owner>/<repo>/rules/branches/main --jq '[.[] | select(.type=="merge_queue")]'`.
- **Si la cola expulsa tu PR** (`removed_from_merge_queue` en el timeline), corré `/mi-merge`: te dice qué run del grupo falló, en qué job y paso, y el siguiente paso. Después del fix hay que **volver a encolar** con `gh pr merge <N> --merge` — `gh run rerun` NO re-encola, el grupo ya se destruyó. *Excepción `agente-de-monitoreo`:* si lo que falla es el deploy de `main` por el shard 4 flaky, ahí sí es `gh run rerun --failed` sobre el MISMO SHA, sin re-encolar.
- **Ya no existe el Merge Captain.** No hay que pasarle PRs a nadie ni esperar turno; la vigilancia de colas y deploys está automatizada (`/merge-watchdog`).
<!-- END snippet:merge-only -->

<!-- BEGIN snippet:subagentes-anidados hash:b6fb672f787eae586d150c930d2e7837 -->
<!-- Bloque generado y propagado desde recursos-compartidos/snippets/subagentes-anidados.md — NO editar aquí; editar en el source y re-propagar. -->

## Subagentes Claude — profundidad opcional (anidamiento)

Cuando orquestes agentes **Claude** (Agent tool) y una sub-tarea sea grande y divisible
(muchos archivos, un módulo extenso, varios repos), ese agente puede a su vez lanzar sus
propios subagentes Claude — hasta **5 niveles de profundidad** (Claude Code 2.1.172+).

- **Úsalo solo si conviene** — no es el default. Para un solo contexto, mantén un agente plano.
- Aplica **solo a agentes Claude**. Los revisores externos (Codex, Gemini) son
  procesos aparte y NO anidan.
- Anidar da **más agentes** (más paralelismo), no **más contexto** por agente — para un
  contexto gigante sigue siendo necesario un agente 1M (tmux).
<!-- END snippet:subagentes-anidados -->
