#!/usr/bin/env bats
# Prueba real del step "Esperar checks y habilitar auto-merge"
# (dependabot-automerge.yml, D-1275/D-1287).
#
# Corre el `run:` EXACTO del workflow -- extraido del YAML por
# extract_step_script.py, nunca una copia mantenida a mano -- con `gh` y
# `timeout` mockeados. Sin red, sin PR real, sin runner de Actions.
#
# `bash -eo pipefail`, siempre: es el shell default de un `run:` en Actions
# (`bash --noprofile --norc -eo pipefail {0}`). Correr con `bash "$SCRIPT"` a
# secas (sin `-e`) fue justamente lo que dejo pasar sin verse el hallazgo
# CRITICO de /revisar-pr #19 -- confirmado 3/3 por los revisores (Seguridad,
# Arquitectura, Calidad): con `-e` heredado, un `timeout ... gh pr checks`
# en rojo abortaba el script ANTES de capturar `CHECKS_EXIT`, saltandose por
# completo la rama que arma auto-merge igual. `set +e` dentro del propio
# script (ver dependabot-automerge.yml) es lo que lo neutraliza -- esta
# prueba solo es real si reproduce el `-e` que lo hubiera destapado.
#
# `timeout` se mockea: macOS no trae `timeout` de coreutils (el runner
# `ubuntu-latest` real si). El mock ignora la duracion y ejecuta el comando
# tal cual, para que la prueba corra igual en ambos SO.
#
# `jq` NO se mockea -- es una herramienta real, igual que en el runner.

setup() {
  WORKFLOW="$BATS_TEST_DIRNAME/../workflows/dependabot-automerge.yml"
  SCRIPT="$BATS_TEST_TMPDIR/step.sh"
  python3 "$BATS_TEST_DIRNAME/extract_step_script.py" \
    "$WORKFLOW" automerge "Esperar checks y habilitar auto-merge" > "$SCRIPT"

  export PR_URL="https://github.com/FaroNovaCorp/fake-repo/pull/1"
  export MERGE_METHOD="merge"
  export WAIT_MINUTES="1"
  export GH_TOKEN="fake-token"
  export GITHUB_STEP_SUMMARY="$BATS_TEST_TMPDIR/summary.md"
  # Ventana de gracia achicada -- ver comentario del step sobre estas dos env vars.
  export GRACE_SECONDS="2"
  export GRACE_POLL_SECONDS="1"

  MOCKDIR="$BATS_TEST_TMPDIR/bin"
  mkdir -p "$MOCKDIR"
  export PATH="$MOCKDIR:$PATH"

  cat > "$MOCKDIR/timeout" <<'EOF'
#!/usr/bin/env bash
shift
exec "$@"
EOF
  chmod +x "$MOCKDIR/timeout"
}

run_step() {
  run bash -eo pipefail "$SCRIPT"
}

# $1 = cuerpo del mock, un `case "$1 $2"` sobre los sub-comandos de gh que
# le interesan a la prueba.
write_gh_mock() {
  cat > "$MOCKDIR/gh" <<EOF
#!/usr/bin/env bash
echo "gh \$*" >> "$BATS_TEST_TMPDIR/gh.log"
$1
EOF
  chmod +x "$MOCKDIR/gh"
}

@test "checks verdes y el PR se mergea dentro de la ventana de gracia: exit 0, sin ::error::" {
  write_gh_mock '
    case "$1 $2" in
      "pr checks") exit 0 ;;
      "pr merge") exit 0 ;;
      "api graphql") echo "{\"data\":{\"resource\":{\"state\":\"MERGED\",\"isInMergeQueue\":false}}}" ;;
    esac
  '
  run_step
  [ "$status" -eq 0 ]
  [[ "$output" != *"::error"* ]]
  grep -q "pr merge --auto" "$BATS_TEST_TMPDIR/gh.log"
}

@test "checks en rojo (bash -e real): arma auto-merge, exit 0, sin vigilancia ni ::error:: (regresion del hallazgo CRITICO)" {
  write_gh_mock '
    case "$1 $2" in
      "pr checks") exit 1 ;;
      "pr merge") exit 0 ;;
      "api graphql") echo "{\"data\":{\"resource\":{\"state\":\"OPEN\",\"isInMergeQueue\":false}}}" ;;
    esac
  '
  run_step
  [ "$status" -eq 0 ]
  [[ "$output" == *"Habilito auto-merge igual"* ]]
  [[ "$output" != *"::error"* ]]
  grep -q "pr merge --auto" "$BATS_TEST_TMPDIR/gh.log"
  # Con checks en rojo nunca debe llegar a la vigilancia (eso es solo tras
  # armar con exito sobre checks verdes).
  ! grep -q "api graphql" "$BATS_TEST_TMPDIR/gh.log"
}

@test "checks verdes pero el PR nunca se completa: exit 1, ::error:: y Job Summary (bug D-1275/D-1287)" {
  write_gh_mock '
    case "$1 $2" in
      "pr checks") exit 0 ;;
      "pr merge") exit 0 ;;
      "api graphql") echo "{\"data\":{\"resource\":{\"state\":\"OPEN\",\"isInMergeQueue\":false}}}" ;;
    esac
  '
  run_step
  [ "$status" -eq 1 ]
  [[ "$output" == *"::error title=Auto-merge armado sin completar"* ]]
  grep -q "auto-merge armado, sin completar" "$GITHUB_STEP_SUMMARY"
}

@test "checks verdes y el PR queda progresando en Merge Queue: NO es el bug, exit 0 sin ::error:: (hallazgo ALTO)" {
  write_gh_mock '
    case "$1 $2" in
      "pr checks") exit 0 ;;
      "pr merge") exit 0 ;;
      "api graphql") echo "{\"data\":{\"resource\":{\"state\":\"OPEN\",\"isInMergeQueue\":true}}}" ;;
    esac
  '
  run_step
  [ "$status" -eq 0 ]
  [[ "$output" != *"::error"* ]]
  [[ "$output" == *"progresando"* ]]
}

@test "gh api graphql falla (rate limit / red): reintenta con ::warning::, no confunde con 'nunca encolo'" {
  cat > "$MOCKDIR/gh" <<EOF
#!/usr/bin/env bash
echo "gh \$*" >> "$BATS_TEST_TMPDIR/gh.log"
case "\$1 \$2" in
  "pr checks") exit 0 ;;
  "pr merge") exit 0 ;;
  "api graphql")
    N=\$(grep -c "api graphql" "$BATS_TEST_TMPDIR/gh.log" 2>/dev/null || echo 0)
    if [ "\$N" -le 1 ]; then
      echo "fake rate limit error" >&2
      exit 1
    fi
    echo '{"data":{"resource":{"state":"MERGED","isInMergeQueue":false}}}'
    ;;
esac
EOF
  chmod +x "$MOCKDIR/gh"
  run_step
  [ "$status" -eq 0 ]
  [[ "$output" == *"::warning::gh api graphql fallo"* ]]
  [[ "$output" != *"::error"* ]]
}

@test "GRACE_SECONDS invalido: falla ruidoso, no silencioso (hallazgo BAJO)" {
  export GRACE_SECONDS="no-numerico"
  write_gh_mock '
    case "$1 $2" in
      "pr checks") exit 0 ;;
      "pr merge") exit 0 ;;
    esac
  '
  run_step
  [ "$status" -eq 1 ]
  [[ "$output" == *"::error::GRACE_SECONDS invalido"* ]]
}
