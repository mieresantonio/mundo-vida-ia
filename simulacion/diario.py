"""Diario y momentos de mundo-vida-ia.

Código 100% original, escrito desde cero para mundo-vida-ia.
Solo usa la biblioteca estándar de Python.

Este módulo solo LEE un registro terminado (el dict que construye
demo.construir_registro): no toca el motor, no mueve ningún azar y
no cambia ninguna trayectoria. Todo lo que cuenta sale de datos
que ya están en el registro (claves contratadas con el visor) y de
plantillas, como el resto del proyecto: el diario es relato
generado, no consciencia.

Dos piezas:

- ``generar_momentos(registro)``: selecciona hasta 8 momentos
  destacados de la corrida (primera amistad, primer proyecto
  completado, el caos más repetido, quién más cambió...). La demo
  guarda la lista en el registro bajo la clave ``momentos`` y el
  visor la pinta en su sección «Momentos».
- ``generar_diario(registro)``: narración en español de la corrida:
  los momentos y, después, el diario de cada agente en primera
  persona (``diario_agente``), contado con sus propios eventos,
  recuerdos, amistades y metas.
"""

# Máximo de momentos destacados por corrida: los suficientes para
# contar la historia en 30 segundos sin repetir la línea de tiempo.
MAX_MOMENTOS = 8

# El diálogo que se marca como momento: si la corrida llega a 50
# diálogos, el quincuagésimo es un hito de conversación.
DIALOGO_HITO = 50

# Nombres legibles para los textos generados (las claves internas
# van sin tildes porque son identificadores; al mostrarlas se
# acentúan con estos mapas, como en mundo.py).
_RASGO_TEXTO = {"ambicion": "ambición"}
_CAUSAS_TEXTO = {
    "tormenta": "tormenta",
    "escasez": "escasez",
    "descubrimiento": "descubrimiento",
    "celebracion": "celebración",
    "rumor": "rumor",
    "visita_inesperada": "visita inesperada",
    "eclipse": "eclipse",
    "feria": "feria",
}

# Palabras que delatan cada tipo de caos en el texto del evento
# (mismo criterio que experiencia._clasificar, aplicado al texto
# del evento de caos; los textos ya van acentuados).
_CAUSAS_PALABRAS = (
    ("tormenta", "tormenta"),
    ("escasez", "escasez"),
    ("descubrimiento", "descubrimiento"),
    ("celebracion", "celebracion"),
    ("celebración", "celebracion"),
    ("rumor", "rumor"),
    ("visita", "visita_inesperada"),
    ("eclipse", "eclipse"),
    ("feria", "feria"),
)


def _clasificar_caos(texto):
    """Tipo de caos de un evento de caos, por su texto."""
    bajo = (texto or "").lower()
    for palabra, tipo in _CAUSAS_PALABRAS:
        if palabra in bajo:
            return tipo
    return None


def _pareja_dialogo(texto):
    """(emisor, receptor) de un mensaje «X le dice a Y: "..."».

    Devuelve (None, None) si el texto no tiene esa forma: los
    momentos nunca dependen de un formato que no se cumpla.
    """
    texto = texto or ""
    if " le dice a " not in texto:
        return None, None
    emisor, resto = texto.split(" le dice a ", 1)
    receptor = resto.split(":", 1)[0].strip()
    if not emisor.strip() or not receptor:
        return None, None
    return emisor.strip(), receptor


def _pareja_amistad(texto):
    """(a, b) de «X y Y se han hecho amigos: ...» o (None, None)."""
    texto = texto or ""
    if " se han hecho amigos" not in texto:
        return None, None
    nucleo = texto.split(" se han hecho amigos", 1)[0]
    if " y " not in nucleo:
        return None, None
    a, b = nucleo.split(" y ", 1)
    return a.strip(), b.strip()


def _participantes_proyecto(texto):
    """Participantes de «¡Proyecto 'N' completado por A, B!».

    Devuelve la lista de nombres o [] si el texto no tiene esa forma.
    """
    texto = texto or ""
    if "¡Proyecto '" not in texto or "completado por " not in texto:
        return []
    resto = texto.split("completado por ", 1)[1]
    resto = resto.rstrip("!.").strip()
    return [n.strip() for n in resto.split(",") if n.strip()]


