"""Tests de la CLI de la demo (2ª tanda, 16 nov 2026).

``python3 -m simulacion.demo`` acepta banderas sin romper la corrida
canónica: ``--semilla N``, ``--ticks N`` y ``--con-ejemplos`` (añade
a Nia, Bruno y Sofía, 8 agentes). Sin banderas, el registro es
exactamente el conocido-bueno (MD5
``b56a5a928fcf5a2722665c8251a5aa7b``, 375 eventos).

Como en TestDemoComoPrograma (test_invariantes), cada test corre la
demo como subprocess sobre una copia temporal del proyecto (carpetas
``simulacion/`` y ``ejemplos/``), así que ningún test reescribe los
``registro.json`` versionados del clon.

Solo usa la biblioteca estándar (``unittest``). Ejecutar desde la
raíz del proyecto con::

    python3 -m unittest discover
"""

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr

# La raíz del proyecto es la carpeta padre de tests/. Se pone al
# principio de sys.path para importar el código real de ESTE clon
# (también cuando la suite corre sobre una copia del proyecto).
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from simulacion.demo import parse_args  # noqa: E402

MD5_CONOCIDO_BUENO = "b56a5a928fcf5a2722665c8251a5aa7b"
EVENTOS_ESPERADOS = 375
AGENTES_CANONICOS = ("Lia", "Tomas", "Nara", "Rui", "Mara")
AGENTES_EJEMPLOS = ("Nia", "Bruno", "Sofía")


def md5_de(datos):
    return hashlib.md5(datos).hexdigest()


class TestCliDemo(unittest.TestCase):
    """La CLI de la demo: banderas que siembran sin romper lo canónico."""

    def _copiar_proyecto(self, destino):
        for carpeta in ("simulacion", "ejemplos"):
            shutil.copytree(
                os.path.join(RAIZ, carpeta),
                os.path.join(destino, carpeta),
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    def _ejecutar(self, argumentos, cwd, debe_fallar=False):
        entorno = dict(os.environ)
        entorno.pop("PYTHONPATH", None)
        resultado = subprocess.run(
            [sys.executable, "-m", "simulacion.demo"] + argumentos,
            cwd=cwd, env=entorno,
            capture_output=True, text=True, timeout=120)
        if debe_fallar:
            self.assertNotEqual(
                resultado.returncode, 0,
                "la demo debía fallar con %r y salió en 0" % argumentos)
        else:
            self.assertEqual(
                resultado.returncode, 0,
                "la demo falló:\\n%s\\n%s" % (resultado.stdout,
                                            resultado.stderr))
        return resultado

    def _leer_registro_de_la_copia(self, copia):
        rutas = [os.path.join(copia, "registro.json"),
                 os.path.join(copia, "visor", "registro.json")]
        bytes_por_ruta = []
        for ruta in rutas:
            self.assertTrue(os.path.isfile(ruta),
                            "la demo no escribió %s" % ruta)
            with open(ruta, "rb") as f:
                bytes_por_ruta.append(f.read())
        # Los dos registro.json de la copia son idénticos entre sí.
        self.assertEqual(bytes_por_ruta[0], bytes_por_ruta[1])
        with open(rutas[0], encoding="utf-8") as f:
            return json.load(f), bytes_por_ruta[0]

    def test_sin_banderas_el_registro_es_el_canonico(self):
        # Sin banderas, la corrida es EXACTAMENTE la canónica:
        # mismo MD5 byte a byte, 375 eventos, 5 agentes.
        with tempfile.TemporaryDirectory() as tmp:
            copia = os.path.join(tmp, "proyecto")
            os.makedirs(copia)
            self._copiar_proyecto(copia)
            resultado = self._ejecutar([], cwd=copia)
            registro, datos = self._leer_registro_de_la_copia(copia)
            self.assertEqual(md5_de(datos), MD5_CONOCIDO_BUENO)
            self.assertEqual(registro["meta"],
                             {"ticks": 30, "semilla": 42})
            self.assertEqual(len(registro["eventos"]), EVENTOS_ESPERADOS)
            self.assertEqual([a["nombre"] for a in registro["agentes"]],
                             list(AGENTES_CANONICOS))
            self.assertIn("5 agentes despiertan", resultado.stdout)
            self.assertIn("Ticks: 30 | Diálogos: 70 | "
                          "Eventos de caos: 11", resultado.stdout)

    def test_semilla_7_cambia_el_registro_pero_es_determinista(self):
        # Otra semilla produce otro mundo, pero dos corridas con la
        # misma semilla dan el mismo registro byte a byte.
        md5s = []
        for nombre in ("primera", "segunda"):
            with tempfile.TemporaryDirectory() as tmp:
                copia = os.path.join(tmp, "proyecto")
                os.makedirs(copia)
                self._copiar_proyecto(copia)
                self._ejecutar(["--semilla", "7"], cwd=copia)
                registro, datos = self._leer_registro_de_la_copia(copia)
                self.assertEqual(registro["meta"]["semilla"], 7)
                self.assertEqual(registro["meta"]["ticks"], 30)
                self.assertNotEqual(md5_de(datos), MD5_CONOCIDO_BUENO,
                                    "la semilla 7 no cambió el registro")
                md5s.append(md5_de(datos))
        self.assertEqual(md5s[0], md5s[1],
                         "dos corridas con --semilla 7 difieren")

    def test_con_ejemplos_y_ticks_ocho_agentes_cinco_ticks(self):
        # --con-ejemplos añade a Nia, Bruno y Sofía (8 agentes) y
        # --ticks manda sobre la duración de la corrida.
        with tempfile.TemporaryDirectory() as tmp:
            copia = os.path.join(tmp, "proyecto")
            os.makedirs(copia)
            self._copiar_proyecto(copia)
            resultado = self._ejecutar(
                ["--con-ejemplos", "--ticks", "5"], cwd=copia)
            registro, _datos = self._leer_registro_de_la_copia(copia)
            self.assertEqual(registro["meta"],
                             {"ticks": 5, "semilla": 42})
            nombres = [a["nombre"] for a in registro["agentes"]]
            self.assertEqual(len(nombres), 8)
            self.assertEqual(nombres,
                             list(AGENTES_CANONICOS) +
                             list(AGENTES_EJEMPLOS))
            self.assertTrue(registro["eventos"])
            self.assertIn("8 agentes despiertan", resultado.stdout)
            self.assertIn("Ticks: 5 |", resultado.stdout)

    def test_ticks_negativo_se_rechaza(self):
        # argparse rechaza --ticks negativo (SystemExit, código 2)
        # tanto en el parser como en la demo real. El parser imprime
        # el error en stderr antes de salir, así que se silencia en
        # la llamada directa para no ensuciar la salida de la suite.
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parse_args(["--ticks", "-1"])
        with tempfile.TemporaryDirectory() as tmp:
            copia = os.path.join(tmp, "proyecto")
            os.makedirs(copia)
            self._copiar_proyecto(copia)
            resultado = self._ejecutar(["--ticks", "-1"], cwd=copia,
                                       debe_fallar=True)
            self.assertIn("--ticks no puede ser negativo",
                          resultado.stderr)
            self.assertFalse(os.path.exists(
                os.path.join(copia, "registro.json")))


if __name__ == "__main__":
    unittest.main()
