"""Pruebas de verificar-acciones.yml (P-1047, SHP2).

Corre el script REAL del step «Verificar acciones», extraído del YAML por
extract_step_script.py: nunca una copia mantenida a mano. GitHub se simula
(FakeGH); sin red, sin zizmor real, sin runner.

Uso: python3 -m unittest discover -s .github/tests -p 'test_*.py'
Requiere PyYAML (lo mismo que extract_step_script.py).
"""

import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import types
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
WORKFLOW = os.path.join(AQUI, "..", "workflows", "verificar-acciones.yml")

LEGIT = "3d3c42e5aac5ba805825da76410c181273ba90b1"      # actions/checkout v7.0.1 (main)
NUEVO = "1111111111111111111111111111111111111111"      # v7.0.2 (main)
IMPOSTOR = "70379aad1a8b40919ce8b382d3cd7d0315cde1d0"   # solo en un fork
SOLO_TAG = "2222222222222222222222222222222222222222"   # v6.9.9 fuera de toda rama
RELEASE = "3333333333333333333333333333333333333333"    # v6.0.0 en releases/v6
PROPIO_OK = "69fd874d44e30b5b306843c14c8881373fa290a5"  # FaroNovaCorp/.github main
PROPIO_FUERA = "4444444444444444444444444444444444444444"  # rama sin mergear


def cargar_script():
    codigo = subprocess.run(
        [sys.executable, os.path.join(AQUI, "extract_step_script.py"), WORKFLOW,
         "verificar", "Verificar acciones"],
        check=True, capture_output=True, text=True).stdout
    mod = types.ModuleType("verificar_acciones")
    exec(compile(codigo, WORKFLOW, "exec"), mod.__dict__)
    return mod


class FakeGH:
    """GitHub simulado: lo justo para las rutas que usa el script."""

    def __init__(self):
        self.repos = {
            "actions/checkout": {"full_name": "actions/checkout", "default_branch": "main",
                                 "owner": {"login": "actions"}},
            "faronovacorp/.github": {"full_name": "FaroNovaCorp/.github", "default_branch": "main",
                                     "owner": {"login": "FaroNovaCorp"}},
        }
        self.commits = {LEGIT, NUEVO, IMPOSTOR, SOLO_TAG, RELEASE, PROPIO_OK, PROPIO_FUERA}
        self.ramas = {
            "actions/checkout": {"main": {LEGIT, NUEVO}, "releases/v6": {RELEASE}},
            "faronovacorp/.github": {"main": {PROPIO_OK}, "feat/x": {PROPIO_FUERA}},
        }
        # tag → (tipo, sha); `tag` = anotado (objeto tag → commit)
        self.tags = {
            ("actions/checkout", "v7.0.1"): ("tag", "a" * 40),
            ("actions/checkout", "v7.0.2"): ("commit", NUEVO),
            ("actions/checkout", "v6.9.9"): ("commit", SOLO_TAG),
            ("actions/checkout", "v6.0.0"): ("commit", RELEASE),
        }
        self.tag_objs = {"a" * 40: LEGIT}
        self.arboles = {}
        self.blobs = {}
        self.llamadas = []

    def api(self, ruta):
        self.llamadas.append(ruta)
        ruta = ruta.split("?")[0]
        m = re.fullmatch(r"repos/([^/]+/[^/]+)", ruta)
        if m:
            r = self.repos.get(m.group(1).lower())
            return (200, r) if r else (404, None)
        m = re.fullmatch(r"repos/([^/]+/[^/]+)/commits/([0-9a-f]{40})", ruta)
        if m:
            return (200, {"sha": m.group(2)}) if m.group(2) in self.commits else (422, None)
        m = re.fullmatch(r"repos/([^/]+/[^/]+)/compare/(.+)\.\.\.([0-9a-f]{40})", ruta)
        if m:
            en = self.ramas.get(m.group(1).lower(), {}).get(m.group(2), set())
            return 200, {"status": "behind" if m.group(3) in en else "diverged"}
        m = re.fullmatch(r"repos/([^/]+/[^/]+)/git/ref/tags/(.+)", ruta)
        if m:
            t = self.tags.get((m.group(1).lower(), m.group(2)))
            return (200, {"object": {"type": t[0], "sha": t[1]}}) if t else (404, None)
        m = re.fullmatch(r"repos/([^/]+/[^/]+)/git/tags/([0-9a-f]{40})", ruta)
        if m:
            return 200, {"object": {"type": "commit", "sha": self.tag_objs[m.group(2)]}}
        m = re.fullmatch(r"repos/([^/]+/[^/]+)/git/trees/(\w+)", ruta)
        if m:
            arbol = self.arboles[m.group(2)]
            return 200, {"truncated": False, "tree": [
                {"path": p, "type": "blob", "sha": s} for p, s in arbol.items()]}
        m = re.fullmatch(r"repos/([^/]+/[^/]+)/git/blobs/(\w+)", ruta)
        if m:
            return 200, {"content": base64.b64encode(self.blobs[m.group(2)].encode()).decode()}
        raise AssertionError(f"ruta no simulada: {ruta}")

    def api_paginado(self, ruta, tope=1000):
        m = re.fullmatch(r"repos/([^/]+/[^/]+)/branches\?per_page=100", ruta)
        assert m, ruta
        ramas = self.ramas.get(m.group(1).lower(), {})
        return [{"name": n, "commit": {"sha": "f" * 40}} for n in ramas]


