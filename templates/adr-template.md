<!--
  Plantilla: adr-template.md
  Source of truth: recursos-compartidos/templates/adr-template.md
  La propaga `./scripts/propagar.sh` a <repo>/templates/ en cada repo FaroNova.
  NO la edites en el destino — el cambio se hace aquí y se re-propaga.

  Cómo usar:
    1. Copia este archivo a docs/adr/ADR-NNN-titulo-slug.md (en recursos-compartidos: adr/ADR-NNN-...).
    2. NNN = siguiente número de la secuencia de TU repo (cada repo empieza en 001; no se reutilizan).
    3. titulo-slug = título en minúsculas, sin acentos, separado por guiones.
    4. Borra este comentario y las notas [entre corchetes], completa cada sección.
    5. Agrega la fila a docs/adr/README.md (tabla ADR | Título | Estado | Fecha).

  Estándar completo: recursos-compartidos/adr/estandar-adr.md
-->

# ADR-NNN: Título de la decisión

**Estado:** Vigente
**Fecha:** YYYY-MM-DD

## Contexto

[Por qué surgió esta decisión. Qué problema o necesidad la motivó. Explicar sin
asumir que el lector conoce el trasfondo.]

## Decisión

[Qué se decidió. Ser concreto y específico: incluir configuraciones clave,
patrones de código, o referencias a la implementación real.]

## Razonamiento

[Opciones evaluadas y por qué se descartaron, justificación de la elegida,
trade-offs considerados. Esto es lo más valioso a futuro.]

## Consecuencias

[Qué implica la decisión: beneficios y limitaciones, deuda técnica si la hay,
plan de migración si aplica.]
