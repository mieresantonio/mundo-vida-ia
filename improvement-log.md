# Registro de mejoras — mundo-vida-ia

## 2026-11-02 · Fase 2, Ciclo 2 (hallazgos MEDIA de la revisión 2026-11-02)

### MUNDO-M5 — El texto generado salía sistemáticamente sin tildes

- **Hallazgo:** todo el texto que produce la simulación (pensamientos,
  diálogos, caos, crecimiento, consola) iba sin acentuar mientras el
  README y el protocolo sí acentúan. Conteo en el registro anterior:
  `energia` ×340, `Asi que` ×230, `compania` ×53, `ultimamente` ×30.
- **Cambio:** acentuado el español en las plantillas y textos de los
  cinco módulos de `simulacion/` (pensar y razones de `agente.py`,
  textos de caos y descripciones de `mundo.py`, cuerpos de diálogo de
  `interaccion.py`, metas derivadas de `experiencia.py` y textos de
  consola de `demo.py`), incluidos comentarios y docstrings visibles
  en el repo. En `mundo.py`, los textos de crecimiento muestran el
  rasgo y el tipo acentuados («su ambición…», «tras vivir 'diálogo'»)
  mediante mapas de visualización, y en el visor las etiquetas de
  rasgos, tipos y distintivos se acentúan igual al pintarlas. Las
  claves internas NO cambian: las claves JSON del registro
  (`energia`, `animo`), los valores de `tipo` (`dialogo`, `accion`),
  los nombres de rasgo (`ambicion`) y los tipos de experiencia son
  identificadores que usan el código y el contrato del visor, y van
  sin tilde a propósito. Ninguna comprobación lógica depende de las
  formas acentuadas (las palabras clave internas —tormenta, escasez,
  descubrimiento— conservan su raíz sin tilde), y `_clasificar()` en
  `experiencia.py` acepta además las formas acentuadas devolviendo
  siempre el identificador canónico.
- **El registro cambia por la corrección ortográfica:** regenerado
  ejecutando la demo en el propio proyecto (30 ticks). MD5 anterior
  `415bad5ef0a6e8880af712bc7f245743` → MD5 nuevo
  `b56a5a928fcf5a2722665c8251a5aa7b` (idéntico en raíz y en `visor/`,
  y reproducible: dos ejecuciones seguidas dan el mismo MD5 y la
  misma salida). Tamaño: 142 961 → 144 419 bytes (la diferencia es el
  coste UTF-8 de las tildes, sin eventos de más ni de menos).
- **Verificaciones:**
  1. `py_compile` limpio en los 5 módulos.
  2. Smoke real y comparación contra el último estado conocido-bueno
     (verificación por contenido, no por nombre): 30 ticks, 375
     eventos con la misma distribución que antes (150 pensamiento ·
     80 acción · 70 diálogo · 64 crecimiento · 11 caos), misma
     secuencia tick/tipo/agente, mismos rasgos finales, mismos
     ánimos/energías finales, mismas metas y mismos conteos de
     recuerdos por agente (45/39/44/41/42). Solo cambian los textos.
     En los textos del registro nuevo (eventos + recuerdos + metas):
     `energia` = 0, `Asi que` = 0, `compania` = 0, `ultimamente` = 0
     (y las formas acentuadas aparecen en espejo de los conteos
     viejos: `energía` ×335, `Así que` ×230, `compañía` ×53,
     `últimamente` ×30). En el archivo completo, `energia` aparece
     ×5: son las claves JSON estructurales, una por agente, que el
     visor lee como `a.energia`. En la salida de consola, 0 líneas
     con las formas sin tilde objetivo.
  3. Checklist de detalle: el contrato del visor se verificó campo a
     campo sobre el registro nuevo (`meta.ticks/semilla`, por agente
     `rasgos_iniciales/finales`, `animo`, `energia`, `metas`,
     `recuerdos`; eventos con `tick/tipo/agente/texto` y los 5 tipos
     dentro de los filtros del visor) y las dos copias del registro
     son idénticas; ortografía revisada en todo el texto tocado
     (incluidos «¿tú cómo lo llevas?», «gustaría» y las cabeceras
     «Código… estándar» de los cinco módulos); sin regresiones en la
     lógica (la demo produce exactamente la misma simulación).

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
