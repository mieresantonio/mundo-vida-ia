"""Suite de regresión permanente de mundo-vida-ia (Fase 2, Ciclo 8).

Fija como tests ejecutables los comportamientos verificados a mano
en los ciclos anteriores de la Fase 2:

- Ciclo 1 (MUNDO-A1): demo.py escribe el registro dentro de su propio
  proyecto, con ruta relativa al script, desde cualquier directorio
  de trabajo.
- Ciclo 1 (MUNDO-A2): el motor rechaza con ``ValueError`` lugares
  iniciales y acciones fuera del catálogo.
- Ciclo 2: el texto generado sale acentuado en español.
- Ciclos 3-5: la demo es determinista —375 eventos, MD5
  ``b56a5a928fcf5a2722665c8251a5aa7b``— y el registro es idéntico
  entre ejecuciones y entre las dos vías (script y módulo).
- Ciclo 4 (MUNDO-M3): el motor rechaza con ``ValueError`` nombres de
  agente duplicados, sin alterar el agente ya registrado.

Todas las cifras de esta suite (MD5, 375 eventos y su distribución,
recuerdos por agente y conteos de formas acentuadas) se obtuvieron
ejecutando el proyecto en la sesión del Ciclo 8 (2026-11-02), no de
memoria: si un cambio legítimo de código o de datos mueve alguna,
hay que regenerar la demo, obtener la cifra nueva ejecutando el
proyecto y actualizar la constante correspondiente documentándolo
en ``improvement-log.md``.

Solo usa la biblioteca estándar (``unittest``). Ejecutar desde la
raíz del proyecto con::

    python3 -m unittest discover

Es una suite sobre una simulación por reglas y plantillas, no sobre
ninguna consciencia: comprueba el comportamiento del código, nada más.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

# La raíz del proyecto es la carpeta padre de tests/. Se pone al
# principio de sys.path para importar el código real de ESTE clon
# (también cuando la suite corre sobre una copia del proyecto).
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from simulacion.agente import ACCIONES_VALIDAS, LUGARES_VALIDOS, Agente
from simulacion.demo import TICKS, SEMILLA, construir_registro, crear_agentes
from simulacion.mundo import LUGARES, Mundo

# Cifras conocido-buenas, obtenidas ejecutando la demo en la sesión
# del Ciclo 8 (ver docstring del módulo).
MD5_CONOCIDO_BUENO = "b56a5a928fcf5a2722665c8251a5aa7b"
EVENTOS_ESPERADOS = 375
DISTRIBUCION_ESPERADA = {
    "pensamiento": 150,
    "accion": 80,
    "dialogo": 70,
    "crecimiento": 64,
    "caos": 11,
}
RECUERDOS_POR_AGENTE = {
    "Lia": 45,
    "Tomas": 39,
    "Nara": 44,
    "Rui": 41,
    "Mara": 42,
}
FORMAS_ACENTUADAS = {"energía": 335, "Así que": 230, "compañía": 53,
                     "últimamente": 30}
FORMAS_SIN_TILDE = ("energia", "Asi que", "compania", "ultimamente")

RASGOS_BASE = {
    "curiosidad": 0.5,
    "sociabilidad": 0.5,
    "paciencia": 0.5,
    "ambicion": 0.5,
}


def agente_base(nombre="Prueba", lugar="plaza"):
    return Agente(nombre, dict(RASGOS_BASE), ["una meta de prueba"], lugar)


def generar_registro():
    """Genera el registro de la demo ejecutando el motor real,
    con los mismos pasos que hace ``demo.main()`` (sin escribir
    archivos): mismos agentes, misma semilla, mismos ticks."""
    mundo = Mundo(semilla=SEMILLA)
    agentes = crear_agentes()
    rasgos_iniciales = {a.nombre: dict(a.rasgos) for a in agentes}
    for agente in agentes:
        mundo.agregar_agente(agente)
    for _ in range(TICKS):
        mundo.tick()
    return construir_registro(mundo, agentes, rasgos_iniciales)


def serializar(registro):
    """Los mismos bytes que demo.py escribe en registro.json."""
    return json.dumps(
        registro, ensure_ascii=False, indent=2).encode("utf-8")


def md5_de(datos):
    return hashlib.md5(datos).hexdigest()


class TestValidacionMotor(unittest.TestCase):
    """Ciclo 1, MUNDO-A2: lugares y acciones inválidos se rechazan."""

    def test_lugar_inicial_invalido_rechazado_en_el_constructor(self):
        for lugar in ("castillo_inventado", "narnia", "", "PLAZA"):
            with self.subTest(lugar=lugar):
                with self.assertRaises(ValueError) as ctx:
                    agente_base(lugar=lugar)
                self.assertIn("Lugar inicial no válido", str(ctx.exception))

    def test_lugar_mutado_tras_construir_rechazado_al_agregar(self):
        agente = agente_base()
        agente.lugar = "narnia"  # mutación posterior a la construcción
        mundo = Mundo()
        with self.assertRaises(ValueError):
            mundo.agregar_agente(agente)
        # El agente rechazado no queda registrado en ninguna parte.
        self.assertEqual(mundo.agentes, [])
        self.assertIsNone(mundo.agente_por_nombre(agente.nombre))

    def test_accion_invalida_rechazada(self):
        agente = agente_base()
        mundo = Mundo()
        mundo.agregar_agente(agente)
        with self.assertRaises(ValueError) as ctx:
            agente.actuar(mundo, {"accion": "volar",
                                  "pensamiento": "quiero volar",
                                  "objetivo": None})
        self.assertIn("Acción no válida", str(ctx.exception))

    def test_accion_ausente_rechazada(self):
        agente = agente_base()
        mundo = Mundo()
        mundo.agregar_agente(agente)
        for decision in ({}, {"accion": None}):
            with self.subTest(decision=decision):
                with self.assertRaises(ValueError):
                    agente.actuar(mundo, decision)

    def test_todos_los_lugares_y_acciones_validas_se_aceptan(self):
        # Control positivo: el rechazo no es «todo lanza», el catálogo
        # documentado funciona entero.
        for lugar in LUGARES_VALIDOS:
            with self.subTest(lugar=lugar):
                self.assertEqual(agente_base(lugar=lugar).lugar, lugar)
        mundo = Mundo()
        agente = agente_base()
        mundo.agregar_agente(agente)
        for accion in ACCIONES_VALIDAS:
            with self.subTest(accion=accion):
                evento = agente.actuar(
                    mundo, {"accion": accion, "pensamiento": "x",
                            "objetivo": None})
                self.assertEqual(evento["tipo"], "accion")
                self.assertEqual(evento["accion"], accion)

    def test_catalogos_de_agente_y_mundo_coinciden(self):
        # LUGARES_VALIDOS (agente.py) y LUGARES (mundo.py) deben ser el
        # mismo conjunto: si se desincronizan, un lugar pasaría un
        # control y fallaría en el otro.
        self.assertEqual(set(LUGARES_VALIDOS), set(LUGARES))
        self.assertEqual(len(LUGARES_VALIDOS), 5)
        self.assertEqual(len(ACCIONES_VALIDAS), 6)


class TestNombresDuplicados(unittest.TestCase):
    """Ciclo 4, MUNDO-M3: nombre duplicado, ValueError y mundo intacto."""

    def test_segundo_agente_con_el_mismo_nombre_rechazado(self):
        mundo = Mundo()
        primero = agente_base(nombre="Repetido")
        mundo.agregar_agente(primero)
        with self.assertRaises(ValueError) as ctx:
            mundo.agregar_agente(agente_base(nombre="Repetido"))
        self.assertIn("Nombre duplicado", str(ctx.exception))
        # El ya registrado queda intacto y es el único con ese nombre.
        self.assertEqual(mundo.agentes, [primero])
        self.assertIs(mundo.agente_por_nombre("Repetido"), primero)
        self.assertEqual(mundo.agentes_en("plaza"), ["Repetido"])

    def test_reregistrar_el_mismo_objeto_tambien_rechazado(self):
        mundo = Mundo()
        agente = agente_base(nombre="Unico")
        mundo.agregar_agente(agente)
        with self.assertRaises(ValueError):
            mundo.agregar_agente(agente)
        self.assertEqual(mundo.agentes, [agente])

    def test_tras_el_rechazo_el_mundo_sigue_corriendo(self):
        mundo = Mundo()
        mundo.agregar_agente(agente_base(nombre="Solo"))
        with self.assertRaises(ValueError):
            mundo.agregar_agente(agente_base(nombre="Solo"))
        mundo.ejecutar(3)
        self.assertEqual(mundo.tick_actual, 3)
        self.assertTrue(mundo.eventos)

    def test_duplicar_un_ejemplo_cargado_tambien_rechazado(self):
        with open(os.path.join(RAIZ, "ejemplos", "exploradora.json"),
                  encoding="utf-8") as f:
            datos = json.load(f)
        mundo = Mundo()
        mundo.agregar_agente(Agente(datos["nombre"], datos["rasgos"],
                                    datos["metas"], datos["lugar_inicial"]))
        with self.assertRaises(ValueError):
            mundo.agregar_agente(Agente(datos["nombre"], datos["rasgos"],
                                        datos["metas"],
                                        datos["lugar_inicial"]))


class TestEjemplos(unittest.TestCase):
    """Control positivo del protocolo: los 3 ejemplos de ejemplos/
    cargan, se agregan (nombres distintos) y el mundo corre ticks."""

    def test_los_tres_ejemplos_funcionan_en_un_mundo(self):
        mundo = Mundo()
        nombres = []
        for archivo in ("exploradora.json", "constructor.json",
                        "organizadora.json"):
            with open(os.path.join(RAIZ, "ejemplos", archivo),
                      encoding="utf-8") as f:
                datos = json.load(f)
            agente = Agente(datos["nombre"], datos["rasgos"],
                            datos["metas"], datos["lugar_inicial"])
            mundo.agregar_agente(agente)
            nombres.append(datos["nombre"])
            self.assertIs(mundo.agente_por_nombre(datos["nombre"]), agente)
        self.assertEqual(len(set(nombres)), 3)
        self.assertEqual(len(mundo.agentes), 3)
        mundo.ejecutar(5)
        self.assertEqual(mundo.tick_actual, 5)
        self.assertTrue(mundo.eventos)


class TestDeterminismo(unittest.TestCase):
    """Ciclos 3-5: mismo registro entre ejecuciones, igual al
    conocido-bueno, y los archivos versionados coinciden con él."""

    @classmethod
    def setUpClass(cls):
        cls.registro = generar_registro()
        cls.bytes_registro = serializar(cls.registro)

    def test_dos_generaciones_son_byte_a_byte_identicas(self):
        self.assertEqual(serializar(generar_registro()),
                         self.bytes_registro)

    def test_el_registro_coincide_con_el_conocido_bueno(self):
        self.assertEqual(md5_de(self.bytes_registro), MD5_CONOCIDO_BUENO)
        self.assertEqual(self.registro["meta"],
                         {"ticks": TICKS, "semilla": SEMILLA})
        eventos = self.registro["eventos"]
        self.assertEqual(len(eventos), EVENTOS_ESPERADOS)
        distribucion = {}
        for evento in eventos:
            distribucion[evento["tipo"]] = \
                distribucion.get(evento["tipo"], 0) + 1
        self.assertEqual(distribucion, DISTRIBUCION_ESPERADA)
        recuerdos = {a["nombre"]: len(a["recuerdos"])
                     for a in self.registro["agentes"]}
        self.assertEqual(recuerdos, RECUERDOS_POR_AGENTE)

    def test_los_registros_versionados_son_ese_mismo_registro(self):
        for ruta in (os.path.join(RAIZ, "registro.json"),
                     os.path.join(RAIZ, "visor", "registro.json")):
            with self.subTest(ruta=ruta):
                with open(ruta, "rb") as f:
                    datos = f.read()
                self.assertEqual(md5_de(datos), MD5_CONOCIDO_BUENO)
                self.assertEqual(datos, self.bytes_registro)


class TestDemoComoPrograma(unittest.TestCase):
    """Ciclo 1, MUNDO-A1 + Ciclos 4-5: la demo ejecutada como programa
    (script y módulo, en copias temporales del proyecto) escribe
    dentro de su propia copia, desde cualquier directorio de trabajo,
    y ambas vías producen el registro conocido-bueno."""

    def _copiar_proyecto(self, destino):
        shutil.copytree(
            os.path.join(RAIZ, "simulacion"),
            os.path.join(destino, "simulacion"),
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    def _ejecutar(self, argumentos, cwd):
        entorno = dict(os.environ)
        entorno.pop("PYTHONPATH", None)
        resultado = subprocess.run(
            [sys.executable] + argumentos, cwd=cwd, env=entorno,
            capture_output=True, text=True, timeout=120)
        self.assertEqual(
            resultado.returncode, 0,
            "la demo falló:\n%s\n%s" % (resultado.stdout,
                                        resultado.stderr))
        return resultado

    def _comprobar_registro_de_la_copia(self, copia):
        rutas = [os.path.join(copia, "registro.json"),
                 os.path.join(copia, "visor", "registro.json")]
        for ruta in rutas:
            self.assertTrue(os.path.isfile(ruta),
                            "la demo no escribió %s" % ruta)
            with open(ruta, "rb") as f:
                datos = f.read()
            self.assertEqual(md5_de(datos), MD5_CONOCIDO_BUENO)
        with open(rutas[0], encoding="utf-8") as f:
            registro = json.load(f)
        self.assertEqual(len(registro["eventos"]), EVENTOS_ESPERADOS)
        return rutas

    def test_script_desde_otro_directorio_escribe_en_su_proyecto(self):
        with tempfile.TemporaryDirectory() as tmp:
            copia = os.path.join(tmp, "proyecto")
            otro_cwd = os.path.join(tmp, "otro")
            os.makedirs(copia)
            os.makedirs(otro_cwd)
            self._copiar_proyecto(copia)
            resultado = self._ejecutar(
                [os.path.join(copia, "simulacion", "demo.py")],
                cwd=otro_cwd)
            self._comprobar_registro_de_la_copia(copia)
            # Nada se escapó al directorio desde el que se lanzó.
            self.assertFalse(os.path.exists(
                os.path.join(otro_cwd, "registro.json")))
            self.assertFalse(os.path.exists(
                os.path.join(otro_cwd, "visor")))
            # La consola resume la corrida y sale acentuada.
            self.assertIn("Ticks: 30 | Diálogos: 70 | "
                          "Eventos de caos: 11", resultado.stdout)
            self.assertIn("energía=", resultado.stdout)

    def test_modulo_desde_la_raiz_de_la_copia(self):
        with tempfile.TemporaryDirectory() as tmp:
            copia = os.path.join(tmp, "proyecto")
            os.makedirs(copia)
            self._copiar_proyecto(copia)
            self._ejecutar(["-m", "simulacion.demo"], cwd=copia)
            self._comprobar_registro_de_la_copia(copia)

    def test_las_dos_vias_producen_el_mismo_registro(self):
        with tempfile.TemporaryDirectory() as tmp:
            bytes_por_via = []
            for nombre, argumentos, cwd_rel in (
                    ("script", None, "otro"),
                    ("modulo", ["-m", "simulacion.demo"], None)):
                copia = os.path.join(tmp, nombre)
                os.makedirs(copia)
                self._copiar_proyecto(copia)
                if argumentos is None:
                    argumentos = [os.path.join(
                        copia, "simulacion", "demo.py")]
                    cwd = os.path.join(tmp, "otro_" + nombre)
                    os.makedirs(cwd)
                else:
                    cwd = copia
                self._ejecutar(argumentos, cwd=cwd)
                with open(os.path.join(copia, "registro.json"),
                          "rb") as f:
                    bytes_por_via.append(f.read())
            self.assertEqual(bytes_por_via[0], bytes_por_via[1])
            self.assertEqual(md5_de(bytes_por_via[0]),
                             MD5_CONOCIDO_BUENO)


class TestTextosAcentuados(unittest.TestCase):
    """Ciclo 2: el texto generado (eventos, recuerdos y metas del
    registro) sale acentuado; las formas sin tilde no aparecen en
    los textos (las claves JSON internas sí van sin tilde a
    propósito y no se miran aquí)."""

    @classmethod
    def setUpClass(cls):
        registro = generar_registro()
        textos = [e["texto"] for e in registro["eventos"]]
        for agente in registro["agentes"]:
            textos.extend(agente["recuerdos"])
            textos.extend(agente["metas"])
        cls.blob = "\n".join(textos)
        cls.pensamientos = [e["texto"] for e in registro["eventos"]
                            if e["tipo"] == "pensamiento"]

    def test_formas_acentuadas_presentes_con_sus_conteos(self):
        for forma, conteo in FORMAS_ACENTUADAS.items():
            with self.subTest(forma=forma):
                self.assertEqual(self.blob.count(forma), conteo)

    def test_formas_sin_tilde_ausentes_en_los_textos(self):
        for forma in FORMAS_SIN_TILDE:
            with self.subTest(forma=forma):
                self.assertEqual(self.blob.count(forma), 0)

    def test_todos_los_pensamientos_llevan_la_plantilla_acentuada(self):
        self.assertEqual(len(self.pensamientos),
                         DISTRIBUCION_ESPERADA["pensamiento"])
        for texto in self.pensamientos:
            self.assertIn("Así que voy a ", texto)
            self.assertIn("energía es", texto)


if __name__ == "__main__":
    unittest.main()
