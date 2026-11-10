"""Tests de la Ronda 4 (Bucle 2): cierre de los hallazgos H-1 a H-5.

Cada hallazgo de la Ronda 2 se cerró con sondas ejecutadas contra
el motor real (scripts en /tmp durante la sesión; los conteos
quedan en el log de la ronda, LOG-RONDA-4-B2.md):

- H-1 (CORREGIDO): ``evolucionar_metas`` descartaba una meta nueva
  explícita con menos de 4 recuerdos. La sonda directa dio 4 de 7
  longitudes de memoria descartadas, y la sonda sobre el llamador
  real (``Mundo.tick`` al completar un proyecto, agentes del
  protocolo con ambición 0.9-1.0, semillas 0-19) dio 26 de 90
  llamadas perdidas, todas con 3 recuerdos: el proyecto se
  completaba y nadie adoptaba la meta nueva que el propio mundo
  entregaba. La corrección: la puerta de los 4 recuerdos solo
  protege la retirada de la primera meta, no el alta explícita.
- H-2 (CORREGIDO, código muerto): el bloque de
  ``registrar_experiencia`` que comprobaba la clave
  ``"__logros__"`` era inalcanzable en efecto (ningún código crea
  ni lee esa clave; grep en todo el repo + sonda exhaustiva:
  ``meta_nueva`` vale ``None`` en 35 de 35 combinaciones tipo x
  repeticiones). Se eliminó el bloque; el campo ``meta_nueva`` se
  mantiene (forma parte del dict documentado) y estos tests fijan
  que la salida no cambió.
- H-3 (CARACTERIZACIÓN): ``resumen_experiencia`` y
  ``Agente.decidir`` no tienen llamadores dentro del proyecto;
  aquí se fija su comportamiento actual en profundidad (copias,
  contador reiniciado tras el hito, percepción guardada, y una
  propiedad sobre 200 agentes aleatorios), sin cambiar el motor.
- H-4 (CORREGIDO): el constructor aceptaba en silencio entradas
  fuera del contrato de ``como-unirse.md`` (metas como cadena ->
  lista de caracteres; metas con enteros -> aceptadas y luego
  ``pensar()`` reventaba al concatenar; rasgo no numérico ->
  error de ``float()``, ajeno al motor). Ahora rechaza con
  ``ValueError`` propio, como ya hacía con lugar/acción/duplicado.
- H-5 (CERRADO como no alcanzable): ``Mundo.lugar_de`` devolvería
  ``{}`` si ``mundo.lugares`` quedara vacío, pero ningún código
  del proyecto vacía ni reduce ``lugares`` (grep + sonda: 100
  semillas x 30 ticks, 300 consultas, 0 resultados que no sean
  una cadena válida; ``lugares`` queda con 5 entradas siempre).
  Solo una mutación externa directa lo provocaría, fuera del
  contrato. Sin cambio en el motor; se fija el comportamiento
  con las entradas que el sistema genera de verdad.

Solo usa la biblioteca estándar (``unittest``). Ejecutar desde la
raíz del proyecto con::

    python3 -m unittest discover
"""

import os
import random
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from simulacion.agente import ACCIONES_VALIDAS, Agente
from simulacion.demo import crear_agentes
from simulacion.experiencia import (
    evolucionar_metas,
    registrar_experiencia,
    resumen_experiencia,
)
from simulacion.mundo import LUGARES, Mundo

RASGOS_BASE = {
    "curiosidad": 0.5,
    "sociabilidad": 0.5,
    "paciencia": 0.5,
    "ambicion": 0.5,
}

PERCEPCION_SOLO = {
    "tick": 1,
    "lugar": "plaza",
    "agentes_cercanos": [],
    "evento_reciente": None,
    "recuerdos": [],
}


def agente_base(nombre="Prueba", lugar="plaza", rasgos=None, metas=None,
                memoria=0):
    agente = Agente(
        nombre,
        dict(rasgos if rasgos is not None else RASGOS_BASE),
        list(metas if metas is not None else ["una meta de prueba"]),
        lugar,
    )
    agente.memoria = ["recuerdo %d" % i for i in range(memoria)]
    return agente


