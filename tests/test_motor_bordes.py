"""Tests de bordes del motor de mundo-vida-ia (Ronda 2, Bucle 2).

Fijan comportamientos verificados de primera mano ejecutando el
motor en la sesión de la Ronda 2 (2026-11-09), en las zonas que la
suite original (``test_invariantes.py``, 20 tests) no ejercitaba
de forma directa según la medición de cobertura con la biblioteca
estándar (``python3 -m trace --count --missing``):

- ``Agente.decidir()`` y ``Agente.actuar()`` sin decisión previa
  (0 ejecuciones en la corrida trazada).
- ``experiencia._clasificar`` sin tipo sugerido, el umbral de
  crecimiento de ``registrar_experiencia``, ``evolucionar_metas``
  completo y ``resumen_experiencia`` (sin ningún llamador en el
  motor: solo se ejercitan aquí).
- ``interaccion.colaborar`` completo (hasta el 23 nov 2026, en
  la demo de la semilla 42 la rama de colaborar de ``Mundo.tick``
  no se disparaba ni una vez en 30 ticks; desde la regla dura de
  colaborar por confianza sí se dispara) y las plantillas de
  ``hablar`` que la demo no produce (cansado, solo, curiosidad y
  la de por defecto).
- Los 6 tipos de caos originales de ``Mundo.generar_caos``
  forzados con un RNG falso determinista, incluidas las ramas que
  la semilla 42 no alcanza (celebración con dos agentes en la
  plaza y rumor con un solo agente). Los 2 tipos nuevos (eclipse
  y feria) se fuerzan igual en tests/test_mejora_2026_11_23.py.
- El protocolo de agente personalizado de ``como-unirse.md``:
  un ``pensar()`` propio que devuelve ``hablar``/``colaborar``
  con ``objetivo`` a ``None`` funciona dentro de ``Mundo.tick``.

Incluye además la regresión del único bug corregido en esta
ronda: ``hablar`` consigo mismo sumaba la confianza dos veces
(+0.10) sobre la misma clave; lo documentado es +0.05 por sentido
y consigo mismo solo hay un sentido.

Y una caracterización que en la Ronda 4 pasó a regresión: en la
Ronda 2 se fijó que ``evolucionar_metas`` con una meta nueva
explícita, sin meta completada y con menos de 4 recuerdos, no
añadía nada y devolvía ``None``. Las sondas de la Ronda 4
demostraron que el llamador real (``Mundo.tick`` al completar un
proyecto) perdía así metas de verdad (26 de 90 llamadas con
ambición 0.9–1.0), así que el motor se corrigió: la puerta de
los 4 recuerdos solo protege la retirada, no el alta explícita.
El test correspondiente fija ahora el comportamiento corregido
y, en ``tests/test_ronda4_hallazgos.py``, que la puerta sigue
bloqueando la evolución derivada sin meta explícita.

Solo usa la biblioteca estándar (``unittest``). Ejecutar desde la
raíz del proyecto con::

    python3 -m unittest discover
"""

import os
import sys
import unittest
from types import SimpleNamespace

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from simulacion.agente import Agente
from simulacion.experiencia import (
    _clasificar,
    evolucionar_metas,
    registrar_experiencia,
    resumen_experiencia,
)
from simulacion.interaccion import colaborar, hablar
from simulacion.mundo import Mundo

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
                energia=None):
    agente = Agente(
        nombre,
        dict(rasgos if rasgos is not None else RASGOS_BASE),
        list(metas if metas is not None else ["una meta de prueba"]),
        lugar,
    )
    if energia is not None:
        agente.energia = energia
    return agente


def rasgos_con(clave, valor):
    rasgos = dict(RASGOS_BASE)
    rasgos[clave] = valor
    return rasgos


