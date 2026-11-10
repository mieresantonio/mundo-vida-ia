"""Tests de la Ronda 6 (Bucle 2): caracterización de ``colaborar``.

Hallazgo lateral de la Ronda 5: en la demo canónica la acción
``colaborar`` se elige 0 de 150 veces a 30 ticks y 0 de 15.000 a
3.000 ticks. Esta ronda lo resolvió con sondas (conteos completos
en LOG-RONDA-6-B2.md) y el veredicto es CARACTERIZADO, no bug:

- ``colaborar`` solo puede ganar en la rama de puntuación de
  ``Agente.pensar`` (agente.py:201-244), con compañía cerca, y su
  puntuación (ambición*4 + sociabilidad*3 + confianza*6) compite
  contra hablar (sociabilidad*10 + 4) y construir (ambición*10).
  La región ganadora existe y es alcanzable: en la rejilla de
  ``pensar`` (rasgos 0.0-1.0 en pasos de 0.1, confianza en
  {0, 0.5, 1}) gana en 5.039 de 43.923 combinaciones.
- En el flujo real de ``Mundo`` sin presets también ocurre con
  agentes del protocolo de rasgos moderados (par curiosidad 0,
  sociabilidad 0.3, paciencia 0, ambición 0.5: 190 elecciones en
  33 de 50 mundos y 53 proyectos completados, semillas 0-49 a
  100 ticks).
- Lo que no ocurre es en la DEMO canónica, por una carrera
  temporal medida: la ventana de puntuación con compañía se
  cierra en el tick 24 (la sociabilidad de los 5 agentes cruza
  0.7 por el crecimiento por diálogo y la regla dura de hablar,
  agente.py:193, captura a todo agente acompañado) y la primera
  confianza >= 0.65 entre un par aparece en el tick 26-27.

Estos tests fijan el camino por el que colaborar SÍ ocurre (vía
API y vía flujo real) y la distancia exacta de la demo a ese
estado. Sin cambios en el motor: el registro canónico y su MD5
quedan intactos.
"""

import os
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from simulacion.agente import Agente
from simulacion.demo import crear_agentes
from simulacion.mundo import Mundo


def _percepcion(cercanos=("P2",), recuerdos=()):
    return {
        "tick": 1,
        "lugar": "plaza",
        "agentes_cercanos": list(cercanos),
        "evento_reciente": None,
        "recuerdos": list(recuerdos),
    }


def _agente_quirurgico(confianza=1.0, **rasgos):
    """Agente en el centro de la región ganadora de colaborar:
    curiosidad 0, sociabilidad 0.69 (justo bajo la regla dura de
    hablar), paciencia 0, ambición 1.0, energía plena."""
    base = {"curiosidad": 0.0, "sociabilidad": 0.69,
            "paciencia": 0.0, "ambicion": 1.0}
    base.update(rasgos)
    agente = Agente("P1", base, ["meta generica"], "plaza")
    agente.energia = 80
    if confianza is not None:
        agente.relaciones["P2"] = confianza
    return agente