class _RngFijo:
    """RNG sin movimiento ni caos espontáneo (como el de la sonda
    determinista de la Ronda 4)."""

    def random(self):
        return 0.99

    def choice(self, secuencia):
        return secuencia[0]


class _ColaboradorSiempre(Agente):
    def pensar(self, percepcion):
        return {"pensamiento": "a colaborar", "accion": "colaborar",
                "objetivo": None}


class TestH1MetaExplicitaSinPuerta(unittest.TestCase):
    """H-1: el alta explícita ya no la bloquea la puerta; la
    retirada y la derivación sin explícita siguen protegidas."""

    def test_meta_explicita_con_0_a_3_recuerdos_se_anade_sin_quitar(self):
        for memoria in range(4):
            with self.subTest(recuerdos=memoria):
                agente = agente_base(metas=["m1"], memoria=memoria)
                self.assertEqual(
                    evolucionar_metas(agente, nueva_meta="nueva"),
                    "nueva")
                self.assertEqual(agente.metas, ["m1", "nueva"])

    def test_meta_explicita_con_metas_vacias_y_pocos_recuerdos_se_anade(self):
        agente = agente_base(metas=[], memoria=0)
        self.assertEqual(
            evolucionar_metas(agente, nueva_meta="primera"), "primera")
        self.assertEqual(agente.metas, ["primera"])

    def test_sin_meta_explicita_la_puerta_sigue_bloqueando(self):
        # La razón documentada de la puerta (no vaciar las metas
        # demasiado pronto) sigue intacta para la evolución
        # derivada: sin meta completada ni explícita y con menos
        # de 4 recuerdos no hay cambio.
        for memoria in (0, 2, 3):
            with self.subTest(recuerdos=memoria):
                agente = agente_base(metas=["m1"], memoria=memoria)
                self.assertIsNone(evolucionar_metas(agente))
                self.assertEqual(agente.metas, ["m1"])

    def test_meta_explicita_con_4_o_mas_recuerdos_sigue_retirando_la_primera(self):
        # Continuidad con la semántica que Mundo.tick ya usaba en
        # los casos que sí pasaban la puerta: se retira la primera
        # y se añade la nueva.
        agente = agente_base(metas=["m1", "m2"], memoria=4)
        self.assertEqual(
            evolucionar_metas(agente, nueva_meta="nueva"), "nueva")
        self.assertEqual(agente.metas, ["m2", "nueva"])

    def test_mundo_ambicion_alta_la_primera_finalizacion_si_evoluciona(self):
        # Regresión de la sonda determinista: con ambición 1.0 el
        # proyecto se completa en 3 colaboraciones (3 recuerdos
        # por participante) y, antes de la corrección, la meta
        # nueva se perdía en esa primera finalización.
        mundo = Mundo(semilla=3)
        mundo.rng = _RngFijo()
        rasgos = dict(RASGOS_BASE, ambicion=1.0)
        agentes = []
        for nombre in ("ColabUno", "ColabDos"):
            agente = _ColaboradorSiempre(
                nombre, dict(rasgos), ["meta de " + nombre], "plaza")
            agentes.append(agente)
            mundo.agregar_agente(agente)
        mundo.ejecutar(2)
        for agente in agentes:
            self.assertIn("meta de " + agente.nombre, agente.metas)
            self.assertTrue(any(
                meta.startswith("Compartir lo aprendido en Proyecto")
                for meta in agente.metas))
        self.assertTrue(any(
            "completa una meta y adopta una nueva" in e["texto"]
            for e in mundo.eventos))


