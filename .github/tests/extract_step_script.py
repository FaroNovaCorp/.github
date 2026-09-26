#!/usr/bin/env python3
"""Imprime el `run:` de un step por nombre, tal cual vive en el workflow.

Uso: extract_step_script.py <workflow.yml> <job_id> <nombre del step>

Existe para que dependabot-automerge.bats corra el script REAL que GitHub
Actions ejecuta -- nunca una copia mantenida a mano que puede quedar
desincronizada del YAML.
"""
import sys

import yaml


def main() -> int:
    if len(sys.argv) != 4:
        print(f"uso: {sys.argv[0]} <workflow.yml> <job_id> <nombre del step>", file=sys.stderr)
        return 2

    workflow_path, job_id, step_name = sys.argv[1], sys.argv[2], sys.argv[3]

    with open(workflow_path, encoding="utf-8") as f:
        doc = yaml.safe_load(f)

    steps = doc["jobs"][job_id]["steps"]
    for step in steps:
        if step.get("name") == step_name:
            sys.stdout.write(step["run"])
            return 0

    print(f"ERROR: step '{step_name}' no encontrado en job '{job_id}'", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
