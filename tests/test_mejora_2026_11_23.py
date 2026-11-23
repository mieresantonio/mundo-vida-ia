"""Tests de la sesión de mejora del 23 nov 2026.

Cubren los comportamientos nuevos de esta sesión, todos con
escenarios construidos a mano (sin depender de ninguna corrida
concreta del generador aleatorio):

- La regla dura de colaborar por confianza (agente.py): con
  confianza >= 0.85 en un cercano y ambición >= 0.6, el agente
  colabora con su mejor amigo antes que charlar o explorar.
- Hablar y colaborar se dirigen al cercano de más confianza, no
  siempre al primero de la lista.
- Los dos tipos de caos nuevos (eclipse y feria) y su crecimiento
  (paciencia y sociabilidad).
- La amistad: confianza mutua >= 0.8 registrada una sola vez por
  par como evento de tipo "amistad", y el mapa de confianza
  ("relaciones") viajando en el registro que lee el visor.
- La plantilla de diálogo de confianza ("confío mucho en ti").

Las cifras de la demo canónica que estos cambios mueven (MD5,
distribución, diálogos, colaboraciones) se fijan en los tests
que ya las cubrían (test_invariantes, test_cli_demo,
test_laboratorio, test_ronda6_colaborar), actualizadas con los
valores medidos en la fase de publicación.

Solo usa la biblioteca estándar (``unittest``). Ejecutar desde la
raíz del proyecto con::

    python3 -m unittest discover
"""

import os
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from simulacion.agente import Agente  # noqa: E402
from simulacion.demo import construir_registro  # noqa: E402
from simulacion.experiencia import (  # noqa: E402
    _clasificar,
    registrar_experiencia,
)
from simulacion.interaccion import hablar  # noqa: E402
from simulacion.laboratorio import medir  # noqa: E402
from simulacion.mundo import TIPOS_CAOS, Mundo  # noqa: E402

RASGOS_BASE = {
    "curiosidad": 0.5,
    "sociabilidad": 0.5,
    "paciencia": 0.5,
    "ambicion": 0.5,
}


def agente_base(nombre="Prueba", lugar="plaza", rasgos=None, energia=None):
    agente = Agente(
        nombre,
        dict(rasgos if rasgos is not None else RASGOS_BASE),
        ["una meta de prueba"],
        lugar,
    )
    if energia is not None:
        agente.energia = energia
    return agente


def _percepcion(cercanos=("P2",), recuerdos=()):
    return {
        "tick": 1,
        "lugar": "plaza",
        "agentes_cercanos": list(cercanos),
        "evento_reciente": None,
        "recuerdos": list(recuerdos),
    }


class _RngFalso:
    """Como el de test_motor_bordes: ``choice`` devuelve el tipo de
    caos fijado si está en la secuencia ofrecida y si no, el
    primer elemento. ``random`` devuelve 0.99 (sin movimiento ni
    caos espontáneo dentro de tick si se usara)."""

    def __init__(self, tipo):
        self.tipo = tipo

    def choice(self, secuencia):
        return self.tipo if self.tipo in secuencia else secuencia[0]

    def random(self):
        return 0.99


def mundo_de_caos(tipo, agentes):
    mundo = Mundo(semilla=1)
    mundo.rng = _RngFalso(tipo)
    for agente in agentes:
        mundo.agregar_agente(agente)
    return mundo


class _RngFijo:
    """Como el de test_ronda4_hallazgos: sin movimiento ni caos
    espontáneo (random() siempre 0.99). Los tests de amistad lo
    usan para que la confianza solo cambie por lo que el propio
    test fija: sin él, una celebración o un rumor de la semilla
    podría mover el umbral que el test está midiendo."""

    def random(self):
        return 0.99

    def choice(self, secuencia):
        return secuencia[0]


class _ObservadorSiempre(Agente):
    """Agente del protocolo que siempre observa: su confianza no
    cambia por diálogo, así que aísla el umbral de amistad."""

    def pensar(self, percepcion):
        return {"pensamiento": "observo en silencio",
                "accion": "observar", "objetivo": None}


