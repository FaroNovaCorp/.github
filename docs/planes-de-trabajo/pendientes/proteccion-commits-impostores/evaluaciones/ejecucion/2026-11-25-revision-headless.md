# Evaluacion de Implementacion — Protección contra commits impostores (F1)

**Fecha:** 2026-11-25
**Metodo:** Equipo headless: Claude Code (agente aislado) + revisor externo Codex `gpt-6-astra` · xhigh · nivel delicado
**Alcance:** F1 (`.github/workflows/verificar-acciones.yml` + `.github/tests/test_verificar_acciones.py`). F2-F5 fuera.
**Rondas:** 5 (máximo)
**Veredicto final:** CAMBIOS REQUERIDOS en ronda 5, aplicados por el dueño del cambio (regla 6); validación en vivo en F3

## Cumplimiento del plan (F1)
- Subtareas: 6/6 (triggers y permisos, qué mete el cambio en main, diff por API, verificación propia, zizmor, resumen y anotaciones).
- Archivos: 2/2.
- Pruebas: 57 OK; ensayo en seco sobre los 94 workflows y action.yml de main de la org: 0 errores; humo contra la API real (impostor de Trivy → rojo; setup-node en `releases/v6` → verde; PRs reales de agente-de-monitoreo → verde).

## Ronda 1 (b1e5aa9) — ambos CAMBIOS REQUERIDOS

| Hallazgo | Revisor | F×G | Fix (1c51f08) |
|---|---|---|---|
| Base = punta de main: PR atrasado hereda cambios de main (falso rojo) | ambos | 42 | merge de prueba contra su primer padre |
| Árbol recursivo con tope de 7 MB (agente-de-monitoreo: 6,4 MB) | Claude | 36 | diff de árboles incremental |
| action.yml como enlace simbólico evade | ambos | 27 / 16 | enlace simbólico en ruta sensible → rojo |
| zizmor bloqueaba por línea, no por par | Codex | 20 | solo impostor-commit en par nuevo bloquea |
| Tope de 40 ramas da falso impostor | Codex | 12 | 300 ramas en paralelo; «búsqueda incompleta» |
| `# vN` flotante movido expulsa de la cola | Claude | 12 | vale si algún vN.x apunta al SHA |
| Comentario libre de reusable propio bloquea | Claude | 9 | comentario libre para FaroNovaCorp/* |
| Timeout de zizmor → rojo total | Claude | 8 | aviso |
| Claves YAML duplicadas | Claude | 8 | rojo |
| Errores de red sin reintento | Claude | 6 | reintento; límite agotado con mensaje |
| Huecos de pruebas | Claude | 9 | +14 pruebas |

## Ronda 2 (1c51f08) — ambos CAMBIOS REQUERIDOS

| Hallazgo | Revisor | F×G | Fix (7560de3) |
|---|---|---|---|
| action.yml como puntero de Git LFS evade | Codex | 18 | raíz que no es mapa / puntero LFS → rojo |
| Submódulo fuera de `.github/` evade | Claude | 14 | todo gitlink o `.gitmodules` nuevo → rojo |
| Orden de padres del merge de prueba sin comprobar | Claude | 9 | se exige padres[1] = head del PR |
| `previos` del camino de respaldo | Claude | 6 | respaldo = punta de la base (más estricto) |
| `pull_request_target` aceptado | Claude | 6 | evento no soportado |
| Límite secundario de la API | Claude | 6 | reintento con espera |

## Ronda 3 (7560de3) — ambos CAMBIOS REQUERIDOS

| Hallazgo | Revisor | F×G | Fix (4ad1443) |
|---|---|---|---|
| Etiquetas YAML (`!!omap`, `!!set`, `!!pairs`) esconden un `uses` | Codex | 27 | árbol de nodos con `compose`, sin etiquetas |
| Checkout de otro repo + `uses: ./…` corre un action.yml no verificado | Claude | 16 | regla de checkout (rehecha en ronda 4) |

## Ronda 4 (4ad1443) — ambos CAMBIOS REQUERIDOS

| Hallazgo | Revisor | F×G | Fix |
|---|---|---|---|
| Regla de checkout evadible: mayúsculas en inputs, espacios, path en expresión | Codex | 27 | inputs como el runner; se verifica el checkout, no el path |
| Propio repo con `ref:` a un commit de fork | ambos | 18 / 14 | SHA literal del propio repo → alcanzable |
| Checkout en una acción compuesta y consumo en el workflow | ambos | 18 / 14 | todo checkout nuevo con `repository`/`ref`, dondequiera |
| Clave de fusión `<<` | Claude | 14 | rojo |

Ensayo en seco tras el fix: 8 falsos rojos en patrones reales (despliegue por `inputs.ref`, robot de migraciones, propagación por matriz) → regla ajustada → 0 sobre los 94 archivos de la org.

## Ronda 5 (86bdb34) — ambos CAMBIOS REQUERIDOS · última ronda (máx. 5)

| Hallazgo | Revisor | F×G | Fix (c31649d) |
|---|---|---|---|
| `actions/checkout/.@sha` no se reconoce como checkout | ambos | 27 / 14 | checkout por dueño/repo con cualquier subruta; subruta con `.`, `..` o `//` → rojo |
| Propio repo con ref literal: rama sin mergear, `refs/pull/N/head`, SHA en mayúsculas, constante en expresión | ambos | 27 / 14 | propio repo: `main`, SHA alcanzable (sin distinguir mayúsculas) o expresión que solo lee contextos unidos por `\|\|` |
| `github-server-url` ajeno baja el árbol de otro servidor | Claude | 14 | rojo si no es github.com |
| Otras acciones que escriben un action.yml (download-artifact, cache) | Claude | 7 | límite aceptado, en la cabecera |
| «Org en main» incluye los 4 repos fuera del ruleset | Claude | 6 | límite aceptado, en la cabecera |

Decisión del dueño del cambio tras la ronda 5 (regla 6): fixes aplicados con 57 pruebas y ensayo en seco (94 archivos de la org, 0 errores); validación en vivo en F3 (Evaluate + PRs de prueba). Sin ronda 6.

## Desviaciones del plan (aceptadas)
- Lista de archivos por diff de árboles, no por `pulls/N/files`/`compare` (sin topes de 3.000/300 archivos).
- Relevantes: `.github/workflows/*.y*ml` de primer nivel y `action.y*ml` (los únicos que GitHub carga), no todo YAML bajo `.github/`.
- zizmor `ref-version-mismatch` avisa; la verificación propia de versión es la que bloquea.

## Límites aceptados (fuera de F1)
- Código arbitrario en `run:` (incluye refs calculadas en ejecución) y acciones que escriben un action.yml en el workspace: revisión del PR y `/cambios-criticos`.
- «Repo de la org en main» incluye los 4 repos sin flujo de PR, fuera del ruleset.
- Ejecución del impostor en el CI del propio PR, antes del merge: F5 (lockfiles).
- Cualquier `dueño/repo@sha` en una rama de su dueño pasa: no hay lista de dueños permitidos.

## Para tarea
- Ninguno.