class TestH4ConstructorTipado(unittest.TestCase):
    """H-4: el constructor rechaza con ValueError propio lo que el
    contrato declara inválido, y mantiene lo válido de siempre."""

    def test_metas_como_cadena_rechazadas_no_se_convierten_en_caracteres(self):
        for metas in ("abc", "aprender", ""):
            with self.subTest(metas=metas):
                with self.assertRaises(ValueError) as ctx:
                    Agente("X", dict(RASGOS_BASE), metas, "plaza")
                self.assertIn("Metas no válidas", str(ctx.exception))

    def test_metas_que_no_son_lista_rechazadas(self):
        for metas in (123, 1.5, {"una": 1}):
            with self.subTest(metas=repr(metas)):
                with self.assertRaises(ValueError) as ctx:
                    Agente("X", dict(RASGOS_BASE), metas, "plaza")
                self.assertIn("Metas no válidas", str(ctx.exception))

    def test_metas_con_elementos_no_cadena_rechazadas(self):
        for metas in ([1, 2], ["bien", 3], [None]):
            with self.subTest(metas=repr(metas)):
                with self.assertRaises(ValueError) as ctx:
                    Agente("X", dict(RASGOS_BASE), metas, "plaza")
                self.assertIn("Metas no válidas", str(ctx.exception))

    def test_rasgo_no_numerico_rechazado_con_error_propio(self):
        for valor in (None, "texto", "0.9", True, [0.5]):
            with self.subTest(valor=repr(valor)):
                rasgos = dict(RASGOS_BASE, curiosidad=valor)
                with self.assertRaises(ValueError) as ctx:
                    Agente("X", rasgos, ["m"], "plaza")
                self.assertIn("Rasgo no válido", str(ctx.exception))
                self.assertIn("curiosidad", str(ctx.exception))

    def test_rasgos_que_no_son_objeto_rechazados(self):
        for rasgos in ("abc", 123, [("curiosidad", 0.1)]):
            with self.subTest(rasgos=repr(rasgos)):
                with self.assertRaises(ValueError) as ctx:
                    Agente("X", rasgos, ["m"], "plaza")
                self.assertIn("Rasgos no válidos", str(ctx.exception))

    def test_controles_validos_del_constructor_se_mantienen(self):
        # Enteros como valor de rasgo: números, se aceptan y se
        # limitan como antes. Tupla de metas: se acepta como lista.
        agente = Agente("X", dict(RASGOS_BASE, curiosidad=1),
                        ("m1", "m2"), "plaza")
        self.assertEqual(agente.rasgos["curiosidad"], 1.0)
        self.assertEqual(agente.metas, ["m1", "m2"])
        # None sigue dando los valores por defecto (fijado en la
        # Ronda 2) y las claves extra se siguen ignorando.
        vacio = Agente("Y", None, None, "plaza")
        self.assertEqual(vacio.rasgos, dict(RASGOS_BASE))
        self.assertEqual(vacio.metas, [])
        extra = Agente("Z", dict(RASGOS_BASE, extra="lo que sea"),
                       ["m"], "plaza")
        self.assertNotIn("extra", extra.rasgos)


class TestH2RegistrarSinBloqueMuerto(unittest.TestCase):
    """H-2: tras eliminar el bloque muerto, la salida de
    registrar_experiencia es la misma de antes en todo el espacio
    probado por la sonda (huella comparada en el log de la ronda)."""

    def test_meta_nueva_siempre_none_y_claves_exactas_en_todos_los_tipos(self):
        for tipo in ("colaborar", "construir", "dialogo", "tormenta",
                     "rumor", "escasez", "celebracion",
                     "descubrimiento", "explorar", None):
            with self.subTest(tipo=tipo):
                agente = agente_base()
                for _ in range(3):
                    resultado = registrar_experiencia(
                        agente, "un evento", tipo)
                    self.assertEqual(
                        set(resultado),
                        {"tipo", "texto", "cambio_rasgo", "meta_nueva"})
                    self.assertIsNone(resultado["meta_nueva"])

    def test_nunca_aparece_la_clave_logros_en_el_conteo(self):
        agente = agente_base()
        for _ in range(3):
            registrar_experiencia(agente, "colaborar en X", "colaborar")
            registrar_experiencia(agente, "construir en Y", "construir")
        self.assertNotIn("__logros__", agente._conteo_experiencias)
        # Tras 3 de cada tipo con umbral 2: un hito y 1 acumulado.
        self.assertEqual(agente._conteo_experiencias,
                         {"colaborar": 1, "construir": 1})


