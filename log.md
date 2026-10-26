# Log de mundo-vida-IA

## Primera corrida verificada — 26 de octubre de 2026

Comando: `python3 simulacion/demo.py` (salida 0, corrido dos veces por el
coordinador con idéntico resultado).

- Semilla: 42. Ticks: 30. Agentes: 5 (Lia, Tomas, Nara, Rui, Mara).
- Eventos totales: 375
  - pensamiento: 150 · acción: 80 · diálogo: 70 · crecimiento: 64 · caos: 11
- Diálogos: 70 (ejemplo: Tomas le dice a Lia: "estoy trabajando en una meta
  que me importa mucho, ¿y tu?").
- Caos: 11 eventos (descubrimientos, escasez en el mercado, rumores en el
  taller, entre otros).
- Crecimiento: los 5 agentes terminaron con rasgos distintos a los iniciales
  (ejemplo: Lia sociabilidad +0.40 y paciencia +0.05; Nara sociabilidad +0.48,
  paciencia +0.05, ambicion +0.12). Recuerdos por agente: entre 39 y 45.
- `registro.json` válido en la raíz y en `visor/registro.json` (verificado con
  `python -m json.tool`).

## Correcciones durante la construcción

- El trabajador del motor encontró que la regla "mucha curiosidad → explorar"
  ignoraba la cautela tras una escasez vivida. Se corrigió en `agente.py`: un
  recuerdo de escasez bloquea ese atajo y el agente pasa a observar. Verificado
  con pruebas: tras escasez → observar; sin escasez → explorar. También
  verificado: poca energía → descansar; mucha sociabilidad + compañía →
  hablar; colaborar llega al 100% y sube la confianza.

## Notas

- El informe del trabajador del motor citó 377 eventos en su corrida; las dos
  corridas del coordinador dieron 375 con el mismo desglose. Diferencia de 2
  eventos, probablemente de su corrida previa a la corrección. Los números de
  este log son los verificados por el coordinador.
- El visor (`visor/index.html`) se probó con lógica estática y un registro de
  muestra en /tmp (nunca dentro del repo); falta una renderización en
  navegador real con el registro verdadero, que se hará al abrirlo con un
  servidor local.
- Pendiente para el padre: subir el contenido al repo GitHub ya creado
  (https://github.com/mieresantonio/mundo-vida-ia) cuando lo disponga.
