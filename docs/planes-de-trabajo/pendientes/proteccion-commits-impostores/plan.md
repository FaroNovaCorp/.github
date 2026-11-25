# Plan de Trabajo: Protección contra commits impostores en GitHub Actions

**Fecha de Creacion**: 2026-11-25
**Estado**: EN PROGRESO
**Prioridad**: ALTA
**Estimacion Total**: 8-12 horas (F1-F4 hoy; F5 por fases con fecha)
**Objetivo**: Que ningún PR de FaroNovaCorp meta una acción fijada a un commit que no sale del repo original (commit impostor, tag movido).
**Tarea vinculada**: TSK-20261125T152619-r4w9 — SHP2 · P-1047 · protección contra commits impostores en GitHub Actions

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

| Fase | Qué | Fecha | Estado |
|---|---|---|---|
| F1 | Workflow `verificar-acciones.yml` en `.github` + tests | 25-nov | En Progreso |
| F2 | Ruleset de org en Evaluate | 25-nov | Pendiente |
| F3 | PRs de prueba + Active + prueba de bloqueo | 25-nov | Pendiente |
| F4 | Defensa 2: `/cambios-criticos` semanal con verificación upstream | 25-nov | Pendiente |
| F5.1 | Lockfiles: medición en seco por repo (`gh actions-lock --no-fix`) | 26-nov | Pendiente |
| F5.2 | Política «Require lockfile» en Evaluate (org) | 27-nov | Pendiente |
| F5.3 | Onboarding: `actions.lock` por repo, `.github` primero | 1-dic a 5-dic | Pendiente |
| F5.4 | «Require lockfile» a Active | 12-dic | Pendiente |

Archivos:
- [ ] `.github/workflows/verificar-acciones.yml`
- [ ] `.github/tests/test_verificar_acciones.py`
- [ ] `~/.claude/scripts/cambios-criticos-upstream.py` (local de la Mac de David)
- [ ] `~/.claude/commands/cambios-criticos.md` + wrapper semanal

## Contexto

- SHP1 (25-nov, `scratch/maestra-28jul-coord/reportes/SHP1-aviso-sha-pinning.md`): `uses: dueño/repo@<sha>` resuelve también un commit que solo vive en un fork (red de forks comparte objetos). Caso Trivy, mar-2026.
- FaroNovaCorp hoy: 0 impostores; `sha_pinning_required: true`; ningún control mira de dónde sale el SHA. PR que solo cambia un SHA entra con CI verde (0 aprobaciones).
- Mandato: David, D-3566, 25-nov: «Respecto a lo de GitHub, sí, encarga la mejor protección que puedas».

Medido 25-nov:
- Org en plan enterprise: ruleset de org con regla `workflows` y modo Evaluate.
- Regla `workflows` (doc Enterprise Cloud, «Available rules for rulesets»): ignora filtros `paths`/`branches`; corre siempre en `pull_request` y `merge_group`; bloquea push directo; no corre en eventos del `GITHUB_TOKEN`; PRs abiertos antes del ruleset no corren solos.
- zizmor 1.32.0: `impostor-commit` y `ref-version-mismatch` atrapan el impostor de Trivy (`actions/checkout@70379aad…`). Falla al leer un YAML válido (`infra-cuenta` `adversarial-review.yml`): no sirve solo.
- Línea base de la org (zizmor sobre `main`): 1 desfase previo (`agente-conversacional` `deploy.yml:349`, `ecr-login # v2`), 0 impostores.
- Lockfiles (GA 28-oct-2026): `.github/workflows/actions.lock`, extensión `gh actions-lock`; política «Require lockfile» Evaluate/Active. La API REST de políticas aún no expone ese tipo de regla (solo `restrict_actions_actors`, `restrict_action_events`): se crea en la interfaz.

## Objetivos

Primarios:
- Check bloqueante en todo repo con flujo de PR de la org.
- Detección semanal de lo que ya está en `main`.
- Lockfiles con fecha de activación.

Secundarios:
- El check no frena PRs que no tocan workflows (sale en segundos).
- Lo ya presente en un archivo tocado avisa, no bloquea.

## Plan de Implementacion

### F1 · Workflow `verificar-acciones.yml`

