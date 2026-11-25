"""Pruebas de verificar-acciones.yml (P-1047, SHP2).

Corre el script REAL del step «Verificar acciones», extraído del YAML por
extract_step_script.py: nunca una copia mantenida a mano. GitHub se simula
(FakeGH); sin red, sin zizmor real, sin runner.

Uso: python3 -m unittest discover -s .github/tests -p 'test_*.py'
Requiere PyYAML (lo mismo que extract_step_script.py).
"""

import base64
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import types
import unittest
import urllib.error
from contextlib import redirect_stdout
from unittest import mock

AQUI = os.path.dirname(os.path.abspath(__file__))
WORKFLOW = os.path.join(AQUI, "..", "workflows", "verificar-acciones.yml")

LEGIT = "3d3c42e5aac5ba805825da76410c181273ba90b1"      # actions/checkout v7.0.1 (main)
NUEVO = "1111111111111111111111111111111111111111"      # v7.0.2 (main); el flotante v7 apunta aquí
IMPOSTOR = "70379aad1a8b40919ce8b382d3cd7d0315cde1d0"   # solo en un fork
SOLO_TAG = "2222222222222222222222222222222222222222"   # v6.9.9 fuera de toda rama
RELEASE = "3333333333333333333333333333333333333333"    # v6.0.0 en releases/v6
LEJANO = "5555555555555555555555555555555555555555"     # v5.0.0 en la rama 45 (después de las primeras 40)
PROPIO_OK = "69fd874d44e30b5b306843c14c8881373fa290a5"  # FaroNovaCorp/.github main
PROPIO_FUERA = "4444444444444444444444444444444444444444"  # rama sin mergear

# Salida real de zizmor 1.32.0 (--format json) sobre una línea con el impostor, recortada.
ZIZMOR_JSON = json.dumps([
    {"ident": "impostor-commit", "desc": "commit with no history in referenced repository",
     "locations": [{"symbolic": {"kind": "Primary"},
                    "concrete": {"location": {"start_point": {"row": 6, "column": 8},
                                              "end_point": {"row": 6, "column": 70}}}}]},
    {"ident": "artipacked", "desc": "credential persistence",
     "locations": [{"symbolic": {"kind": "Primary"},
                    "concrete": {"location": {"start_point": {"row": 6, "column": 8},
                                              "end_point": {"row": 6, "column": 70}}}}]},
])


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
        self.commits = {LEGIT, NUEVO, IMPOSTOR, SOLO_TAG, RELEASE, LEJANO, PROPIO_OK, PROPIO_FUERA}
        ramas = {"main": {LEGIT, NUEVO}, "releases/v6": {RELEASE}}
        for i in range(60):
            ramas[f"z-rama-{i:02d}"] = {LEJANO} if i == 45 else set()
        self.ramas = {"actions/checkout": ramas,
                      "faronovacorp/.github": {"main": {PROPIO_OK}, "feat/x": {PROPIO_FUERA}}}
        # tag → (tipo, sha); `tag` = anotado (objeto tag → commit)
        self.tags = {
            ("actions/checkout", "v7.0.1"): ("tag", "a" * 40),
            ("actions/checkout", "v7.0.2"): ("commit", NUEVO),
            ("actions/checkout", "v7"): ("commit", NUEVO),
            ("actions/checkout", "v6.9.9"): ("commit", SOLO_TAG),
            ("actions/checkout", "v6.0.0"): ("commit", RELEASE),
            ("actions/checkout", "v5.0.0"): ("commit", LEJANO),
        }
        self.tag_objs = {"a" * 40: LEGIT}
        self.arboles = {}   # sha → {nombre: entrada}
        self.blobs = {}
        self.padres = {}
        self.llamadas = []

    # -- árboles: se arman desde {ruta: (sha, modo)} con sha determinista por contenido
    def arbol(self, archivos):
        raiz = {}
        for ruta, (sha, modo) in archivos.items():
            nodo, partes = raiz, ruta.split("/")
            for p in partes[:-1]:
                nodo = nodo.setdefault(p, {})
            nodo[partes[-1]] = (sha, modo)

        def registrar(nodo):
            entradas = {}
            for nombre, v in sorted(nodo.items()):
                if isinstance(v, dict):
                    entradas[nombre] = {"path": nombre, "type": "tree", "mode": "040000",
                                        "sha": registrar(v)}
                else:
                    sha, modo = v
                    tipo = "commit" if modo == "160000" else "blob"
                    entradas[nombre] = {"path": nombre, "type": tipo, "mode": modo, "sha": sha}
            sha = hashlib.sha1(json.dumps(entradas, sort_keys=True).encode()).hexdigest()
            self.arboles[sha] = entradas
            return sha

        return registrar(raiz)

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
        m = re.fullmatch(r"repos/([^/]+/[^/]+)/git/commits/(\w+)", ruta)
        if m:
            return 200, {"parents": [{"sha": p} for p in self.padres[m.group(2)]]}
        m = re.fullmatch(r"repos/([^/]+/[^/]+)/compare/(.+)\.\.\.(\w+)", ruta)
        if m:
            if m.group(1).lower() == "faronovacorp/x":
                return 200, {"merge_base_commit": {"sha": "mb"}}
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
            return 200, {"truncated": False, "tree": list(self.arboles[m.group(2)].values())}
        m = re.fullmatch(r"repos/([^/]+/[^/]+)/git/blobs/(\w+)", ruta)
        if m:
            return 200, {"content": base64.b64encode(self.blobs[m.group(2)].encode()).decode()}
        raise AssertionError(f"ruta no simulada: {ruta}")

    def api_paginado(self, ruta, tope=1000):
        m = re.fullmatch(r"repos/([^/]+/[^/]+)/branches\?per_page=100", ruta)
        if m:
            ramas = self.ramas.get(m.group(1).lower(), {})
            return [{"name": n, "commit": {"sha": "f" * 40}} for n in ramas]
        m = re.fullmatch(r"repos/([^/]+/[^/]+)/tags\?per_page=100", ruta)
        if m:
            return [{"name": t, "commit": {"sha": self.tag_commit_pelado(r, t)}}
                    for (r, t) in self.tags if r == m.group(1).lower()]
        raise AssertionError(ruta)

    def tag_commit_pelado(self, repo, tag):
        tipo, sha = self.tags[(repo, tag)]
        return self.tag_objs[sha] if tipo == "tag" else sha


