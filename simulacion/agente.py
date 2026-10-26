"""Agente con razonamiento creencias-deseos-intenciones (BDI).

Codigo 100% original, escrito desde cero para mundo-vida-ia.
Solo usa la biblioteca estandar de Python.
"""

RASGOS_VALIDOS = ("curiosidad", "sociabilidad", "paciencia", "ambicion")
ACCIONES_VALIDAS = ("hablar", "explorar", "construir", "descansar", "colaborar", "observar")

_COSTE_ENERGIA = {
    "hablar": 3,
    "explorar": 8,
    "construir": 10,
    "descansar": -20,  # negativo = recupera energia
    "colaborar": 7,
    "observar": 2,
}


def _limitar(valor, minimo=0.0, maximo=1.0):
    return max(minimo, min(maximo, float(valor)))


class Agente:
    """Un habitante del mundo simulado.

    Constructor fijado por la API del proyecto:
        Agente(nombre, rasgos, metas, lugar_inicial)
    """

    def __init__(self, nombre, rasgos, metas, lugar_inicial):
        self.nombre = str(nombre)
        rasgos = dict(rasgos or {})
        self.rasgos = {
            clave: _limitar(rasgos.get(clave, 0.5)) for clave in RASGOS_VALIDOS
        }
        self.metas = list(metas or [])
        self.lugar_inicial = str(lugar_inicial)
        self.lugar = str(lugar_inicial)
        self.memoria = []  # lista de cadenas con eventos vividos
        self.relaciones = {}  # nombre -> confianza float 0.0-1.0
        self.energia = 80
        self.animo = self._animo_inicial()
        self._ultima_percepcion = None
        self._ultimo_pensamiento = None
        # Contadores internos usados por experiencia.py (no forman parte
        # de la API publica, pero se guardan aqui para no perderlos).
        self._conteo_experiencias = {}

    # -- estado ---------------------------------------------------------
    def _animo_inicial(self):
        rasgo_max = max(self.rasgos, key=lambda k: self.rasgos[k])
        return {
            "curiosidad": "curioso",
            "sociabilidad": "alegre",
            "paciencia": "tranquilo",
            "ambicion": "inquieto",
        }[rasgo_max]

    def _actualizar_animo(self, accion):
        if self.energia < 30:
            self.animo = "cansado"
        elif accion == "explorar":
            self.animo = "curioso"
        elif accion in ("hablar", "colaborar"):
            self.animo = "alegre"
        elif accion == "construir":
            self.animo = "inquieto"
        elif accion == "descansar":
            self.animo = "tranquilo"
        # "observar" no cambia el animo: el agente sigue como estaba.

    # -- percepcion -----------------------------------------------------
    def percibir(self, mundo):
        """Construye el diccionario de percepcion a partir del mundo.

        Acepta cualquier objeto mundo que exponga tick_actual,
        lugar_de()/lugares, agentes_en() o los atributos equivalentes
        usados por mundo.py. Si algo falta, se usa un valor sensato.
        """
        tick = getattr(mundo, "tick_actual", 0)
        lugar = self.lugar
        try:
            lugar = mundo.lugar_de(self)
        except Exception:
            pass
        cercanos = []
        try:
            cercanos = [
                nombre for nombre in mundo.agentes_en(lugar)
                if nombre != self.nombre
            ]
        except Exception:
            cercanos = []
        evento_reciente = getattr(mundo, "evento_reciente", None)
        percepcion = {
            "tick": tick,
            "lugar": lugar,
            "agentes_cercanos": cercanos,
            "evento_reciente": evento_reciente,
            "recuerdos": list(self.memoria[-3:]),
        }
        self._ultima_percepcion = percepcion
        return percepcion

    # -- razonamiento BDI ----------------------------------------------
    def pensar(self, percepcion):
        """Creencias -> deseos -> intencion, sin eleccion aleatoria.

        Creencias: recuerdos + percepcion actual.
        Deseos: metas del agente.
        Intencion: la accion con mayor puntuacion segun rasgos,
        energia, animo, compania y recuerdos, con reglas duras
        prioritarias que garantizan coherencia con los rasgos.
        """
        cercanos = list(percepcion.get("agentes_cercanos") or [])
        recuerdos = list(percepcion.get("recuerdos") or [])
        lugar = percepcion.get("lugar", self.lugar)
        evento = percepcion.get("evento_reciente")
        texto_recuerdos = " ".join(recuerdos).lower()
        vivio_escasez = "escasez" in texto_recuerdos
        vivio_tormenta = "tormenta" in texto_recuerdos
        hubo_descubrimiento = (
            "descubrimiento" in texto_recuerdos
            or (evento and "descubrimiento" in str(evento).lower())
        )
        meta_principal = self.metas[0] if self.metas else None

        creencias = []
        if cercanos:
            creencias.append(
                "veo cerca a " + ", ".join(cercanos) + " en " + str(lugar)
            )
        else:
            creencias.append("estoy solo en " + str(lugar))
        if recuerdos:
            creencias.append("recuerdo: " + "; ".join(recuerdos))
        if evento:
            creencias.append("acaba de ocurrir: " + str(evento))
        creencias.append(
            "me siento %s y mi energia es %d" % (self.animo, self.energia)
        )

        deseos = []
        if meta_principal:
            deseos.append("quiero lograr: " + meta_principal)
        if self.rasgos["sociabilidad"] >= 0.6:
            deseos.append("quiero estar con otros")
        if self.rasgos["curiosidad"] >= 0.6:
            deseos.append("quiero descubrir cosas nuevas")

        # Reglas duras, en orden de prioridad (coherencia garantizada):
        # 1. Sin energia, descansar. 2. Muy sociable + compania, hablar.
        # 3. Muy curioso + sin descubrimiento reciente, explorar.
        if self.energia < 30:
            accion, objetivo = "descansar", None
            razon = "estoy agotado y necesito recuperar fuerzas"
        elif self.rasgos["sociabilidad"] >= 0.7 and cercanos:
            accion, objetivo = "hablar", cercanos[0]
            razon = "me gusta la compania y hay alguien cerca"
        elif (self.rasgos["curiosidad"] >= 0.7 and not hubo_descubrimiento
              and not vivio_escasez):
            accion, objetivo = "explorar", None
            razon = "mi curiosidad me empuja a descubrir algo nuevo"
        else:
            # Puntuacion determinista para el resto de casos.
            p = {
                "hablar": 0.0,
                "explorar": 0.0,
                "construir": 0.0,
                "descansar": 0.0,
                "colaborar": 0.0,
                "observar": 0.0,
            }
            p["hablar"] += self.rasgos["sociabilidad"] * 10
            if cercanos:
                p["hablar"] += 4
                mejor_confianza = max(
                    (self.relaciones.get(n, 0.0) for n in cercanos),
                    default=0.0,
                )
                p["colaborar"] += mejor_confianza * 6
            p["explorar"] += self.rasgos["curiosidad"] * 10
            if hubo_descubrimiento:
                p["explorar"] -= 4
            p["construir"] += self.rasgos["ambicion"] * 10
            p["colaborar"] += self.rasgos["ambicion"] * 4
            p["colaborar"] += self.rasgos["sociabilidad"] * 3
            if not cercanos:
                p["hablar"] = 0.0
                p["colaborar"] = 0.0
            p["descansar"] += max(0, (50 - self.energia)) / 5.0
            p["observar"] += self.rasgos["paciencia"] * 6
            if vivio_tormenta:
                p["observar"] += 2
                p["explorar"] -= 2
            if vivio_escasez:
                # La escasez vivida vuelve al agente mas cauto:
                # prefiere observar antes que salir a explorar.
                p["observar"] += 4
                p["explorar"] -= 5
                p["construir"] -= 2
            if self.energia < 45:
                p["descansar"] += 3
            # Desempate determinista segun este orden fijo.
            orden = ("hablar", "colaborar", "explorar", "construir",
                     "observar", "descansar")
            accion = max(orden, key=lambda a: (p[a], -orden.index(a)))
            objetivo = cercanos[0] if accion in ("hablar", "colaborar") and cercanos else None
            razon = "tras valorar mis rasgos, mi energia y lo que recuerdo"

        pensamiento = (
            "Creo que " + "; ".join(creencias) + ". "
            + ("Deseo " + "; ".join(deseos) + ". " if deseos else "")
            + "Asi que voy a " + accion + " porque " + razon + "."
        )
        if vivio_escasez and accion == "observar":
            pensamiento += " La escasez que vivi me hace ser cauto."
        if objetivo:
            pensamiento += " Mi objetivo es " + str(objetivo) + "."

        resultado = {
            "pensamiento": pensamiento,
            "accion": accion,
            "objetivo": objetivo,
        }
        self._ultimo_pensamiento = resultado
        return resultado

    def decidir(self, percepcion=None):
        """Devuelve la decision actual; sin argumento usa la ultima
        percepcion conocida (o una percepcion vacia si no hay ninguna)."""
        if percepcion is None:
            percepcion = self._ultima_percepcion or {
                "tick": 0,
                "lugar": self.lugar,
                "agentes_cercanos": [],
                "evento_reciente": None,
                "recuerdos": list(self.memoria[-3:]),
            }
        return self.pensar(percepcion)

    def actuar(self, mundo, decision=None):
        """Ejecuta la decision en el mundo y devuelve un evento.

        El evento tiene las claves tick, tipo, agente y texto, y
        ademas accion, objetivo y pensamiento para que mundo.py
        pueda convertirlo en dialogo o colaboracion cuando toca.
        """
        if decision is None:
            decision = self.pensar(self.percibir(mundo))
        accion = decision.get("accion", "observar")
        if accion not in ACCIONES_VALIDAS:
            accion = "observar"
        coste = _COSTE_ENERGIA[accion]
        self.energia = max(0, min(100, self.energia - coste))
        self._actualizar_animo(accion)
        tick = getattr(mundo, "tick_actual", 0)
        texto = "%s decide %s en %s. %s" % (
            self.nombre, accion, self.lugar, decision.get("pensamiento", ""))
        return {
            "tick": tick,
            "tipo": "accion",
            "agente": self.nombre,
            "texto": texto,
            "accion": accion,
            "objetivo": decision.get("objetivo"),
            "pensamiento": decision.get("pensamiento", ""),
        }
