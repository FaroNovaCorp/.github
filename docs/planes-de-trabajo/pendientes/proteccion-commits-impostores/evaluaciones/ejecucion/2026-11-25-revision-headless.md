# Evaluacion de Implementacion — Protección contra commits impostores (F1)

**Fecha:** 2026-11-25
**Metodo:** Equipo headless: Claude Code (agente aislado) + revisor externo Codex `gpt-6-astra` · xhigh · nivel delicado
**Alcance:** F1 (`.github/workflows/verificar-acciones.yml` + `.github/tests/test_verificar_acciones.py`). F2-F5 fuera.
**Rondas:** 3
**Veredicto final:** PENDIENTE-RONDA-3

## Cumplimiento del plan (F1)
- Subtareas: 6/6 (triggers y permisos, qué mete el cambio en main, diff por API, verificación propia, zizmor, resumen y anotaciones).
- Archivos: 2/2.
- Pruebas: 47 OK; humo contra la API real (impostor de Trivy → rojo; setup-node en `releases/v6` → verde; PRs reales de agente-de-monitoreo → verde).

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

## Ronda 3 (7560de3)

PENDIENTE

## Desviaciones del plan (aceptadas)
- Lista de archivos por diff de árboles, no por `pulls/N/files`/`compare` (sin topes de 3.000/300 archivos).
- Relevantes: `.github/workflows/*.y*ml` de primer nivel y `action.y*ml` (los únicos que GitHub carga), no todo YAML bajo `.github/`.
- zizmor `ref-version-mismatch` avisa; la verificación propia de versión es la que bloquea.

## Para tarea
- `cargar_yaml` con YAML 1.1: `on`/`true` o `1`/`01` como claves del mismo mapa cuentan como duplicadas (no ocurre en workflows reales). F×G 2.
