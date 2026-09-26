#!/usr/bin/env bats
# Prueba real del step "Esperar checks y habilitar auto-merge"
# (dependabot-automerge.yml, D-1275/D-1287).
#
# Corre el `run:` EXACTO del workflow -- extraido del YAML por
# extract_step_script.py, nunca una copia mantenida a mano -- con `gh` y
# `timeout` mockeados. Sin red, sin PR real, sin runner de Actions.
#
# `timeout` se mockea tambien: macOS no trae `timeout` de coreutils (el
# runner `ubuntu-latest` real si). El mock ignora la duracion y ejecuta el
# comando tal cual, para que la prueba corra igual en ambos SO.

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
      "pr view") echo MERGED ;;
    esac
  '
  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  [[ "$output" != *"::error"* ]]
  grep -q "pr merge --auto" "$BATS_TEST_TMPDIR/gh.log"
}

@test "checks en rojo: arma auto-merge, exit 0, sin vigilancia ni ::error::" {
  write_gh_mock '
    case "$1 $2" in
      "pr checks") exit 1 ;;
      "pr merge") exit 0 ;;
      "pr view") echo OPEN ;;
    esac
  '
  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"Habilito auto-merge igual"* ]]
  [[ "$output" != *"::error"* ]]
  # Con checks en rojo nunca debe llamar `gh pr view` (esa es la vigilancia
  # posterior al armado exitoso, que aqui no corresponde).
  ! grep -q "pr view" "$BATS_TEST_TMPDIR/gh.log"
}

@test "checks verdes pero el PR nunca se completa: exit 1, ::error:: y Job Summary (bug D-1275/D-1287)" {
  write_gh_mock '
    case "$1 $2" in
      "pr checks") exit 0 ;;
      "pr merge") exit 0 ;;
      "pr view") echo OPEN ;;
    esac
  '
  run bash "$SCRIPT"
  [ "$status" -eq 1 ]
  [[ "$output" == *"::error title=Auto-merge armado sin completar"* ]]
  grep -q "auto-merge armado, sin completar" "$GITHUB_STEP_SUMMARY"
}
