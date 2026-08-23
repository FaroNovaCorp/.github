<!--
  Snippet: plan-padre-header.md
  Uso: incluir al inicio de § Estado de Implementacion en todo plan padre nuevo.
  Lo inyecta automaticamente `/crear-plan-equipo` desde recursos-compartidos/templates/.
  Si modificas este snippet, propagar a todos los repos con `./scripts/propagar.sh`.
-->

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
