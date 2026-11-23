"""Diálogo y relaciones entre agentes.

Código 100% original, escrito desde cero para mundo-vida-ia.
Los mensajes se componen a partir del pensamiento del hablante
(plantillas elegidas por el contenido de ese pensamiento),
no son texto aleatorio sin relación con lo pensado.
Solo usa la biblioteca estándar de Python.
"""

_AUMENTO_CONFIANZA = 0.05


def _confianza_actual(agente, otro_nombre):
    return float(agente.relaciones.get(otro_nombre, 0.0))


def _subir_confianza(agente, otro_nombre, cantidad=_AUMENTO_CONFIANZA):
    agente.relaciones[otro_nombre] = min(
        1.0, _confianza_actual(agente, otro_nombre) + cantidad)


# Nombres propios para los proyectos de la aldea (2ª tanda, 23 nov
# 2026). Antes todos se llamaban «Proyecto del mercado» (o del lugar
# donde nacían) y ninguno se recordaba; ahora cada proyecto toma un
# nombre de esta tabla según su lugar, con los participantes dentro
# del nombre («El puesto de Mara y Nara»). Dos plantillas por lugar:
# la primera nombra a dos participantes ({a} y {b}) y la segunda a
# uno solo ({a}); la elección es determinista (suma de las
# longitudes de los nombres, módulo 2), así que la misma corrida
# produce siempre el mismo nombre y el determinismo por semilla se
# mantiene. Los nombres no llevan tildes para no mover el conteo de
# formas acentuadas más de lo que ya mueve el cambio de texto.
_NOMBRES_PROYECTO = {
    "plaza": ("La plaza de {a} y {b}", "El rincón de {a}"),
    "biblioteca": ("La biblioteca de {a} y {b}", "El mapa de {a}"),
    "taller": ("El taller de {a} y {b}", "La herramienta de {a}"),
    "bosque": ("El sendero de {a} y {b}", "El claro de {a}"),
    "mercado": ("El puesto de {a} y {b}", "La feria de {a}"),
}


def nombre_proyecto(lugar, participantes):
    """Nombre propio para un proyecto nuevo.

    ``participantes`` es la lista de nombres de quienes lo empiezan
    (el primero es quien toma la iniciativa). Si la plantilla
    elegida necesita dos nombres y solo hay uno, se usa la otra
    plantilla del lugar; si el lugar no está en la tabla, el nombre
    es «Proyecto de {a}». Nunca devuelve una plantilla sin rellenar.
    """
    nombres = [str(n) for n in (participantes or ["alguien"])]
    plantillas = _NOMBRES_PROYECTO.get(
        str(lugar), ("Proyecto de {a} y {b}", "Proyecto de {a}"))
    indice = sum(len(n) for n in nombres) % len(plantillas)
    plantilla = plantillas[indice]
    if "{b}" in plantilla and len(nombres) < 2:
        plantilla = plantillas[(indice + 1) % len(plantillas)]
    segundo = nombres[1] if len(nombres) > 1 else nombres[0]
    return plantilla.format(a=nombres[0], b=segundo)


def hablar(emisor, receptor, pensamiento):
    """Genera un mensaje del emisor al receptor y sube la confianza mutua.

    Devuelve el texto del mensaje. La confianza sube en ambos sentidos
    en cada diálogo, así que dialogar repetidamente crea amistad.
    """
    texto = (pensamiento or "").lower()
    nombre_receptor = receptor.nombre
    if "descubrimiento" in texto or "descubrir" in texto:
        cuerpo = ("tengo la cabeza llena de cosas por descubrir, "
                  "¿has visto algo nuevo por aquí últimamente?")
    elif "cansado" in texto or "agotado" in texto or "descansar" in texto:
        cuerpo = "estoy algo cansado, pero me alegra charlar un rato contigo."
    elif "escasez" in texto:
        cuerpo = ("desde la escasez ando más cauto, "
                  "¿tú cómo lo llevas?")
    elif "tormenta" in texto:
        cuerpo = ("la tormenta me dejó pensando, "
                  "¿a ti también te afectó?")
    elif "confío mucho" in texto:
        # Sesión de mejora, 23 nov 2026: el pensamiento de un
        # agente que va a colaborar por confianza dice "confío
        # mucho en X"; si ese pensamiento llega a diálogo (porque
        # otro agente lo escucha), el mensaje lo dice tal cual en
        # vez de caer en la plantilla genérica de metas.
        cuerpo = "confío mucho en ti, ¿hacemos algo juntos?"
    elif "meta" in texto or "quiero lograr" in texto or "proyecto" in texto:
        cuerpo = "estoy trabajando en una meta que me importa mucho, ¿y tú?"
    elif "solo" in texto:
        cuerpo = "estaba solo por aquí y me alegra encontrarte."
    elif "curiosidad" in texto or "curioso" in texto:
        cuerpo = "mi curiosidad no me deja quieto, ¿me cuentas algo interesante?"
    else:
        cuerpo = "¿cómo te va hoy? Me gustaría saber en qué andas."
    mensaje = "%s le dice a %s: \"%s\"" % (emisor.nombre, nombre_receptor, cuerpo)
    _subir_confianza(emisor, nombre_receptor)
    if receptor is not emisor:
        # Si el emisor se habla a sí mismo no hay un segundo sentido:
        # sin esta guarda la misma clave sumaba dos veces (+0.10 en
        # una sola llamada en vez del +0.05 documentado).
        _subir_confianza(receptor, emisor.nombre)
    return mensaje


def colaborar(agentes, proyecto):
    """Avanza (o crea) un proyecto compartido entre los agentes.

    proyecto puede ser un nombre (str) o un diccionario de proyecto
    devuelto por una llamada anterior. Cada llamada suma progreso
    según el número de participantes y su ambición media; al llegar
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
