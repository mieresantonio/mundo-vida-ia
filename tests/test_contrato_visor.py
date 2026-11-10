"""Contrato motor -> visor de mundo-vida-ia (Ronda 10, Bucle 2).

El visor (``visor/index.html``) consume ``registro.json`` con una
estructura concreta, pero hasta esta ronda ninguna prueba fijaba ese
contrato: las 98 pruebas anteriores prueban el motor, no lo que el
visor lee. Si el motor renombrara una clave o emitiera un tipo de
evento nuevo, el visor se rompería en silencio (sección vacía o
eventos sin filtro ni color, sin ninguna excepción visible).

Este fichero fija el contrato REAL, extraído del código de ambas
partes en la Ronda 10:

Del visor (``visor/index.html``):
- L607: ``RASGOS = ["curiosidad", "sociabilidad", "paciencia",
  "ambicion"]`` — las únicas claves de rasgo que pinta.
- L608: ``TIPOS = ["todos", "pensamiento", "dialogo", "caos",
  "accion", "crecimiento"]`` — "todos" es un pseudo-filtro; los
  tipos reales son los otros cinco.
- L636-673 (``tarjetaAgente``): lee de cada agente ``nombre``,
  ``rasgos_iniciales``, ``rasgos_finales``, ``animo``, ``energia``,
  ``metas`` y ``recuerdos`` (de recuerdos solo ``.length``, L657).
- L675-682 (``eventoHTML``) y L723-729: lee de cada evento ``tick``,
  ``tipo``, ``agente`` y ``texto``.
- L714-719 (``pintar``): lee ``meta.ticks``, ``meta.semilla``,
  ``agentes.length`` y ``eventos.length``.
- L751 (``cargar``): la ÚNICA validación estructural del visor es
  ``datos.meta`` presente y ``agentes``/``eventos`` arrays; si falla,
  prueba la otra ruta y al final muestra el panel de error
  (``mostrarError``, L738). Todo lo demás degrada en silencio:
  rasgo ausente -> fila omitida (L638-640), metas ausentes ->
  «Sin metas registradas» (L650), tipo de evento desconocido ->
  se pinta solo en «todos», sin color ni filtro propio (L676,
  L685-703), ``agente`` ausente -> se omite el nombre (L680).

Del motor:
- ``simulacion/demo.py`` L68-88 (``construir_registro``): proyecta
  ``meta{ticks, semilla}``, ``agentes`` con exactamente las 7 claves
  de arriba y ``eventos`` con exactamente ``tick/tipo/agente/texto``.
- ``simulacion/mundo.py`` L92-99 (``_registrar``) y sus llamadores:
  ``pensamiento`` (L203), ``dialogo`` (L217), ``accion`` (L234,
  L255), ``crecimiento`` (L102-111 y L249-253) siempre con
  ``agente`` = nombre (cadena); ``caos`` (L193) siempre con
  ``agente`` = None.
- ``simulacion/agente.py`` L7: ``RASGOS_VALIDOS`` son los mismos 4
  rasgos del visor, y el constructor (L41-69) los completa todos,
  numéricos en 0.0-1.0; ``energia`` se mantiene en 0-100.

Los registros se generan de verdad (demo canónica y un barrido de
semillas/ticks) y se validan tras un viaje de ida y vuelta por JSON,
que es la forma en que el visor los consume (``fetch`` + ``.json()``).
Nunca se ejecuta ``demo.main()``: no se reescribe ningún
``registro.json``.

Solo biblioteca estándar (``unittest``). Ejecutar desde la raíz::

    python3 -m unittest discover
"""

import json
import os
import re
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from simulacion.agente import RASGOS_VALIDOS
from simulacion.demo import SEMILLA, TICKS, construir_registro, crear_agentes
from simulacion.mundo import Mundo

RUTA_VISOR = os.path.join(RAIZ, "visor", "index.html")

# El contrato, clave a clave, tal como lo lee el visor.
CLAVES_SUPERIORES = {"meta", "agentes", "eventos"}
CLAVES_META = {"ticks", "semilla"}
CLAVES_AGENTE = {
    "nombre", "rasgos_iniciales", "rasgos_finales",
    "animo", "energia", "metas", "recuerdos",
}
CLAVES_EVENTO = {"tick", "tipo", "agente", "texto"}