class TestAgenteBordes(unittest.TestCase):
    """Constructor, reglas duras de pensar() y límites de energía."""

    def test_rasgos_fuera_de_rango_se_limitan_a_0_1(self):
        agente = Agente("Limites", {
            "curiosidad": 1.7, "sociabilidad": -0.3,
            "paciencia": 0.5, "ambicion": 2.0,
        }, [], "plaza")
        self.assertEqual(agente.rasgos, {
            "curiosidad": 1.0, "sociabilidad": 0.0,
            "paciencia": 0.5, "ambicion": 1.0,
        })

    def test_rasgos_ausentes_valen_0_5_y_las_claves_extra_se_ignoran(self):
        agente = Agente("Minimo", {"curiosidad": 0.1, "extra": 0.9},
                        [], "plaza")
        self.assertEqual(agente.rasgos["curiosidad"], 0.1)
        self.assertEqual(agente.rasgos["sociabilidad"], 0.5)
        self.assertNotIn("extra", agente.rasgos)

    def test_rasgos_y_metas_none_dan_los_valores_por_defecto(self):
        agente = Agente("Vacio", None, None, "plaza")
        self.assertEqual(agente.rasgos, dict(RASGOS_BASE))
        self.assertEqual(agente.metas, [])
        self.assertEqual(agente.energia, 80)
        self.assertEqual(agente.memoria, [])
        self.assertEqual(agente.relaciones, {})

    def test_animo_inicial_segun_el_rasgo_dominante(self):
        esperados = {
            "curiosidad": "curioso",
            "sociabilidad": "alegre",
            "paciencia": "tranquilo",
            "ambicion": "inquieto",
        }
        for rasgo, animo in esperados.items():
            with self.subTest(rasgo=rasgo):
                agente = agente_base(rasgos=rasgos_con(rasgo, 0.9))
                self.assertEqual(agente.animo, animo)

    def test_regla_dura_sin_energia_descansa_y_a_30_ya_no_es_forzado(self):
        # Con curiosidad 0.7 el agente exploraría; con energía 29
        # manda la regla dura de descansar y con 30 vuelve la
        # regla de la curiosidad.
        agente = agente_base(rasgos=rasgos_con("curiosidad", 0.7),
                             energia=29)
        self.assertEqual(agente.pensar(PERCEPCION_SOLO)["accion"],
                         "descansar")
        agente.energia = 30
        self.assertEqual(agente.pensar(PERCEPCION_SOLO)["accion"],
                         "explorar")

    def test_regla_dura_sociable_con_compania_habla_con_el_primero(self):
        agente = agente_base(rasgos=rasgos_con("sociabilidad", 0.7))
        percepcion = dict(PERCEPCION_SOLO)
        percepcion["agentes_cercanos"] = ["Otro", "Tercero"]
        decision = agente.pensar(percepcion)
        self.assertEqual(decision["accion"], "hablar")
        self.assertEqual(decision["objetivo"], "Otro")

    def test_regla_dura_curioso_explora_sin_descubrimiento_reciente(self):
        agente = agente_base(rasgos=rasgos_con("curiosidad", 0.7))
        self.assertEqual(agente.pensar(PERCEPCION_SOLO)["accion"],
                         "explorar")
        percepcion = dict(PERCEPCION_SOLO)
        percepcion["recuerdos"] = ["hubo un descubrimiento ayer"]
        self.assertNotEqual(agente.pensar(percepcion)["accion"],
                            "explorar")

    def test_recuerdo_de_escasez_vuelve_cauto_al_curioso(self):
        agente = agente_base(rasgos=rasgos_con("curiosidad", 0.7))
        percepcion = dict(PERCEPCION_SOLO)
        percepcion["recuerdos"] = ["escasez: faltan provisiones"]
        decision = agente.pensar(percepcion)
        self.assertEqual(decision["accion"], "observar")
        self.assertIn("La escasez que viví me hace ser cauto",
                      decision["pensamiento"])

    def test_agente_sin_metas_ni_recuerdos_piensa_y_actua(self):
        agente = agente_base(metas=[])
        decision = agente.pensar(PERCEPCION_SOLO)
        self.assertNotIn("quiero lograr", decision["pensamiento"])
        mundo = Mundo()
        mundo.agregar_agente(agente)
        evento = agente.actuar(mundo, decision)
        self.assertEqual(evento["tipo"], "accion")

    def test_percibir_recorta_a_los_ultimos_tres_recuerdos_y_se_excluye(self):
        mundo = Mundo()
        agente = agente_base(nombre="Percibe")
        mundo.agregar_agente(agente)
        mundo.agregar_agente(agente_base(nombre="Vecino"))
        agente.memoria = ["r1", "r2", "r3", "r4", "r5"]
        percepcion = agente.percibir(mundo)
        self.assertEqual(percepcion["recuerdos"], ["r3", "r4", "r5"])
        self.assertEqual(percepcion["agentes_cercanos"], ["Vecino"])
        self.assertEqual(percepcion["lugar"], "plaza")

    def test_percibir_tolera_un_mundo_sin_los_atributos_del_motor(self):
        percepcion = agente_base().percibir(SimpleNamespace())
        self.assertEqual(percepcion["tick"], 0)
        self.assertEqual(percepcion["agentes_cercanos"], [])
        self.assertEqual(percepcion["lugar"], "plaza")

    def test_decidir_sin_argumento_usa_la_ultima_percepcion_o_una_vacia(self):
        agente = agente_base(rasgos=rasgos_con("curiosidad", 0.7))
        self.assertEqual(agente.decidir()["accion"], "explorar")
        self.assertEqual(agente.decidir(PERCEPCION_SOLO)["accion"],
                         "explorar")
        mundo = Mundo()
        mundo.agregar_agente(agente)
        agente.percibir(mundo)
        self.assertEqual(agente.decidir()["accion"], "explorar")

    def test_actuar_sin_decision_piensa_y_percibe_por_su_cuenta(self):
        mundo = Mundo()
        agente = agente_base(rasgos=rasgos_con("curiosidad", 0.7))
        mundo.agregar_agente(agente)
        evento = agente.actuar(mundo)
        self.assertEqual(evento["accion"], "explorar")
        self.assertEqual(evento["agente"], agente.nombre)

    def test_energia_nunca_sale_de_0_a_100_al_actuar(self):
        mundo = Mundo()
        casos = (
            ("descansar", 100, 100),
            ("construir", 5, 0),
            ("descansar", 0, 20),
            ("explorar", 3, 0),
        )
        for accion, antes, despues in casos:
            with self.subTest(accion=accion, antes=antes):
                agente = agente_base(nombre="E%s%s" % (accion, antes),
                                     energia=antes)
                mundo.agregar_agente(agente)
                agente.actuar(mundo, {"accion": accion,
                                      "pensamiento": "x",
                                      "objetivo": None})
                self.assertEqual(agente.energia, despues)

    def test_observar_no_cambia_el_animo(self):
        mundo = Mundo()
        agente = agente_base()
        agente.animo = "alegre"
        mundo.agregar_agente(agente)
        agente.actuar(mundo, {"accion": "observar", "pensamiento": "x",
                              "objetivo": None})
        self.assertEqual(agente.animo, "alegre")