BASE = """name: ci
on: pull_request
jobs:
  a:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{LEGIT} # v7.0.1
      - run: echo hola
"""


def base_wf():
    return BASE.replace("{LEGIT}", LEGIT)


def wf(paso):
    return base_wf().replace("      - run: echo hola\n", paso + "      - run: echo hola\n")


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = cargar_script()

    def setUp(self):
        self.gh = FakeGH()
        self.m.api = self.gh.api
        self.m.api_paginado = self.gh.api_paginado

    def revisar(self, head, base=None):
        base = base_wf() if base is None else base
        hall, _ = self.m.revisar_archivo(".github/workflows/ci.yml", base, head, self.m.Verificador())
        return hall

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

    def test_commit_en_rama_mas_alla_de_las_primeras_40_pasa(self):
        head = BASE.replace("{LEGIT}", LEJANO).replace("v7.0.1", "v5.0.0")
        self.assertEqual(self.revisar(head), [])

    def test_busqueda_incompleta_lo_dice(self):
        self.m.MAX_RAMAS = 10
        try:
            head = BASE.replace("{LEGIT}", IMPOSTOR).replace("v7.0.1", "v6.0.2")
            errs = self.errores(self.revisar(head))
        finally:
            self.m.MAX_RAMAS = 300
        self.assertTrue(any("búsqueda incompleta" in e["motivo"] for e in errs), errs)

    def test_comentario_desfasado_bloquea(self):
        head = BASE.replace("{LEGIT}", NUEVO)  # comentario sigue diciendo v7.0.1
        errs = self.errores(self.revisar(head))
        self.assertEqual(len(errs), 1, errs)
        self.assertIn("v7.0.1 apunta a", errs[0]["motivo"])

    def test_mayor_flotante_movido_pasa_si_un_vN_x_apunta(self):
        # v7 ya apunta a NUEVO, pero LEGIT es v7.0.1: `# v7` sigue siendo cierto.
        head = wf(f"      - uses: actions/checkout@{LEGIT} # v7\n")
        self.assertEqual(self.revisar(head, base=""), [])

    def test_mayor_de_otra_familia_bloquea(self):
        head = wf(f"      - uses: actions/checkout@{LEGIT} # v6\n")
        errs = self.errores(self.revisar(head, base=""))
        self.assertTrue(any("v6" in e["motivo"] for e in errs), errs)

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

    def test_reusable_propio_en_main_pasa_con_comentario_libre(self):
        for nota in (" # re-pin P-144 (D-1275/D-1287, PR .github#19)", " # pin tras P-385 (ruleset 2.1)", ""):
            head = base_wf() + (
                "  b:\n"
                f"    uses: FaroNovaCorp/.github/.github/workflows/secret-scan.yml@{PROPIO_OK}{nota}\n")
            self.assertEqual(self.revisar(head), [], nota)

    def test_reusable_propio_sin_mergear_bloquea(self):
        head = base_wf() + (
            "  b:\n"
            f"    uses: FaroNovaCorp/.github/.github/workflows/secret-scan.yml@{PROPIO_FUERA}\n")
        errs = self.errores(self.revisar(head))
        self.assertIn("reusable propio fuera de `main`", errs[0]["motivo"])

    def test_escape_yaml_bloquea(self):
        # "\x61" = "a": el valor real es actions/checkout@IMPOSTOR, oculto en el texto.
        head = wf(f'      - uses: "\\x61ctions/checkout@{IMPOSTOR}" # v7.0.1\n')
        errs = self.errores(self.revisar(head))
        self.assertTrue(any("no aparece literal" in e["motivo"] for e in errs), errs)

    def test_clave_duplicada_bloquea(self):
        head = wf(f"      - uses: actions/checkout@{IMPOSTOR} # v7.0.1\n"
                  f"        uses: actions/checkout@{NUEVO} # v7.0.2\n")
        errs = self.errores(self.revisar(head))
        self.assertTrue(any("duplicada" in e["motivo"] for e in errs), errs)

    def test_etiquetas_yaml_no_esconden_el_uses(self):
        for etiqueta in ("!!omap", "!!pairs", "!!seq", "!custom"):
            accion = ("name: demo\ndescription: demo\nruns:\n  using: composite\n"
                      f"  steps: {etiqueta}\n"
                      f"    - uses: actions/checkout@{IMPOSTOR} # v7.0.1\n")
            hall, _ = self.m.revisar_archivo("local/action.yml", "", accion, self.m.Verificador())
            self.assertTrue(any("no está en ninguna rama" in e["motivo"] for e in self.errores(hall)),
                            (etiqueta, hall))
        conjunto = f"jobs:\n  a:\n    steps: !!set\n      ? uses: actions/checkout@{IMPOSTOR} # v7.0.1\n"
        hall, _ = self.m.revisar_archivo(".github/workflows/ci.yml", "", conjunto, self.m.Verificador())
        self.assertTrue(self.errores(hall), hall)

    def test_clave_uses_entre_comillas_duplicada_bloquea(self):
        head = wf(f"      - uses: actions/checkout@{NUEVO} # v7.0.2\n"
                  f'        "uses": actions/checkout@{IMPOSTOR} # v7.0.1\n')
        errs = self.errores(self.revisar(head))
        self.assertTrue(any("duplicada" in e["motivo"] for e in errs), errs)

    def checkout(self, entradas, propio="FaroNovaCorp/x", base=None):
        paso = (f"      - uses: actions/checkout@{LEGIT} # v7.0.1\n        with:\n"
                + "".join(f"          {k}: {v}\n" for k, v in entradas)
                + "      - uses: ./x\n")
        with mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": propio}):
            return self.errores(self.revisar(wf(paso), base=base))

    def test_checkout_de_otro_repo(self):
        errs = self.checkout([("repository", "actions/checkout"), ("ref", IMPOSTOR), ("path", "x")])
        self.assertTrue(any("ninguna rama" in e["motivo"] for e in errs), errs)
        self.assertEqual(self.checkout([("repository", "actions/checkout"), ("ref", NUEVO)]), [])
        for ref in ("main", "v7", "${{ env.REF }}"):
            errs = self.checkout([("repository", "actions/checkout"), ("ref", ref)])
            self.assertTrue(any("sin SHA fijo" in e["motivo"] for e in errs), (ref, errs))
        errs = self.checkout([("repository", "actions/checkout")])
        self.assertTrue(any("sin SHA fijo" in e["motivo"] for e in errs), errs)

    def test_checkout_inputs_como_el_runner(self):
        # Mayúsculas en el nombre, espacios en el valor, path en expresión: igual se verifica.
        errs = self.checkout([("Repository", "actions/checkout"), ("REF", f"' {IMPOSTOR} '"),
                              ("path", "${{ 'x' }}")])
        self.assertTrue(any("ninguna rama" in e["motivo"] for e in errs), errs)
        errs = self.checkout([("repository", "actions/checkout"), ("ref", NUEVO), ("Ref", IMPOSTOR)])
        self.assertTrue(errs, errs)                       # nombres repetidos sin mayúsculas: no verificable
        errs = self.checkout([("repository", "${{ format('actions/{0}', 'checkout') }}"), ("ref", NUEVO)])
        self.assertTrue(any("no verificable" in e["motivo"] for e in errs), errs)

    def test_checkout_del_propio_repo(self):
        propio = "Actions/Checkout"
        # Patrones reales de la org: despliegue por inputs.ref, robot de migraciones, sidecar.
        for entradas in ([("ref", "${{ github.event.pull_request.head.sha }}")], [("ref", "main")],
                         [("ref", "${{ github.event.inputs.ref || github.sha }}")],
                         [("ref", "${{ steps.plan.outputs.sha }}")], [("ref", "refs/heads/main")],
                         [("repository", "${{ github.repository }}")], [("path", "sidecar")], [("ref", NUEVO)]):
            self.assertEqual(self.checkout(entradas, propio=propio), [], entradas)
        for ref in (IMPOSTOR, IMPOSTOR.upper()):                          # sin repository: propio repo
            errs = self.checkout([("ref", ref)], propio=propio)
            self.assertTrue(any("ninguna rama" in e["motivo"] for e in errs), (ref, errs))
        errs = self.checkout([("repository", "${{ github.repository }}"), ("ref", IMPOSTOR)], propio=propio)
        self.assertTrue(any("ninguna rama" in e["motivo"] for e in errs), errs)
        # Rama sin mergear, PR de un fork, tag, constante disfrazada de expresión: nadie verificó ese árbol.
        for ref in ("rama-sin-mergear", "refs/pull/9/head", "v1.0.0", "${{ 'rama' }}",
                    "${{ github.sha && 'rama' }}"):
            errs = self.checkout([("ref", ref)], propio=propio)
            self.assertTrue(any("propio repo" in e["motivo"] for e in errs), (ref, errs))

    def test_checkout_con_subruta_o_servidor_ajeno(self):
        paso = (f"      - uses: actions/checkout/.@{LEGIT} # v7.0.1\n"
                f"        with:\n          repository: actions/checkout\n          ref: {IMPOSTOR}\n"
                "      - uses: ./x\n")
        errs = self.errores(self.revisar(wf(paso)))
        self.assertTrue(any("subruta" in e["motivo"] for e in errs), errs)
        self.assertTrue(any("ninguna rama" in e["motivo"] for e in errs), errs)
        errs = self.checkout([("github-server-url", "https://evil.example.com")])
        self.assertTrue(any("servidor" in e["motivo"] for e in errs), errs)
        self.assertEqual(self.checkout([("github-server-url", "https://github.com")]), [])
        self.assertEqual(self.checkout([("github-server-url", "${{ github.server_url }}")]), [])

    def test_checkout_de_la_org_en_main(self):
        for entradas in ([("repository", "FaroNovaCorp/recursos-compartidos"), ("ref", "main")],
                         [("repository", "${{ github.repository_owner }}/otro")],
                         [("repository", "${{ github.repository_owner }}/${{ matrix.repo }}"), ("ref", "main")]):
            self.assertEqual(self.checkout(entradas), [], entradas)
        errs = self.checkout([("repository", "FaroNovaCorp/recursos-compartidos"), ("ref", "feat/x")])
        self.assertTrue(any("sin SHA fijo" in e["motivo"] for e in errs), errs)
        errs = self.checkout([("repository", "${{ github.repository_owner }}/${{ matrix.repo }}"), ("ref", IMPOSTOR)])
        self.assertTrue(any("no verificable" in e["motivo"] for e in errs), errs)

    def test_checkout_en_accion_compuesta(self):
        accion = ("name: carga\ndescription: carga\nruns:\n  using: composite\n  steps:\n"
                  f"    - uses: actions/checkout@{LEGIT} # v7.0.1\n"
                  f"      with:\n        repository: actions/checkout\n        ref: {IMPOSTOR}\n        path: x\n")
        hall, _ = self.m.revisar_archivo("loader/action.yml", "", accion, self.m.Verificador())
        self.assertTrue(any("ninguna rama" in e["motivo"] for e in self.errores(hall)), hall)

    def test_checkout_previo_no_se_revisa(self):
        previo = wf(f"      - uses: actions/checkout@{LEGIT} # v7.0.1\n"
                    "        with:\n          repository: actions/checkout\n          ref: main\n")
        self.assertEqual(self.revisar(previo.replace("echo hola", "echo chao"), base=previo), [])

    def test_clave_de_fusion_bloquea(self):
        head = base_wf() + ("  b:\n    runs-on: ubuntu-latest\n    steps:\n"
                            "      - <<: {uses: actions/checkout}\n")
        errs = self.errores(self.revisar(head))
        self.assertTrue(any("<<" in e["motivo"] for e in errs), errs)

    def test_alias_yaml_con_ancla_en_linea_nueva_se_verifica(self):
        head = base_wf() + (
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
                  "      - uses: $/.github/actions/y\n"
                  "      - uses: docker://alpine@sha256:" + "0" * 64 + "\n"
                  "      - uses: docker://alpine:3\n")
        hall = self.revisar(head)
        self.assertEqual(self.errores(hall), [])
        self.assertEqual(len(hall), 1)
        self.assertIn("docker", hall[0]["motivo"])

    def test_yaml_invalido_bloquea(self):
        errs = self.errores(self.revisar("jobs: [\n"))
        self.assertIn("YAML", errs[0]["motivo"])

    def test_puntero_lfs_o_raiz_que_no_es_mapa_bloquea(self):
        lfs = ("version https://git-lfs.github.com/spec/v1\n"
               "oid sha256:" + "a" * 64 + "\nsize 512\n")
        errs = self.errores(self.revisar(lfs))
        self.assertIn("Git LFS", errs[0]["motivo"])
        for texto in ("", "solo texto\n", "- uses: x\n"):
            errs = self.errores(self.revisar(texto))
            self.assertTrue(errs and "raíz no es un mapa" in errs[0]["motivo"], texto)

    def test_cache_por_par(self):
        head = wf(f"      - uses: actions/checkout@{NUEVO} # v7.0.2\n"
                  f"      - uses: actions/checkout@{NUEVO} # v7.0.2\n")
        self.assertEqual(self.revisar(head), [])
        self.assertEqual(sum(r.startswith("repos/actions/checkout/compare") for r in self.gh.llamadas), 1)