class TestH3ResumenExperiencia(unittest.TestCase):
    """H-3: caracterización de resumen_experiencia (sin cambios
    en el motor)."""

    def test_resumen_de_agente_recien_creado(self):
        agente = agente_base()
        self.assertEqual(resumen_experiencia(agente), {
            "nombre": "Prueba",
            "recuerdos": 0,
            "conteo_por_tipo": {},
            "rasgos": dict(RASGOS_BASE),
            "metas": ["una meta de prueba"],
        })

    def test_resumen_sin_contador_o_con_contador_none_no_falla(self):
        agente = agente_base()
        del agente._conteo_experiencias
        self.assertEqual(
            resumen_experiencia(agente)["conteo_por_tipo"], {})
        agente._conteo_experiencias = None
        self.assertEqual(
            resumen_experiencia(agente)["conteo_por_tipo"], {})

    def test_resumen_refleja_el_reinicio_del_contador_tras_el_hito(self):
        # Comportamiento actual fijado: tras el hito (2 del mismo
        # tipo) el contador del tipo vuelve a 0, así que el resumen
        # muestra 0 aunque haya 2 recuerdos de ese tipo.
        agente = agente_base()
        registrar_experiencia(agente, "diálogo con X", "dialogo")
        registrar_experiencia(agente, "diálogo con Y", "dialogo")
        resumen = resumen_experiencia(agente)
        self.assertEqual(resumen["recuerdos"], 2)
        self.assertEqual(resumen["conteo_por_tipo"], {"dialogo": 0})
        self.assertEqual(resumen["rasgos"]["sociabilidad"], 0.53)

    def test_resumen_con_varios_tipos_cuenta_los_acumulados(self):
        agente = agente_base()
        registrar_experiencia(agente, "tormenta", "tormenta")
        for _ in range(3):
            registrar_experiencia(agente, "rumor", "rumor")
        registrar_experiencia(agente, "escasez", "escasez")
        resumen = resumen_experiencia(agente)
        self.assertEqual(resumen["recuerdos"], 5)
        self.assertEqual(resumen["conteo_por_tipo"],
                         {"tormenta": 1, "rumor": 3, "escasez": 1})

    def test_resumen_las_tres_colecciones_son_copias_independientes(self):
        agente = agente_base()
        registrar_experiencia(agente, "tormenta", "tormenta")
        resumen = resumen_experiencia(agente)
        self.assertIsNot(resumen["metas"], agente.metas)
        self.assertIsNot(resumen["rasgos"], agente.rasgos)
        self.assertIsNot(resumen["conteo_por_tipo"],
                         agente._conteo_experiencias)
        resumen["conteo_por_tipo"]["tormenta"] = 99
        resumen["rasgos"]["curiosidad"] = 9.9
        resumen["metas"].append("intrusa")
        self.assertEqual(agente._conteo_experiencias["tormenta"], 1)
        self.assertEqual(agente.rasgos["curiosidad"], 0.5)
        self.assertEqual(agente.metas, ["una meta de prueba"])