# Barrido corto: la demo canónica entra por SEMILLA/TICKS y además
# como un caso más del barrido.
SEMILLAS_BARRIDO = (0, 1, 7, 42, 99)
TICKS_BARRIDO = (0, 1, 5, 30)


# ------------------------------------------------------------------
# Extracción del contrato desde el propio código del visor.
# ------------------------------------------------------------------

def _script_del_visor():
    with open(RUTA_VISOR, encoding="utf-8") as f:
        fuente = f.read()
    return fuente.split("<script>", 1)[1].split("</script>", 1)[0]


def _lista_js(script, nombre):
    m = re.search(r"const %s = \[([^\]]*)\]" % nombre, script)
    if not m:
        return None
    return re.findall(r'"([^"]+)"', m.group(1))


def rasgos_del_visor():
    return _lista_js(_script_del_visor(), "RASGOS")


def tipos_del_visor():
    """Tipos reales del visor: su lista TIPOS sin el pseudo «todos»."""
    tipos = _lista_js(_script_del_visor(), "TIPOS")
    if tipos is None:
        return None
    return [t for t in tipos if t != "todos"]


# ------------------------------------------------------------------
# Generación real de registros (sin tocar ningún fichero).
# ------------------------------------------------------------------

def generar_registro(semilla, ticks):
    mundo = Mundo(semilla=semilla)
    agentes = crear_agentes()
    rasgos_iniciales = {a.nombre: dict(a.rasgos) for a in agentes}
    for agente in agentes:
        mundo.agregar_agente(agente)
    mundo.ejecutar(ticks)
    registro = construir_registro(mundo, agentes, rasgos_iniciales)
    # El visor consume JSON parseado: el contrato se comprueba sobre
    # la forma serializada, no sobre los objetos Python.
    return json.loads(json.dumps(registro, ensure_ascii=False))


def todos_los_registros():
    """[(etiqueta, registro, semilla, ticks)] demo canónica + barrido."""
    casos = [("demo canónica", SEMILLA, TICKS)]
    casos += [
        ("semilla %d, %d ticks" % (s, t), s, t)
        for s in SEMILLAS_BARRIDO for t in TICKS_BARRIDO
    ]
    return [(etq, generar_registro(s, t), s, t) for etq, s, t in casos]


# ------------------------------------------------------------------
# Validadores del contrato: devuelven la lista de problemas (vacía si
# el registro cumple). Cada problema nombra la clave culpable, para
# que un fallo señale exactamente qué parte del contrato se rompió.
# ------------------------------------------------------------------