class TestColaborarPensar(unittest.TestCase):
    """La región ganadora de colaborar en Agente.pensar."""

    def test_estado_quirurgico_dispara_colaborar(self):
        agente = _agente_quirurgico(confianza=1.0)
        decision = agente.pensar(_percepcion())
        self.assertEqual(decision["accion"], "colaborar")
        self.assertEqual(decision["objetivo"], "P2")

    def test_umbral_de_confianza_medida(self):
        # Umbral teórico contra hablar: confianza >
        # (4 + 7*sociabilidad - 4*ambicion) / 6 = 0.805 para
        # sociabilidad 0.69 y ambición 1.0. La sonda lo confirmó:
        # 0.80 -> hablar, 0.81 -> colaborar. Se fijan valores
        # alejados del empate flotante.
        for confianza, esperada in ((0.0, "hablar"), (0.5, "hablar"),
                                    (0.8, "hablar"),
                                    (0.9, "colaborar"),
                                    (1.0, "colaborar")):
            with self.subTest(confianza=confianza):
                agente = _agente_quirurgico(confianza=confianza)
                self.assertEqual(
                    agente.pensar(_percepcion())["accion"], esperada)

    def test_bloqueos_que_impiden_colaborar(self):
        # Cada ingrediente del estado mínimo es necesario: si se
        # quita uno, otra acción captura la decisión.
        casos = {
            # sociabilidad 0.7: la regla dura de hablar (agente.py:193)
            "sociabilidad_0.7": (
                _agente_quirurgico(sociabilidad=0.7), _percepcion(),
                "hablar"),
            # curiosidad 0.7 sin descubrimiento: regla dura de
            # explorar (agente.py:196)
            "curiosidad_0.7": (
                _agente_quirurgico(curiosidad=0.7), _percepcion(),
                "explorar"),
            # energía < 30: regla dura de descansar (agente.py:190)
            "energia_29": (
                _agente_quirurgico(), _percepcion(), "descansar"),
            # sin compañía: colaborar se pone a 0 (agente.py:224-226)
            "sin_compania": (
                _agente_quirurgico(), _percepcion(cercanos=()),
                "construir"),
        }
        agente_energia = casos["energia_29"][0]
        agente_energia.energia = 29
        for nombre, (agente, percepcion, esperada) in casos.items():
            with self.subTest(caso=nombre):
                self.assertEqual(
                    agente.pensar(percepcion)["accion"], esperada)

    def test_lia_no_colabora_ni_con_confianza_maxima(self):
        # Rasgos de Lia en la demo (demo.py): su hablar en
        # puntuación vale 0.6*10 + 4 = 10 y su colaborar máximo
        # 0.5*4 + 0.6*3 + 1.0*6 = 9.8 — ni con confianza 1.0 con
        # el vecino puede ganar; y con curiosidad 0.9 la regla
        # dura de explorar actúa antes si no hay descubrimiento.
        lia = crear_agentes()[0]
        lia.energia = 80
        lia.relaciones["Tomas"] = 1.0
        sin_descubrimiento = lia.pensar(_percepcion(cercanos=("Tomas",)))
        self.assertEqual(sin_descubrimiento["accion"], "explorar")
        con_descubrimiento = lia.pensar(_percepcion(
            cercanos=("Tomas",),
            recuerdos=["descubrimiento en el bosque"]))
        self.assertEqual(con_descubrimiento["accion"], "hablar")

    def test_las_metas_no_influyen_en_la_accion(self):
        # pensar() usa la meta principal solo en el texto de los
        # deseos (agente.py:162, 180-181), no en la puntuación:
        # ni una meta de colaborar cambia la acción elegida.
        for metas in ([], ["meta generica"],
                      ["Colaborar en un proyecto compartido"],
                      ["Colaborar", "Colaborar", "Colaborar"]):
            with self.subTest(metas=metas):
                agente = _agente_quirurgico(confianza=1.0)
                agente.metas = list(metas)
                self.assertEqual(
                    agente.pensar(_percepcion())["accion"],
                    "colaborar")
                agente_sin = _agente_quirurgico(confianza=0.0)
                agente_sin.metas = list(metas)
                self.assertEqual(
                    agente_sin.pensar(_percepcion())["accion"],
                    "hablar")


