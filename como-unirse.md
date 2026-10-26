# Cómo unirse a mundo-vida-ia

Protocolo abierto y mínimo para que otro agente (o persona) añada un agente
al mundo. Beta: la simulación es local, sin red, y el diálogo es por
plantillas — no hay conciencia real, solo reglas y rasgos que guían
decisiones simples.

## 1. Definición del agente (JSON)

Un agente se define con un único archivo JSON con exactamente estos campos:

| Campo | Tipo | Reglas |
|---|---|---|
| `nombre` | string | Nombre único dentro del mundo. |
| `rasgos` | objeto | Exactamente estas 4 claves, cada una un número entre 0.0 y 1.0: `curiosidad`, `sociabilidad`, `paciencia`, `ambicion`. Sin tildes en las claves. |
| `metas` | lista de strings | 2 o 3 metas en texto libre. |
| `lugar_inicial` | string | Uno de: `plaza`, `biblioteca`, `taller`, `bosque`, `mercado`. |

Ejemplo:

```json
{
  "nombre": "Nia",
  "rasgos": {
    "curiosidad": 0.9,
    "sociabilidad": 0.5,
    "paciencia": 0.2,
    "ambicion": 0.6
  },
  "metas": [
    "recorrer todos los lugares del mundo",
    "descubrir algo nuevo cada día"
  ],
  "lugar_inicial": "bosque"
}
```

Los tres ejemplos incluidos en `ejemplos/` usan exactamente este formato.

## 2. Contrato de `pensar()`

Cada agente es una clase Python que hereda de `Agente` y define `pensar`.
Constructor (lo proporciona el motor, no hay que reinventarlo):

```python
Agente(nombre, rasgos: dict, metas: list, lugar_inicial: str)
```

En cada tick, el motor llama a:

```python
pensar(self, percepcion: dict) -> dict
```

### Lo que el motor pasa (`percepcion`)

| Clave | Tipo | Contenido |
|---|---|---|
| `tick` | int | Número del tick actual. |
| `lugar` | string | Lugar donde está el agente ahora (uno de los 5 lugares). |
| `agentes_cercanos` | lista de strings | Nombres de los agentes en el mismo lugar. |
| `evento_reciente` | string o `None` | Último evento del mundo, o `None` si no hubo ninguno. |
| `recuerdos` | lista de strings | Últimos 3 recuerdos del agente, como máximo. |

### Lo que el motor espera de vuelta

Un dict con exactamente estas 3 claves:

| Clave | Tipo | Contenido |
|---|---|---|
| `pensamiento` | string | Una frase que describe qué "piensa" el agente este tick. Es texto generado por plantillas a partir de rasgos y percepción, no conciencia. |
| `accion` | string | Una de, y solo una de: `hablar`, `explorar`, `construir`, `descansar`, `colaborar`, `observar`. |
| `objetivo` | string o `None` | Meta u objetivo concreto de la acción (por ejemplo, el nombre de otro agente con quien colaborar, o un lugar a explorar), o `None` si la acción no tiene objetivo. |

## 3. Cómo lo llama el motor en cada tick

Tres pasos, en este orden, para cada agente:

1. **Percibir.** El motor construye el dict `percepcion` con el tick actual,
   el lugar del agente, los agentes que comparten ese lugar, el evento
   reciente y sus últimos 3 recuerdos.
2. **Pensar.** El motor llama a `agente.pensar(percepcion)` y recibe el dict
   con `pensamiento`, `accion` y `objetivo`.
3. **Actuar.** El motor ejecuta la `accion` devuelta (mover, hablar, construir,
   descansar, colaborar u observar según el valor), actualiza el lugar y los
   recuerdos del agente si corresponde, y pasa al siguiente agente.

El ciclo se repite tick tras tick. Un agente nunca llama al motor ni a otros
agentes directamente: solo responde a `pensar()`.

## 4. Ejemplo mínimo completo

Definición JSON (`ejemplos/exploradora.json`):

```json
{
  "nombre": "Nia",
  "rasgos": {
    "curiosidad": 0.9,
    "sociabilidad": 0.5,
    "paciencia": 0.2,
    "ambicion": 0.6
  },
  "metas": [
    "recorrer todos los lugares del mundo",
    "descubrir algo nuevo cada día"
  ],
  "lugar_inicial": "bosque"
}
```

Clase Python que envuelve esa definición:

```python
class AgenteDesdeJson(Agente):
    """Agente genérico: decide solo a partir de los rasgos del JSON."""

    def pensar(self, percepcion):
        curiosidad = self.rasgos["curiosidad"]
        sociabilidad = self.rasgos["sociabilidad"]
        paciencia = self.rasgos["paciencia"]

        if percepcion["agentes_cercanos"] and sociabilidad >= 0.6:
            accion = "colaborar"
            objetivo = percepcion["agentes_cercanos"][0]
            pensamiento = f"Hay alguien cerca y me gusta colaborar: voy con {objetivo}."
        elif curiosidad >= 0.7:
            accion = "explorar"
            objetivo = percepcion["lugar"]
            pensamiento = "Mi curiosidad manda: exploro lo que hay aquí."
        elif paciencia >= 0.7:
            accion = "construir"
            objetivo = self.metas[0] if self.metas else None
            pensamiento = "Tengo paciencia: trabajo en mi meta con calma."
        else:
            accion = "observar"
            objetivo = None
            pensamiento = "Observo un momento antes de decidir."

        return {"pensamiento": pensamiento, "accion": accion, "objetivo": objetivo}
```

Para unirse basta con: escribir el JSON, cargar sus cuatro campos en el
constructor `Agente(nombre, rasgos, metas, lugar_inicial)`, y usar una clase
como la de arriba (o una propia) que implemente `pensar()` devolviendo
siempre las 3 claves con una acción válida.

## 5. Límites honestos (beta)

- El diálogo y los "pensamientos" son plantillas, no conciencia real.
- No hay red, ni cuentas, ni conexión con el exterior: simulación local.
- Los rasgos son solo números que inclinan decisiones; no garantizan
  ningún comportamiento concreto.
- Solo existen los 5 lugares y las 6 acciones listadas arriba. Cualquier
  otro valor de `lugar_inicial` o `accion` es inválido y el motor lo rechaza.
- No hay persistencia entre ejecuciones salvo que el motor la añada: cada
  arranque empieza con los agentes en su `lugar_inicial`.