class TestDetectar(Base):
    def test_diff_incremental_y_archivos_relevantes(self):
        b = self.gh.arbol({".github/workflows/ci.yml": ("x1", "100644"), "README.md": ("r1", "100644"),
                           "action.yml": ("a1", "100644"), "src/mod/a.py": ("p1", "100644")})
        h = self.gh.arbol({".github/workflows/ci.yml": ("x2", "100644"), "README.md": ("r2", "100644"),
                           "action.yml": ("a1", "100644"), "src/mod/a.py": ("p1", "100644"),
                           ".github/workflows/nuevo.yml": ("n1", "100644"),
                           "sub/dir/action.yaml": ("s1", "100644")})
        self.gh.llamadas.clear()
        cambios, prohibidos = self.m.detectar("FaroNovaCorp/x", b, h)
        self.assertEqual(cambios, [
            {"ruta": ".github/workflows/ci.yml", "base": "x1", "head": "x2"},
            {"ruta": ".github/workflows/nuevo.yml", "base": None, "head": "n1"},
            {"ruta": "sub/dir/action.yaml", "base": None, "head": "s1"},
        ])
        self.assertEqual(prohibidos, [])
        # `src/` no cambió: no se baja a ese subárbol (raíz, .github, workflows, sub, dir).
        arboles = [r for r in self.gh.llamadas if "git/trees" in r]
        self.assertLessEqual(len(arboles), 10)

    def test_enlace_simbolico_y_submodulo_prohibidos(self):
        b = self.gh.arbol({"README.md": ("r1", "100644")})
        h = self.gh.arbol({"README.md": ("r1", "100644"),
                           "local/action.yml": ("../payload/manifest.yml", "120000"),
                           ".github/actions/x": ("../../vendor/x", "120000"),
                           ".github/vendor": ("c" * 40, "160000"),
                           "vendor/checkout": ("d" * 40, "160000"),
                           ".gitmodules": ("gm1", "100644"),
                           "docs/enlace.md": ("../README.md", "120000")})
        cambios, prohibidos = self.m.detectar("FaroNovaCorp/x", b, h)
        self.assertEqual(cambios, [])
        self.assertEqual([r for r, _ in prohibidos],
                         [".github/actions/x", ".github/vendor", ".gitmodules", "local/action.yml",
                          "vendor/checkout"])