class TestColaborarEnElMundo(unittest.TestCase):
    """Colaborar dentro del bucle real de Mundo.tick."""

    def _par(self, sociabilidad, ambicion):
        return [
            Agente(nombre,
                   {"curiosidad": 0.0, "sociabilidad": sociabilidad,
                    "paciencia": 0.0, "ambicion": ambicion},
                   ["meta de " + nombre], "plaza")
            for nombre in ("P1", "P2")
        ]

    def test_mundo_via_api_completa_proyecto_y_evoluciona_metas(self):
        # Vía API pública: rasgos dentro de la región ganadora y
        # confianza mutua preestablecida en el atributo público
        # ``relaciones``. Semilla 42, 30 ticks (sonda de la ronda:
        # 4 decisiones colaborar, proyecto completado en el
        # tick 26 y una adopción de meta por participante).
        mundo = Mundo(semilla=42)
        p1, p2 = self._par(sociabilidad=0.6, ambicion=1.0)
        p1.relaciones["P2"] = 1.0
        p2.relaciones["P1"] = 1.0
        mundo.agregar_agente(p1)
        mundo.agregar_agente(p2)
        mundo.ejecutar(30)
        completados = [e for e in mundo.eventos
                       if e["tipo"] == "accion"
                       and "completado por" in e["texto"]]
        adopciones = [e for e in mundo.eventos
                      if "adopta una nueva" in e["texto"]]
        self.assertEqual(len(completados), 1)
        self.assertIn("Proyecto del plaza", completados[0]["texto"])
        self.assertEqual(len(adopciones), 2)
        for agente in (p1, p2):
            self.assertEqual(
                agente.metas,
                ["Compartir lo aprendido en Proyecto del plaza"])

    def test_mundo_1_tick_preset_avanza_40_y_80_en_toda_semilla(self):
        # El primer tick es independiente de la semilla (el
        # movimiento y el caos van después del bucle de agentes):
        # ambos agentes colaboran y el proyecto nace al 40% y
        # avanza al 80% (avance 15 + 15*1.0 + 5*2 = 40 por llamada).
        for semilla in range(10):
            with self.subTest(semilla=semilla):
                mundo = Mundo(semilla=semilla)
                p1, p2 = self._par(sociabilidad=0.69, ambicion=1.0)
                p1.relaciones["P2"] = 1.0
                p2.relaciones["P1"] = 1.0
                mundo.agregar_agente(p1)
                mundo.agregar_agente(p2)
                mundo.ejecutar(1)
                avances = [e["texto"] for e in mundo.eventos
                           if "avanzan en" in e["texto"]]
                self.assertEqual(len(avances), 2)
                self.assertEqual(mundo.proyecto_actual["progreso"], 80)

    def test_flujo_real_sin_presets_completa_proyecto(self):
        # Sin tocar relaciones: un par del protocolo con rasgos
        # moderados (sociabilidad 0.3, ambición 0.5) sí llega a
        # colaborar en el flujo real — en la rejilla de la ronda
        # (semillas 0-49, 100 ticks) ocurrió 190 veces en 33 de
        # 50 mundos, con 53 proyectos completados. Aquí se fija
        # una corrida concreta: semilla 4, 46 ticks, 3 decisiones
        # colaborar, proyecto de la biblioteca completado y las
        # dos metas evolucionadas.
        mundo = Mundo(semilla=4)
        p1, p2 = self._par(sociabilidad=0.3, ambicion=0.5)
        mundo.agregar_agente(p1)
        mundo.agregar_agente(p2)
        mundo.ejecutar(46)
        completados = [e for e in mundo.eventos
                       if e["tipo"] == "accion"
                       and "completado por" in e["texto"]]
        adopciones = [e for e in mundo.eventos
                      if "adopta una nueva" in e["texto"]]
        self.assertEqual(len(completados), 1)
        self.assertIn("Proyecto del biblioteca",
                      completados[0]["texto"])
        self.assertEqual(len(adopciones), 2)
        for agente in (p1, p2):
            self.assertEqual(
                agente.metas,
                ["Compartir lo aprendido en Proyecto del biblioteca"])

    def test_demo_canonica_queda_fuera_de_la_region(self):
        # La distancia de la demo, fijada: semilla 42, 30 ticks,
        # 0 decisiones colaborar entre los 150 pensamientos, 0
        # proyectos y las metas finales iguales a las iniciales.
        mundo = Mundo(semilla=42)
        agentes = crear_agentes()
        metas_iniciales = {a.nombre: list(a.metas) for a in agentes}
        for agente in agentes:
            mundo.agregar_agente(agente)
        mundo.ejecutar(30)
        pensamientos = [e["texto"] for e in mundo.eventos
                        if e["tipo"] == "pensamiento"]
        self.assertEqual(len(pensamientos), 150)
        self.assertEqual(
            sum(1 for t in pensamientos if "voy a colaborar" in t), 0)
        self.assertIsNone(mundo.proyecto_actual)
        self.assertEqual(
            sum(1 for e in mundo.eventos
                if "completado por" in e["texto"]), 0)
        for agente in agentes:
            self.assertEqual(agente.metas, metas_iniciales[agente.nombre])


if __name__ == "__main__":
    unittest.main()
