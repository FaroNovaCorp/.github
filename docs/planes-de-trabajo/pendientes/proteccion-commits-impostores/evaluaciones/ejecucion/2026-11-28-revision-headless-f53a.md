# Evaluacion de Implementacion — Protección contra commits impostores (F5.3a)

**Fecha:** 2026-11-28
**Metodo:** Equipo headless: Claude `opus` (agente aislado) + Codex `gpt-6-astra` · xhigh · nivel delicado
**Alcance:** F5.3a (`verificar-acciones.yml` lee `actions.lock` + pruebas + plan). F1-F4 ya revisadas; F5.3b-F5.4 fuera.
**Rondas:** 4 (máximo 5)
**Veredicto final:** APROBADO por ambos (ronda 4)

## Cumplimiento del plan (F5.3a)
- Aceptar `@vX` solo con respaldo del lockfile; sin entrada, inalcanzable o de fork → rojo; solo-tag/solo-fork → rojo; `@sha40` sin lockfile como antes.
- Pruebas pedidas: lockfile válido, entrada ausente, sha inalcanzable, sha de fork, tag movido, `@sha40` sin lockfile, reescritura `@<sha> # vX` → `@vX` (SHP3 § A).
- Pruebas: 113 OK. 19 defensas quitadas una a una en memoria: cada una pone la suite en rojo.
- Simulación (`gh actions-lock` v0.5.1 en clones desechables, API real, zizmor simulado): incorporación VERDE en los 18 repos; borrar el lockfile dejando tags → ROJO donde hay tags.

## Ronda 1 (fc6ce74) — Claude APROBADO · Codex CAMBIOS REQUERIDOS

| Hallazgo | Revisor | F×G | Resolución |
|---|---|---|---|
| Paso nuevo por SHA no verificaba lo que el lockfile le cuelga | Codex | 24 | si hay entrada para el par, se verifica su cierre |
| Relación `uses` nueva no verificaba el destino sin cambios | Codex | 16 | cierre de entradas nuevas, cambiadas y activadas |
| No se exige entrada para un paso por SHA en workflow incorporado | Codex | 25 | no se cambia (abajo); límite en la cabecera |

Razón del tercero (dueño del cambio): encargo «líneas `@<sha40>` sin lockfile, como hoy»; la línea fija el código; completitud = `gh actions-lock --verify`; regla nueva en un check de toda la org sin semántica del runner probada en vivo = riesgo de falso rojo general. Codex la aceptó en ronda 2; Claude de acuerdo.

## Ronda 2 — Claude APROBADO · Codex CAMBIOS REQUERIDOS

| Hallazgo | Revisor | F×G | Resolución |
|---|---|---|---|
| El cierre del lockfile del llamador se aplicaba a un reusable por SHA (falso rojo) | Codex | 8 | reusables fuera |

## Ronda 3 — Claude APROBADO · Codex CAMBIOS REQUERIDOS

| Hallazgo | Revisor | F×G | Resolución |
|---|---|---|---|
| Exclusión demasiado amplia: acción en directorio `x.yml` sin verificar transitivas | Codex | 8 | regla del parser oficial: YAML directo bajo `.github/workflows/` |

## Ronda 4 — ambos APROBADO

## Para tarea (descartados, sin tarea: F×G ≤ 4, ninguno abre ejecución sin verificar en estado alcanzable pasando por el check)
- Reusable con tag que ya estaba en main y la incorporación activa · 4 (0 casos en la org; no se puede meter uno nuevo).
- Referencia local nueva a acción compuesta sin cambios, lockfile sin regenerar · 3 (pide entrada rancia ya en main).
- `with: {uses: …}` igual a un paso → falso rojo · 2.
- Motivo en `action.yml` no menciona `$/` · 2.
- Falso rojo por nombre de repo viejo con entrada · 2.
- Archivo llamado solo `.yml` no cuenta como reusable · 2.
- Reusable por SHA con extensión en mayúsculas · 1.
- `RecursionError` con YAML de ~500 niveles (falla cerrado) · 1.
- `workflows_en` relee dos árboles · 1.

## Límites aceptados
- No se compara el grafo transitivo del lockfile con el `action.yml` de cada acción.
- Entradas anteriores a F5.3b no se verifican hasta que se activan: precondición 0 `actions.lock` al mover el `sha`.
- Semántica del runner (qué corre con lockfile): tomada de la documentación de GitHub, sin prueba en vivo.
- Sin probar: un PR real de Dependabot con lockfile.

## Prueba en vivo (28-nov, tras la ronda 4)
- Copia del check nuevo como workflow aparte en `ensayo-identidad-app`, zizmor real.
- #14, incorporación hecha por `gh actions-lock`: nuevo VERDE (3 archivos, 0 errores, 0 avisos); regla de la org (`c10094c`) ROJO por `@v7.0.1`.
- #15, solo `actions.lock` con commit de fork: nuevo ROJO («no está en ninguna rama de actions/checkout»), anotado en la línea de la entrada.
- Ambos cerrados sin mergear; ramas borradas; `main` sin cambio.