class TestPiezas(Base):
    def test_script_sin_expresiones_de_github(self):
        # GitHub evalúa todo `${{ … }}` dentro de `run:` antes de correrlo: el
        # 25-nov una en un comentario invalidó el workflow entero.
        codigo = subprocess.run(
            [sys.executable, os.path.join(AQUI, "extract_step_script.py"), WORKFLOW,
             "verificar", "Verificar acciones"], check=True, capture_output=True, text=True).stdout
        self.assertNotIn("${{", codigo)

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

    def test_zizmor_bloquea_solo_impostor_en_par_nuevo(self):
        self.m.correr_zizmor = lambda archivo: [
            ("ref-version-mismatch", 7, 7, "desfase"), ("impostor-commit", 7, 7, "impostor"),
            ("impostor-commit", 9, 9, "previo")]
        with tempfile.TemporaryDirectory() as d:
            hall = self.m.revisar_zizmor(".github/workflows/ci.yml", base_wf(), d, {7})
        self.assertEqual([h["nivel"] for h in hall], ["aviso", "error", "aviso"])

    def test_zizmor_par_previo_con_comentario_editado_avisa(self):
        base = BASE.replace("{LEGIT}", NUEVO)          # desfase previo en la línea 7
        head = base.replace("# v7.0.1", "# v7.0.1  (bump pendiente)")
        hall, de_pares_nuevos = self.m.revisar_archivo(".github/workflows/ci.yml", base, head,
                                                       self.m.Verificador())
        self.assertEqual((hall, de_pares_nuevos), ([], set()))
        self.m.correr_zizmor = lambda archivo: [("impostor-commit", 7, 7, "x")]
        with tempfile.TemporaryDirectory() as d:
            hall = self.m.revisar_zizmor(".github/workflows/ci.yml", head, d, de_pares_nuevos)
        self.assertEqual(hall[0]["nivel"], "aviso")

    def test_zizmor_que_falla_avisa(self):
        self.m.correr_zizmor = lambda archivo: None
        with tempfile.TemporaryDirectory() as d:
            hall = self.m.revisar_zizmor(".github/workflows/ci.yml", base_wf(), d, {7})
        self.assertEqual(hall[0]["nivel"], "aviso")

    def test_correr_zizmor_lee_json_real_y_tolera_timeout(self):
        mod = cargar_script()  # correr_zizmor sin parchear
        ok = subprocess.CompletedProcess([], 0, stdout=ZIZMOR_JSON, stderr="")
        with mock.patch.object(mod.subprocess, "run", return_value=ok):
            self.assertEqual(mod.correr_zizmor("x.yml"),
                             [("impostor-commit", 7, 7, "commit with no history in referenced repository")])
        with mock.patch.object(mod.subprocess, "run", side_effect=subprocess.TimeoutExpired("z", 120)):
            self.assertIsNone(mod.correr_zizmor("x.yml"))
        roto = subprocess.CompletedProcess([], 1, stdout="", stderr="fatal")
        with mock.patch.object(mod.subprocess, "run", return_value=roto):
            self.assertIsNone(mod.correr_zizmor("x.yml"))

    def test_pedir_reintenta_errores_de_red_y_pagina(self):
        mod = cargar_script()

        class Resp(io.BytesIO):
            def __init__(self, cuerpo, link=None):
                super().__init__(cuerpo)
                self.status = 200
                self.headers = {"Link": link} if link else {}

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        pagina2 = f'<{mod.API}/repos/a/b/branches?page=2>; rel="next"'
        respuestas = [ConnectionResetError("reset"), Resp(b'[{"name": "uno"}]', pagina2),
                      Resp(b'[{"name": "dos"}]')]

        def urlopen(req, timeout):
            r = respuestas.pop(0)
            if isinstance(r, Exception):
                raise r
            return r

        with mock.patch.dict(os.environ, {"GH_TOKEN": "fake"}), \
                mock.patch.object(mod.urllib.request, "urlopen", urlopen), \
                mock.patch.object(mod.time, "sleep", lambda s: None):
            self.assertEqual([r["name"] for r in mod.api_paginado("repos/a/b/branches?per_page=100")],
                             ["uno", "dos"])

    def test_pedir_reintenta_limite_secundario(self):
        mod = cargar_script()

        class Resp(io.BytesIO):
            status, headers = 200, {}

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        respuestas = [(403, {"Retry-After": "1"}, b""),
                      (403, {"X-RateLimit-Remaining": "12"}, b"You have exceeded a secondary rate limit"),
                      Resp(b'{"ok": true}')]
        esperas = []

        def urlopen(req, timeout):
            r = respuestas.pop(0)
            if isinstance(r, tuple):
                raise urllib.error.HTTPError(req.full_url, r[0], "x", r[1], io.BytesIO(r[2]))
            return r

        with mock.patch.dict(os.environ, {"GH_TOKEN": "fake"}), \
                mock.patch.object(mod.urllib.request, "urlopen", urlopen), \
                mock.patch.object(mod.time, "sleep", esperas.append):
            self.assertEqual(mod.api("repos/a/b"), (200, {"ok": True}))
        self.assertEqual(esperas, [1, 30])

    def test_pedir_404_y_limite_agotado(self):
        mod = cargar_script()

        def error(code, cab):
            def urlopen(req, timeout):
                raise urllib.error.HTTPError(req.full_url, code, "x", cab, io.BytesIO(b""))
            return urlopen

        with mock.patch.dict(os.environ, {"GH_TOKEN": "fake"}):
            with mock.patch.object(mod.urllib.request, "urlopen", error(404, {})):
                self.assertEqual(mod.api("repos/a/b"), (404, None))
            with mock.patch.object(mod.urllib.request, "urlopen", error(403, {"X-RateLimit-Remaining": "0"})):
                with self.assertRaises(mod.ErrorApi):
                    mod.api("repos/a/b")

    def test_informar_escapa_comandos(self):
        hall = [self.m.hallazgo("error", "a,b:c.yml", 3, "x/y@z\n::stop-commands::t", "malo\nmás")]
        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": os.path.join(d, "s.md")}), \
                redirect_stdout(buf):
            n = self.m.informar(hall, 1)
        self.assertEqual(n, 1)
        salida = buf.getvalue().splitlines()
        self.assertTrue(salida[0].startswith("::error file=a%2Cb%3Ac.yml,line=3,"), salida[0])
        self.assertFalse(any(l.startswith("::stop-commands") for l in salida))