class TestExperiencia(unittest.TestCase):
    """experiencia.py: clasificación, umbral, metas y resumen."""

    def test_clasificar_sin_tipo_sugerido_infiere_del_texto(self):
        casos = {
            "hubo una tormenta ayer": "tormenta",
            "un diálogo bonito": "dialogo",
            "dialogo sin tilde": "dialogo",
            "una celebración grande": "celebracion",
            "una escasez dura": "escasez",
            "quiero colaborar con otros": "colaborar",
            "voy a construir una mesa": "construir",
            "un descubrimiento inesperado": "descubrimiento",
            "nada conocido": "vivencia",
            "": "vivencia",
            None: "vivencia",
        }
        for texto, esperado in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(_clasificar(texto), esperado)

    def test_clasificar_con_tipo_sugerido_lo_devuelve_tal_cual(self):
        self.assertEqual(_clasificar("hubo una tormenta", "rumor"),
                         "rumor")

    def test_registrar_acumula_memoria_y_al_umbral_el_rasgo_crece(self):
        agente = agente_base()
        primero = registrar_experiencia(agente, "diálogo con X")
        self.assertEqual(primero["tipo"], "dialogo")
        self.assertIsNone(primero["cambio_rasgo"])
        self.assertEqual(agente.memoria, ["diálogo con X"])
        segundo = registrar_experiencia(agente, "diálogo con Y")
        self.assertEqual(segundo["cambio_rasgo"], {
            "rasgo": "sociabilidad", "antes": 0.5, "despues": 0.53,
        })
        self.assertEqual(agente.rasgos["sociabilidad"], 0.53)
        # El contador del tipo se reinicia tras el hito.
        self.assertEqual(agente._conteo_experiencias["dialogo"], 0)

    def test_registrar_con_el_rasgo_en_el_tope_no_cambia_ni_falla(self):
        agente = agente_base(rasgos=rasgos_con("sociabilidad", 1.0))
        registrar_experiencia(agente, "dialogo", "dialogo")
        resultado = registrar_experiencia(agente, "dialogo", "dialogo")
        self.assertIsNone(resultado["cambio_rasgo"])
        self.assertEqual(agente.rasgos["sociabilidad"], 1.0)
        self.assertEqual(agente._conteo_experiencias["dialogo"], 0)

    def test_registrar_tipos_sin_crecimiento_solo_acumulan_conteo(self):
        # El conjunto completo sin crecimiento (16 nov 2026, 2ª
        # tanda): explorar, rumor, visita_inesperada y vivencia
        # (texto sin clasificar) se registran y cuentan, pero
        # ningún rasgo se mueve por muchos que se acumulen. Antes
        # este test solo cubría el rumor; los cuatro pasan por la
        # misma rama (`tipo not in _CRECIMIENTO`).
        casos = (
            ("rumor", "rumor sobre alguien"),
            ("explorar", "explorar bosque"),
            ("visita_inesperada", "visita_inesperada: conocí a una viajera"),
            (None, "nada conocido"),
        )
        for tipo, texto in casos:
            with self.subTest(tipo=tipo or "vivencia"):
                agente = agente_base()
                for _ in range(3):
                    resultado = registrar_experiencia(agente, texto, tipo)
                    self.assertIsNone(resultado["cambio_rasgo"])
                clave = tipo or "vivencia"
                self.assertEqual(agente._conteo_experiencias[clave], 3)
                self.assertEqual(agente.rasgos, dict(RASGOS_BASE))
                self.assertEqual(len(agente.memoria), 3)

    def test_registrar_crea_el_contador_si_el_agente_no_lo_tiene(self):
        # Agentes ajenos al constructor de Agente (p. ej. objetos
        # simples del protocolo): la función crea _conteo_experiencias.
        falso = SimpleNamespace(nombre="Falso", memoria=[],
                                rasgos=dict(RASGOS_BASE))
        resultado = registrar_experiencia(falso, "tormenta x", "tormenta")
        self.assertEqual(resultado["tipo"], "tormenta")
        self.assertEqual(falso._conteo_experiencias, {"tormenta": 1})
        self.assertEqual(falso.memoria, ["tormenta x"])

    def test_evolucionar_con_meta_completada_y_nueva_explicitas(self):
        agente = agente_base(metas=["vieja", "otra"])
        nueva = evolucionar_metas(agente, meta_completada="vieja",
                                  nueva_meta="nueva")
        self.assertEqual(nueva, "nueva")
        self.assertEqual(agente.metas, ["otra", "nueva"])

    def test_evolucionar_con_completada_ausente_tambien_anade_la_nueva(self):
        agente = agente_base(metas=["m1"])
        nueva = evolucionar_metas(agente, meta_completada="inexistente",
                                  nueva_meta="nueva")
        self.assertEqual(nueva, "nueva")
        self.assertEqual(agente.metas, ["m1", "nueva"])

    def test_evolucionar_no_duplica_una_meta_ya_presente(self):
        agente = agente_base(metas=["m1"])
        nueva = evolucionar_metas(agente, meta_completada="m1",
                                  nueva_meta="m1")
        self.assertEqual(nueva, "m1")
        self.assertEqual(agente.metas, ["m1"])

    def test_evolucionar_sin_cambio_devuelve_none(self):
        # REGRESIÓN 16 nov 2026 (2ª tanda): el docstring promete
        # None "si no hubo cambio", pero una meta nueva ya presente,
        # sin meta completada y sin retirada (menos de 4 recuerdos),
        # devolvía la meta sin haber tocado nada — y Mundo.tick
        # registra "adopta una nueva" cuando el valor es verdadero.
        agente = agente_base(metas=["m1"])
        agente.memoria = ["solo", "dos"]
        self.assertIsNone(evolucionar_metas(agente, nueva_meta="m1"))
        self.assertEqual(agente.metas, ["m1"])

    def test_evolucionar_sin_completada_deriva_la_nueva_del_ultimo_recuerdo(self):
        casos = {
            "colaborar en un proyecto":
                "Compartir lo aprendido colaborando con otros",
            "un descubrimiento genial":
                "Explorar un lugar nuevo tras el último descubrimiento",
            "la tormenta ya pasó":
                "Ayudar a otros a prepararse para la próxima tormenta",
            "escasez total":
                "Guardar recursos para tiempos de escasez",
            "otra cosa cualquiera":
                "Convertir lo vivido en algo útil para los demás",
        }
        for ultimo, esperada in casos.items():
            with self.subTest(ultimo=ultimo):
                agente = agente_base(metas=["m1", "m2"])
                agente.memoria = ["a", "b", "c", ultimo]
                self.assertEqual(evolucionar_metas(agente), esperada)
                self.assertEqual(agente.metas, ["m2", esperada])

    def test_evolucionar_caracterizacion_puerta_de_recuerdos(self):
        # REGRESIÓN Ronda 4 (en la Ronda 2 esto era una
        # caracterización del descarte): sin meta completada y con
        # menos de 4 recuerdos, una meta nueva explícita SÍ se
        # añade, y no se retira ninguna (la puerta de los 4
        # recuerdos protege la retirada, no el alta). La evolución
        # derivada sin meta explícita sigue bloqueada por la
        # puerta: eso lo fija tests/test_ronda4_hallazgos.py.
        agente = agente_base(metas=["m1"])
        agente.memoria = ["solo", "dos"]
        self.assertEqual(
            evolucionar_metas(agente, nueva_meta="nueva"), "nueva")
        self.assertEqual(agente.metas, ["m1", "nueva"])

    def test_resumen_experiencia_devuelve_copias_independientes(self):
        agente = agente_base()
        registrar_experiencia(agente, "tormenta x", "tormenta")
        resumen = resumen_experiencia(agente)
        self.assertEqual(resumen["nombre"], agente.nombre)
        self.assertEqual(resumen["recuerdos"], 1)
        self.assertEqual(resumen["conteo_por_tipo"], {"tormenta": 1})
        self.assertEqual(resumen["rasgos"], dict(RASGOS_BASE))
        self.assertEqual(resumen["metas"], ["una meta de prueba"])
        resumen["rasgos"]["curiosidad"] = 9.9
        resumen["metas"].append("intrusa")
        self.assertEqual(agente.rasgos["curiosidad"], 0.5)
        self.assertEqual(agente.metas, ["una meta de prueba"])


