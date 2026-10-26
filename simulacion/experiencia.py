"""Registro de experiencias y crecimiento de los agentes.

Codigo 100% original, escrito desde cero para mundo-vida-ia.
Cada evento vivido queda en la memoria del agente y, al acumular
suficientes experiencias de un mismo tipo, un rasgo cambia un poco
(siempre dentro de 0.0-1.0) y las metas pueden evolucionar.
Solo usa la biblioteca estandar de Python.
"""

# Tipo de experiencia -> (rasgo que crece, incremento por hito).
_CRECIMIENTO = {
    "tormenta": ("paciencia", 0.05),
    "dialogo": ("sociabilidad", 0.03),
    "colaborar": ("sociabilidad", 0.03),
    "descubrimiento": ("curiosidad", 0.03),
    "construir": ("ambicion", 0.03),
    "escasez": ("paciencia", 0.04),
    "celebracion": ("sociabilidad", 0.02),
}

# Experiencias necesarias para un hito de crecimiento.
_UMBRAL_HITO = 2


def _clasificar(texto, tipo_sugerido=None):
    if tipo_sugerido:
        return tipo_sugerido
    bajo = (texto or "").lower()
    for palabra in ("tormenta", "escasez", "descubrimiento", "celebracion",
                    "dialogo", "colaborar", "construir"):
        if palabra in bajo:
            return palabra
    return "vivencia"


def registrar_experiencia(agente, evento_texto, tipo=None):
    """Anade un evento a la memoria y aplica crecimiento si toca.

    Devuelve un diccionario con el rasgo cambiado (o None) y la
    meta nueva anadida (o None), para que el mundo lo registre
    como evento de tipo "crecimiento". Nunca devuelve None:
    siempre informa de lo ocurrido, aunque no haya cambio.
    """
    tipo = _clasificar(evento_texto, tipo)
    agente.memoria.append(str(evento_texto))
    conteo = getattr(agente, "_conteo_experiencias", None)
    if conteo is None:
        conteo = {}
        agente._conteo_experiencias = conteo
    conteo[tipo] = conteo.get(tipo, 0) + 1

    cambio = None
    if tipo in _CRECIMIENTO and conteo[tipo] >= _UMBRAL_HITO:
        rasgo, incremento = _CRECIMIENTO[tipo]
        anterior = float(agente.rasgos.get(rasgo, 0.5))
        nuevo = max(0.0, min(1.0, anterior + incremento))
        agente.rasgos[rasgo] = round(nuevo, 4)
        conteo[tipo] = 0
        if nuevo != anterior:
            cambio = {"rasgo": rasgo, "antes": anterior, "despues": nuevo}

    meta_nueva = None
    if tipo in ("colaborar", "construir") and conteo.get("__logros__", 0) >= 0:
        # La evolucion de metas se gestiona en evolucionar_metas();
        # aqui solo se deja constancia de que hubo un logro.
        pass
    return {
        "tipo": tipo,
        "texto": str(evento_texto),
        "cambio_rasgo": cambio,
        "meta_nueva": meta_nueva,
    }


def evolucionar_metas(agente, meta_completada=None, nueva_meta=None):
    """Quita una meta completada y anade una derivada de lo vivido.

    Si no se indica meta completada, se retira la primera meta
    solo cuando el agente ya acumula al menos 4 recuerdos, para
    no vaciar sus metas demasiado pronto. Si no se indica meta
    nueva, se deriva una de los recuerdos mas recientes.
    Devuelve la meta nueva anadida, o None si no hubo cambio.
    """
    if meta_completada is not None:
        if meta_completada in agente.metas:
            agente.metas.remove(meta_completada)
    elif len(agente.memoria) >= 4 and agente.metas:
        agente.metas.pop(0)
    else:
        return None
    if nueva_meta is None:
        ultimo = agente.memoria[-1] if agente.memoria else "lo vivido"
        if "colabor" in ultimo.lower():
            nueva_meta = "Compartir lo aprendido colaborando con otros"
        elif "descubrimiento" in ultimo.lower():
            nueva_meta = "Explorar un lugar nuevo tras el ultimo descubrimiento"
        elif "tormenta" in ultimo.lower():
            nueva_meta = "Ayudar a otros a prepararse para la proxima tormenta"
        elif "escasez" in ultimo.lower():
            nueva_meta = "Guardar recursos para tiempos de escasez"
        else:
            nueva_meta = "Convertir lo vivido en algo util para los demas"
    if nueva_meta not in agente.metas:
        agente.metas.append(nueva_meta)
    return nueva_meta


def resumen_experiencia(agente):
    """Resumen corto del recorrido del agente (para la demo)."""
    conteo = getattr(agente, "_conteo_experiencias", {}) or {}
    return {
        "nombre": agente.nombre,
        "recuerdos": len(agente.memoria),
        "conteo_por_tipo": dict(conteo),
        "rasgos": dict(agente.rasgos),
        "metas": list(agente.metas),
    }
