"""Demo de mundo-vida-ia: 5 agentes, 30 ticks, historia en espanol.

Codigo 100% original, escrito desde cero para mundo-vida-ia.
Semilla fija (42) para que cada ejecucion sea reproducible.
Solo usa la biblioteca estandar de Python.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agente import Agente
from mundo import Mundo

SEMILLA = 42
TICKS = 30


def crear_agentes():
    return [
        Agente("Lia", {
            "curiosidad": 0.9, "sociabilidad": 0.6,
            "paciencia": 0.5, "ambicion": 0.5,
        }, ["Descubrir un lugar secreto del bosque"],
         "bosque"),
        Agente("Tomas", {
            "curiosidad": 0.4, "sociabilidad": 0.9,
            "paciencia": 0.6, "ambicion": 0.4,
        }, ["Hacer tres amigos nuevos en la plaza"],
         "plaza"),
        Agente("Nara", {
            "curiosidad": 0.5, "sociabilidad": 0.4,
            "paciencia": 0.9, "ambicion": 0.6,
        }, ["Leer todos los libros de la biblioteca"],
         "biblioteca"),
        Agente("Rui", {
            "curiosidad": 0.5, "sociabilidad": 0.5,
            "paciencia": 0.4, "ambicion": 0.9,
        }, ["Construir un taller mejor para todos"],
         "taller"),
        Agente("Mara", {
            "curiosidad": 0.7, "sociabilidad": 0.8,
            "paciencia": 0.3, "ambicion": 0.7,
        }, ["Organizar un mercado de trueque semanal"],
         "mercado"),
    ]


def construir_registro(mundo, agentes, rasgos_iniciales):
    return {
        "meta": {"ticks": mundo.tick_actual, "semilla": mundo.semilla},
        "agentes": [
            {
                "nombre": a.nombre,
                "rasgos_iniciales": rasgos_iniciales[a.nombre],
                "rasgos_finales": dict(a.rasgos),
                "animo": a.animo,
                "energia": a.energia,
                "metas": list(a.metas),
                "recuerdos": list(a.memoria),
            }
            for a in agentes
        ],
        "eventos": [
            {
                "tick": e["tick"],
                "tipo": e["tipo"],
                "agente": e["agente"],
                "texto": e["texto"],
            }
            for e in mundo.eventos
        ],
    }


def main():
    mundo = Mundo(semilla=SEMILLA)
    agentes = crear_agentes()
    rasgos_iniciales = {a.nombre: dict(a.rasgos) for a in agentes}
    for agente in agentes:
        mundo.agregar_agente(agente)

    print("=== MUNDO-VIDA-IA ===")
    print("5 agentes despiertan en un mundo pequeno: plaza, biblioteca, "
          "taller, bosque y mercado.")
    print("Cada uno piensa, actua, habla, colabora... y el caos interviene.\n")

    for _ in range(TICKS):
        antes = len(mundo.eventos)
        mundo.tick()
        nuevos = mundo.eventos[antes:]
        print("--- Tick %d ---" % mundo.tick_actual)
        for evento in nuevos:
            tipo = evento["tipo"]
            if tipo == "pensamiento":
                print("  [piensa %s] %s"
                      % (evento["agente"], evento["texto"]))
            elif tipo == "dialogo":
                print("  [dialogo] %s" % evento["texto"])
            elif tipo == "caos":
                print("  [CAOS] %s" % evento["texto"])
            elif tipo == "crecimiento":
                print("  [crece] %s" % evento["texto"])
            else:
                print("  [%s] %s" % (evento["agente"], evento["texto"]))
        print()

    registro = construir_registro(mundo, agentes, rasgos_iniciales)
    base = os.path.expanduser("~/workspace/mundo-vida-ia")
    visor = os.path.join(base, "visor")
    os.makedirs(visor, exist_ok=True)
    rutas = [
        os.path.join(base, "registro.json"),
        os.path.join(visor, "registro.json"),
    ]
    for ruta in rutas:
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(registro, f, ensure_ascii=False, indent=2)
    dialogos = sum(1 for e in registro["eventos"] if e["tipo"] == "dialogo")
    caos = sum(1 for e in registro["eventos"] if e["tipo"] == "caos")
    print("=== FIN DE LA SIMULACION ===")
    print("Ticks: %d | Dialogos: %d | Eventos de caos: %d"
          % (TICKS, dialogos, caos))
    for agente in registro["agentes"]:
        cambio = agente["rasgos_finales"] != agente["rasgos_iniciales"]
        print("  %s: animo=%s, energia=%d, rasgos cambiaron=%s"
              % (agente["nombre"], agente["animo"], agente["energia"], cambio))
    for ruta in rutas:
        print("Registro guardado en: %s" % ruta)


if __name__ == "__main__":
    main()