class TestMain(Base):
    """Evento completo: árboles, merge de prueba, instalación y zizmor simulados."""

    def correr(self, evento, nombre, base_arch, head_arch, padres=("B", "PRHEAD")):
        b = self.gh.arbol(base_arch)
        h = self.gh.arbol(head_arch)
        self.gh.padres = {"MERGE": [b if p == "B" else p for p in padres]}
        self.gh.arboles["MERGE"] = self.gh.arboles[h]
        self.gh.arboles["PRHEAD"] = self.gh.arboles[h]
        self.gh.arboles["B"] = self.gh.arboles[b]
        self.gh.blobs = {"x1": base_wf(), "x2": BASE.replace("{LEGIT}", IMPOSTOR),
                         "x3": BASE.replace("{LEGIT}", NUEVO).replace("v7.0.1", "v7.0.2")}
        instalado = []
        self.m.instalar = lambda: instalado.append(True)
        self.m.correr_zizmor = lambda archivo: []
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "ev.json")
            with open(ruta, "w") as f:
                json.dump(evento, f)
            env = {"GITHUB_EVENT_PATH": ruta, "GITHUB_EVENT_NAME": nombre,
                   "GITHUB_REPOSITORY": "FaroNovaCorp/x", "GITHUB_SHA": "MERGE"}
            with mock.patch.dict(os.environ, env), redirect_stdout(io.StringIO()):
                rc = self.m.main()
        return rc, instalado

    PR = {"pull_request": {"base": {"sha": "B"}, "head": {"sha": "PRHEAD"}}}

    def test_pr_sin_cambios_relevantes_no_instala(self):
        arch = {".github/workflows/ci.yml": ("x1", "100644"), "src/a.py": ("p1", "100644")}
        rc, inst = self.correr(self.PR, "pull_request", arch,
                               {**arch, "src/a.py": ("p2", "100644")})
        self.assertEqual((rc, inst), (0, []))

    def test_pr_atrasado_no_hereda_cambios_de_main(self):
        # main subió el workflow a x3; el merge de prueba ya trae x3: sin cambio relevante.
        main_arch = {".github/workflows/ci.yml": ("x3", "100644"), "src/a.py": ("p1", "100644")}
        merge_arch = {".github/workflows/ci.yml": ("x3", "100644"), "src/a.py": ("p2", "100644")}
        rc, inst = self.correr(self.PR, "pull_request", main_arch, merge_arch)
        self.assertEqual((rc, inst), (0, []))

    def test_pr_con_impostor_falla(self):
        rc, inst = self.correr(self.PR, "pull_request", {".github/workflows/ci.yml": ("x1", "100644")},
                               {".github/workflows/ci.yml": ("x2", "100644")})
        self.assertEqual((rc, inst), (1, [True]))

    def test_pr_con_bump_legitimo_pasa(self):
        rc, inst = self.correr(self.PR, "pull_request", {".github/workflows/ci.yml": ("x1", "100644")},
                               {".github/workflows/ci.yml": ("x3", "100644")})
        self.assertEqual((rc, inst), (0, [True]))

    def test_pr_con_enlace_simbolico_falla_sin_instalar(self):
        rc, inst = self.correr(self.PR, "pull_request", {"README.md": ("r1", "100644")},
                               {"README.md": ("r1", "100644"), "a/action.yml": ("../m.yml", "120000")})
        self.assertEqual((rc, inst), (1, []))

    def test_sin_merge_de_prueba_compara_contra_la_punta(self):
        arch_b = {".github/workflows/ci.yml": ("x1", "100644")}
        arch_h = {".github/workflows/ci.yml": ("x2", "100644")}
        for padres in (("PRHEAD",), ("PRHEAD", "B")):   # un padre, o padres al revés
            rc, inst = self.correr(self.PR, "pull_request", arch_b, arch_h, padres=padres)
            self.assertEqual((rc, inst), (1, [True]), padres)
            self.assertIn("repos/FaroNovaCorp/x/git/trees/B", self.gh.llamadas)

    def test_pull_request_target_no_se_acepta(self):
        rc, _ = self.correr(self.PR, "pull_request_target", {"a": ("1", "100644")}, {"a": ("1", "100644")})
        self.assertEqual(rc, 1)

    def test_cola_con_impostor_falla(self):
        ev = {"merge_group": {"base_sha": "B", "head_sha": "MERGE"}}
        rc, _ = self.correr(ev, "merge_group", {".github/workflows/ci.yml": ("x1", "100644")},
                            {".github/workflows/ci.yml": ("x2", "100644")})
        self.assertEqual(rc, 1)

    def test_evento_no_soportado_falla(self):
        rc, _ = self.correr({}, "push", {"a": ("1", "100644")}, {"a": ("1", "100644")})
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
