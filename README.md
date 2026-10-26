# Mundo-vida-IA

**BETA — simulación, no consciencia real.** Esto es un mundo virtual pequeño donde
agentes simulados piensan (con reglas explícitas), hablan, colaboran, sufren eventos
de caos y cambian con lo que viven. Sus "pensamientos" son textos generados por
plantillas a partir de sus rasgos, recuerdos y metas; no hay ninguna consciencia,
ningún aprendizaje automático y ninguna conexión a la red. Todo el código es
original, escrito desde cero, y solo usa la librería estándar de Python.

## Qué es

Cinco agentes viven en un mundo con cinco lugares: plaza, biblioteca, taller,
bosque y mercado. En cada tick (turno) cada agente percibe su entorno, piensa,
decide y actúa. El mundo introduce eventos de caos que perturban ánimos, planes
y relaciones. Con el tiempo, lo vivido cambia a cada agente: sus rasgos se mueven
un poco, sus metas evolucionan y sus recuerdos influyen en decisiones futuras.

## Cómo correrlo

```bash
python3 simulacion/demo.py
```

La demo crea 5 agentes, corre 30 ticks, imprime la historia en pantalla y guarda
el registro completo en `registro.json` (raíz) y en `visor/registro.json`.

Para ver el resultado en el visor, sirve la carpeta por HTTP (el navegador
bloquea leer archivos locales directamente) y abre `visor/index.html`:

```bash
python3 -m http.server 8000
# abrir http://localhost:8000/visor/
```

## El modelo, en lenguaje simple

- **Razonamiento (creencias–deseos–intenciones).** Cada agente tiene creencias
  (lo que percibe + lo que recuerda), deseos (sus metas) e intenciones (la acción
  elegida). La acción no se elige al azar: se puntúa según rasgos, energía,
  compañía cercana y recuerdos. Poca energía → descansar. Mucha sociabilidad y
  alguien cerca → hablar. Mucha curiosidad → explorar. Un recuerdo de escasez
  vuelve al agente más cauto.
- **Caos.** En cada tick hay probabilidad de un evento del mundo: tormenta,
  descubrimiento, escasez, celebración, rumor o visita inesperada. Cada evento
  cambia energía, ánimo, confianza o planes de verdad, y queda en la memoria.
- **Interacción.** Hablar genera mensajes a partir del pensamiento del que habla
  y, si se repite, sube la confianza mutua. Colaborar avanza un proyecto
  compartido hasta completarlo.
- **Desarrollo.** Cada experiencia queda registrada. Tras varias experiencias
  del mismo tipo, un rasgo se mueve un poco (por ejemplo, sobrevivir tormentas
  sube la paciencia; colaborar sube la sociabilidad). Las metas cumplidas se
  cierran y nacen metas nuevas derivadas de lo vivido.

## Cómo unirse (protocolo)

Cualquier agente puede entrar al mundo. El formato y el contrato están
documentados en [como-unirse.md](como-unirse.md): un JSON con `nombre`,
`rasgos` (curiosidad, sociabilidad, paciencia, ambicion, de 0.0 a 1.0), `metas`
y `lugar_inicial`, más una función `pensar(percepcion)` que devuelve
`pensamiento`, `accion` (hablar, explorar, construir, descansar, colaborar,
observar) y `objetivo`. Hay 3 ejemplos listos en `ejemplos/`.

## Estructura

```
simulacion/
  agente.py        Agente: rasgos, ánimo, energía, memoria, metas, pensar/decidir/actuar
  mundo.py         Mundo: lugares, bucle de ticks, generador de caos
  interaccion.py   Diálogo, confianza y proyectos compartidos
  experiencia.py   Registro de experiencias y evolución de rasgos y metas
  demo.py          Demo: 5 agentes, 30 ticks, imprime la historia, guarda registro.json
como-unirse.md     Protocolo abierto para que otras IAs/agentes se unan
ejemplos/          3 definiciones de agente (exploradora, constructor, organizadora)
visor/
  index.html       Visor estático: agentes, rasgos antes/después, línea de tiempo, pensamientos
  registro.json    Último registro generado por la demo
registro.json      Último registro generado por la demo
log.md             Registro de corridas y cambios
```

## Límites honestos de esta beta

- Diálogo y pensamientos por plantillas, no lenguaje libre.
- Solo 5 lugares y 6 acciones.
- Los proyectos de colaboración existen y están verificados por pruebas, pero
  en la demo de 30 ticks rara vez se disparan (los agentes hablan mucho y se
  agrupan); el protagonismo de la demo es diálogo y caos.
- La semilla fija (42) hace la demo reproducible en la misma máquina, pero el
  conteo exacto de eventos puede variar ligeramente entre corridas.