BASE = """name: ci
on: pull_request
jobs:
  a:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{LEGIT} # v7.0.1
      - run: echo hola
"""


def wf(paso):
    return BASE.replace("{LEGIT}", LEGIT).replace("      - run: echo hola\n", paso + "      - run: echo hola\n")


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = cargar_script()

    def setUp(self):
        self.gh = FakeGH()
        self.m.api = self.gh.api
        self.m.api_paginado = self.gh.api_paginado

    def revisar(self, head, base=None):
        base = BASE.replace("{LEGIT}", LEGIT) if base is None else base
        return self.m.revisar_archivo(".github/workflows/ci.yml", base, head, self.m.Verificador())

    def errores(self, hallazgos):
        return [h for h in hallazgos if h["nivel"] == "error"]


class TestVerificacionPropia(Base):
    def test_bump_legitimo_pasa(self):
        head = BASE.replace("{LEGIT}", NUEVO).replace("v7.0.1", "v7.0.2")
        self.assertEqual(self.revisar(head), [])

    def test_impostor_de_fork_bloquea(self):
        head = BASE.replace("{LEGIT}", IMPOSTOR).replace("v7.0.1", "v6.0.2")
        errs = self.errores(self.revisar(head))
        self.assertTrue(any("no está en ninguna rama" in e["motivo"] for e in errs), errs)
        self.assertTrue(any("v6.0.2" in e["motivo"] for e in errs), errs)

    def test_tag_movido_fuera_de_ramas_bloquea(self):
        head = BASE.replace("{LEGIT}", SOLO_TAG).replace("v7.0.1", "v6.9.9")
        errs = self.errores(self.revisar(head))
        self.assertEqual(len(errs), 1, errs)
        self.assertIn("no está en ninguna rama", errs[0]["motivo"])

    def test_commit_en_rama_de_release_pasa(self):
        head = BASE.replace("{LEGIT}", RELEASE).replace("v7.0.1", "v6.0.0")
        self.assertEqual(self.revisar(head), [])

    def test_comentario_desfasado_bloquea(self):
        head = BASE.replace("{LEGIT}", NUEVO)  # comentario sigue diciendo v7.0.1
        errs = self.errores(self.revisar(head))
        self.assertEqual(len(errs), 1, errs)
        self.assertIn("v7.0.1 apunta a", errs[0]["motivo"])

    def test_tag_inexistente_bloquea(self):
        head = BASE.replace("{LEGIT}", NUEVO).replace("v7.0.1", "v9.9.9")
        errs = self.errores(self.revisar(head))
        self.assertIn("no existe", errs[0]["motivo"])

    def test_tercero_sin_version_bloquea(self):
        head = BASE.replace("{LEGIT}", NUEVO).replace(" # v7.0.1", "")
        errs = self.errores(self.revisar(head))
        self.assertIn("sin versión", errs[0]["motivo"])

    def test_tag_anotado_se_pela(self):
        head = wf(f"      - uses: actions/checkout@{LEGIT} # v7.0.1\n")
        self.assertEqual(self.revisar(head, base=""), [])

    def test_sin_sha_bloquea(self):
        head = wf("      - uses: actions/checkout@v7\n")
        errs = self.errores(self.revisar(head))
        self.assertIn("SHA completo", errs[0]["motivo"])

    def test_commit_inexistente_bloquea(self):
        head = BASE.replace("{LEGIT}", "9" * 40)
        errs = self.errores(self.revisar(head))
        self.assertTrue(any("no existe en actions/checkout" in e["motivo"] for e in errs), errs)

    def test_repo_inexistente_bloquea(self):
        head = wf(f"      - uses: nadie/nada@{NUEVO} # v1.0.0\n")
        errs = self.errores(self.revisar(head))
        self.assertTrue(any("no se pudo leer el repo" in e["motivo"] for e in errs), errs)

    def test_reusable_propio_en_main_pasa_sin_version(self):
        head = BASE.replace("{LEGIT}", LEGIT) + (
            "  b:\n"
            f"    uses: FaroNovaCorp/.github/.github/workflows/secret-scan.yml@{PROPIO_OK}"
            " # re-pin P-144 (D-1275/D-1287, PR .github#19)\n")
        self.assertEqual(self.revisar(head), [])

    def test_reusable_propio_sin_mergear_bloquea(self):
        head = BASE.replace("{LEGIT}", LEGIT) + (
            "  b:\n"
            f"    uses: FaroNovaCorp/.github/.github/workflows/secret-scan.yml@{PROPIO_FUERA}\n")
        errs = self.errores(self.revisar(head))
        self.assertIn("reusable propio fuera de `main`", errs[0]["motivo"])

    def test_escape_yaml_bloquea(self):
        # "\x61" = "a": el valor real es actions/checkout@IMPOSTOR, oculto en el texto.
        head = wf(f'      - uses: "\\x61ctions/checkout@{IMPOSTOR}" # v7.0.1\n')
        errs = self.errores(self.revisar(head))
        self.assertTrue(any("no aparece literal" in e["motivo"] for e in errs), errs)

    def test_alias_yaml_con_ancla_en_linea_nueva_se_verifica(self):
        head = BASE.replace("{LEGIT}", LEGIT) + (
            "  b:\n    runs-on: ubuntu-latest\n    steps:\n"
            f"      - uses: &co actions/checkout@{IMPOSTOR} # v7.0.1\n"
            "      - uses: *co\n")
        errs = self.errores(self.revisar(head))
        self.assertTrue(any("no está en ninguna rama" in e["motivo"] for e in errs), errs)

    def test_uso_previo_intacto_no_se_revisa(self):
        # La base ya tenía un comentario desfasado; el PR toca otra línea.
        base = BASE.replace("{LEGIT}", NUEVO)
        head = base.replace("echo hola", "echo chao")
        self.assertEqual(self.revisar(head, base=base), [])
        self.assertFalse(any("compare" in r for r in self.gh.llamadas))

    def test_locales_y_docker(self):
        head = wf("      - uses: ./.github/actions/x\n"
                  "      - uses: docker://alpine@sha256:" + "0" * 64 + "\n"
                  "      - uses: docker://alpine:3\n")
        hall = self.revisar(head)
        self.assertEqual(self.errores(hall), [])
        self.assertEqual(len(hall), 1)
        self.assertIn("docker", hall[0]["motivo"])

    def test_yaml_invalido_bloquea(self):
        errs = self.errores(self.revisar("jobs: [\n"))
        self.assertIn("YAML", errs[0]["motivo"])

    def test_cache_por_par(self):
        head = wf(f"      - uses: actions/checkout@{NUEVO} # v7.0.2\n"
                  f"      - uses: actions/checkout@{NUEVO} # v7.0.2\n")
        self.assertEqual(self.revisar(head), [])
        self.assertEqual(sum(r.startswith("repos/actions/checkout/compare") for r in self.gh.llamadas), 1)


