"""Tests de la 2ª tanda de mejora del 23 nov 2026.

Cubren las cuatro mecánicas nuevas de esta tanda, todas con
escenarios construidos a mano (sin depender de ninguna corrida
concreta del generador aleatorio, salvo el test de integración
con la demo canónica, que usa su semilla fija 42):

- Metas compartidas (experiencia.py + mundo.py): al hacerse
  amigos (confianza mutua >= 0.8), cada agente adopta la meta de
  hacer un proyecto con el otro, sin perder ninguna meta propia;
  al completar un proyecto juntos, esa meta se cumple y se retira.
- Nombres propios para los proyectos (interaccion.py): el nombre
  depende del lugar y de los participantes, de forma determinista.
- Diario y momentos (diario.py): el diario de cada agente y los
  momentos destacados se generan solo con datos del registro.
- El registro guarda los momentos (demo.py) para que el visor los
  pinte; el contrato de esos momentos se fija en
  test_contrato_visor (ver PARCHE-test_contrato_visor.md).

Las cifras de la demo canónica que estos cambios mueven (MD5,
distribución de eventos, diálogos) se fijan en los tests que ya
las cubrían (test_invariantes, test_cli_demo, test_laboratorio,
test_ronda6_colaborar), actualizadas con los valores medidos en
la fase de publicación (medir_nuevas_cifras_tanda2.py).

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
from simulacion.demo import construir_registro, crear_agentes  # noqa: E402
from simulacion.diario import (  # noqa: E402
    diario_agente,
    generar_diario,
    generar_momentos,
)
from simulacion.experiencia import (  # noqa: E402
    adoptar_meta_compartida,
    meta_compartida_con,
)
from simulacion.interaccion import nombre_proyecto  # noqa: E402
from simulacion.mundo import Mundo  # noqa: E402

RASGOS_BASE = {
    "curiosidad": 0.5,
    "sociabilidad": 0.5,
    "paciencia": 0.5,
    "ambicion": 0.5,
}

# Rasgos que hacen ganar a colaborar por puntuación con confianza
# máxima en el cercano (ver test_meta_compartida_se_cumple...):
# colaborar = 1.0*6 + 1.0*4 + 0.1*3 = 10.3, por encima de
# construir (10.0) y de hablar (5.0). Sin reglas duras (energía
# 80, sociabilidad y curiosidad por debajo de 0.7).
RASGOS_COLABORADOR = {
    "curiosidad": 0.1,
    "sociabilidad": 0.1,
    "paciencia": 0.1,
    "ambicion": 1.0,
}


class _RngQuieto:
    """RNG que nunca mueve a nadie ni genera caos: random() siempre
    1.0 (por encima de las probabilidades de movimiento y caos) y
    choice() siempre el primer elemento. Aísla la lógica del tick
    del azar, como _RngQuieto de test_motor_bordes (1ª tanda)."""

    def random(self):
        return 1.0

    def choice(self, secuencia):
        return list(secuencia)[0]


def _agente(nombre="Ana", lugar="plaza", rasgos=None, metas=None):
    return Agente(
        nombre,
        dict(rasgos if rasgos is not None else RASGOS_BASE),
        list(metas if metas is not None else ["Explorar el mundo"]),
        lugar,
    )


def _eventos_de(mundo, tipo):
    return [e for e in mundo.eventos if e["tipo"] == tipo]


def _registro_fabricado():
    """Un registro pequeño con de todo: 2 agentes, 1 amistad,
    1 proyecto completado, 3 diálogos y 2 caos."""
    return {
        "meta": {"ticks": 10, "semilla": 7},
        "agentes": [
            {
                "nombre": "Ana",
                "rasgos_iniciales": {"curiosidad": 0.5, "sociabilidad": 0.5,
                                     "paciencia": 0.5, "ambicion": 0.5},
                "rasgos_finales": {"curiosidad": 0.9, "sociabilidad": 0.5,
                                   "paciencia": 0.5, "ambicion": 0.5},
                "animo": "alegre",
                "energia": 60,
                "metas": ["Explorar el mundo",
                          "Hacer un proyecto juntos con Ben"],
                "recuerdos": ["diálogo con Ben", "diálogo con Ben",
                              "colaborar en El puesto de Ana y Ben"],
            },
            {
                "nombre": "Ben",
                "rasgos_iniciales": {"curiosidad": 0.5, "sociabilidad": 0.5,
                                     "paciencia": 0.5, "ambicion": 0.5},
                "rasgos_finales": {"curiosidad": 0.5, "sociabilidad": 0.55,
                                   "paciencia": 0.5, "ambicion": 0.5},
                "animo": "tranquilo",
                "energia": 70,
                "metas": ["Explorar el mundo",
                          "Hacer un proyecto juntos con Ana"],
                "recuerdos": ["diálogo con Ana"],
            },
        ],
        "eventos": [
            {"tick": 1, "tipo": "dialogo", "agente": "Ana",
             "texto": "Ana le dice a Ben: \"¿cómo te va hoy?\""},
            {"tick": 2, "tipo": "caos", "agente": None,
             "texto": "Una tormenta repentina azota el mundo."},
            {"tick": 3, "tipo": "dialogo", "agente": "Ben",
             "texto": "Ben le dice a Ana: \"¿cómo te va hoy?\""},
            {"tick": 4, "tipo": "dialogo", "agente": "Ana",
             "texto": "Ana le dice a Ben: \"¿cómo te va hoy?\""},
            {"tick": 5, "tipo": "amistad", "agente": "Ana",
             "texto": "Ana y Ben se han hecho amigos: su confianza "
                      "mutua ya es muy alta."},
            {"tick": 5, "tipo": "crecimiento", "agente": "Ana",
             "texto": "Ana adopta una meta compartida: Hacer un "
                      "proyecto juntos con Ben."},
            {"tick": 6, "tipo": "caos", "agente": None,
             "texto": "Una tormenta repentina azota el mundo."},
            {"tick": 8, "tipo": "accion", "agente": "Ana",
             "texto": "¡Proyecto 'El puesto de Ana y Ben' completado "
                      "por Ana, Ben!"},
        ],
    }


class TestMetasCompartidas(unittest.TestCase):
    def test_adoptar_meta_compartida_anade_sin_quitar(self):
        # Con 5 recuerdos, evolucionar_metas retiraría la primera
        # meta; adoptar_meta_compartida NO debe hacerlo: hacerse
        # amigo no borra la meta propia del agente.
        agente = _agente(metas=["Explorar el mundo"])
        agente.memoria = ["recuerdo %d" % i for i in range(5)]
        resultado = adoptar_meta_compartida(agente, "Nara")
        self.assertEqual(resultado, "Hacer un proyecto juntos con Nara")
        self.assertEqual(
            agente.metas,
            ["Explorar el mundo", "Hacer un proyecto juntos con Nara"])

    def test_adoptar_meta_compartida_repetida_devuelve_none(self):
        agente = _agente()
        adoptar_meta_compartida(agente, "Nara")
        self.assertIsNone(adoptar_meta_compartida(agente, "Nara"))
        self.assertEqual(
            agente.metas.count("Hacer un proyecto juntos con Nara"), 1)

    def test_meta_compartida_con_devuelve_texto_o_none(self):
        agente = _agente()
        self.assertIsNone(meta_compartida_con(agente, "Nara"))
        adoptar_meta_compartida(agente, "Nara")
        self.assertEqual(meta_compartida_con(agente, "Nara"),
                         "Hacer un proyecto juntos con Nara")
        self.assertIsNone(meta_compartida_con(agente, "Rui"))


class TestAmistadAdoptaMetas(unittest.TestCase):
    def _mundo_con_par(self, confianza_a_b, confianza_b_a,
                       lugar_a="plaza", lugar_b="plaza"):
        mundo = Mundo(semilla=42)
        mundo.rng = _RngQuieto()
        ana = _agente("Ana", lugar_a)
        ben = _agente("Ben", lugar_b)
        ana.relaciones["Ben"] = confianza_a_b
        ben.relaciones["Ana"] = confianza_b_a
        mundo.agregar_agente(ana)
        mundo.agregar_agente(ben)
        return mundo, ana, ben

    def test_amistad_adopta_metas_compartidas(self):
        mundo, ana, ben = self._mundo_con_par(0.8, 0.8)
        mundo.tick()
        amistades = _eventos_de(mundo, "amistad")
        self.assertEqual(len(amistades), 1)
        self.assertEqual(mundo.amistades, [("Ana", "Ben")])
        self.assertIn("Hacer un proyecto juntos con Ben", ana.metas)
        self.assertIn("Hacer un proyecto juntos con Ana", ben.metas)
        # Las metas propias siguen intactas (la adopción no retira).
        self.assertIn("Explorar el mundo", ana.metas)
        self.assertIn("Explorar el mundo", ben.metas)
        adopciones = [e for e in _eventos_de(mundo, "crecimiento")
                      if "meta compartida" in e["texto"]]
        self.assertEqual(len(adopciones), 2)

    def test_amistad_solo_una_vez_y_meta_solo_una_vez(self):
        mundo, ana, ben = self._mundo_con_par(0.8, 0.8)
        mundo.tick()
        mundo.tick()
        self.assertEqual(len(_eventos_de(mundo, "amistad")), 1)
        self.assertEqual(
            ana.metas.count("Hacer un proyecto juntos con Ben"), 1)
        self.assertEqual(
            ben.metas.count("Hacer un proyecto juntos con Ana"), 1)

    def test_sin_amistad_no_hay_meta_compartida(self):
        # Lugares distintos: sin diálogos que suban la confianza,
        # 0.7 no llega al umbral 0.8 en un tick.
        mundo, ana, ben = self._mundo_con_par(0.7, 0.7,
                                              lugar_a="plaza",
                                              lugar_b="bosque")
        mundo.tick()
        self.assertEqual(_eventos_de(mundo, "amistad"), [])
        self.assertNotIn("Hacer un proyecto juntos con Ben", ana.metas)

    def test_confianza_en_un_solo_sentido_no_basta(self):
        mundo, ana, ben = self._mundo_con_par(1.0, 0.0,
                                              lugar_a="plaza",
                                              lugar_b="bosque")
        mundo.tick()
        self.assertEqual(_eventos_de(mundo, "amistad"), [])
        self.assertEqual(mundo.amistades, [])


class TestMetaCompartidaSeCumple(unittest.TestCase):
    def _mundo_colaborador(self):
        mundo = Mundo(semilla=42)
        mundo.rng = _RngQuieto()
        ana = _agente("Ana", "mercado", rasgos=RASGOS_COLABORADOR)
        ben = _agente("Ben", "mercado", rasgos=RASGOS_COLABORADOR)
        ana.relaciones["Ben"] = 1.0
        ben.relaciones["Ana"] = 1.0
        mundo.agregar_agente(ana)
        mundo.agregar_agente(ben)
        return mundo, ana, ben

    def test_meta_compartida_se_cumple_al_completar_proyecto_juntos(self):
        # Tick 1: colaboran (progreso 80) y se hacen amigos con la
        # confianza preset a 1.0, adoptando la meta compartida.
        # Tick 2: con el proyecto a 99, colaboran y lo completan:
        # la meta compartida se retira y nace la de compartir lo
        # aprendido, con el nombre propio del proyecto.
        mundo, ana, ben = self._mundo_colaborador()
        mundo.tick()
        self.assertIn("Hacer un proyecto juntos con Ben", ana.metas)
        self.assertEqual(mundo.proyecto_actual["progreso"], 80)
        nombre = mundo.proyecto_actual["nombre"]
        self.assertEqual(nombre,
                         nombre_proyecto("mercado", ["Ana", "Ben"]))
        mundo.proyecto_actual["progreso"] = 99
        mundo.tick()
        self.assertNotIn("Hacer un proyecto juntos con Ben", ana.metas)
        self.assertNotIn("Hacer un proyecto juntos con Ana", ben.metas)
        self.assertIn("Compartir lo aprendido en " + nombre, ana.metas)
        self.assertIn("Compartir lo aprendido en " + nombre, ben.metas)
        # La amistad no se vuelve a registrar ni la meta se
        # re-adopta: el par ya está en la guarda.
        self.assertEqual(len(_eventos_de(mundo, "amistad")), 1)
        cierres = [e for e in _eventos_de(mundo, "crecimiento")
                   if "completa una meta y adopta una nueva" in e["texto"]]
        self.assertEqual(len(cierres), 2)

    def test_completar_sin_meta_compartida_retira_la_primera(self):
        # Amistad pre-registrada en la guarda (sin metas adoptadas):
        # al completar, no hay meta compartida que cumplir y el
        # comportamiento es el de siempre: con 4+ recuerdos, se
        # retira la primera meta.
        mundo, ana, ben = self._mundo_colaborador()
        mundo._amistades.add(("Ana", "Ben"))
        mundo.amistades.append(("Ana", "Ben"))
        ana.memoria = ["recuerdo uno", "recuerdo dos"]
        ben.memoria = ["recuerdo uno", "recuerdo dos"]
        mundo.tick()
        self.assertNotIn("Hacer un proyecto juntos con Ben", ana.metas)
        mundo.proyecto_actual["progreso"] = 99
        mundo.tick()
        self.assertNotIn("Explorar el mundo", ana.metas)
        self.assertTrue(any(m.startswith("Compartir lo aprendido en ")
                            for m in ana.metas))


class TestNombresDeProyectos(unittest.TestCase):
    def test_nombre_determinista_y_con_participantes(self):
        nombre = nombre_proyecto("mercado", ["Ana", "Ben"])
        self.assertEqual(nombre, "El puesto de Ana y Ben")
        self.assertEqual(nombre_proyecto("mercado", ["Ana", "Ben"]),
                         nombre)

    def test_nombre_cambia_con_el_lugar(self):
        nombres = {lugar: nombre_proyecto(lugar, ["Ana", "Ben"])
                   for lugar in ("plaza", "biblioteca", "taller",
                                 "bosque", "mercado")}
        self.assertEqual(len(set(nombres.values())), 5)
        self.assertEqual(nombres["plaza"], "La plaza de Ana y Ben")
        self.assertEqual(nombres["biblioteca"],
                         "La biblioteca de Ana y Ben")

    def test_nombre_con_un_participante_sin_huecos(self):
        # "Mara" (4 letras) elige la plantilla de dos nombres, que
        # no puede rellenarse con uno solo: cae a la de uno.
        nombre = nombre_proyecto("taller", ["Mara"])
        self.assertEqual(nombre, "La herramienta de Mara")
        self.assertNotIn("{", nombre)
        self.assertEqual(nombre_proyecto("taller", ["Rui"]),
                         "La herramienta de Rui")

    def test_nombre_con_lugar_desconocido(self):
        self.assertEqual(nombre_proyecto("cueva", ["Ana", "Ben"]),
                         "Proyecto de Ana y Ben")


class TestMomentos(unittest.TestCase):
    def test_momentos_primera_amistad_y_proyecto(self):
        momentos = generar_momentos(_registro_fabricado())
        titulos = [m["titulo"] for m in momentos]
        self.assertIn("Primera amistad", titulos)
        self.assertIn("Primer proyecto completado", titulos)
        self.assertIn("Primera meta compartida", titulos)
        amistad = [m for m in momentos
                   if m["titulo"] == "Primera amistad"][0]
        self.assertEqual(amistad["tick"], 5)
        proyecto = [m for m in momentos
                    if m["titulo"] == "Primer proyecto completado"][0]
        self.assertEqual(proyecto["tick"], 8)
        ticks = [m["tick"] for m in momentos]
        self.assertEqual(ticks, sorted(ticks))

    def test_momentos_sin_amistad_ni_proyecto(self):
        registro = _registro_fabricado()
        registro["eventos"] = [e for e in registro["eventos"]
                               if e["tipo"] in ("dialogo", "caos")]
        titulos = [m["titulo"] for m in generar_momentos(registro)]
        self.assertNotIn("Primera amistad", titulos)
        self.assertNotIn("Primer proyecto completado", titulos)
        self.assertNotIn("Primera meta compartida", titulos)
        # Los momentos de resumen sí existen con estos datos.
        self.assertIn("Quién más cambió", titulos)
        self.assertIn("Quién más habló", titulos)
        self.assertIn("La pareja que más habló", titulos)

    def test_momentos_dialogo_numero_cincuenta(self):
        registro = _registro_fabricado()
        registro["eventos"] = [
            {"tick": i + 1, "tipo": "dialogo", "agente": "Ana",
             "texto": "Ana le dice a Ben: \"hola\""}
            for i in range(50)
        ]
        momentos = generar_momentos(registro)
        hito = [m for m in momentos
                if m["titulo"] == "Diálogo número 50"]
        self.assertEqual(len(hito), 1)
        self.assertEqual(hito[0]["tick"], 50)
        # Con 49 diálogos no hay hito.
        registro["eventos"] = registro["eventos"][:49]
        titulos = [m["titulo"] for m in generar_momentos(registro)]
        self.assertNotIn("Diálogo número 50", titulos)

    def test_momentos_caos_mas_repetido(self):
        momentos = generar_momentos(_registro_fabricado())
        caos = [m for m in momentos
                if m["titulo"] == "El caos más repetido"]
        self.assertEqual(len(caos), 1)
        self.assertIn("tormenta", caos[0]["texto"])
        self.assertIn("2 veces", caos[0]["texto"])
        self.assertEqual(caos[0]["tick"], 2)

    def test_momentos_quien_mas_cambio_y_hablo(self):
        momentos = generar_momentos(_registro_fabricado())
        cambio = [m for m in momentos
                  if m["titulo"] == "Quién más cambió"][0]
        self.assertIn("Ana", cambio["texto"])
        self.assertIn("curiosidad", cambio["texto"])
        self.assertIn("0.50 a 0.90", cambio["texto"])
        hablo = [m for m in momentos
                 if m["titulo"] == "Quién más habló"][0]
        self.assertIn("Ana", hablo["texto"])
        self.assertIn("2 veces", hablo["texto"])
        pareja = [m for m in momentos
                  if m["titulo"] == "La pareja que más habló"][0]
        self.assertIn("Ana y Ben", pareja["texto"])
        self.assertIn("3 veces", pareja["texto"])

    def test_momentos_maximo_ocho(self):
        self.assertLessEqual(len(generar_momentos(_registro_fabricado())),
                             8)

    def test_momentos_registro_vacio_no_rompe(self):
        self.assertEqual(generar_momentos({}), [])
        self.assertEqual(generar_momentos(None), [])
        self.assertEqual(generar_momentos({"meta": {}, "agentes": [],
                                           "eventos": []}), [])


class TestDiario(unittest.TestCase):
    def test_diario_agente_cuenta_su_historia(self):
        texto = diario_agente(_registro_fabricado(), "Ana")
        self.assertIn("Soy Ana.", texto)
        self.assertIn("Hablé 2 veces; la primera vez, con Ben.", texto)
        self.assertIn("Me hice amigo de Ben.", texto)
        # El proyecto se completó en el tick 8, después de la
        # amistad (tick 5): la meta compartida se cumplió.
        self.assertIn("Cumplí mi meta de hacer un proyecto con Ben.",
                      texto)
        self.assertIn("curiosidad: de 0.50 a 0.90", texto)
        self.assertIn("Guardo 3 recuerdos", texto)

    def test_diario_agente_con_meta_pendiente(self):
        registro = _registro_fabricado()
        registro["eventos"] = [e for e in registro["eventos"]
                               if not (e["tipo"] == "accion")]
        texto = diario_agente(registro, "Ana")
        self.assertIn("Quiero hacer un proyecto con Ben", texto)
        self.assertNotIn("Cumplí mi meta", texto)

    def test_diario_agente_sin_amigos_ni_dialogos(self):
        registro = {"meta": {"ticks": 3, "semilla": 1},
                    "agentes": [{
                        "nombre": "Solo",
                        "rasgos_iniciales": {"curiosidad": 0.5},
                        "rasgos_finales": {"curiosidad": 0.5},
                        "animo": "tranquilo", "energia": 80,
                        "metas": ["Explorar el mundo"],
                        "recuerdos": [],
                    }],
                    "eventos": []}
        texto = diario_agente(registro, "Solo")
        self.assertIn("No hablé con nadie", texto)
        self.assertIn("No hice amigos en esta corrida.", texto)
        self.assertIn("Mis rasgos casi no se movieron.", texto)

    def test_diario_agente_desconocido(self):
        self.assertIn("No hay ningún agente llamado X",
                      diario_agente(_registro_fabricado(), "X"))

    def test_generar_diario_estructura(self):
        texto = generar_diario(_registro_fabricado())
        self.assertIn("Diario del mundo: 10 ticks, semilla 7, "
                      "2 agentes.", texto)
        self.assertIn("Momentos destacados:", texto)
        self.assertIn("- Tick 5: Primera amistad.", texto)
        self.assertIn("Diario de Ana:", texto)
        self.assertIn("Diario de Ben:", texto)
        self.assertTrue(texto.endswith("Fin del diario."))


class TestRegistroConMomentos(unittest.TestCase):
    def test_construir_registro_incluye_momentos(self):
        mundo = Mundo(semilla=42)
        agentes = crear_agentes()
        rasgos = {a.nombre: dict(a.rasgos) for a in agentes}
        for agente in agentes:
            mundo.agregar_agente(agente)
        mundo.ejecutar(3)
        registro = construir_registro(mundo, agentes, rasgos)
        self.assertIn("momentos", registro)
        for momento in registro["momentos"]:
            self.assertEqual(set(momento),
                             {"tick", "titulo", "texto"})
            self.assertIsInstance(momento["tick"], int)
        ticks = [m["tick"] for m in registro["momentos"]]
        self.assertEqual(ticks, sorted(ticks))
        self.assertLessEqual(len(registro["momentos"]), 8)

    def test_diario_de_la_demo_canonica(self):
        # Integración con el motor real (semilla 42, 30 ticks): el
        # diario se genera sin romperse y nombra a los 5 agentes.
        # No afirma amistades ni proyectos concretos: esas cifras
        # las mide el script de publicación.
        mundo = Mundo(semilla=42)
        agentes = crear_agentes()
        rasgos = {a.nombre: dict(a.rasgos) for a in agentes}
        for agente in agentes:
            mundo.agregar_agente(agente)
        mundo.ejecutar(30)
        registro = construir_registro(mundo, agentes, rasgos)
        texto = generar_diario(registro)
        for nombre in ("Lia", "Tomas", "Nara", "Rui", "Mara"):
            self.assertIn("Diario de %s:" % nombre, texto)
        self.assertTrue(texto.endswith("Fin del diario."))


if __name__ == "__main__":
    unittest.main()