- Triggers `pull_request` + `merge_group`; sin `cancel-in-progress`; `contents: read`; `ubuntu-24.04`; sin checkout del código del PR.
- Qué mete el cambio en main: PR → merge de prueba (`GITHUB_SHA`) contra su primer padre; cola → `base_sha`…`head_sha`. Un PR atrasado no hereda los cambios de main.
- Diff de árboles incremental por API (solo directorios que cambiaron; sin el tope de 7 MB del árbol recursivo). Relevantes: `.github/workflows/*.yml|yaml` de primer nivel (los únicos que GitHub carga) y `action.yml|action.yaml` en cualquier ruta. Sin relevantes → verde sin instalar nada.
- Enlace simbólico bajo `.github/` o como `action.yml` → rojo. Submódulo o `.gitmodules` nuevo, en cualquier ruta → rojo. Puntero de Git LFS o raíz que no es mapa → rojo (hoy: 0 de cada uno en la org).
- YAML como árbol de nodos sin construir (PyYAML `compose`, venv, `--require-hashes`): etiquetas como `!!omap` no esconden nada, igual que en el runner. Claves duplicadas → rojo.
- Todo `actions/checkout` nuevo que elige otro árbol (`repository:`/`ref:`, inputs sin mayúsculas ni espacios, como el runner): SHA literal → alcanzable; repo de la org en `main`; propio repo con rama o expresión. Otro repo sin SHA → rojo. Clave `<<` → rojo.
- Pares nuevos = `uses` de head que no estaban en la base. Por cada uno:
  - SHA completo de 40.
  - Commit existe en el repo dueño.
  - Alcanzable desde una RAMA del dueño (por defecto, releases, resto; hasta 300 ramas en paralelo). Solo-tag o solo-fork → rojo. Búsqueda incompleta → rojo con ese motivo.
  - Terceros: el tag del comentario apunta a ese SHA; `# vN` vale si algún `vN.x` apunta. Sin versión → rojo.
  - Reusables propios (`FaroNovaCorp/*`): en la rama por defecto; comentario libre.
  - El par aparece literal en una línea añadida (corta escapes y alias).
- zizmor 1.32.0 por archivo, `--no-config --no-ignores`: `impostor-commit` en la línea de un par nuevo → rojo; `ref-version-mismatch`, pares previos o zizmor que no lee el archivo → aviso. La verificación propia es la autoridad.
- Resumen en `GITHUB_STEP_SUMMARY` y anotaciones por línea.
- Tests: casos con API simulada (impostor, solo-tag, comentario desfasado, escape YAML, archivo sin cambios relevantes).
- PR propio en `.github` (`Va solo: seguridad`), revisión nivel 2, encolar.

### F2 · Ruleset de org en Evaluate

- `POST /orgs/FaroNovaCorp/rulesets`: `target: branch`, `~DEFAULT_BRANCH`, repos `~ALL` menos los 4 sin flujo de PR, regla `workflows` con `repository_id` de `.github`, `path`, `sha` del merge, `do_not_enforce_on_create: true`, sin bypass.
- Antes: aviso 2 a la maestra con el cambio y el deshacer (`PUT …/rulesets/<id>` `enforcement: disabled`, o `DELETE`).

### F3 · Prueba y Active

- `ensayo-identidad-app`: PR con impostor en un workflow `workflow_dispatch` (nunca corre) → rojo; PR legítimo → verde.
- Active. Repetir el PR impostor: `mergeable_state` bloqueado.
- Cerrar los PRs de prueba y borrar sus ramas.
- PRs abiertos sin el check: listarlos; el dueño hace push o reabre.

### F4 · Defensa 2

- Script local `cambios-criticos-upstream.py`: inventario de `uses` en `main` de los repos vivos + alcanzabilidad (criterio de `verificar_upstream.py` de SHP1).
- Lo corre el wrapper semanal; NO-ALCANZABLE o SOLO-TAG → fila «Revisar» en la BANDEJA.

### F5 · Lockfiles

- F5.1 · 26-nov · `gh actions-lock --no-fix` en cada repo, en seco: errores, acciones locales `./`, reusables.
- F5.2 · 27-nov · «Require lockfile» en Evaluate, org, todos los repos (interfaz: Settings → Actions → Policies; navegador con el aviso de David).
- F5.3 · 1-dic a 5-dic · `actions.lock` por repo; `.github` primero (sus reusables deben estar onboarded antes que los que los llaman). Dependabot regenera las entradas.
- F5.4 · 12-dic · Active, tras 7 días de Policy insights sin «would block».

## Criterios de Exito

- PR de prueba con impostor: check rojo y merge bloqueado; PR legítimo: verde.
- Check activo en todo repo con flujo de PR de la org (ruleset Active).
- Corrida semanal de `/cambios-criticos` con la sección upstream.
- Lockfiles: Evaluate el 27-nov, Active el 12-dic.

## Estimaciones

| Fase | Estimación |
|---|---|
| F1 | 3-4 h |
| F2 | 30 min |
| F3 | 1 h |
| F4 | 1-2 h |
| F5 | 3-4 h repartidas |

## Referencias

- `scratch/maestra-28jul-coord/reportes/SHP1-aviso-sha-pinning.md` y `SHP1-anexos/` (`verificar_upstream.py`, `inventario_uses.py`)
- Informe: `scratch/maestra-28jul-coord/reportes/SHP2-proteccion-sha-pinning.md`
- https://docs.github.com/en/enterprise-cloud@latest/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets
- https://docs.github.com/en/actions/how-tos/administer/enforce-workflow-lockfiles
- https://docs.zizmor.sh/audits/

## Aprobacion

- Mandato de David, D-3566 (25-nov-2026). Revisión nivel 2 por `/revisar-cambio`.
