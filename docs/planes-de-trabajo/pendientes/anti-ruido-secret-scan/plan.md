# Plan de Trabajo: Anti-ruido del secret-scan reusable

**Fecha de Creacion**: 2026-08-09
**Estado**: EN PROGRESO
**Prioridad**: ALTA
**Estimacion Total**: 1-2 horas
**Objetivo**: Eliminar el ruido de Issues duplicados que abre el secret-scan reusable desde ramas efimeras de merge queue/PR, sin debilitar la cobertura del escaneo.
**Tarea vinculada**: TSK-20260809T173629-kfu9 — Secret-scan: 1 issue por rama efimera (merge-queue/refs-pull) sin dedup real

---

## Table of Contents

1. [Estado de Implementacion](#estado-de-implementacion)
2. [Contexto](#contexto)
3. [Objetivos](#objetivos)
4. [Plan de Implementacion](#plan-de-implementacion)
5. [Criterios de Exito](#criterios-de-exito)
6. [Estimaciones](#estimaciones)
7. [Referencias](#referencias)
8. [Aprobacion](#aprobacion)

---

## Estado de Implementacion

> ### REGLA INVIOLABLE — Actualizar este plan al cerrar cada sesion
>
> Este plan es la **fuente de verdad** del trabajo pendiente entre sesiones. El handoff (`/continuar-en-siguiente-sesion`) NO narra lo que falta — lo lee de aqui.
>
> **Antes de cerrar una sesion que toco este plan:**
> 1. Marcar las filas de § Estado de Implementacion completadas en esta sesion como `Completada`.
> 2. Agregar cabos sueltos, decisiones pendientes y bloqueos descubiertos como filas nuevas o sub-bullets — no dejarlos en el handoff.
> 3. Enlazar PRs mergeados en la fila correspondiente.
> 4. Si la siguiente sesion debe arrancar por un punto especifico, escribirlo aqui — no en el handoff.
>
> El comando `/continuar-en-siguiente-sesion` corre un gate bloqueante: si detecta `plan_paths` en la tarea, pregunta si este archivo refleja el trabajo de la sesion. Si no, exige un PR doc-only de actualizacion ANTES de generar el handoff.
>
> Motivacion: incidente 2026-05-26/27 (TSK-20260527T015140-8drj) — plan padre stale entre sesiones porque el handoff narraba todo. Decision del CTO: "no perdamos el hilo entre sesiones".

| Fase | Descripcion | Estado |
|------|-------------|--------|
| 1 | Excluir ramas efimeras (`pull_request`, `merge_group`) del modo "abrir Issue" | Completada |
| 2 | Dedup por fingerprint real del hallazgo (detector+file+line+commit), no por titulo | Completada |
| 3 | `core.setFailed` cuando sobrevive un hallazgo real (`findings`), no solo en `tool_error` | Completada |
| 4 | PR abierto, verificacion (harness mockeado, 7/7 escenarios), revision /revisar-pr (2 Codex) | En Progreso — falta smoke post-merge en vivo |

**Checklist de archivos:**
- [x] `.github/workflows/secret-scan.yml` (unico archivo a tocar — reusable de la org)

**Fixes adicionales aplicados tras revision `/revisar-pr` (2 Codex, Seguridad + Calidad, ambos convergieron en los mismos 4 hallazgos):**
- [x] `core.setFailed` tambien cuando `exit 183` pero el JSONL no es parseable (fail-open pre-existente que contradecia la Fase 3 — antes quedaba en `core.warning` sin fallar el check)
- [x] Dedup de Issues con `github.paginate` en vez de `per_page: 50` fijo (la Fase 2 decia "TODOS los Issues", `per_page` fijo solo cubria la primera pagina)
- [x] Fingerprint calculado con el commit COMPLETO (`commitFull`), no el SHA truncado a 8 chars usado para mostrar en la tabla
- [x] Este plan actualizado (hallazgo MEDIO de ambos Codex: el estado seguia en `Pendiente` pese a la implementacion)

**Pendiente antes de dar la Fase 4 por completada — smoke post-merge en vivo (ver seccion "Verificacion post-merge" mas abajo).**

---

## Contexto

Hallazgo del triage `TSK-20260809T172814-94w5` (11 Issues "Secrets detectados" abiertos en 3 dias en `agente-de-monitoreo`, todos falso positivo por el bug del detector `Lob`, ya cubierto por `TSK-20260806T155600-98y4` via `exclude_detectors: "Lob"`).

Root cause **distinta y aun no cubierta**: el workflow reusable `secret-scan.yml` (repo `FaroNovaCorp/.github`, hoy en `origin/main` @ `7899dcfd4646820b5264fec02808a2724cc82a60`) abre un Issue de GitHub nuevo por cada rama que dispara un hallazgo, y el dedup actual compara **titulo exacto** (`Secrets detectados en ${repo} (branch: ${branch})`). En Merge Queue y PRs la rama es efimera y cambia en cada intento (`gh-readonly-queue/main/pr-N-<sha>`, `refs/pull/N/merge`), asi que el titulo nunca coincide entre corridas — nunca dedupea, aunque el hallazgo subyacente (archivo/linea/commit) sea el mismo.

Ademas, hoy ningun run con `result === 'findings'` llama `core.setFailed` (solo `core.error`) — el check `scan/trufflehog` queda verde aunque haya un hallazgo real, asi que ni el equipo lo ve en la PR ni `coordination_alerts` lo captura (esa tabla solo ingiere `workflow_run_failed` via `conclusion != success`).

**Version actual del reusable (origin/main `7899dcf`)** ya incorpora un fix reciente (`96533a8`, PR #3, mergeado 2026-08-07): parseo correcto del JSON de TruffleHog (`--json` en vez de `--results=json`), `exclude_detectors` configurable (default `Lob`), y `core.setFailed` en el caso `tool_error`. Ese fix es ortogonal a este plan — este plan construye sobre esa base, no la reemplaza.

**Consumidores del reusable (7 repos)**: `agente_conversacional`, `agente_de_monitoreo`, `consola_de_alertas`, `landing`, `planeacion_por_escenarios_1`, `recursos-compartidos`, `tablero-equipo`. De estos, 4 pinean a SHA exacto (`agente_conversacional`, `agente_de_monitoreo`, `consola_de_alertas`, `landing`) y 3 usan `@main` flotante (`planeacion_por_escenarios_1`, `recursos-compartidos`, `tablero-equipo` — tradeoff ya documentado y abierto en `TSK-20260809T050130-sejf`, fuera de alcance de este plan). Los repos con `@main` reciben este fix apenas se mergee; los 4 pineados necesitaran un bump de pin en un PR separado (no incluido aqui — mismo patron que `TSK-20260809T050130-sejf`).

## Objetivos

**Primarios:**
1. No abrir Issues desde ramas efimeras de merge queue / PR (`pull_request`, `merge_group`) — el required check ya cubre esos casos.
2. Deduplicar por fingerprint real del hallazgo (detector + file + line + commit), buscando entre TODOS los Issues abiertos con label `secrets` — no por titulo exacto.
3. `core.setFailed` cuando sobrevive un hallazgo real (`result === 'findings'`) — el fallo fluye solo a `/alertas-sistema` via `workflow_run_failed`, sin ingester nuevo.

**Secundarios:**
- No reducir cobertura de deteccion (mismos detectores, mismo scope de commits).
- Mantener visibilidad del detalle (archivo/linea/detector) para el equipo aunque no se abra Issue — via Job Summary del run.

## Plan de Implementacion

### Fase 1 — Ephemeral refs no abren Issue
- Detectar `context.eventName === 'pull_request' || context.eventName === 'merge_group'` (equivalente a los refs `refs/pull/*/merge` y `gh-readonly-queue/*` que menciona el hallazgo original — `eventName` es la senal canonica del `context` de `actions/github-script`).
- En esos casos: NO crear/comentar Issue. Si hay hallazgos, igual escribir el detalle (tabla redactada) en el Job Summary del run para que quede visible en el check de la PR.

### Fase 2 — Dedup por fingerprint
- Calcular `fingerprint = sha256(sorted(detector|file|line|commit por cada hallazgo)).slice(0,16)`.
- Embeber `<!-- secret-scan-fingerprint: <hash> -->` en el body del Issue.
- Al buscar duplicado: `listForRepo({state:'open', labels:'security,secrets'})` y buscar por el marcador embebido en el body, no por `title === title`.
- Si hay match: comentar en el Issue existente. Si no: crear uno nuevo con el marcador.

### Fase 3 — `core.setFailed` en hallazgos reales
- Tanto en el caso `findings` como en `tool_error`, llamar `core.setFailed(...)` con un mensaje corto (ademas de `core.error`/log existente).
- Aplica en TODAS las ramas (efimeras o no) — el check debe fallar siempre que haya un hallazgo real; lo unico condicional es si se abre o no un Issue nuevo.

### Fase 4 — PR + verificacion
- Commit + push del branch de trabajo, PR normal contra `main` (el repo `.github` hoy no tiene merge queue).
- Verificar en un run real (o simulacion controlada): rama efimera no abre Issue; hallazgo duplicado no re-abre; hallazgo real → check rojo (`setFailed`) visible como `workflow_run_failed`.
- Reportar a la sesion maestra y esperar señal de merge.

**Verificacion pre-merge realizada:** `.github` no tiene ningun workflow que se dispare sobre si mismo (`secret-scan.yml`/`update-docs.yml` son ambos `workflow_call` puros) — no hay CI que ejecutar contra el PR. En su lugar se armo un harness (`node`, en `/private/tmp/.../scratchpad/verify_secret_scan.mjs`, no versionado) que corre el bloque JS real extraido del YAML contra `context`/`core`/`github` mockeados. 7/7 escenarios pasan: rama efimera (`pull_request` y `merge_group`) con hallazgo → sin Issue + check rojo + detalle en Job Summary; duplicado por fingerprint en rama no-efimera → comenta, no re-abre; mismo titulo viejo con fingerprint distinto → SI abre (confirma que el bug de dedup-por-titulo esta resuelto); hallazgo real sin duplicado → abre Issue Y falla el check; `tool_error` en rama efimera → sin Issue, check rojo igual; `findings` sin JSON parseable → check rojo (fix post-revision, ver abajo). No se dispara ningun secreto real ni se toca ningun repo de produccion para esto.

### Verificacion post-merge (smoke en vivo)

El harness mockeado prueba la LOGICA; falta confirmar el comportamiento real contra la API de GitHub. Candidatos entre los repos que usan `@main` flotante (reciben el fix apenas se mergee este PR, sin esperar bump de pin — ver `TSK-20260809T050130-sejf`):

| Repo | Trigger de su `secret-scan.yml` | Que valida |
|---|---|---|
| `tablero-equipo` | `pull_request` | Rama efimera → sin Issue nuevo, check rojo si hay hallazgo/tool_error |
| `recursos-compartidos`, `planeacion-por-escenarios-1` | `push` | Rama no-efimera → Issue con marcador de fingerprint; dedup en el segundo hallazgo identico |

**Plan pasivo (default, sin tocar nada mas):** en las proximas 1-2 rondas de `/merge-watchdog`, filtrar `gh run list --workflow "Secret Scan" --json conclusion,event,createdAt` sobre esos repos por `conclusion=failure`. Cuando aparezca uno: si `event` es `pull_request`/`merge_group` → confirmar en GitHub que NO se abrio Issue nuevo; si es `push` → confirmar que el Issue tiene `<!-- secret-scan-fingerprint: ... -->` en el body, y que una recurrencia comenta en vez de re-abrir.

**Plan activo (opcional, requiere luz verde explicita — NO ejecutado unilateralmente):** `recursos-compartidos` tiene funciones de test reales que matcheaban el detector `Lob` (el falso positivo que origino el fix de `exclude_detectors`, ya excluido por default). Correr manualmente el workflow via `workflow_dispatch` pasando `exclude_detectors: ""` sobre una PR descartable forzaria un finding determinista sin usar ningun secreto real. No se hizo aqui porque implica destapar deliberadamente un detector ruidoso en un repo compartido — decision de David/maestra, no de esta sesion.

La validacion definitiva del incidente original (11 Issues en `agente-de-monitoreo` via Merge Queue) solo llega cuando `TSK-20260809T205433-d5p5` (bump de pin en los 4 repos pineados) se complete — ese repo es el unico que reproduce exactamente el escenario que origino esta tarea.

## Criterios de Exito

**Tecnicos:**
- `secret-scan.yml` sigue siendo un `workflow_call` valido (YAML valido, `actionlint`/CI en verde).
- Ningun detector removido ni `extra_args`/`exclude_detectors` debilitado.

**Funcionales:**
- Rama efimera (PR o merge queue) con hallazgo → check rojo, SIN Issue nuevo.
- Push/dispatch en rama no-efimera con el MISMO hallazgo (mismo detector+file+line+commit) dos veces → un solo Issue, con comentario en el segundo run.
- Hallazgo real (simulado) → `core.setFailed` dispara `workflow_run_failed`, capturable por `/alertas-sistema`.

**Calidad:**
- Sin abrir un ingester nuevo — reusa el pipeline existente de `coordination_alerts`.
- Cambio acotado a `.github/workflows/secret-scan.yml` (un solo archivo).

## Estimaciones

| Fase | Estimacion |
|------|-----------|
| 1 — Ephemeral refs | 20 min |
| 2 — Dedup fingerprint | 30 min |
| 3 — setFailed | 10 min |
| 4 — PR + verificacion | 30-40 min |
| **Total** | **1.5-2h** |

## Referencias

- Tarea: `TSK-20260809T173629-kfu9`
- Relacionadas: `TSK-20260806T155600-98y4` (exclude_detectors Lob), `TSK-20260809T050130-sejf` (bump de pin + politica @main, completada), `TSK-20260809T172814-94w5` (triage que origino este hallazgo)
- Archivo objetivo: `.github/workflows/secret-scan.yml` (`origin/main` @ `7899dcfd4646820b5264fec02808a2724cc82a60`)
- Consumidores: `agente_conversacional`, `agente_de_monitoreo`, `consola_de_alertas`, `landing`, `planeacion_por_escenarios_1`, `recursos-compartidos`, `tablero-equipo`

## Aprobacion

Direccion de las 3 lineas ya aprobada por David (ver brief `scratch/maestra-28jul-coord/briefs/brief-K1-kfu9-anti-ruido-secretscan.md`, seccion "Alcance"). Este plan corto documenta el detalle tecnico de implementacion antes de tocar el workflow reusable. Estado: **PENDIENTE de revision** — reportado a la sesion maestra tras crearlo.