class TestInteraccion(unittest.TestCase):
    """interaccion.py: plantillas de hablar, confianza y colaborar."""

    def test_hablar_elige_la_plantilla_segun_el_pensamiento(self):
        casos = {
            "tengo un descubrimiento entre manos": "cosas por descubrir",
            "estoy cansado hoy": "estoy algo cansado",
            "desde la escasez ando pensando": "desde la escasez",
            "la tormenta de ayer": "la tormenta me dejó pensando",
            "quiero lograr mi meta": "una meta que me importa",
            "estoy solo por aquí": "estaba solo por aquí",
            "mi curiosidad es enorme": "mi curiosidad no me deja quieto",
            "hola, qué tal": "¿cómo te va hoy?",
        }
        for pensamiento, fragmento in casos.items():
            with self.subTest(pensamiento=pensamiento):
                mensaje = hablar(agente_base(nombre="Emisor"),
                                 agente_base(nombre="Receptor"),
                                 pensamiento)
                self.assertIn(fragmento, mensaje)
                self.assertTrue(
                    mensaje.startswith('Emisor le dice a Receptor: "'))

    def test_hablar_sube_la_confianza_mutua_0_05_y_nunca_pasa_de_1(self):
        emisor = agente_base(nombre="Emisor")
        receptor = agente_base(nombre="Receptor")
        hablar(emisor, receptor, "hola")
        self.assertEqual(emisor.relaciones["Receptor"], 0.05)
        self.assertEqual(receptor.relaciones["Emisor"], 0.05)
        for _ in range(30):
            hablar(emisor, receptor, "hola")
        self.assertEqual(emisor.relaciones["Receptor"], 1.0)
        self.assertEqual(receptor.relaciones["Emisor"], 1.0)

    def test_hablar_con_uno_mismo_solo_suma_una_vez(self):
        # Regresión Ronda 2: antes de la corrección, hablarse a sí
        # mismo sumaba +0.10 (los dos «sentidos» caían en la misma
        # clave). Lo documentado es +0.05 por sentido y aquí solo
        # hay un sentido.
        agente = agente_base(nombre="Solo")
        hablar(agente, agente, "hola")
        self.assertEqual(agente.relaciones["Solo"], 0.05)

    def test_colaborar_avanza_acumula_y_completa(self):
        uno = agente_base(nombre="Uno")
        dos = agente_base(nombre="Dos")
        estado = colaborar([uno, dos], "Proyecto X")
        self.assertEqual(estado["nombre"], "Proyecto X")
        self.assertEqual(estado["participantes"], ["Uno", "Dos"])
        self.assertEqual(estado["progreso"], 32)
        self.assertFalse(estado["completado"])
        self.assertEqual(uno.relaciones["Dos"], 0.03)
        self.assertEqual(dos.relaciones["Uno"], 0.03)
        estado = colaborar([uno, dos], estado)
        self.assertEqual(estado["progreso"], 64)
        estado = colaborar([uno, dos], estado)
        estado = colaborar([uno, dos], estado)
        self.assertEqual(estado["progreso"], 100)
        self.assertTrue(estado["completado"])
        self.assertIn("completado", estado["mensaje"])

    def test_colaborar_sobre_un_proyecto_completado_no_lo_toca(self):
        uno = agente_base(nombre="Uno")
        estado = {"nombre": "Listo", "participantes": ["Uno"],
                  "progreso": 100, "completado": True, "mensaje": ""}
        resultado = colaborar([uno], estado)
        self.assertEqual(resultado["progreso"], 100)
        self.assertIn("ya estaba completado", resultado["mensaje"])
        self.assertEqual(uno.relaciones, {})

    def test_colaborar_con_entradas_degradadas_no_falla(self):
        self.assertEqual(colaborar([], "Proyecto vacío")["progreso"], 22)
        self.assertEqual(colaborar([agente_base()], None)["nombre"],
                         "proyecto compartido")
        parcial = colaborar([agente_base()], {"nombre": "Parcial"})
        self.assertEqual(parcial["nombre"], "Parcial")
        self.assertGreater(parcial["progreso"], 0)


