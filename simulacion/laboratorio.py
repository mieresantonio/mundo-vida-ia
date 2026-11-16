"""Laboratorio de semillas de mundo-vida-ia (2ª tanda, 16 nov 2026).

Corre el motor en silencio sobre varias semillas y compara cómo
diverge la simulación: eventos, diálogos, caos, colaboraciones y
rasgos finales por semilla. No escribe ningún registro: solo mide
mundos en memoria, así que la demo canónica queda intacta.

Su primera pregunta es la abierta más interesante del repo: en la
demo canónica la acción ``colaborar`` no se elige ni una vez
(0 de 150 a 30 ticks, 0 de 15.000 a 3.000 ticks; ver Ronda 6) —
¿en cuántas semillas sí llega a ocurrir, y qué tienen en común
esos mundos?

Uso::

    python3 -m simulacion.laboratorio [N] [--desde S] [--ticks T]
                                        [--con-ejemplos] [--json]

N es el número de semillas (por defecto 20), desde 0 salvo que se
diga --desde. Con --json la salida es JSON (tabla + resumen).

Solo usa la biblioteca estándar de Python.
"""

import argparse
import json
import os
import sys

if __package__ in (None, ""):
    # Ejecutado como script (python3 simulacion/laboratorio.py):
    # no hay paquete, así que se añade la carpeta del script a
    # sys.path y se importa en absoluto, como en demo.py.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from demo import cargar_ejemplos, crear_agentes
    from mundo import Mundo
else:
    # Ejecutado como módulo desde la raíz del proyecto
    # (python3 -m simulacion.laboratorio): imports relativos.
    from .demo import cargar_ejemplos, crear_agentes
    from .mundo import Mundo

SEMILLAS_POR_DEFECTO = 20
TICKS_POR_DEFECTO = 30
TIPOS_EVENTO = ("pensamiento", "accion", "dialogo", "crecimiento", "caos")
RASGOS = ("curiosidad", "sociabilidad", "paciencia", "ambicion")


def _es_colaboracion(texto):
    """True si el evento de acción es un mensaje de proyecto, es
    decir, una colaboración real con compañeros. Las dos formas las
    produce interaccion.colaborar: «… avanzan en '…': progreso N%.»
    y «¡Proyecto '…' completado por …!». No basta con buscar
    «Proyecto»: los recuerdos («colaborar en Proyecto del taller»)
    viajan dentro de pensamientos y de textos de acción genéricos,
    y no son colaboraciones.
    """
    return " avanzan en '" in texto or texto.startswith("¡Proyecto '")


def _es_proyecto_completado(texto):
    return texto.startswith("¡Proyecto '")


def _es_eleccion_colaborar(texto):
    """True si el pensamiento registra la decisión de colaborar:
    todo pensamiento termina en «Así que voy a <acción> porque …»,
    así que «voy a colaborar» solo aparece cuando la acción elegida
    fue colaborar. Es la medida directa de «veces que se eligió
    colaborar», distinta de las colaboraciones reales (con
    proyecto): en la práctica coinciden, porque sin compañía la
    puntuación de colaborar es 0 y nunca se elige.
    """
    return "voy a colaborar" in texto


def correr_mundo(semilla, ticks=TICKS_POR_DEFECTO, con_ejemplos=False):
    """Un mundo completo en memoria: los 5 agentes de la demo (más
    Nia, Bruno y Sofía con con_ejemplos), N ticks, sin imprimir
    nada y sin escribir ningún archivo.
    """
    mundo = Mundo(semilla=semilla)
    agentes = crear_agentes()
    if con_ejemplos:
        agentes.extend(cargar_ejemplos())
    for agente in agentes:
        mundo.agregar_agente(agente)
    mundo.ejecutar(ticks)
    return mundo, agentes


def medir(mundo, agentes):
    """Mide una corrida terminada. Devuelve un dict con los conteos
    por tipo de evento, las colaboraciones reales (mensajes de
    proyecto), las veces que se eligió colaborar (pensamientos
    «voy a colaborar»), los proyectos completados, la confianza
    máxima entre cualquier par de agentes y la media de los rasgos
    finales.
    """
    conteo = {tipo: 0 for tipo in TIPOS_EVENTO}
    colaboraciones = 0
    proyectos = 0
    elecciones = 0
    for evento in mundo.eventos:
        conteo[evento["tipo"]] = conteo.get(evento["tipo"], 0) + 1
        if evento["tipo"] == "pensamiento":
            if _es_eleccion_colaborar(evento["texto"]):
                elecciones += 1
            continue
        if evento["tipo"] != "accion":
            continue
        texto = evento["texto"]
        if _es_colaboracion(texto):
            colaboraciones += 1
            if _es_proyecto_completado(texto):
                proyectos += 1
    confianza_max = 0.0
    for agente in agentes:
        for valor in agente.relaciones.values():
            confianza_max = max(confianza_max, valor)
    rasgos_medios = {}
    for rasgo in RASGOS:
        rasgos_medios[rasgo] = round(
            sum(a.rasgos[rasgo] for a in agentes) / len(agentes), 3)
    medida = {
        "semilla": mundo.semilla,
        "ticks": mundo.tick_actual,
        "agentes": len(agentes),
        "eventos": len(mundo.eventos),
        "colaboraciones": colaboraciones,
        "proyectos_completados": proyectos,
        "elecciones_colaborar": elecciones,
        "confianza_max": round(confianza_max, 3),
        "rasgos_finales_medios": rasgos_medios,
    }
    medida.update(conteo)
    return medida