class TestPiezas(Base):
    def test_es_relevante(self):
        si = [".github/workflows/ci.yml", ".github/workflows/x.yaml", "action.yml",
              ".github/actions/a/action.yaml", "sub/dir/action.yml"]
        no = [".github/dependabot.yml", ".github/workflows/sub/x.yml", "README.md",
              ".github/workflows/x.json", "docs/workflow.yml"]
        for p in si:
            self.assertTrue(self.m.es_relevante(p), p)
        for p in no:
            self.assertFalse(self.m.es_relevante(p), p)

    def test_version_en_comentario(self):
        casos = {"v7.0.1": "v7.0.1", "v7": "v7", "7.0.1": "7.0.1", "tag=v7.0.1": "v7.0.1",
                 "v2.21.1 (pre, main y post)": "v2.21.1", "v1.2.3-rc.1": "v1.2.3-rc.1",
                 "re-pin P-144: detectar (D-1275/D-1287, PR .github#19)": None, "": None}
        for texto, esperado in casos.items():
            m = self.m.VER_RE.search(texto)
            self.assertEqual(m.group(1) if m else None, esperado, texto)

    def test_comentario(self):
        u = f"actions/checkout@{LEGIT}"
        self.assertEqual(self.m.comentario(f"  - uses: {u} # v7.0.1", u), "v7.0.1")
        self.assertEqual(self.m.comentario(f"  - uses: '{u}'  #v7", u), "v7")
        self.assertEqual(self.m.comentario(f"  - uses: {u}", u), "")
        self.assertFalse(self.m.aparece(u, f"  - uses: evil-{u} # v7.0.1"))

    def test_detectar(self):
        self.gh.arboles = {
            "b": {".github/workflows/ci.yml": "x1", "README.md": "r1", "action.yml": "a1"},
            "h": {".github/workflows/ci.yml": "x2", "README.md": "r2", "action.yml": "a1",
                  ".github/workflows/nuevo.yml": "n1"},
        }
        cambios = self.m.detectar("FaroNovaCorp/x", "b", "h")
        self.assertEqual(cambios, [
            {"ruta": ".github/workflows/ci.yml", "base": "x1", "head": "x2"},
            {"ruta": ".github/workflows/nuevo.yml", "base": None, "head": "n1"},
        ])

    def test_zizmor_solo_bloquea_lineas_nuevas(self):
        base = BASE.replace("{LEGIT}", LEGIT)
        head = base.replace("echo hola", "echo chao")
        self.m.correr_zizmor = lambda archivo: [
            ("ref-version-mismatch", 7, 7, "desfase previo"), ("impostor-commit", 8, 8, "nuevo")]
        with tempfile.TemporaryDirectory() as d:
            hall = self.m.revisar_zizmor(".github/workflows/ci.yml", base, head, d)
        self.assertEqual([h["nivel"] for h in hall], ["aviso", "error"])
        self.m.correr_zizmor = lambda archivo: None
        with tempfile.TemporaryDirectory() as d:
            hall = self.m.revisar_zizmor(".github/workflows/ci.yml", base, head, d)
        self.assertEqual(hall[0]["nivel"], "aviso")

    def test_informar_escapa_comandos(self, ):
        hall = [self.m.hallazgo("error", "a,b:c.yml", 3, "x/y@z\n::stop-commands::t", "malo\nmás")]
        with tempfile.TemporaryDirectory() as d:
            os.environ["GITHUB_STEP_SUMMARY"] = os.path.join(d, "s.md")
            from io import StringIO
            from contextlib import redirect_stdout
            buf = StringIO()
            with redirect_stdout(buf):
                n = self.m.informar(hall, [{}])
            del os.environ["GITHUB_STEP_SUMMARY"]
        self.assertEqual(n, 1)
        salida = buf.getvalue().splitlines()
        self.assertTrue(salida[0].startswith("::error file=a%2Cb%3Ac.yml,line=3,"), salida[0])
        self.assertFalse(any(l.startswith("::stop-commands") for l in salida))