class _RngFalso:
    """Sustituto determinista del RNG del mundo para forzar el caos.

    ``choice`` devuelve el tipo de caos fijado si está en la
    secuencia ofrecida y si no, el primer elemento (el objetivo o
    el segundo agente). ``random`` devuelve 0.99 (sin movimiento
    ni caos espontáneo dentro de tick si se usara).
    """

    def __init__(self, tipo):
        self.tipo = tipo

    def choice(self, secuencia):
        return self.tipo if self.tipo in secuencia else secuencia[0]

    def random(self):
        return 0.99


class _RngQuieto:
    """RNG sin movimiento ni caos espontáneo (como el _RngFijo de
    test_ronda4_hallazgos): aísla la rama de colaborar de
    Mundo.tick del azar del movimiento y del caos, que desde el
    23 nov 2026 (8 tipos de caos) cambian de flujo y podrían
    separar a los agentes antes de completar el proyecto."""

    def random(self):
        return 0.99

    def choice(self, secuencia):
        return secuencia[0]


def mundo_de_caos(tipo, agentes):
    mundo = Mundo(semilla=1)
    mundo.rng = _RngFalso(tipo)
    for agente in agentes:
        mundo.agregar_agente(agente)
    return mundo


class TestMundoBordes(unittest.TestCase):
    """mundo.py: mundo vacío, consultas, caos forzado e invariantes."""

    def test_mundo_vacio_no_genera_caos_ni_falla_en_tick(self):
        mundo = Mundo()
        self.assertIsNone(mundo.generar_caos())
        self.assertEqual(mundo.eventos, [])
        self.assertIsNone(mundo.evento_reciente)
        self.assertEqual(mundo.ejecutar(0), [])
        self.assertEqual(mundo.tick_actual, 0)
        mundo.tick()
        self.assertEqual(mundo.tick_actual, 1)

    def test_consultas_de_lugar_y_agentes(self):
        mundo = Mundo()
        agente = agente_base(nombre="Ubicado", lugar="bosque")
        mundo.agregar_agente(agente)
        self.assertEqual(mundo.lugar_de(agente), "bosque")
        self.assertEqual(mundo.lugar_de("Ubicado"), "bosque")
        # Nombre desconocido y agente no registrado: cae a la plaza.
        self.assertEqual(mundo.lugar_de("Fantasma"), "plaza")
        self.assertEqual(mundo.lugar_de(agente_base(nombre="Fuera")),
                         "plaza")
        self.assertEqual(mundo.agentes_en("mercado"), [])
        self.assertIsNone(mundo.agente_por_nombre("Fantasma"))

    def test_caos_tormenta_y_escasez_quitan_energia_con_suelo_en_0(self):
        for tipo, coste in (("tormenta", 15), ("escasez", 10)):
            with self.subTest(tipo=tipo):
                uno = agente_base(nombre="Uno", energia=80)
                dos = agente_base(nombre="Dos", energia=5)
                mundo = mundo_de_caos(tipo, [uno, dos])
                texto = mundo.generar_caos()
                self.assertEqual(uno.energia, 80 - coste)
                self.assertEqual(dos.energia, 0)
                self.assertEqual(uno.animo, "inquieto")
                self.assertTrue(
                    any(tipo in recuerdo for recuerdo in uno.memoria))
                self.assertEqual(mundo.evento_reciente, texto)
                self.assertEqual(mundo.eventos[-1]["tipo"], "caos")

    def test_caos_descubrimiento_premia_solo_al_objetivo(self):
        objetivo = agente_base(nombre="Objetivo", energia=98)
        otro = agente_base(nombre="Otro", energia=50)
        mundo = mundo_de_caos("descubrimiento", [objetivo, otro])
        mundo.generar_caos()
        self.assertEqual(objetivo.energia, 100)
        self.assertEqual(objetivo.animo, "curioso")
        self.assertEqual(otro.energia, 50)
        self.assertTrue(
            any("descubrimiento" in r for r in objetivo.memoria))

    def test_caos_celebracion_suma_energia_y_confianza_solo_en_la_plaza(self):
        uno = agente_base(nombre="Uno", energia=95)
        dos = agente_base(nombre="Dos", energia=80)
        lejos = agente_base(nombre="Lejos", lugar="bosque", energia=80)
        mundo = mundo_de_caos("celebracion", [uno, dos, lejos])
        mundo.generar_caos()
        self.assertEqual((uno.energia, dos.energia, lejos.energia),
                         (100, 90, 90))
        self.assertEqual(uno.relaciones["Dos"], 0.05)
        self.assertEqual(dos.relaciones["Uno"], 0.05)
        self.assertEqual(lejos.relaciones, {})

    def test_caos_rumor_baja_la_confianza_con_suelo_en_0(self):
        uno = agente_base(nombre="Uno")
        dos = agente_base(nombre="Dos")
        uno.relaciones["Dos"] = 0.03
        dos.relaciones["Uno"] = 0.5
        mundo = mundo_de_caos("rumor", [uno, dos])
        mundo.generar_caos()
        self.assertEqual(uno.relaciones["Dos"], 0.0)
        self.assertEqual(dos.relaciones["Uno"], 0.45)
        self.assertEqual(uno.animo, "inquieto")

    def test_caos_rumor_con_un_solo_agente_se_pierde_sin_destino(self):
        unico = agente_base(nombre="Unico")
        mundo = mundo_de_caos("rumor", [unico])
        texto = mundo.generar_caos()
        self.assertEqual(
            texto, "Un rumor sin destino se pierde entre los lugares.")
        self.assertEqual(unico.memoria, [])
        self.assertEqual([e["tipo"] for e in mundo.eventos], ["caos"])

    def test_caos_visita_inesperada_deja_una_idea_y_curiosidad(self):
        objetivo = agente_base(nombre="Objetivo")
        mundo = mundo_de_caos("visita_inesperada", [objetivo])
        mundo.generar_caos()
        self.assertEqual(objetivo.animo, "curioso")
        self.assertTrue(
            any("visita_inesperada" in r for r in objetivo.memoria))

    def test_invariantes_en_varias_semillas_y_ticks_largos(self):
        # Por agente y tick el motor registra exactamente 1
        # pensamiento y exactamente 1 evento de acción o diálogo;
        # energía, rasgos, confianza y lugar se mantienen en rango.
        for semilla in (0, 1, 7, 123, 2026):
            with self.subTest(semilla=semilla):
                mundo = Mundo(semilla=semilla)
                agentes = [
                    agente_base(nombre="S%d-%d" % (semilla, i), lugar=lugar)
                    for i, lugar in enumerate(
                        ("plaza", "biblioteca", "taller", "bosque",
                         "mercado"))
                ]
                for agente in agentes:
                    mundo.agregar_agente(agente)
                eventos = mundo.ejecutar(60)
                pensamientos = sum(
                    1 for e in eventos if e["tipo"] == "pensamiento")
                acciones = sum(
                    1 for e in eventos
                    if e["tipo"] in ("accion", "dialogo"))
                self.assertEqual(pensamientos, 300)
                self.assertEqual(acciones, 300)
                for agente in agentes:
                    self.assertTrue(0 <= agente.energia <= 100)
                    self.assertIn(agente.lugar, mundo.lugares)
                    for valor in agente.rasgos.values():
                        self.assertTrue(0.0 <= valor <= 1.0)
                    for valor in agente.relaciones.values():
                        self.assertTrue(0.0 <= valor <= 1.0)

    def test_determinismo_tambien_fuera_de_la_semilla_42(self):
        def correr(semilla):
            mundo = Mundo(semilla=semilla)
            for i in range(3):
                mundo.agregar_agente(
                    agente_base(nombre="N%d" % i, lugar="plaza"))
            return [(e["tick"], e["tipo"], e["agente"], e["texto"])
                    for e in mundo.ejecutar(25)]

        self.assertEqual(correr(7), correr(7))
        self.assertNotEqual(correr(7), correr(8))


