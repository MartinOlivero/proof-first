---
name: proof-first
description: This skill should be used when work touches money, authentication, user data, permissions, deploys, outbound messages, backups or scheduled jobs — anything where being wrong is expensive — and someone needs to know whether it actually works. It replaces the agent's own report with evidence observable from outside the agent, on a 0-6 scale, and carries a catalogue of what counts as real proof versus the false proof usually accepted for each kind of work. Trigger phrases (Spanish) include "¿cómo compruebo que esto funciona?", "¿esto ya está probado?", "verificá que el pago funcione", "¿cómo sé que el login anda?", "quedó andando?", "probalo de verdad". Trigger phrases (English) include "how do I verify this", "is this actually tested", "prove the payment works", "check that it really works", "show me the evidence". Use it INSTEAD of trusting a green test suite the agent itself wrote.
---

# Proof-First Development

**Nunca confiar en el reporte del agente. Solo en un artefacto observable desde
afuera del agente.**

Un test verde es el agente calificándose solo: lo escribió el mismo que escribió
el código, comparte sus supuestos y sus puntos ciegos. Un cargo apareciendo en
el panel de Stripe, no: lo emitió un tercero que no tiene interés en aprobarte.

## La escala

Un solo eje ordena todo: **la distancia entre el que afirma y el que comprueba.**

| Nivel | Qué es | Quién comprueba |
|:---:|---|---|
| 0 | "Listo, ya está implementado" | Nadie. Es una afirmación. |
| 1 | Muestra el código que escribió | Nadie. Mostrar no es probar. |
| 2 | Test verde escrito por el mismo agente | El constructor. Se aprueba solo. |
| 3 | Test preexistente, o escrito por el verificador | Alguien distinto. |
| 4 | La cosa ejecutándose: captura, log, `curl` | La máquina. El hecho, no el relato. |
| 5 | Un tercero sin interés lo confirma | Stripe, el servidor de mail, el DNS. |
| 6 | Una persona real lo usó y le funcionó | La realidad. |

Del 0 al 2 se está confiando. Del 3 para arriba, comprobando.

## La regla

```
Plata, auth, datos de usuario, permisos, deploy, mensajes, backup, cron
    → nivel 5 o no está hecho
Todo lo demás
    → nivel 4 alcanza
```

**Cuanto más caro es equivocarse, más lejos del agente tiene que estar la prueba.**

## Cómo se consigue cada prueba

Para saber qué es prueba válida y qué es falsa prueba en cada caso, leer
`references/catalogo.md`. Tiene las diez categorías con las tres columnas:
la prueba que vale, la falsa prueba habitual, y el comando concreto.

## El artefacto se pega crudo

> Si se resume, no cuenta.

No "verifiqué el pago y funciona". Va la respuesta literal del proveedor, el
`curl` con su status code, el JSON tal cual salió. Un resumen **es** el reporte
del agente, que es justamente lo que no se cree.

## Quién comprueba

Lanzá el subagente `witness`. No lo hagas vos: vos escribiste el código y ya
te convenciste de que está bien. El verificador arranca con contexto limpio y
con la consigna invertida —*demostrá que esto NO funciona*—, y no puede editar
código: si pudiera arreglar, aprobaría lo que él mismo arregló.

## Registrar

Todo lo que se prueba o se deja sin probar va a `PROOF.md` en la raíz del
proyecto, versionado en git para que sea auditable por un tercero.

- Probado → un acta con la **coordenada** de la prueba (el ID del cargo, el
  status, el usuario), nunca una copia. Las copias también se pudren.
- Sin probar por decisión del usuario → una deuda, **con su nombre y la fecha**.
  La diferencia entre "lo postergamos a propósito" y "nos olvidamos" es la
  información más valiosa del archivo.

## Si no hay hooks

Esta skill funciona sola. Los hooks solo agregan obligatoriedad; el criterio
está acá completo. Sin ellos se pierde el capataz, nunca el método.
