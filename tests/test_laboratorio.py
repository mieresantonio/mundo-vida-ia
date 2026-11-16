"""Tests del laboratorio de semillas (2ª tanda, 16 nov 2026).

El laboratorio corre el motor en silencio sobre varias semillas y
compara las corridas. Estos tests fijan que el barrido es
determinista, que la semilla 42 reproduce la demo canónica (375
eventos, 70 diálogos, 11 caos, 0 colaboraciones) y que la CLI
funciona como subprocess sobre una copia temporal del proyecto
(sin reescribir los ``registro.json`` versionados: el laboratorio
no escribe ningún archivo).

Solo usa la biblioteca estándar (``unittest``). Ejecutar desde la
raíz del proyecto con::

    python3 -m unittest discover
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

# La raíz del proyecto es la carpeta padre de tests/. Se pone al
# principio de sys.path para importar el código real de ESTE clon
# (también cuando la suite corre sobre una copia del proyecto).
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from simulacion.agente import Agente  # noqa: E402
from simulacion.laboratorio import barrer, main, medir, resumir  # noqa: E402
from simulacion.mundo import Mundo  # noqa: E402


class TestLaboratorio(unittest.TestCase):
    """El barrido es determinista y la semilla 42 es la demo."""

    def test_barrido_determinista(self):
        # El mismo barrido dos veces da las mismas medidas.
        self.assertEqual(barrer(range(5)), barrer(range(5)))

    def test_semilla_42_reproduce_la_demo_canonica(self):
        # La semilla 42 con los 5 agentes de la demo es la corrida
        # canónica: 375 eventos, 70 diálogos, 11 caos, 0
        # colaboraciones (la Ronda 6 midió 0 de 150 elecciones).
        (medida,) = barrer([42])
        self.assertEqual(medida["eventos"], 375)
        self.assertEqual(medida["dialogo"], 70)
        self.assertEqual(medida["caos"], 11)
        self.assertEqual(medida["pensamiento"], 150)
        self.assertEqual(medida["colaboraciones"], 0)
        self.assertEqual(medida["elecciones_colaborar"], 0)
        self.assertEqual(medida["proyectos_completados"], 0)
        self.assertEqual(medida["agentes"], 5)

    def test_veinte_semillas_sin_colaborar(self):
        # REGRESIÓN 16 nov 2026 (2ª tanda): el laboratorio midió 0
        # colaboraciones en 600 semillas distintas con los agentes
        # de la demo. Este test fija el hallazgo en la suite con 20
        # semillas: si un cambio futuro del motor abre la puerta a
        # colaborar, el test lo dirá y habrá que actualizarlo a
        # conciencia, no por accidente.
        resultados = barrer(range(20))
        self.assertEqual(len(resultados), 20)
        for medida in resultados:
            self.assertEqual(medida["colaboraciones"], 0,
                             "la semilla %d colabora" % medida["semilla"])
            self.assertEqual(medida["elecciones_colaborar"], 0,
                             "la semilla %d elige colaborar"
                             % medida["semilla"])

    def test_medir_cuenta_colaboraciones_en_caso_positivo(self):
        # Caso positivo de la Ronda 6 (flujo real sin presets):
        # un par con rasgos moderados (sociabilidad 0.3, ambición
        # 0.5), semilla 4, 46 ticks: 3 decisiones colaborar y el
        # proyecto completado. Si medir() no contara bien, este
        # test lo cazaría: el 0 de la demo no bastaría para
        # validar el conteo.
        mundo = Mundo(semilla=4)
        for nombre in ("P1", "P2"):
            mundo.agregar_agente(Agente(
                nombre,
                {"curiosidad": 0.0, "sociabilidad": 0.3,
                 "paciencia": 0.0, "ambicion": 0.5},
                ["meta de " + nombre], "plaza"))
        mundo.ejecutar(46)
        medida = medir(mundo, mundo.agentes)
        self.assertEqual(medida["elecciones_colaborar"], 3)
        self.assertEqual(medida["colaboraciones"], 3)
        self.assertEqual(medida["proyectos_completados"], 1)

    def test_con_ejemplos_reproduce_la_demo_de_ocho(self):
        # La misma semilla 42 con los 3 ejemplos: 590 eventos,
        # 116 diálogos, 10 caos (cifras medidas al verificar la
        # bandera --con-ejemplos de la demo, 16 nov 2026).
        (medida,) = barrer([42], con_ejemplos=True)
        self.assertEqual(medida["eventos"], 590)
        self.assertEqual(medida["dialogo"], 116)
        self.assertEqual(medida["caos"], 10)
        self.assertEqual(medida["agentes"], 8)

    def test_resumen_cuenta_las_semillas_que_colaboran(self):
        # resumir() sobre medidas fabricadas: el conteo y la
        # comparación de confianza salen de los datos, no del azar.
        resultados = [
            {"semilla": 0, "eventos": 300, "pensamiento": 150,
             "colaboraciones": 0,
             "proyectos_completados": 0, "elecciones_colaborar": 0,
             "confianza_max": 0.5},
            {"semilla": 1, "eventos": 320, "pensamiento": 150,
             "colaboraciones": 3,
             "proyectos_completados": 1, "elecciones_colaborar": 3,
             "confianza_max": 0.9},
            {"semilla": 2, "eventos": 310, "pensamiento": 150,
             "colaboraciones": 1,
             "proyectos_completados": 0, "elecciones_colaborar": 2,
             "confianza_max": 0.8},
        ]
        resumen = resumir(resultados)
        self.assertEqual(resumen["semillas"], 3)
        self.assertEqual(resumen["semillas_con_colaboracion"], 2)
        self.assertEqual(resumen["que_colaboran"], [1, 2])
        self.assertEqual(resumen["colaboraciones_totales"], 4)
        self.assertEqual(resumen["proyectos_completados"], 1)
        self.assertEqual(resumen["elecciones_colaborar_total"], 5)
        self.assertEqual(resumen["decisiones_totales"], 450)
        self.assertEqual(resumen["eventos_min"], 300)
        self.assertEqual(resumen["eventos_max"], 320)
        self.assertEqual(resumen["confianza_max_media_con_colaboracion"],
                         0.85)
        self.assertEqual(resumen["confianza_max_media_sin_colaboracion"],
                         0.5)


class TestLaboratorioCli(unittest.TestCase):
    """La CLI como subprocess: tabla y JSON, sin escribir archivos."""

    def _copiar_proyecto(self, destino):
        for carpeta in ("simulacion", "ejemplos"):
            shutil.copytree(
                os.path.join(RAIZ, carpeta),
                os.path.join(destino, carpeta),
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    def test_tabla_tres_semillas_en_subprocess(self):
        with tempfile.TemporaryDirectory() as tmp:
            copia = os.path.join(tmp, "proyecto")
            os.makedirs(copia)
            self._copiar_proyecto(copia)
            entorno = dict(os.environ)
            entorno.pop("PYTHONPATH", None)
            resultado = subprocess.run(
                [sys.executable, "-m", "simulacion.laboratorio", "3"],
                cwd=copia, env=entorno,
                capture_output=True, text=True, timeout=120)
            self.assertEqual(
                resultado.returncode, 0,
                "el laboratorio falló:\\n%s\\n%s" % (resultado.stdout,
                                                   resultado.stderr))
            self.assertIn("semilla", resultado.stdout)
            self.assertIn("Con colaboración:", resultado.stdout)
            # El laboratorio no escribe ningún registro.
            self.assertFalse(os.path.exists(
                os.path.join(copia, "registro.json")))

    def test_json_tres_semillas(self):
        # --json por llamada directa a main(): JSON válido con 3
        # semillas y el resumen; determinista entre llamadas.
        salidas = []
        for _ in range(2):
            buffer = StringIO()
            with redirect_stdout(buffer):
                main(["3", "--json"])
            salidas.append(json.loads(buffer.getvalue()))
        self.assertEqual(salidas[0], salidas[1])
        self.assertEqual(len(salidas[0]["semillas"]), 3)
        self.assertEqual(salidas[0]["resumen"]["semillas"], 3)
        self.assertEqual(
            [s["semilla"] for s in salidas[0]["semillas"]], [0, 1, 2])


if __name__ == "__main__":
    unittest.main()
