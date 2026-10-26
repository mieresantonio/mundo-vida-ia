"""Mundo simulado: lugares, bucle de ticks y eventos de caos.

Codigo 100% original, escrito desde cero para mundo-vida-ia.
Solo usa la biblioteca estandar de Python.
"""

import random

from agente import Agente
from experiencia import registrar_experiencia, evolucionar_metas
from interaccion import hablar, colaborar

LUGARES = {
    "plaza": "el corazon del pueblo, donde todos se cruzan",
    "biblioteca": "silenciosa, llena de libros y mapas viejos",
    "taller": "olor a madera y herramientas; aqui se construye",
    "bosque": "senderos, claros y sonidos que invitan a explorar",
    "mercado": "puestos, trueques y noticias de todos lados",
}

TIPOS_CAOS = (
    "tormenta",
    "descubrimiento",
    "escasez",
    "celebracion",
    "rumor",
    "visita_inesperada",
)

_PROBABILIDAD_CAOS = 0.3
_PROBABILIDAD_MOVIMIENTO = 0.2


class Mundo:
    """Contiene agentes, lugares y el reloj de la simulacion."""

    def __init__(self, semilla=42):
        self.semilla = int(semilla)
        self.rng = random.Random(self.semilla)
        self.lugares = dict(LUGARES)
        self.tick_actual = 0
        self.agentes = []  # lista de Agente, en orden de creacion
        self._por_nombre = {}
        self.evento_reciente = None
        self.eventos = []  # eventos con tick/tipo/agente/texto
        self.proyecto_actual = None

    # -- agentes y lugares ----------------------------------------------
    def agregar_agente(self, agente):
        self.agentes.append(agente)
        self._por_nombre[agente.nombre] = agente
        if agente.lugar not in self.lugares:
            agente.lugar = agente.lugar_inicial
        return agente

    def lugar_de(self, agente):
        nombre = agente.nombre if isinstance(agente, Agente) else str(agente)
        encontrado = self._por_nombre.get(nombre)
        return encontrado.lugar if encontrado else self.lugares and "plaza"

    def agentes_en(self, lugar):
        return [a.nombre for a in self.agentes if a.lugar == lugar]

    def agente_por_nombre(self, nombre):
        return self._por_nombre.get(nombre)

    # -- eventos ----------------------------------------------------------
    def _registrar(self, tipo, agente, texto):
        evento = {
            "tick": self.tick_actual,
            "tipo": tipo,
            "agente": agente,
            "texto": texto,
        }
        self.eventos.append(evento)
        return evento

    def _crecimiento(self, agente, resultado):
        cambio = resultado.get("cambio_rasgo")
        if cambio:
            self._registrar(
                "crecimiento", agente.nombre,
                "%s crece: su %s pasa de %.2f a %.2f tras vivir '%s'."
                % (agente.nombre, cambio["rasgo"], cambio["antes"],
                   cambio["despues"], resultado["tipo"]))

    # -- caos -------------------------------------------------------------
    def generar_caos(self):
        """Genera un evento de caos que perturba de verdad a los agentes.

        Devuelve el texto del evento, o None si no hay agentes.
        """
        if not self.agentes:
            return None
        tipo = self.rng.choice(TIPOS_CAOS)
        objetivo = self.rng.choice(self.agentes)
        if tipo == "tormenta":
            texto = ("Una tormenta repentina azota el mundo: viento, "
                     "lluvia y truenos interrumpen todos los planes.")
            for agente in self.agentes:
                agente.energia = max(0, agente.energia - 15)
                agente.animo = "inquieto"
                self._crecimiento(
                    agente, registrar_experiencia(
                        agente, "tormenta: la tormenta me sorprendio", "tormenta"))
        elif tipo == "descubrimiento":
            texto = ("%s encuentra algo inesperado en %s: un objeto "
                     "antiguo que nadie habia visto antes."
                     % (objetivo.nombre, objetivo.lugar))
            objetivo.animo = "curioso"
            objetivo.energia = min(100, objetivo.energia + 5)
            self._crecimiento(
                objetivo, registrar_experiencia(
                    objetivo, "descubrimiento en " + objetivo.lugar,
                    "descubrimiento"))
        elif tipo == "escasez":
            texto = ("Escasez en el mercado: faltan provisiones y todos "
                     "deben pensar dos veces antes de gastar energia.")
            for agente in self.agentes:
                agente.energia = max(0, agente.energia - 10)
                agente.animo = "inquieto"
                self._crecimiento(
                    agente, registrar_experiencia(
                        agente, "escasez: faltan provisiones", "escasez"))
        elif tipo == "celebracion":
            texto = ("Celebracion espontanea en la plaza: musica, "
                     "comida compartida y risas para todos.")
            for agente in self.agentes:
                agente.energia = min(100, agente.energia + 10)
                agente.animo = "alegre"
                self._crecimiento(
                    agente, registrar_experiencia(
                        agente, "celebracion en la plaza", "celebracion"))
            vecinos = self.agentes_en("plaza")
            for i, nombre_a in enumerate(vecinos):
                for nombre_b in vecinos[i + 1:]:
                    a = self._por_nombre[nombre_a]
                    b = self._por_nombre[nombre_b]
                    a.relaciones[nombre_b] = min(1.0, a.relaciones.get(nombre_b, 0.0) + 0.05)
                    b.relaciones[nombre_a] = min(1.0, b.relaciones.get(nombre_a, 0.0) + 0.05)
        elif tipo == "rumor":
            otros = [a for a in self.agentes if a is not objetivo]
            if otros:
                segundo = self.rng.choice(otros)
                texto = ("Un rumor corre por %s: dicen que %s y %s "
                         "esconden algo. La confianza entre ellos tiembla."
                         % (objetivo.lugar, objetivo.nombre, segundo.nombre))
                for a, b in ((objetivo, segundo), (segundo, objetivo)):
                    a.relaciones[b.nombre] = max(
                        0.0, a.relaciones.get(b.nombre, 0.0) - 0.05)
                objetivo.animo = "inquieto"
                self._crecimiento(
                    objetivo, registrar_experiencia(
                        objetivo, "rumor sobre " + segundo.nombre, "rumor"))
            else:
                texto = "Un rumor sin destino se pierde entre los lugares."
        else:  # visita_inesperada
            texto = ("Una visita inesperada llega al mundo: una viajera "
                     "desconocida saluda a %s en %s y le deja una idea nueva."
                     % (objetivo.nombre, objetivo.lugar))
            objetivo.animo = "curioso"
            self._crecimiento(
                objetivo, registrar_experiencia(
                    objetivo, "visita_inesperada: conoci a una viajera",
                    "visita_inesperada"))
        self.evento_reciente = texto
        self._registrar("caos", None, texto)
        return texto

    # -- bucle principal --------------------------------------------------
    def tick(self):
        """Avanza un tick: pensar, actuar, dialogar, moverse y caos."""
        self.tick_actual += 1
        for agente in list(self.agentes):
            percepcion = agente.percibir(self)
            decision = agente.pensar(percepcion)
            self._registrar("pensamiento", agente.nombre,
                            decision["pensamiento"])
            evento_accion = agente.actuar(self, decision)
            accion = evento_accion["accion"]
            cercanos = [
                n for n in self.agentes_en(agente.lugar)
                if n != agente.nombre
            ]
            if accion == "hablar" and cercanos:
                receptor_nombre = decision.get("objetivo")
                if receptor_nombre not in cercanos:
                    receptor_nombre = cercanos[0]
                receptor = self._por_nombre[receptor_nombre]
                mensaje = hablar(agente, receptor, decision["pensamiento"])
                self._registrar("dialogo", agente.nombre, mensaje)
                self._crecimiento(
                    agente, registrar_experiencia(
                        agente, "dialogo con " + receptor_nombre, "dialogo"))
                self._crecimiento(
                    receptor, registrar_experiencia(
                        receptor, "dialogo con " + agente.nombre, "dialogo"))
            elif accion == "colaborar" and cercanos:
                companeros = [agente] + [
                    self._por_nombre[n] for n in cercanos[:2]
                ]
                if self.proyecto_actual is None:
                    self.proyecto_actual = colaborar(
                        companeros, "Proyecto del " + agente.lugar)
                else:
                    self.proyecto_actual = colaborar(
                        companeros, self.proyecto_actual)
                self._registrar("accion", agente.nombre,
                                self.proyecto_actual["mensaje"])
                for participante in companeros:
                    self._crecimiento(
                        participante, registrar_experiencia(
                            participante,
                            "colaborar en " + self.proyecto_actual["nombre"],
                            "colaborar"))
                if self.proyecto_actual["completado"]:
                    for participante in companeros:
                        nueva = evolucionar_metas(
                            participante,
                            nueva_meta=("Compartir lo aprendido en "
                                        + self.proyecto_actual["nombre"]))
                        if nueva:
                            self._registrar(
                                "crecimiento", participante.nombre,
                                "%s completa una meta y adopta una nueva: %s."
                                % (participante.nombre, nueva))
                    self.proyecto_actual = None
            else:
                self._registrar("accion", agente.nombre,
                                evento_accion["texto"])
                if accion == "explorar":
                    self._crecimiento(
                        agente, registrar_experiencia(
                            agente, "explorar " + agente.lugar, "explorar"))
                elif accion == "construir":
                    self._crecimiento(
                        agente, registrar_experiencia(
                            agente, "construir en " + agente.lugar, "construir"))
        # Movimiento ocasional entre lugares.
        for agente in self.agentes:
            if self.rng.random() < _PROBABILIDAD_MOVIMIENTO:
                destinos = [l for l in self.lugares if l != agente.lugar]
                agente.lugar = self.rng.choice(destinos)
        # Caos: ~30% por tick (casi seguro al menos una vez en 30 ticks,
        # pero lejos de ocurrir en todos).
        if self.rng.random() < _PROBABILIDAD_CAOS:
            self.generar_caos()
        else:
            self.evento_reciente = None

    def ejecutar(self, ticks):
        for _ in range(int(ticks)):
            self.tick()
        return self.eventos