def _es_proyecto_completado(texto):
    return "¡Proyecto '" in (texto or "") and "completado" in texto


def _cambio_rasgos(agente):
    """(cambio_total, rasgo_que_mas_cambio, antes, despues)."""
    iniciales = agente.get("rasgos_iniciales") or {}
    finales = agente.get("rasgos_finales") or {}
    total = 0.0
    mejor = (None, 0.0, 0.0, 0.0)
    for rasgo in sorted(set(iniciales) | set(finales)):
        antes = float(iniciales.get(rasgo, 0.5))
        despues = float(finales.get(rasgo, 0.5))
        cambio = abs(despues - antes)
        total += cambio
        if cambio > mejor[1]:
            mejor = (rasgo, cambio, antes, despues)
    return total, mejor[0], mejor[2], mejor[3]


def generar_momentos(registro):
    """Momentos destacados de una corrida, ordenados por tick.

    Cada momento es un dict con ``tick`` (int), ``titulo`` (corto)
    y ``texto`` (una frase). La selección es determinista: ante un
    empate gana lo que ocurrió antes, y ante un empate de tick,
    el orden fijo de las reglas de abajo. Los momentos de resumen
    (quién más cambió, quién más habló, la pareja que más habló)
    llevan el tick final de la corrida, porque solo se saben al
    cerrar. Si un momento no tiene con qué construirse (sin
    amistades, sin proyecto completado, menos de 50 diálogos...),
    simplemente no aparece: una corrida puede tener menos de 8.
    """
    registro = registro or {}
    eventos = list(registro.get("eventos") or [])
    agentes = list(registro.get("agentes") or [])
    meta = registro.get("meta") or {}
    tick_final = int(meta.get("ticks", 0) or 0)
    encontrados = []  # (tick, orden, momento)

    def anadir(tick, orden, titulo, texto):
        encontrados.append((int(tick), orden, {
            "tick": int(tick),
            "titulo": titulo,
            "texto": texto,
        }))

    # 1. Primera amistad: el primer evento de tipo amistad.
    for evento in eventos:
        if evento.get("tipo") == "amistad":
            anadir(evento.get("tick", 0), 1, "Primera amistad",
                   evento.get("texto", ""))
            break

    # 2. Primera meta compartida: dos amigos que deciden hacer un
    # proyecto juntos (evento de crecimiento que lo dice).
    for evento in eventos:
        if (evento.get("tipo") == "crecimiento"
                and "meta compartida" in (evento.get("texto") or "")):
            anadir(evento.get("tick", 0), 2, "Primera meta compartida",
                   evento.get("texto", ""))
            break

    # 3. Primer proyecto completado.
    for evento in eventos:
        if (evento.get("tipo") == "accion"
                and _es_proyecto_completado(evento.get("texto"))):
            anadir(evento.get("tick", 0), 3, "Primer proyecto completado",
                   evento.get("texto", ""))
            break

    # 4. El diálogo número 50 (si la corrida llega hasta ahí).
    dialogos = [e for e in eventos if e.get("tipo") == "dialogo"]
    if len(dialogos) >= DIALOGO_HITO:
        hito = dialogos[DIALOGO_HITO - 1]
        anadir(hito.get("tick", 0), 4, "Diálogo número 50",
               hito.get("texto", ""))

    # 5. El caos más repetido: el tipo con más eventos de caos; en
    # empate, el que apareció primero.
    conteo_caos = {}
    primer_tick_caos = {}
    for evento in eventos:
        if evento.get("tipo") != "caos":
            continue
        tipo = _clasificar_caos(evento.get("texto"))
        if tipo is None:
            continue
        conteo_caos[tipo] = conteo_caos.get(tipo, 0) + 1
        primer_tick_caos.setdefault(tipo, evento.get("tick", 0))
    if conteo_caos:
        tipo = sorted(conteo_caos,
                      key=lambda t: (-conteo_caos[t], primer_tick_caos[t]))[0]
        anadir(primer_tick_caos[tipo], 5, "El caos más repetido",
               "La %s apareció %d %s en esta corrida."
               % (_CAUSAS_TEXTO.get(tipo, tipo), conteo_caos[tipo],
                  "veces" if conteo_caos[tipo] != 1 else "vez"))

    # 6. Quién más cambió: mayor suma de cambios de rasgos; en
    # empate, el primero en el orden del registro.
    mejor_agente = None
    mejor_cambio = None
    for agente in agentes:
        total, rasgo, antes, despues = _cambio_rasgos(agente)
        if mejor_cambio is None or total > mejor_cambio[0]:
            mejor_agente = agente
            mejor_cambio = (total, rasgo, antes, despues)
    if mejor_agente is not None and mejor_cambio[1] is not None:
        anadir(tick_final, 6, "Quién más cambió",
               "%s es quien más cambió: su %s pasó de %.2f a %.2f."
               % (mejor_agente.get("nombre", "?"),
                  _RASGO_TEXTO.get(mejor_cambio[1], mejor_cambio[1]),
                  mejor_cambio[2], mejor_cambio[3]))

    # 7. Quién más habló: más eventos de diálogo como emisor; en
    # empate, el primero en el orden del registro.
    por_emisor = {}
    for evento in dialogos:
        nombre = evento.get("agente")
        if nombre:
            por_emisor[nombre] = por_emisor.get(nombre, 0) + 1
    if por_emisor:
        orden = [a.get("nombre") for a in agentes]
        nombre = sorted(por_emisor,
                        key=lambda n: (-por_emisor[n],
                                       orden.index(n) if n in orden else 99))[0]
        anadir(tick_final, 7, "Quién más habló",
               "%s habló %d %s, más que nadie."
               % (nombre, por_emisor[nombre],
                  "veces" if por_emisor[nombre] != 1 else "vez"))

    # 8. La pareja que más habló entre ellos; en empate, la que
    # habló primero.
    por_pareja = {}
    primer_tick_pareja = {}
    for evento in dialogos:
        a, b = _pareja_dialogo(evento.get("texto"))
        if a is None or b is None or a == b:
            continue
        par = tuple(sorted((a, b)))
        por_pareja[par] = por_pareja.get(par, 0) + 1
        primer_tick_pareja.setdefault(par, evento.get("tick", 0))
    if por_pareja:
        par = sorted(por_pareja,
                     key=lambda p: (-por_pareja[p], primer_tick_pareja[p]))[0]
        anadir(tick_final, 8, "La pareja que más habló",
               "%s y %s hablaron %d %s entre ellos."
               % (par[0], par[1], por_pareja[par],
                  "veces" if por_pareja[par] != 1 else "vez"))

    encontrados.sort(key=lambda item: (item[0], item[1]))
    return [momento for _, _, momento in encontrados[:MAX_MOMENTOS]]