class _HabladorSinObjetivo(Agente):
    """Agente del protocolo (como-unirse.md) que siempre habla
    sin señalar objetivo: el mundo debe dirigir el diálogo al
    primer agente cercano."""

    def pensar(self, percepcion):
        return {"pensamiento": "quiero charlar", "accion": "hablar",
                "objetivo": None}


class _ColaboradorSiempre(Agente):
    """Agente del protocolo que siempre colabora."""

    def pensar(self, percepcion):
        return {"pensamiento": "a colaborar", "accion": "colaborar",
                "objetivo": None}


class TestProtocoloAgentesPersonalizados(unittest.TestCase):
    """La rama de Mundo.tick que la demo no alcanza, vía el
    protocolo público de agentes personalizados."""

    def test_hablar_sin_objetivo_dialoga_con_el_cercano(self):
        mundo = Mundo(semilla=3)
        mundo.agregar_agente(_HabladorSinObjetivo(
            "Hablador", dict(RASGOS_BASE), ["m"], "plaza"))
        mundo.agregar_agente(agente_base(nombre="Vecino"))
        mundo.tick()
        dialogos = [e for e in mundo.eventos if e["tipo"] == "dialogo"]
        self.assertTrue(
            any(e["texto"].startswith('Hablador le dice a Vecino: "')
                for e in dialogos))

    def test_colaborar_en_tick_crea_completa_y_hace_evolucionar_metas(self):
        mundo = Mundo(semilla=3)
        # Sin movimiento ni caos: lo que este test mide es la rama
        # de colaborar de Mundo.tick, no la suerte del azar.
        mundo.rng = _RngQuieto()
        agentes = []
        for nombre in ("ColabUno", "ColabDos"):
            agente = _ColaboradorSiempre(
                nombre, dict(RASGOS_BASE), ["meta de " + nombre], "plaza")
            agente.memoria = ["a", "b", "c", "d"]
            agentes.append(agente)
            mundo.agregar_agente(agente)
        mundo.ejecutar(6)
        for agente in agentes:
            self.assertTrue(any(
                meta.startswith("Compartir lo aprendido en Proyecto")
                for meta in agente.metas))
        self.assertTrue(any(
            e["tipo"] == "accion" and "Proyecto del plaza" in e["texto"]
            for e in mundo.eventos))


if __name__ == "__main__":
    unittest.main()
