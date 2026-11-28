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
| F1 | Workflow `verificar-acciones.yml` en `.github` + tests | 25-nov | Completada · .github#24 (c10094c) |
| F2 | Ruleset de org en Evaluate | 25-nov | Completada · ruleset 28092239 |
| F3 | PRs de prueba + Active + prueba de bloqueo | 25-nov | Completada · active 16:19; ensayo-identidad-app#11 BLOCKED, #12 CLEAN |
| F4 | Defensa 2: `/cambios-criticos` semanal con verificación upstream | 25-nov | Completada · patrón 8; texto con llave (registro #174) |
| F5.1 | Lockfiles: medición en seco por repo (`gh actions-lock --no-fix`) | 26-nov | Completada · informe SHP3 (`scratch/maestra-28jul-coord/reportes/SHP3-lockfiles-en-seco.md`) |
| F5.2 | Política «Require lockfile» en Evaluate (org) | 27-nov | Completada · política de Actions 18025, Evaluate, 18 repos por `repository_id`; informe SHP4 |
| F5.3a | `verificar-acciones` lee `actions.lock` (choque A, opción a · D-3713) | 27-nov | Completada · PR de la rama `feat/shp5-p-1047-check-lee-lockfile`; informe SHP5. No rige hasta F5.3b |
| F5.3b | Owner (David o Raúl) mueve el `sha` del ruleset 28092239 al merge de F5.3a; prueba en vivo | antes del 1-dic | Pendiente |
| F5.3c | Onboarding: `actions.lock` por repo, `.github` primero; 18 repos | 1-dic a 5-dic | Pendiente · espera F5.3b |
| F5.4 | «Require lockfile» a Active | 12-dic | Pendiente |

Archivos:
- [x] `.github/workflows/verificar-acciones.yml`
- [x] `.github/tests/test_verificar_acciones.py`
- [x] `~/.claude/scripts/cambios-criticos-upstream.py` (local de la Mac de David)
- [x] `~/.claude/commands/cambios-criticos.md` + wrapper semanal

Cabos sueltos (25-nov):
- Ruleset: `~ALL` menos direccion-comercial, empleados-virtuales, control-calidad (D-3586 decisión 1).
- PRs abiertos antes del ruleset (D-3586 decisión 2): 19 reabiertos con el chequeo en verde. Sin chequeo hasta su próxima actualización: 9 con conflictos, 3 apilados sobre otra rama (no aplica), 2 de Dependabot (adm#5948, landing#585: un push o `@dependabot rebase`).
- Cambiar el check: merge en `.github` + mover el `sha` del ruleset 28092239 (owner).

Cabos sueltos (27-nov):
- Política 18025 `P-1047 require lockfile`: Evaluate, solo «Require lockfile»; `actions/permissions` y rulesets sin cambio.
- Alcance 18, no 14: P-536 añadió `secret-scan.yml` el 27-nov a control-calidad, direccion-comercial, empleados-virtuales, owners-control. Los 4 entran en F5.3.
- Desvío aceptado: la interfaz guarda «All workflows» como `workflow_path.include: ["~ALL"]` (esquema: todos los workflows). Repos sin `~ALL`.
- URLs: políticas `organizations/FaroNovaCorp/settings/actions/rules`; insights `…/settings/actions/rules/insights`.
- Policy insights: cada run de los 18 sale «Evaluate · Would block» con el archivo del workflow. Sin ver aún: `pull_request`, `merge_group`, `schedule`, Dependabot.
- Choque A (`verificar-acciones` vs `@vX` de `gh actions-lock`): decide David antes del 1-dic; opciones y recomendación en `scratch/maestra-28jul-coord/reportes/SHP4-lockfile-evaluate.md`.
- Deshacer F5.2: Disabled en la página, o `gh api -X DELETE orgs/FaroNovaCorp/actions/policies/18025`.
- Siguiente sesión: arrancar por la decisión del choque A, luego F5.3. (Cerrado: decidido y hecho en F5.3a.)

Cabos sueltos (27-nov, F5.3a):
- Choque A: David, D-3713: «Respecto a lo que dices de GitHub, vamos con la más segura, por favor» → opción a.
- Antes de mover el `sha` (F5.3b): 0 `actions.lock` en `main` de los repos del ruleset y 0 PRs abiertos que lo toquen. El check viejo no mira el lockfile y el nuevo solo verifica entradas nuevas, cambiadas o activadas. Guion: `scratch/maestra-28jul-coord/reportes/SHP5-anexos/mover-sha-ruleset.sh`.
- Prueba en vivo antes de mover el `sha` (28-nov, `ensayo-identidad-app`, copia del check nuevo como workflow aparte, zizmor real; ambos cerrados sin mergear, ramas borradas): #14 incorporación con `gh actions-lock` → nuevo VERDE, el de la regla (`c10094c`) ROJO por `@v7.0.1`; #15 solo `actions.lock` con `commit` de fork → nuevo ROJO.
- Después de F5.3b, en `ensayo-identidad-app`: PR con lockfile legítimo → verde; PR que solo cambia el `commit` del lockfile a uno de fork → BLOCKED. Cerrar ambos sin mergear.
- Simulación del 27-nov (`gh actions-lock` v0.5.1 en clones desechables, API real, zizmor simulado): la incorporación de los 18 repos sale verde con el check nuevo; `agente-de-monitoreo` con `--migrate-local-actions`.
- La defensa 2 queda ciega con el onboarding: `cambios-criticos-upstream.py` solo lee `@<sha40>` y no lee `actions.lock`. Enseñarle el lockfile antes de cerrar F5.3c.
- El check solo entiende lockfile `v0.0.3` y sus campos conocidos. Si GitHub (CLI o Dependabot) cambia el formato → rojo con su motivo; se actualiza aquí y se mueve el `sha`.
- Sin probar: un PR real de Dependabot con lockfile (formato que escribe).
- Onboarding: los workflows y `action.yml` conservan SHA donde el lockfile no fija (`jobs.<id>.uses`, acciones compuestas locales).
- El check no exige entrada para un paso por SHA en un workflow incorporado: la completitud la cubre el workflow `verify` de la extensión (SHP3 § F5.3, punto 6); añadirlo en F5.3c.
- Revisión F5.3a: 4 rondas, Claude y Codex APROBADO · `evaluaciones/ejecucion/2026-11-28-revision-headless-f53a.md`.

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
- Todo `actions/checkout` nuevo (cualquier subruta) que elige otro árbol (`repository:`/`ref:`/`github-server-url:`, inputs como el runner): SHA literal → alcanzable; repo de la org en `main`; propio repo en `main` o con ref calculada (solo contextos). Lo demás → rojo. Subruta con `.`/`..`, clave `<<` → rojo.
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
- F5.2 · 27-nov · «Require lockfile» en Evaluate, org, los 18 repos activos con workflows, por lista explícita (interfaz: Settings → Actions → Policies; navegador con el aviso de David).
- F5.3a · `verificar-acciones` acepta `uses: dueño/repo@vX` solo si `.github/workflows/actions.lock` lo respalda:
  - paso de un job (no `jobs.<id>.uses`, no `action.yml`: ahí sigue el SHA);
  - entrada para ese workflow; `commit` de 40 alcanzable desde una rama del dueño (mismo criterio); tag de versión que apunta a ese commit (`@vN`: algún `vN.x`); `owner_id`/`repo_id` del repo; igual para sus transitivas;
  - lockfile cambiado, aunque ningún workflow cambie: entradas nuevas, cambiadas o activadas se verifican; quitar la entrada de un tag que sigue → rojo;
  - formato cerrado `v0.0.3`.
- F5.3b · mover el `sha` del ruleset 28092239 (owner). Deshacer: el mismo guion con el `sha` anterior (`c10094cd7a1f56e5f8578ca2135b3c5a27d12efe`).
- F5.3c · 1-dic a 5-dic · `actions.lock` por repo; `.github` primero (sus reusables deben estar onboarded antes que los que los llaman). Dependabot regenera las entradas.
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