class TestMain(Base):
    def correr(self, evento, nombre, cambios_en_head):
        self.gh.arboles = {"b": {".github/workflows/ci.yml": "x1"},
                           "h": {".github/workflows/ci.yml": "x2" if cambios_en_head else "x1"}}
        self.gh.blobs = {"x1": BASE.replace("{LEGIT}", LEGIT),
                         "x2": BASE.replace("{LEGIT}", IMPOSTOR)}
        instalado = []
        self.m.instalar = lambda: instalado.append(True)
        self.m.correr_zizmor = lambda archivo: []
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "ev.json")
            with open(ruta, "w") as f:
                json.dump(evento, f)
            os.environ.update({"GITHUB_EVENT_PATH": ruta, "GITHUB_EVENT_NAME": nombre,
                               "GITHUB_REPOSITORY": "FaroNovaCorp/x"})
            from io import StringIO
            from contextlib import redirect_stdout
            with redirect_stdout(StringIO()):
                rc = self.m.main()
        return rc, instalado

    def test_pr_sin_cambios_relevantes_no_instala(self):
        rc, inst = self.correr({"pull_request": {"base": {"sha": "b"}, "head": {"sha": "h"}}},
                               "pull_request", False)
        self.assertEqual((rc, inst), (0, []))

    def test_pr_con_impostor_falla(self):
        rc, inst = self.correr({"pull_request": {"base": {"sha": "b"}, "head": {"sha": "h"}}},
                               "pull_request", True)
        self.assertEqual((rc, inst), (1, [True]))

    def test_cola_con_impostor_falla(self):
        rc, _ = self.correr({"merge_group": {"base_sha": "b", "head_sha": "h"}}, "merge_group", True)
        self.assertEqual(rc, 1)

    def test_evento_no_soportado_falla(self):
        rc, _ = self.correr({}, "push", True)
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