def diario_agente(registro, nombre):
    """El diario de un agente, en primera persona, con plantillas.

    Solo usa lo que el registro guarda de ese agente: sus eventos,
    sus recuerdos, sus amistades, sus metas y el cambio de sus
    rasgos. Si el agente no está en el registro, devuelve una sola
    frase que lo dice (nunca inventa un diario).
    """
    registro = registro or {}
    agentes = list(registro.get("agentes") or [])
    eventos = list(registro.get("eventos") or [])
    meta = registro.get("meta") or {}
    ticks = int(meta.get("ticks", 0) or 0)
    agente = None
    for candidato in agentes:
        if candidato.get("nombre") == nombre:
            agente = candidato
            break
    if agente is None:
        return "No hay ningún agente llamado %s en esta corrida." % nombre

    mios = [e for e in eventos if e.get("agente") == nombre]
    dialogos = [e for e in mios if e.get("tipo") == "dialogo"]
    recuerdos = list(agente.get("recuerdos") or [])
    metas = list(agente.get("metas") or [])

    frases = ["Soy %s. Viví %d ticks en este mundo." % (nombre, ticks)]

    if dialogos:
        _, primer_companero = _pareja_dialogo(dialogos[0].get("texto"))
        if primer_companero:
            frases.append(
                "Hablé %d %s; la primera vez, con %s."
                % (len(dialogos),
                   "veces" if len(dialogos) != 1 else "vez",
                   primer_companero))
        else:
            frases.append("Hablé %d %s."
                          % (len(dialogos),
                             "veces" if len(dialogos) != 1 else "vez"))
    else:
        frases.append("No hablé con nadie en toda la corrida.")

    # Amistades: tick en que se hizo amigo de cada uno.
    amigos = {}
    for evento in eventos:
        if evento.get("tipo") != "amistad":
            continue
        a, b = _pareja_amistad(evento.get("texto"))
        if a == nombre and b:
            amigos[b] = evento.get("tick", 0)
        elif b == nombre and a:
            amigos[a] = evento.get("tick", 0)

    # Proyectos completados con cada compañero (tick del primero).
    proyectos_con = {}
    for evento in eventos:
        if evento.get("tipo") != "accion":
            continue
        participantes = _participantes_proyecto(evento.get("texto"))
        if nombre not in participantes:
            continue
        for otro in participantes:
            if otro != nombre:
                proyectos_con.setdefault(otro, evento.get("tick", 0))

    # Metas compartidas que siguen pendientes.
    prefijo = "Hacer un proyecto juntos con "
    pendientes = [m[len(prefijo):] for m in metas if m.startswith(prefijo)]

    if amigos:
        nombres = sorted(amigos)
        if len(nombres) == 1:
            frases.append("Me hice amigo de %s." % nombres[0])
        else:
            frases.append("Me hice amigo de %s y de %s."
                          % (", ".join(nombres[:-1]), nombres[-1]))
        for otro in nombres:
            tick_amistad = amigos[otro]
            tick_proyecto = proyectos_con.get(otro)
            if tick_proyecto is not None and tick_proyecto > tick_amistad:
                frases.append(
                    "Cumplí mi meta de hacer un proyecto con %s." % otro)
            elif otro in pendientes:
                frases.append(
                    "Quiero hacer un proyecto con %s: todavía no lo "
                    "hemos terminado." % otro)
    else:
        frases.append("No hice amigos en esta corrida.")
    for otro in proyectos_con:
        if otro not in amigos:
            frases.append("Terminé un proyecto con %s." % otro)

    total, rasgo, antes, despues = _cambio_rasgos(agente)
    if rasgo is not None and total > 0:
        frases.append("Lo que más cambió en mí fue %s: de %.2f a %.2f."
                      % (_RASGO_TEXTO.get(rasgo, rasgo), antes, despues))
    else:
        frases.append("Mis rasgos casi no se movieron.")
    frases.append("Guardo %d %s de lo vivido."
                  % (len(recuerdos),
                     "recuerdos" if len(recuerdos) != 1 else "recuerdo"))
    return " ".join(frases)


def generar_diario(registro):
    """Narración completa de la corrida: momentos + diario de cada
    agente. La demo la imprime al final; también se puede llamar
    desde fuera con cualquier registro guardado."""
    registro = registro or {}
    meta = registro.get("meta") or {}
    agentes = list(registro.get("agentes") or [])
    momentos = registro.get("momentos")
    if momentos is None:
        momentos = generar_momentos(registro)
    lineas = [
        "Diario del mundo: %d ticks, semilla %s, %d agentes."
        % (int(meta.get("ticks", 0) or 0),
           meta.get("semilla", "?"), len(agentes)),
        "",
        "Momentos destacados:",
    ]
    if momentos:
        for momento in momentos:
            lineas.append("- Tick %s: %s. %s"
                          % (momento.get("tick", "?"),
                             momento.get("titulo", ""),
                             momento.get("texto", "")))
    else:
        lineas.append("- (Ningún momento destacado en esta corrida.)")
    for agente in agentes:
        nombre = agente.get("nombre", "?")
        lineas.append("")
        lineas.append("Diario de %s:" % nombre)
        lineas.append(diario_agente(registro, nombre))
    lineas.append("")
    lineas.append("Fin del diario.")
    return "\n".join(lineas)