def _es_numero(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def problemas_estructura(registro, semilla, ticks):
    probs = []
    if not isinstance(registro, dict):
        return ["el registro no es un objeto JSON"]
    for clave in sorted(CLAVES_SUPERIORES):
        if clave not in registro:
            probs.append("falta la clave superior %r que el visor lee" % clave)
    if probs:
        return probs
    if not isinstance(registro["meta"], dict):
        probs.append("'meta' no es un objeto")
    else:
        for clave in sorted(CLAVES_META):
            if clave not in registro["meta"]:
                probs.append("falta 'meta.%s' que el visor lee" % clave)
        meta = registro["meta"]
        if "ticks" in meta:
            if not isinstance(meta["ticks"], int) or isinstance(meta["ticks"], bool):
                probs.append("'meta.ticks' no es un entero: %r" % (meta["ticks"],))
            elif meta["ticks"] != ticks:
                probs.append(
                    "'meta.ticks'=%r no coincide con los ticks pedidos (%d)"
                    % (meta["ticks"], ticks))
        if "semilla" in meta:
            if not isinstance(meta["semilla"], int) or isinstance(meta["semilla"], bool):
                probs.append("'meta.semilla' no es un entero: %r" % (meta["semilla"],))
            elif meta["semilla"] != semilla:
                probs.append(
                    "'meta.semilla'=%r no coincide con la semilla pedida (%d)"
                    % (meta["semilla"], semilla))
    if not isinstance(registro["agentes"], list):
        probs.append("'agentes' no es una lista (el visor exige Array)")
    if not isinstance(registro["eventos"], list):
        probs.append("'eventos' no es una lista (el visor exige Array)")
    return probs


def problemas_agentes(registro, rasgos_visor):
    probs = []
    for i, a in enumerate(registro.get("agentes") or []):
        donde = "agentes[%d]" % i
        if not isinstance(a, dict):
            probs.append("%s no es un objeto" % donde)
            continue
        for clave in sorted(CLAVES_AGENTE):
            if clave not in a:
                probs.append("%s: falta la clave %r que el visor lee" % (donde, clave))
        if probs:
            continue
        if not isinstance(a["nombre"], str) or not a["nombre"]:
            probs.append("%s.nombre no es una cadena no vacía: %r" % (donde, a["nombre"]))
        if not isinstance(a["animo"], str) or not a["animo"]:
            probs.append("%s.animo no es una cadena no vacía: %r" % (donde, a["animo"]))
        if not _es_numero(a["energia"]):
            probs.append("%s.energia no es numérica: %r" % (donde, a["energia"]))
        elif not 0 <= a["energia"] <= 100:
            probs.append(
                "%s.energia=%r fuera del rango 0-100 que el visor pinta como «/ 100»"
                % (donde, a["energia"]))
        for campo in ("metas", "recuerdos"):
            if not isinstance(a[campo], list):
                probs.append("%s.%s no es una lista: %r" % (donde, campo, a[campo]))
            elif any(not isinstance(x, str) for x in a[campo]):
                probs.append("%s.%s contiene elementos que no son cadenas" % (donde, campo))
        for campo in ("rasgos_iniciales", "rasgos_finales"):
            rasgos = a[campo]
            if not isinstance(rasgos, dict):
                probs.append("%s.%s no es un objeto: %r" % (donde, campo, rasgos))
                continue
            if rasgos_visor is not None and set(rasgos) != set(rasgos_visor):
                probs.append(
                    "%s.%s tiene las claves %s y el visor pinta exactamente %s"
                    % (donde, campo, sorted(rasgos), rasgos_visor))
            for rasgo, valor in sorted(rasgos.items()):
                if not _es_numero(valor):
                    probs.append(
                        "%s.%s.%s no es numérico (el visor le aplica "
                        "Number().toFixed(2)): %r" % (donde, campo, rasgo, valor))
                elif not 0.0 <= valor <= 1.0:
                    probs.append(
                        "%s.%s.%s=%r fuera del rango 0.0-1.0 que el visor "
                        "convierte en porcentaje" % (donde, campo, rasgo, valor))
    return probs


def problemas_eventos(registro, tipos_visor):
    probs = []
    nombres = {
        a.get("nombre") for a in registro.get("agentes") or []
        if isinstance(a, dict)
    }
    ticks_meta = (registro.get("meta") or {}).get("ticks")
    for i, e in enumerate(registro.get("eventos") or []):
        donde = "eventos[%d]" % i
        if not isinstance(e, dict):
            probs.append("%s no es un objeto" % donde)
            continue
        for clave in sorted(CLAVES_EVENTO):
            if clave not in e:
                probs.append("%s: falta la clave %r que el visor lee" % (donde, clave))
        if probs:
            continue
        if not isinstance(e["tick"], int) or isinstance(e["tick"], bool):
            probs.append("%s.tick no es un entero: %r" % (donde, e["tick"]))
        elif isinstance(ticks_meta, int) and ticks_meta > 0:
            if not 1 <= e["tick"] <= ticks_meta:
                probs.append(
                    "%s.tick=%d fuera del rango 1..meta.ticks (%d)"
                    % (donde, e["tick"], ticks_meta))
        if not isinstance(e["tipo"], str):
            probs.append("%s.tipo no es una cadena: %r" % (donde, e["tipo"]))
        elif tipos_visor is not None and e["tipo"] not in tipos_visor:
            probs.append(
                "%s.tipo=%r no está en los tipos que el visor sabe "
                "pintar/filtrar: %s" % (donde, e["tipo"], tipos_visor))
        if not isinstance(e["texto"], str):
            probs.append("%s.texto no es una cadena: %r" % (donde, e["texto"]))
        # Campo por tipo que el visor usa igual para todos (muestra el
        # nombre si viene): el motor garantiza nombre en todo tipo
        # salvo «caos», que siempre lleva agente=None (mundo.py L193).
        if e.get("tipo") == "caos":
            if e["agente"] is not None:
                probs.append(
                    "%s: un evento 'caos' lleva agente=%r y el motor "
                    "siempre lo registra sin agente (None)" % (donde, e["agente"]))
        else:
            if not isinstance(e["agente"], str) or not e["agente"]:
                probs.append(
                    "%s: un evento de tipo %r lleva agente=%r; el motor "
                    "siempre lo registra con el nombre del agente"
                    % (donde, e.get("tipo"), e["agente"]))
            elif e["agente"] not in nombres:
                probs.append(
                    "%s.agente=%r no es el nombre de ningún agente del registro"
                    % (donde, e["agente"]))
    return probs


# ------------------------------------------------------------------
# Tests sobre registros generados de verdad.
# ------------------------------------------------------------------

class TestContratoSobreRegistrosGenerados(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.casos = todos_los_registros()
        cls.rasgos_visor = rasgos_del_visor()
        cls.tipos_visor = tipos_del_visor()

    def test_estructura_superior_y_meta(self):
        for etq, registro, semilla, ticks in self.casos:
            with self.subTest(caso=etq):
                self.assertEqual(
                    problemas_estructura(registro, semilla, ticks), [])

    def test_agentes_claves_y_tipos(self):
        # Presencia y tipos de las 7 claves, energía en 0-100 y
        # metas/recuerdos como listas de cadenas.
        for etq, registro, _s, _t in self.casos:
            with self.subTest(caso=etq):
                probs = [
                    p for p in problemas_agentes(registro, self.rasgos_visor)
                    if ".rasgos_" not in p
                ]
                self.assertEqual(probs, [])

    def test_rasgos_claves_son_exactamente_las_del_visor(self):
        self.assertIsNotNone(self.rasgos_visor,
                             "no se pudo extraer RASGOS de visor/index.html")
        for etq, registro, _s, _t in self.casos:
            with self.subTest(caso=etq):
                probs = [
                    p for p in problemas_agentes(registro, self.rasgos_visor)
                    if ".rasgos_" in p and "no es numérico" not in p
                    and "fuera del rango" not in p
                ]
                self.assertEqual(probs, [])

    def test_rasgos_inicial_y_final_numericos_en_rango(self):
        for etq, registro, _s, _t in self.casos:
            with self.subTest(caso=etq):
                probs = [
                    p for p in problemas_agentes(registro, self.rasgos_visor)
                    if "no es numérico" in p or "fuera del rango 0.0-1.0" in p
                ]
                self.assertEqual(probs, [])

    def test_eventos_claves_y_tipos(self):
        for etq, registro, _s, _t in self.casos:
            with self.subTest(caso=etq):
                probs = [
                    p for p in problemas_eventos(registro, self.tipos_visor)
                    if "no está en los tipos" not in p
                ]
                self.assertEqual(probs, [])

    def test_tipos_de_evento_dentro_del_conjunto_del_visor(self):
        self.assertIsNotNone(self.tipos_visor,
                             "no se pudo extraer TIPOS de visor/index.html")
        for etq, registro, _s, _t in self.casos:
            with self.subTest(caso=etq):
                vistos = {e.get("tipo") for e in registro["eventos"]}
                fuera = vistos - set(self.tipos_visor)
                self.assertEqual(
                    fuera, set(),
                    "tipos que el visor no sabe pintar ni filtrar: %r" % (fuera,))

    def test_campos_por_tipo_de_evento(self):
        # caos -> agente None; demás tipos -> agente = nombre de un
        # agente del registro; tick entero dentro de 1..meta.ticks.
        for etq, registro, _s, _t in self.casos:
            with self.subTest(caso=etq):
                probs = [
                    p for p in problemas_eventos(registro, self.tipos_visor)
                    if "caos" in p or "no es el nombre" in p
                    or "siempre lo registra" in p or "fuera del rango 1.." in p
                ]
                self.assertEqual(probs, [])

    def test_demo_canonica_ejercita_los_cinco_tipos_del_visor(self):
        registro = generar_registro(SEMILLA, TICKS)
        vistos = {e["tipo"] for e in registro["eventos"]}
        self.assertEqual(vistos, set(self.tipos_visor))

    def test_pensamientos_de_la_demo_listos_para_su_seccion(self):
        # La sección 02 del visor filtra tipo == "pensamiento" y cita
        # tick, agente y texto de cada uno.
        registro = generar_registro(SEMILLA, TICKS)
        pensamientos = [
            e for e in registro["eventos"] if e["tipo"] == "pensamiento"
        ]
        self.assertTrue(pensamientos, "la demo no produjo pensamientos")
        for e in pensamientos:
            self.assertIsInstance(e["agente"], str)
            self.assertTrue(e["agente"])
            self.assertIsInstance(e["texto"], str)
            self.assertTrue(e["texto"])

    def test_el_registro_crudo_sobrevive_al_viaje_json(self):
        # Sin viaje JSON previo: lo que construir_registro devuelve
        # debe serializarse y volver idéntico (eso consume el visor).
        mundo = Mundo(semilla=SEMILLA)
        agentes = crear_agentes()
        iniciales = {a.nombre: dict(a.rasgos) for a in agentes}
        for agente in agentes:
            mundo.agregar_agente(agente)
        mundo.ejecutar(TICKS)
        crudo = construir_registro(mundo, agentes, iniciales)
        viajado = json.loads(json.dumps(crudo, ensure_ascii=False))
        self.assertEqual(viajado, crudo)
        self.assertEqual(problemas_estructura(viajado, SEMILLA, TICKS), [])
        self.assertEqual(problemas_agentes(viajado, self.rasgos_visor), [])
        self.assertEqual(problemas_eventos(viajado, self.tipos_visor), [])


class TestContratoDelRegistroVersionado(unittest.TestCase):
    """El registro commiteado es el que el visor sirve tal cual: debe
    cumplir el mismo contrato que un registro recién generado."""

    def _validar_fichero(self, ruta):
        with open(ruta, encoding="utf-8") as f:
            registro = json.load(f)
        self.assertEqual(
            problemas_estructura(registro, SEMILLA, TICKS), [])
        self.assertEqual(problemas_agentes(registro, rasgos_del_visor()), [])
        self.assertEqual(problemas_eventos(registro, tipos_del_visor()), [])
        return registro

    def test_registro_versionado_en_raiz_cumple_el_contrato(self):
        self._validar_fichero(os.path.join(RAIZ, "registro.json"))

    def test_registro_del_visor_cumple_el_contrato_y_es_el_mismo(self):
        # El visor intenta «../registro.json» y «registro.json»: ambas
        # rutas deben servir un registro válido y el mismo contenido.
        raiz = self._validar_fichero(os.path.join(RAIZ, "registro.json"))
        del_visor = self._validar_fichero(
            os.path.join(RAIZ, "visor", "registro.json"))
        self.assertEqual(del_visor, raiz)


class TestContratoContraElCodigoDelVisor(unittest.TestCase):
    """Si el visor cambia lo que lee, estos tests fallan primero:
    obligan a actualizar el contrato en vez de dejarlo pudrirse."""

    def test_las_listas_del_visor_coinciden_con_el_motor(self):
        self.assertEqual(rasgos_del_visor(), list(RASGOS_VALIDOS))
        script = _script_del_visor()
        tipos_crudos = _lista_js(script, "TIPOS")
        self.assertIsNotNone(tipos_crudos)
        self.assertEqual(tipos_crudos[0], "todos")
        self.assertEqual(
            sorted(t for t in tipos_crudos if t != "todos"),
            ["accion", "caos", "crecimiento", "dialogo", "pensamiento"])

    def test_el_visor_no_lee_ninguna_clave_fuera_del_contrato(self):
        script = _script_del_visor()
        self.assertEqual(
            set(re.findall(r"\ba\.(\w+)", script)), CLAVES_AGENTE,
            "tarjetaAgente lee claves de agente fuera del contrato")
        self.assertEqual(
            set(re.findall(r"\be\.(\w+)", script)), CLAVES_EVENTO,
            "el visor lee claves de evento fuera del contrato")
        self.assertEqual(
            set(re.findall(r"\bdatos\.(\w+)", script)), CLAVES_SUPERIORES,
            "el visor lee claves superiores fuera del contrato")
        self.assertEqual(
            set(re.findall(r"\bdatos\.meta\.(\w+)", script)), CLAVES_META,
            "el visor lee claves de meta fuera del contrato")

    def test_el_visor_solo_valida_la_forma_basica_antes_de_pintar(self):
        # Documenta con el propio código la única guarda del visor:
        # sin meta o sin arrays no pinta y muestra el error; el resto
        # de ausencias degradan en silencio (de ahí estos tests).
        script = _script_del_visor()
        for fragmento in ("!datos.meta",
                          "Array.isArray(datos.agentes)",
                          "Array.isArray(datos.eventos)",
                          "mostrarError()"):
            self.assertIn(fragmento, script)


if __name__ == "__main__":
    unittest.main()
