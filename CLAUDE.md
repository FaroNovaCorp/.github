# Claude Instructions — .github

Repo especial de GitHub para la organización FaroNovaCorp: perfil público de la org (`profile/README.md`) y workflows reusables (`.github/workflows/`) que otros repos FaroNova invocan — dependabot-automerge, secret-scan, update-docs.

No es un repo de producto; los cambios aquí afectan a toda la organización.

<!-- BEGIN snippet:agrupar-prs hash:75137b2ee6dcd9ceae7c422d80270076 -->
## Agrupar PRs — reducir el número, no el trabajo

> Propagado desde `recursos-compartidos/snippets/agrupar-prs.md`; no editar aquí. Texto completo: [agrupar-prs.md](https://github.com/FaroNovaCorp/recursos-compartidos/blob/main/docs/estandares/agrupar-prs.md).

Lo que no requiera desplegarse ya mismo se acumula en un solo PR: cada PR que entra a la Merge Queue paga una corrida completa de CI, sin importar su tamaño. Salen solos, en su propio PR: un fix de producción, un cambio de seguridad, algo que desbloquea a otra persona.

Planes y registros de sesión sin código: al acumulador diario `acum/planes-<repo>-<fecha>` (`.claude/scripts/acum-planes.sh`), no a un PR suelto. El plan que cambia con código va en ese PR. El PR del acumulador se abre solo al cierre; encolarlo pide aprobación explícita del humano dueño de la sesión.

Decide el agente en cada `gh pr create`, no el humano: declara la razón en el body, una línea (`Va solo: <razón>` / `Agrupa: <PR o rama>`). Con duda real, pregunta al humano dueño de la sesión antes de crear el PR.
<!-- END snippet:agrupar-prs -->

<!-- BEGIN snippet:documentacion-estandar hash:97827d7f58def4c6924124a9d9a835a1 -->
## Estándar de documentación del repo

> Propagado desde `recursos-compartidos/snippets/documentacion-estandar.md`; no editar aquí. Convención completa: [documentacion.md](https://github.com/FaroNovaCorp/recursos-compartidos/blob/main/docs/estandares/documentacion.md).

Doc técnica bajo `docs/` (`adr/`, `arquitectura/`, `estandares/`, `datos/`, cada una con `README.md` índice). ADRs: uno por archivo en `docs/adr/`, numeración por repo desde `ADR-001`, plantilla `templates/adr-template.md`. Diagramas en Mermaid embebido (C4, `flowchart`, `erDiagram`). Docs nuevos con front-matter YAML (`title`, `repo`, `seccion`, `generado`); los generados desde código llevan `generado: true` y no se editan a mano.
<!-- END snippet:documentacion-estandar -->

<!-- BEGIN snippet:estandar-costos-ci hash:18a0a69bf18e90815d853a076cdd9f30 -->
## Estándar de costo de CI (GitHub Actions)

> Propagado desde `recursos-compartidos/snippets/estandar-costos-ci.md`; no editar aquí. Texto completo: [costos-ci.md](https://github.com/FaroNovaCorp/recursos-compartidos/blob/main/docs/estandares/costos-ci.md).

GitHub factura cada job al minuto entero hacia arriba y cada job es una VM: consolidar, no paralelizar. Un job con steps nombrados en vez de muchos jobs cortos. Secret scan solo en `pull_request` (no `push:[main]`; excepción: repo sin `pull_request`). `ci.yml` reusable embebido en `deploy.yml`, no además standalone (antes de quitar el standalone, verificar que los required checks salen del run embebido, `test / *`). Docs-only: `paths-ignore` + gemelo passthrough para los required checks. `timeout-minutes` por job (nunca en `terraform apply`), tools pineadas, retry con timeout en descargas. `concurrency` con `cancel-in-progress` solo en workflows que no despliegan; nunca en `terraform apply` ni en `merge_group`.

**Antes de empujar:** juntar los commits locales y empujar una vez; un push encima cancela la suite en curso. Plan y docs del PR en el mismo push que el código, no después. `/revisar-cambio` local antes del primer push. No mergear `main` a la rama después del verde si no hay conflicto: la cola integra. Correr local lo que corre el job de lint, tipos y guards; la receta de comandos es por repo (`agente-de-monitoreo`: `docs/ci-cd.md` § «Antes de empujar»).
<!-- END snippet:estandar-costos-ci -->

<!-- BEGIN snippet:flujo-merges hash:867d80d93396366cd7f1b60d91d8c33e -->
## Flujo de merges

> Propagado desde `recursos-compartidos/snippets/flujo-merges.md`; no editar aquí. Detalle: [flujo-merges.md](https://github.com/FaroNovaCorp/recursos-compartidos/blob/main/docs/estandares/flujo-merges.md).

PR en verde → `gh pr merge <N> --merge`: encola donde hay Merge Queue, mergea directo donde no. Verificar que quedó `MERGED`, no solo encolado. Expulsión de cola → `/mi-merge`, arreglar y volver a `gh pr merge <N> --merge`: `gh run rerun` NO re-encola. Única excepción, `agente-de-monitoreo` con el deploy de `main` caído por el shard 4 flaky: `gh run rerun --failed` sobre el MISMO SHA, sin re-encolar.
<!-- END snippet:flujo-merges -->

<!-- BEGIN snippet:flujo-secretos hash:fe2a43609a887656850abde4309c98d8 -->
## Flujo de entrega de secretos a una sesión de Claude Code

> Propagado desde `recursos-compartidos/snippets/flujo-secretos.md`; no editar aquí. Texto completo: [flujo-secretos.md](https://github.com/FaroNovaCorp/recursos-compartidos/blob/main/docs/estandares/flujo-secretos.md).

Un secreto nunca se pega en el chat, ni citado, ni «solo para verificar». (1) Código TOTP/MFA: no es secreto; se teclea directo en la ventana de la sesión que lo necesita; antes se le dice en cuál (nombre y color); nadie lo relaya. (2) Secreto persistente: a AWS Secrets Manager con el prefijo `!`, del portapapeles a stdin: `! rtk proxy bash -c 'set -o pipefail; pbpaste | aws secretsmanager create-secret --name <ruta> --secret-string file:///dev/stdin --region us-east-1'` (requiere admin por `assume-role` con MFA desde el profile BASE). (3) Comando largo: la sesión lo escribe a `/tmp/<propósito>.sh` y el developer corre una línea corta; solo argumentos efímeros (un MFA sí, un secreto persistente jamás), las credenciales temporales mueren con el script y este imprime solo resultados no sensibles. (4) Después, copiar otra cosa: macOS guarda historial del portapapeles. En macOS 26+, además, borrar la entrada de la llave del historial de portapapeles de Spotlight, o tenerlo apagado: copiar otra cosa no la saca de ahí. A mano; sin comando oficial.
<!-- END snippet:flujo-secretos -->

<!-- BEGIN snippet:merge-only hash:c2daffaaafbda196fd3ca0c9e8e1fe36 -->
## Política de merge: solo merge commit

> Propagado desde `recursos-compartidos/snippets/merge-only.md`; no editar aquí. Decisión: [ADR-007](https://github.com/FaroNovaCorp/recursos-compartidos/blob/main/adr/ADR-007-merge-only-strategy.md); operación completa: [flujo-merges.md](https://github.com/FaroNovaCorp/recursos-compartidos/blob/main/docs/estandares/flujo-merges.md).

Merge commit es la única estrategia: `gh pr merge <N> --merge`; `--squash` y `--rebase` fallan. En repos con Merge Queue ese comando encola, y el merge directo devuelve `HTTP 405`: esperado, nadie salta la cola. Qué repos tienen cola: `QUEUE_REPOS` en `hooks/block-direct-merge.sh`, o `gh api repos/<owner>/<repo>/rules/branches/main`. `removed_from_merge_queue` solo es expulsión si NO hay `merged`; desempate: `gh pr view <N> --json state`. Ya no existe el Merge Captain.
<!-- END snippet:merge-only -->

<!-- BEGIN snippet:subagentes-anidados hash:8404ae06d9a36bb2c752efd5b2ab9ffe -->
## Subagentes Claude — profundidad opcional (anidamiento)

> Propagado desde `recursos-compartidos/snippets/subagentes-anidados.md`; no editar aquí. Texto completo: [subagentes-anidados.md](https://github.com/FaroNovaCorp/recursos-compartidos/blob/main/docs/estandares/subagentes-anidados.md).

Un subagente Claude puede lanzar los suyos, hasta 5 niveles (Claude Code 2.1.172+). Solo si la sub-tarea es grande y divisible; para un solo contexto, agente plano. Revisores externos (Codex, Gemini) no anidan. Da más agentes, no más contexto por agente. Agente aislado con hook de rtk: todo `git` que rtk reescribe queda bloqueado. Implementación → `/usr/bin/git` solo sobre su árbol. Revisor → sin `git` ni `/usr/bin/git`. Orquestador de `/revisar-*` → sesión principal. Detalle: § «`git` en un agente aislado».
<!-- END snippet:subagentes-anidados -->
