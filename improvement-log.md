# Registro de mejoras — mundo-vida-ia

## 2026-11-02 · Fase 2, Ciclo 1 (hallazgos ALTA de la revisión 2026-11-02)

### MUNDO-A1 — La demo escribía en una ruta absoluta fija

- **Hallazgo:** `simulacion/demo.py` usaba
  `os.path.expanduser("~/workspace/mundo-vida-ia")` como base para guardar
  `registro.json` y `visor/registro.json`: ejecutada desde cualquier clon
  en otra ruta, escribía fuera de ese clon (demostrado en la revisión:
  corría en `/tmp` y escribía en el repo real).
- **Cambio:** la base ahora es la raíz del proyecto calculada desde la
  ubicación del propio script
  (`os.path.dirname(os.path.dirname(os.path.abspath(__file__)))`:
  `demo.py` vive en `simulacion/`, la raíz es su carpeta padre). No se
  tocó la lógica de la simulación.
- **Verificaciones:**
  1. `py_compile` limpio en los 5 módulos de `simulacion/`.
  2. Smoke real desde una copia en `/tmp/mundo-copia`: la demo corrió
     los 30 ticks completos (70 diálogos, 11 eventos de caos, como en la
     corrida documentada) e imprimió «Registro guardado en:
     /tmp/mundo-copia/…» para ambas rutas; el MD5 del `registro.json`
     del repo real fue idéntico antes y después
     (`415bad5ef0a6e8880af712bc7f245743`), y el registro generado en la
     copia salió byte a byte idéntico al versionado (mismo MD5), así
     que la reproducibilidad determinista se mantiene.
  3. Checklist de detalle: sin rutas absolutas ni referencias a
     `~/workspace` en el código de `simulacion/`; el README ya describía
     este comportamiento («guarda el registro en `registro.json` y en
     `visor/registro.json`» desde el repo), así que ahora es veraz sin
     cambios.

### MUNDO-A2 — El motor no rechazaba lugares ni acciones inválidas

- **Hallazgo:** `como-unirse.md` §5 afirma «cualquier otro valor de
  `lugar_inicial` o `accion` es inválido y el motor lo rechaza», pero era
  falso: un lugar inventado se aceptaba (la guarda de
  `Mundo.agregar_agente()` era un no-op) y una acción fuera del catálogo
  se convertía en silencio a «observar» en `Agente.actuar()`.
- **Cambio (el código ahora cumple lo que el documento promete):**
  - `agente.py`: nueva constante `LUGARES_VALIDOS` (los 5 lugares, en
    sincronía con `LUGARES` de `mundo.py`); el constructor lanza
    `ValueError` con mensaje claro si `lugar_inicial` no está en la
    lista. `actuar()` lanza `ValueError` si la acción falta o no está
    en `ACCIONES_VALIDAS` (ya no hay conversión silenciosa).
  - `mundo.py`: `agregar_agente()` comprueba el lugar ANTES de registrar
    al agente y lanza `ValueError` si no existe en el mundo (segunda
    línea de defensa, p. ej. si el lugar se mutó tras construir).
- **Verificaciones:**
  1. `py_compile` limpio en los 5 módulos.
  2. Smoke real en la copia de `/tmp`: `Agente(..., "castillo_inventado")`
     → `ValueError: Lugar inicial no válido…`; lugar mutado +
     `agregar_agente()` → `ValueError` y el agente NO queda registrado
     (0 agentes); `actuar()` con `"volar"` → `ValueError: Acción no
     válida…`; acción ausente → `ValueError`. Los 3 ejemplos de
     `ejemplos/` se cargan, se agregan y actúan con acciones válidas, y
     un mundo normal corre ticks sin error. La demo completa (30 ticks)
     también corrió sin cambios en su salida ni en su registro.
  3. Checklist de detalle: textos de error nuevos con ortografía
     cuidada (tildes en «no válido», «Acción»); `como-unirse.md` no
     necesita cambios porque su afirmación ahora es cierta; sin
     regresiones en el flujo normal.