class TestColaborarPorConfianza(unittest.TestCase):
    """La regla dura 2 de Agente.pensar (23 nov 2026)."""

    def _ambicioso(self, confianza, sociabilidad=0.69, curiosidad=0.0,
                   ambicion=1.0, energia=80):
        agente = agente_base(
            nombre="P1",
            rasgos={"curiosidad": curiosidad, "sociabilidad": sociabilidad,
                    "paciencia": 0.0, "ambicion": ambicion},
            energia=energia)
        agente.relaciones["P2"] = confianza
        return agente

    def test_confianza_alta_y_ambicion_colabora_pese_a_ser_muy_sociable(self):
        # El cambio central de la sesión: con sociabilidad 0.9 la
        # regla dura de hablar capturaba antes al agente; ahora,
        # con confianza 0.9 en el cercano y ambición 1.0, colabora
        # con él en vez de charlar.
        agente = self._ambicioso(confianza=0.9, sociabilidad=0.9)
        decision = agente.pensar(_percepcion())
        self.assertEqual(decision["accion"], "colaborar")
        self.assertEqual(decision["objetivo"], "P2")
        self.assertIn("confío mucho en P2", decision["pensamiento"])

    def test_colaborar_gana_a_explorar_con_curiosidad_alta(self):
        # Con curiosidad 0.9 la regla dura de explorar actuaba
        # antes; la amistad probada con ambición pesa más.
        agente = self._ambicioso(confianza=0.9, curiosidad=0.9)
        decision = agente.pensar(_percepcion())
        self.assertEqual(decision["accion"], "colaborar")
        self.assertEqual(decision["objetivo"], "P2")

    def test_umbral_de_confianza_de_la_regla_nueva(self):
        # 0.85 son 17 diálogos: por debajo, la regla no dispara y
        # manda lo de siempre (aquí, la regla dura de hablar con
        # sociabilidad 0.9); en 0.85, colabora.
        for confianza, esperada in ((0.8, "hablar"), (0.85, "colaborar"),
                                    (1.0, "colaborar")):
            with self.subTest(confianza=confianza):
                agente = self._ambicioso(confianza=confianza,
                                         sociabilidad=0.9)
                self.assertEqual(
                    agente.pensar(_percepcion())["accion"], esperada)

    def test_sin_ambicion_la_confianza_alta_solo_da_conversacion(self):
        # Ambición 0.5, bajo el mínimo 0.6: ni con confianza 1.0
        # colabora; en puntuación, hablar (10.9) sigue ganando a
        # colaborar (10.07) con sociabilidad 0.69.
        agente = self._ambicioso(confianza=1.0, ambicion=0.5)
        decision = agente.pensar(_percepcion())
        self.assertEqual(decision["accion"], "hablar")

    def test_sin_energia_manda_descansar_antes_que_colaborar(self):
        agente = self._ambicioso(confianza=1.0, energia=29)
        self.assertEqual(agente.pensar(_percepcion())["accion"],
                         "descansar")

    def test_sin_compania_no_hay_con_quien_colaborar(self):
        agente = self._ambicioso(confianza=1.0)
        decision = agente.pensar(_percepcion(cercanos=()))
        self.assertEqual(decision["accion"], "construir")
        self.assertIsNone(decision["objetivo"])

    def test_objetivo_es_el_cercano_de_mas_confianza(self):
        # Hablar se dirige al cercano de más confianza, no al
        # primero de la lista; en empate (sin confianza
        # registrada), al primero, como antes.
        agente = agente_base(
            nombre="P1",
            rasgos={"curiosidad": 0.0, "sociabilidad": 0.9,
                    "paciencia": 0.0, "ambicion": 0.5})
        agente.relaciones.update({"A": 0.2, "B": 0.5, "C": 0.1})
        decision = agente.pensar(_percepcion(cercanos=("A", "B", "C")))
        self.assertEqual(decision["accion"], "hablar")
        self.assertEqual(decision["objetivo"], "B")
        sin_confianza = agente_base(
            nombre="P1",
            rasgos={"curiosidad": 0.0, "sociabilidad": 0.9,
                    "paciencia": 0.0, "ambicion": 0.5})
        decision = sin_confianza.pensar(_percepcion(cercanos=("A", "B", "C")))
        self.assertEqual(decision["objetivo"], "A")


