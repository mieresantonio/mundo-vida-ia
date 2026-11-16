"""Demo de mundo-vida-ia: 5 agentes, 30 ticks, historia en español.

Código 100% original, escrito desde cero para mundo-vida-ia.
Semilla fija (42) para que cada ejecución sea reproducible.
Solo usa la biblioteca estándar de Python.

Banderas (sin banderas, la corrida es exactamente la canónica):
  --semilla N      otra semilla para el generador aleatorio
  --ticks N        número de ticks de la simulación
  --con-ejemplos   añade a Nia, Bruno y Sofía (ejemplos/), 8 agentes
"""

import argparse
import json
import os
import sys

if __package__ in (None, ""):
    # Ejecutado como script (python3 simulacion/demo.py): no hay
    # paquete, así que se añade la carpeta del script a sys.path y
    # se importa en absoluto, como siempre.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from agente import Agente
    from mundo import Mundo
else:
    # Ejecutado como módulo desde la raíz del proyecto
    # (python3 -m simulacion.demo): imports relativos al paquete.
    from .agente import Agente
    from .mundo import Mundo

SEMILLA = 42
TICKS = 30

# Los 3 agentes de ejemplos/, en el orden Nia, Bruno, Sofía:
# exploradora (Nia), constructor (Bruno), organizadora (Sofía).
EJEMPLOS = ("exploradora.json", "constructor.json", "organizadora.json")


def raiz_proyecto():
    """Raíz del proyecto relativa a este script (demo.py vive en
    simulacion/, la raíz es su carpeta padre): así la demo lee y
    escribe dentro del clon desde el que se ejecuta, esté donde esté.
    """
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse_args(argv=None):
    """Banderas de la CLI. Los valores por defecto son las constantes
    de la demo canónica, así que sin banderas la corrida es
    exactamente la de siempre (semilla 42, 30 ticks, 5 agentes).
    """
    parser = argparse.ArgumentParser(
        prog="simulacion.demo",
        description="Mundo-vida-ia: 5 agentes, 30 ticks, historia en "
                    "español. Sin banderas, la corrida canónica.",
    )
    parser.add_argument("--semilla", type=int, default=SEMILLA,
                        help="semilla del generador aleatorio "
                             "(por defecto: %(default)s)")
    parser.add_argument("--ticks", type=int, default=TICKS,
                        help="número de ticks de la simulación "
                             "(por defecto: %(default)s)")
    parser.add_argument("--con-ejemplos", action="store_true",
                        help="añade a Nia, Bruno y Sofía "
                             "(ejemplos/): 8 agentes en el mundo")
    args = parser.parse_args(argv)
    if args.ticks < 0:
        parser.error("--ticks no puede ser negativo")
    return args


def cargar_ejemplos():
    """Los 3 agentes de ejemplos/ como objetos Agente, en el orden
    Nia, Bruno, Sofía. Sus nombres no chocan con los de la demo
    (los 8 conviven; ver test_invariantes, regresión 16 nov 2026).
    """
    agentes = []
    for archivo in EJEMPLOS:
        ruta = os.path.join(raiz_proyecto(), "ejemplos", archivo)
        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)
        agentes.append(Agente(datos["nombre"], datos["rasgos"],
                              datos["metas"], datos["lugar_inicial"]))
    return agentes


def asegurar_salida_utf8():
    """La demo imprime español con tildes y eñes; en una consola
    forzada a ASCII, el primer print() moría con UnicodeEncodeError
    antes de simular y sin escribir el registro. Se pide UTF-8 con
    reemplazo de lo no representable; si la salida no admite
    reconfiguración (p. ej. un StringIO en tests), se deja como está.
    """
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


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


def main(argv=None):
    args = parse_args(argv)
    asegurar_salida_utf8()
    mundo = Mundo(semilla=args.semilla)
    agentes = crear_agentes()
    if args.con_ejemplos:
        agentes.extend(cargar_ejemplos())
    rasgos_iniciales = {a.nombre: dict(a.rasgos) for a in agentes}
    for agente in agentes:
        mundo.agregar_agente(agente)

    print("=== MUNDO-VIDA-IA ===")
    print("%d agentes despiertan en un mundo pequeño: plaza, biblioteca, "
          "taller, bosque y mercado." % len(agentes))
    print("Cada uno piensa, actúa, habla, colabora... y el caos interviene.\n")

    for _ in range(args.ticks):
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
                print("  [diálogo] %s" % evento["texto"])
            elif tipo == "caos":
                print("  [CAOS] %s" % evento["texto"])
            elif tipo == "crecimiento":
                print("  [crece] %s" % evento["texto"])
            else:
                print("  [%s] %s" % (evento["agente"], evento["texto"]))
        print()

    registro = construir_registro(mundo, agentes, rasgos_iniciales)
    base = raiz_proyecto()
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
    print("=== FIN DE LA SIMULACIÓN ===")
    print("Ticks: %d | Diálogos: %d | Eventos de caos: %d"
          % (args.ticks, dialogos, caos))
    for agente in registro["agentes"]:
        cambio = agente["rasgos_finales"] != agente["rasgos_iniciales"]
        print("  %s: ánimo=%s, energía=%d, rasgos cambiaron=%s"
              % (agente["nombre"], agente["animo"], agente["energia"], cambio))
    for ruta in rutas:
        print("Registro guardado en: %s" % ruta)


if __name__ == "__main__":
    main()