class TestH3Decidir(unittest.TestCase):
    """H-3: caracterización de Agente.decidir (sin cambios en el
    motor)."""

    def test_decidir_estructura_exacta_y_determinismo(self):
        agente = agente_base()
        primera = agente.decidir(PERCEPCION_SOLO)
        segunda = agente.decidir(PERCEPCION_SOLO)
        self.assertEqual(primera, segunda)
        self.assertEqual(set(primera),
                         {"pensamiento", "accion", "objetivo"})
        self.assertIn(primera["accion"], ACCIONES_VALIDAS)
        self.assertIn("Así que voy a " + primera["accion"],
                      primera["pensamiento"])

    def test_decidir_sin_argumento_usa_la_ultima_percepcion(self):
        agente = agente_base(rasgos=dict(RASGOS_BASE, sociabilidad=0.7))
        # Sin percepción guardada parte de una vacía: está solo y
        # la regla social no puede dispararse.
        self.assertNotEqual(agente.decidir()["accion"], "hablar")
        mundo = Mundo()
        mundo.agregar_agente(agente)
        mundo.agregar_agente(agente_base(nombre="Vecino"))
        agente.percibir(mundo)
        decision = agente.decidir()
        self.assertEqual(decision["accion"], "hablar")
        self.assertEqual(decision["objetivo"], "Vecino")

    def test_decidir_con_percepcion_explicita_no_sustituye_la_guardada(self):
        agente = agente_base(rasgos=dict(RASGOS_BASE, sociabilidad=0.7))
        mundo = Mundo()
        mundo.agregar_agente(agente)
        agente.percibir(mundo)  # solo: queda guardada la de solo
        con_compania = dict(PERCEPCION_SOLO, agentes_cercanos=["Vecino"])
        self.assertEqual(agente.decidir(con_compania)["accion"], "hablar")
        # La explícita no pisa la guardada: decidir() a secas sigue
        # usando la percepción de estar solo.
        self.assertNotEqual(agente.decidir()["accion"], "hablar")

    def test_decidir_propiedad_sobre_200_agentes_aleatorios(self):
        rng = random.Random(20261109)
        pool_recuerdos = ["", "hubo escasez ayer", "una tormenta pasó",
                          "un descubrimiento nuevo", "charlé con alguien"]
        for i in range(200):
            rasgos = {clave: rng.random() for clave in RASGOS_BASE}
            agente = agente_base(nombre="P%d" % i, rasgos=rasgos)
            agente.energia = rng.randint(0, 100)
            cercanos = [n for n in ("A", "B", "C") if rng.random() < 0.5]
            percepcion = {
                "tick": rng.randint(0, 50),
                "lugar": "plaza",
                "agentes_cercanos": cercanos,
                "evento_reciente": rng.choice([None, "descubrimiento"]),
                "recuerdos": rng.sample(pool_recuerdos, 2),
            }
            with self.subTest(i=i):
                decision = agente.decidir(percepcion)
                self.assertIn(decision["accion"], ACCIONES_VALIDAS)
                self.assertIsInstance(decision["pensamiento"], str)
                self.assertIn("Así que voy a " + decision["accion"],
                              decision["pensamiento"])
                if decision["accion"] in ("hablar", "colaborar") and cercanos:
                    self.assertEqual(decision["objetivo"], cercanos[0])
                else:
                    self.assertTrue(
                        decision["objetivo"] is None
                        or isinstance(decision["objetivo"], str))


class TestH5LugarDe(unittest.TestCase):
    """H-5: con las entradas que el sistema genera de verdad,
    lugar_de siempre devuelve una cadena válida (la fragilidad de
    ``lugares`` vacío no es alcanzable desde el motor)."""

    def test_tras_ejecutar_varias_semillas_lugares_intactos_y_plaza(self):
        for semilla in range(10):
            with self.subTest(semilla=semilla):
                mundo = Mundo(semilla=semilla)
                agentes = crear_agentes()
                for agente in agentes:
                    mundo.agregar_agente(agente)
                mundo.ejecutar(30)
                self.assertEqual(len(mundo.lugares), 5)
                self.assertEqual(set(mundo.lugares), set(LUGARES))
                desconocido = mundo.lugar_de("Fantasma")
                self.assertIsInstance(desconocido, str)
                self.assertEqual(desconocido, "plaza")
                for agente in agentes:
                    self.assertIn(mundo.lugar_de(agente), LUGARES)

    def test_lugar_de_devuelve_cadena_para_toda_entrada_del_protocolo(self):
        mundo = Mundo()
        registrado = agente_base(nombre="Registrado", lugar="taller")
        mundo.agregar_agente(registrado)
        entradas = (registrado, "Registrado", "Desconocido",
                    agente_base(nombre="NoRegistrado"), 123)
        for entrada in entradas:
            with self.subTest(entrada=repr(entrada)):
                resultado = mundo.lugar_de(entrada)
                self.assertIsInstance(resultado, str)
                self.assertIn(resultado, LUGARES)
        self.assertEqual(mundo.lugar_de(registrado), "taller")


if __name__ == "__main__":
    unittest.main()