class TestCaosNuevos(unittest.TestCase):
    """Eclipse y feria (23 nov 2026): 8 tipos de caos."""

    def test_los_ocho_tipos_de_caos_existen_y_se_pueden_forzar(self):
        self.assertEqual(len(TIPOS_CAOS), 8)
        self.assertEqual(set(TIPOS_CAOS),
                         {"tormenta", "descubrimiento", "escasez",
                          "celebracion", "rumor", "visita_inesperada",
                          "eclipse", "feria"})
        for tipo in TIPOS_CAOS:
            with self.subTest(tipo=tipo):
                mundo = mundo_de_caos(
                    tipo, [agente_base(nombre="Uno"),
                           agente_base(nombre="Dos")])
                texto = mundo.generar_caos()
                self.assertIsInstance(texto, str)
                self.assertTrue(texto)
                self.assertEqual(mundo.eventos[-1]["tipo"], "caos")
                self.assertEqual(mundo.evento_reciente, texto)

    def test_caos_eclipse_quita_energia_y_ensena_paciencia(self):
        uno = agente_base(nombre="Uno", energia=80)
        dos = agente_base(nombre="Dos", energia=5)
        mundo = mundo_de_caos("eclipse", [uno, dos])
        mundo.generar_caos()
        self.assertEqual((uno.energia, dos.energia), (70, 0))
        self.assertEqual(uno.animo, "inquieto")
        self.assertTrue(any("eclipse" in r for r in uno.memoria))
        # Segundo eclipse: hito de crecimiento (umbral 2) y la
        # paciencia sube 0.04, de 0.5 a 0.54.
        mundo.generar_caos()
        self.assertEqual(uno.rasgos["paciencia"], 0.54)
        self.assertEqual(uno.energia, 60)

    def test_caos_feria_suma_energia_y_confianza_solo_en_el_mercado(self):
        uno = agente_base(nombre="Uno", lugar="mercado", energia=95)
        dos = agente_base(nombre="Dos", lugar="mercado", energia=80)
        lejos = agente_base(nombre="Lejos", lugar="plaza", energia=80)
        mundo = mundo_de_caos("feria", [uno, dos, lejos])
        mundo.generar_caos()
        self.assertEqual((uno.energia, dos.energia, lejos.energia),
                         (100, 85, 85))
        self.assertEqual(uno.animo, "alegre")
        self.assertEqual(uno.relaciones["Dos"], 0.05)
        self.assertEqual(dos.relaciones["Uno"], 0.05)
        self.assertEqual(lejos.relaciones, {})
        self.assertTrue(any("feria" in r for r in uno.memoria))


class TestAmistad(unittest.TestCase):
    """La amistad (23 nov 2026): confianza mutua >= 0.8, un evento
    por par, y el mapa de confianza en el registro."""

    def _par(self, confianza_ida, confianza_vuelta):
        mundo = Mundo(semilla=42)
        mundo.rng = _RngFijo()
        agentes = []
        for nombre in ("Ana", "Ben"):
            agente = _ObservadorSiempre(nombre, dict(RASGOS_BASE),
                                        ["meta de " + nombre], "plaza")
            agentes.append(agente)
            mundo.agregar_agente(agente)
        agentes[0].relaciones["Ben"] = confianza_ida
        agentes[1].relaciones["Ana"] = confianza_vuelta
        return mundo, agentes

    def test_la_amistad_se_registra_al_cruzar_0_8_mutuo(self):
        mundo, _agentes = self._par(0.8, 0.8)
        mundo.tick()
        self.assertEqual(mundo.amistades, [("Ana", "Ben")])
        amistades = [e for e in mundo.eventos if e["tipo"] == "amistad"]
        self.assertEqual(len(amistades), 1)
        self.assertEqual(amistades[0]["tick"], 1)
        self.assertEqual(amistades[0]["agente"], "Ana")
        self.assertIn("Ana y Ben se han hecho amigos",
                      amistades[0]["texto"])

    def test_la_amistad_solo_se_registra_una_vez_por_par(self):
        mundo, _agentes = self._par(1.0, 1.0)
        mundo.ejecutar(5)
        amistades = [e for e in mundo.eventos if e["tipo"] == "amistad"]
        self.assertEqual(len(amistades), 1)
        self.assertEqual(mundo.amistades, [("Ana", "Ben")])

    def test_confianza_en_un_solo_sentido_no_es_amistad(self):
        # 0.9 en un sentido y 0.0 en el otro: la mutua es 0.0 y no
        # hay amistad aunque pasen los ticks (los observadores no
        # dialogan, así que la confianza no se mueve).
        mundo, _agentes = self._par(0.9, 0.0)
        mundo.ejecutar(3)
        self.assertEqual(mundo.amistades, [])
        self.assertEqual([e for e in mundo.eventos
                          if e["tipo"] == "amistad"], [])

    def test_por_debajo_de_0_8_mutuo_no_hay_amistad(self):
        mundo, _agentes = self._par(0.75, 0.75)
        mundo.ejecutar(3)
        self.assertEqual(mundo.amistades, [])

    def test_las_relaciones_viajan_en_el_registro_para_el_visor(self):
        mundo, agentes = self._par(0.8, 0.8)
        mundo.tick()
        iniciales = {a.nombre: dict(a.rasgos) for a in agentes}
        registro = construir_registro(mundo, agentes, iniciales)
        por_nombre = {a["nombre"]: a for a in registro["agentes"]}
        self.assertEqual(por_nombre["Ana"]["relaciones"], {"Ben": 0.8})
        self.assertEqual(por_nombre["Ben"]["relaciones"], {"Ana": 0.8})
        self.assertEqual(
            sum(1 for e in registro["eventos"]
                if e["tipo"] == "amistad"), 1)


