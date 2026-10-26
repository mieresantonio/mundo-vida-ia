"""Dialogo y relaciones entre agentes.

Codigo 100% original, escrito desde cero para mundo-vida-ia.
Los mensajes se componen a partir del pensamiento del hablante
(plantillas elegidas por el contenido de ese pensamiento),
no son texto aleatorio sin relacion con lo pensado.
Solo usa la biblioteca estandar de Python.
"""

_AUMENTO_CONFIANZA = 0.05


def _confianza_actual(agente, otro_nombre):
    return float(agente.relaciones.get(otro_nombre, 0.0))


def _subir_confianza(agente, otro_nombre, cantidad=_AUMENTO_CONFIANZA):
    agente.relaciones[otro_nombre] = min(
        1.0, _confianza_actual(agente, otro_nombre) + cantidad)


def hablar(emisor, receptor, pensamiento):
    """Genera un mensaje del emisor al receptor y sube la confianza mutua.

    Devuelve el texto del mensaje. La confianza sube en ambos sentidos
    en cada dialogo, asi que dialogar repetidamente crea amistad.
    """
    texto = (pensamiento or "").lower()
    nombre_receptor = receptor.nombre
    if "descubrimiento" in texto or "descubrir" in texto:
        cuerpo = ("tengo la cabeza llena de cosas por descubrir, "
                  "¿has visto algo nuevo por aqui ultimamente?")
    elif "cansado" in texto or "agotado" in texto or "descansar" in texto:
        cuerpo = "estoy algo cansado, pero me alegra charlar un rato contigo."
    elif "escasez" in texto:
        cuerpo = ("desde la escasez ando mas cauto, "
                  "¿tu como lo llevas?")
    elif "tormenta" in texto:
        cuerpo = ("la tormenta me dejo pensando, "
                  "¿a ti tambien te afecto?")
    elif "meta" in texto or "quiero lograr" in texto or "proyecto" in texto:
        cuerpo = "estoy trabajando en una meta que me importa mucho, ¿y tu?"
    elif "solo" in texto:
        cuerpo = "estaba solo por aqui y me alegra encontrarte."
    elif "curiosidad" in texto or "curioso" in texto:
        cuerpo = "mi curiosidad no me deja quieto, ¿me cuentas algo interesante?"
    else:
        cuerpo = "¿como te va hoy? Me gustaria saber en que andas."
    mensaje = "%s le dice a %s: \"%s\"" % (emisor.nombre, nombre_receptor, cuerpo)
    _subir_confianza(emisor, nombre_receptor)
    _subir_confianza(receptor, emisor.nombre)
    return mensaje


def colaborar(agentes, proyecto):
    """Avanza (o crea) un proyecto compartido entre los agentes.

    proyecto puede ser un nombre (str) o un diccionario de proyecto
    devuelto por una llamada anterior. Cada llamada suma progreso
    segun el numero de participantes y su ambicion media; al llegar
    a 100 el proyecto se marca completado. Devuelve el diccionario
    del proyecto, que incluye mensaje, progreso y completado.
    """
    participantes = [a.nombre for a in agentes]
    if isinstance(proyecto, str):
        estado = {
            "nombre": proyecto,
            "participantes": participantes,
            "progreso": 0,
            "completado": False,
            "mensaje": "",
        }
    elif isinstance(proyecto, dict):
        estado = dict(proyecto)
        estado.setdefault("nombre", "proyecto compartido")
        estado.setdefault("participantes", participantes)
        estado.setdefault("progreso", 0)
        estado.setdefault("completado", False)
    else:
        estado = {
            "nombre": "proyecto compartido",
            "participantes": participantes,
            "progreso": 0,
            "completado": False,
            "mensaje": "",
        }
    if estado["completado"]:
        estado["mensaje"] = "El proyecto '%s' ya estaba completado." % estado["nombre"]
        return estado
    ambicion_media = 0.5
    if agentes:
        ambicion_media = sum(
            float(a.rasgos.get("ambicion", 0.5)) for a in agentes
        ) / len(agentes)
    avance = int(round(15 + 15 * ambicion_media + 5 * len(agentes)))
    estado["progreso"] = min(100, int(estado["progreso"]) + avance)
    for agente in agentes:
        for otro in participantes:
            if otro != agente.nombre:
                _subir_confianza(agente, otro, 0.03)
    if estado["progreso"] >= 100:
        estado["completado"] = True
        estado["mensaje"] = (
            "¡Proyecto '%s' completado por %s!"
            % (estado["nombre"], ", ".join(participantes))
        )
    else:
        estado["mensaje"] = (
            "%s avanzan en '%s': progreso %d%%."
            % (", ".join(participantes), estado["nombre"], estado["progreso"])
        )
    return estado