def barrer(semillas, ticks=TICKS_POR_DEFECTO, con_ejemplos=False):
    """Corre el motor sobre cada semilla y devuelve la lista de
    medidas, en el orden dado. Determinista: el mismo barrido da
    siempre las mismas medidas.
    """
    resultados = []
    for semilla in semillas:
        mundo, agentes = correr_mundo(semilla, ticks, con_ejemplos)
        resultados.append(medir(mundo, agentes))
    return resultados


def _media(valores):
    return round(sum(valores) / len(valores), 3) if valores else 0.0


def resumir(resultados):
    """Resumen del barrido: cuántas semillas colaboran (la pregunta
    abierta del repo), totales, rango de eventos y la comparación
    clave — la confianza máxima media en los mundos que colaboran
    frente a los que no — para ver qué tienen en común.
    """
    con_colaboracion = [r for r in resultados if r["colaboraciones"] > 0]
    sin_colaboracion = [r for r in resultados if r["colaboraciones"] == 0]
    eventos = [r["eventos"] for r in resultados]
    return {
        "semillas": len(resultados),
        "semillas_con_colaboracion": len(con_colaboracion),
        "que_colaboran": [r["semilla"] for r in con_colaboracion],
        "colaboraciones_totales": sum(r["colaboraciones"]
                                      for r in resultados),
        "proyectos_completados": sum(r["proyectos_completados"]
                                     for r in resultados),
        "elecciones_colaborar_total": sum(
            r["elecciones_colaborar"] for r in resultados),
        "decisiones_totales": sum(r["pensamiento"] for r in resultados),
        "eventos_min": min(eventos) if eventos else 0,
        "eventos_max": max(eventos) if eventos else 0,
        "eventos_media": _media(eventos),
        "confianza_max_media_con_colaboracion": _media(
            [r["confianza_max"] for r in con_colaboracion]),
        "confianza_max_media_sin_colaboracion": _media(
            [r["confianza_max"] for r in sin_colaboracion]),
    }


def formatear_tabla(resultados, resumen):
    """Tabla de texto: una fila por semilla, más el resumen."""
    lineas = []
    cabecera = ("semilla  eventos  diál.  caos  colab.  proy.  "
                "conf.máx  soc.med")
    lineas.append(cabecera)
    lineas.append("-" * len(cabecera))
    for r in resultados:
        lineas.append(
            "%7d  %7d  %5d  %4d  %6d  %5d  %8.2f  %7.2f"
            % (r["semilla"], r["eventos"], r["dialogo"], r["caos"],
               r["colaboraciones"], r["proyectos_completados"],
               r["confianza_max"],
               r["rasgos_finales_medios"]["sociabilidad"]))
    lineas.append("-" * len(cabecera))
    con = ("Semillas: %d | Con colaboración: %d"
           % (resumen["semillas"], resumen["semillas_con_colaboracion"]))
    if resumen["que_colaboran"]:
        con += " %s" % (resumen["que_colaboran"],)
    lineas.append(con)
    lineas.append("Colaboraciones totales: %d | Proyectos completados: %d"
                  % (resumen["colaboraciones_totales"],
                     resumen["proyectos_completados"]))
    lineas.append("Colaborar elegido: %d de %d decisiones"
                  % (resumen["elecciones_colaborar_total"],
                     resumen["decisiones_totales"]))
    lineas.append("Eventos: min %d, max %d, media %.1f"
                  % (resumen["eventos_min"], resumen["eventos_max"],
                     resumen["eventos_media"]))
    lineas.append("Confianza máx media: con colaboración %.2f, "
                  "sin colaboración %.2f"
                  % (resumen["confianza_max_media_con_colaboracion"],
                     resumen["confianza_max_media_sin_colaboracion"]))
    return "\n".join(lineas)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="simulacion.laboratorio",
        description="Laboratorio de semillas: corre el motor sobre "
                    "N semillas y compara cómo diverge la simulación.",
    )
    parser.add_argument("n", type=int, nargs="?",
                        default=SEMILLAS_POR_DEFECTO,
                        help="número de semillas (por defecto: "
                             "%(default)s)")
    parser.add_argument("--desde", type=int, default=0,
                        help="primera semilla (por defecto: %(default)s)")
    parser.add_argument("--ticks", type=int, default=TICKS_POR_DEFECTO,
                        help="ticks por corrida (por defecto: "
                             "%(default)s)")
    parser.add_argument("--con-ejemplos", action="store_true",
                        help="añade a Nia, Bruno y Sofía (8 agentes)")
    parser.add_argument("--json", action="store_true",
                        help="salida en JSON en vez de tabla de texto")
    args = parser.parse_args(argv)
    if args.n < 1:
        parser.error("el número de semillas debe ser al menos 1")
    if args.ticks < 0:
        parser.error("--ticks no puede ser negativo")
    return args


def main(argv=None):
    args = parse_args(argv)
    semillas = range(args.desde, args.desde + args.n)
    resultados = barrer(semillas, args.ticks, args.con_ejemplos)
    resumen = resumir(resultados)
    if args.json:
        print(json.dumps({"resumen": resumen, "semillas": resultados},
                         ensure_ascii=False, indent=2))
    else:
        print(formatear_tabla(resultados, resumen))


if __name__ == "__main__":
    main()