class TestHablarConfianza(unittest.TestCase):
    """La plantilla de diálogo de confianza (23 nov 2026)."""

    def test_hablar_con_pensamiento_de_confianza_usa_la_plantilla_nueva(self):
        emisor = agente_base(nombre="Ana")
        receptor = agente_base(nombre="Ben")
        mensaje = hablar(
            emisor, receptor,
            "Creo que veo cerca a Ben. Así que voy a colaborar porque "
            "confío mucho en Ben y juntos podemos construir algo.")
        self.assertIn("confío mucho en ti, ¿hacemos algo juntos?",
                      mensaje)
        self.assertEqual(emisor.relaciones["Ben"], 0.05)
        self.assertEqual(receptor.relaciones["Ana"], 0.05)


class TestLaboratorioAmistades(unittest.TestCase):
    """medir() cuenta las amistades de la corrida."""

    def test_medir_cuenta_amistades(self):
        mundo = Mundo(semilla=42)
        mundo.rng = _RngFijo()
        agentes = []
        for nombre in ("Ana", "Ben"):
            agente = _ObservadorSiempre(nombre, dict(RASGOS_BASE),
                                        ["meta de " + nombre], "plaza")
            agentes.append(agente)
            mundo.agregar_agente(agente)
        agentes[0].relaciones["Ben"] = 0.8
        agentes[1].relaciones["Ana"] = 0.8
        mundo.ejecutar(3)
        medida = medir(mundo, agentes)
        self.assertEqual(medida["amistades"], 1)
        self.assertEqual(medida["amistad"], 1)


class TestExperienciaNuevosTipos(unittest.TestCase):
    """Eclipse y feria mueven rasgos al hito (23 nov 2026)."""

    def test_eclipse_suben_la_paciencia_al_segundo(self):
        agente = agente_base()
        self.assertEqual(_clasificar("eclipse: el cielo se oscureció"), "eclipse")
        resultado = registrar_experiencia(
            agente, "eclipse: el cielo se oscureció de repente", "eclipse")
        self.assertIsNone(resultado["cambio_rasgo"])
        resultado = registrar_experiencia(
            agente, "eclipse: el cielo se oscureció de repente", "eclipse")
        self.assertEqual(resultado["cambio_rasgo"],
                         {"rasgo": "paciencia", "antes": 0.5,
                          "despues": 0.54})

    def test_feria_sube_la_sociabilidad_al_segundo(self):
        agente = agente_base()
        self.assertEqual(_clasificar("feria en el mercado"), "feria")
        registrar_experiencia(agente, "feria en el mercado", "feria")
        resultado = registrar_experiencia(
            agente, "feria en el mercado", "feria")
        self.assertEqual(resultado["cambio_rasgo"],
                         {"rasgo": "sociabilidad", "antes": 0.5,
                          "despues": 0.52})


if __name__ == "__main__":
    unittest.main()
