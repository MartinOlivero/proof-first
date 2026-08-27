# Proof-First Development — diseño

**Fecha:** 2026-08-27
**Estado:** aprobado para implementar
**Autor:** Martín Olivero (IamAutom)

---

## 1. El problema

Un agente de IA escribe código más rápido de lo que un humano puede leerlo. El
cuello de botella dejó de ser *escribir*: ahora es **verificar**.

Cuando el agente dice "listo, el pago ya funciona", esa frase no es evidencia.
Es una afirmación de la misma parte que hizo el trabajo. Y la forma más común de
"verificarla" hoy —un test verde que escribió ese mismo agente— es el alumno
corrigiendo su propio examen: aprueba siempre.

Los métodos existentes no cierran este hueco:

- **SDD (Spec-Driven Development)** ordena *qué* construir. Una spec en prosa no
  es verificable por una máquina: alguien tiene que leerla y juzgar.
- **TDD** produce tests, pero si los escribe el mismo agente que escribió el
  código, comparten los mismos supuestos y los mismos puntos ciegos.
- **RDD (Receipt-Driven Development, de gentle-ai)** revisa el candidato de
  código congelado, con proceso transaccional. Su propia documentación aclara:
  *"reviewers receive provider-issued immutable context, not live workspace
  state"*. Nunca sale del código a mirar el mundo.

Ninguno responde la pregunta que importa cuando el sistema ya está corriendo:
**¿esto que dice que funciona, funciona de verdad, afuera?**

---

## 2. El principio

> **Nunca confiar en el reporte del agente. Solo en un artefacto observable
> desde afuera del agente.**

Un test verde es el agente calificándose solo. Un cargo apareciendo en el panel
de Stripe, no.

Un solo eje ordena toda la propuesta: **la distancia entre el que afirma y el
que comprueba.** Cuanto más lejos está el que comprueba de quien construyó, más
vale la prueba.

El nombre del método sale de ahí: **Proof-First Development (PFD)**. SDD pone
primero la especificación; PFD pone primero la prueba.

---

## 3. Alcance

### Dentro

- Definir qué cuenta como evidencia y con qué fuerza (la escala).
- Definir, para cada tipo de trabajo, cuál es la prueba que vale y cuál es la
  falsa prueba habitual (el catálogo).
- Impedir que se dé por cerrado un cambio caro sin evidencia externa.
- Ir a buscar esa evidencia con un verificador que no participó de la
  construcción.
- Registrar el estado vivo del trabajo y las actas de lo probado, con
  vencimiento automático.

### Fuera

- **Memoria de largo plazo entre proyectos.** Eso lo cubren `CLAUDE.md` (lo
  estable) y herramientas como engram (histórico buscable). Ver §11.
- **Revisión de calidad de código.** No opinamos sobre estilo, arquitectura ni
  legibilidad. Eso es RDD, `code-review` y similares.
- **Gestión de proyecto.** El cuaderno registra estado, no estima ni planifica.
- **Construcción.** Eso es `saas-builder`. PFD no escribe features.

---

## 4. La escala de evidencia

| Nivel | Qué es | Quién comprueba |
|:---:|---|---|
| **0** | "Listo, ya está implementado" | Nadie. Es una afirmación. |
| **1** | Muestra el código que escribió | Nadie. Mostrar no es probar. |
| **2** | Test verde escrito por el mismo agente | El constructor. Se aprueba solo. |
| **3** | Test preexistente, o escrito por el verificador | Alguien distinto. |
| **4** | La cosa ejecutándose: captura, log, `curl` | La máquina. El hecho, no el relato. |
| **5** | Un tercero sin interés lo confirma | Stripe, el servidor de mail, el DNS. |
| **6** | Una persona real lo usó y le funcionó | La realidad. |

Del 0 al 2 se está confiando. Del 3 para arriba, comprobando.

### Regla operativa

```
Plata, auth, datos de usuario, permisos, deploy  →  nivel 5 o no está hecho
Todo lo demás                                    →  nivel 4 alcanza
```

Un solo dial gobierna todo el plugin: **cuanto más caro es equivocarse, más
lejos del agente tiene que estar la prueba.** El mismo dial decide cuándo se
frena, cuándo se llama al verificador y cuándo se registra un acta.

---

## 5. El catálogo

Para cada tipo de trabajo: la prueba que vale, la falsa prueba habitual, y cómo
se consigue la buena. La columna del medio es el corazón pedagógico del plugin.

| # | Qué se construyó | ✅ Prueba que vale | ❌ Falsa prueba | Cómo se consigue |
|---|---|---|---|---|
| 1 | **Cobro / pago** | El cargo aparece en el panel del proveedor **y** el webhook llegó al servidor | El usuario vio la pantalla de "gracias por tu compra" | API del proveedor (Stripe MCP o `curl` a su API) + log del endpoint de webhook |
| 2 | **Login / auth** | Sesión real desde navegador limpio **+ un acceso no autorizado que es rechazado** | Entró el usuario que ya estaba logueado | Navegador en sesión privada + `curl` sin token esperando 401 |
| 3 | **Guardar datos** | La fila está en la base, consultada **por fuera de la app** | La pantalla muestra el dato | Query directa a la base o al endpoint de administración |
| 4 | **Borrar datos** | El dato **ya no está**, consultado por fuera | Desapareció de la pantalla | Misma query que #3, esperando vacío |
| 5 | **Permisos / multi-tenant** | El usuario B **no puede** ver lo de A | El usuario A ve lo suyo | Dos sesiones distintas, la segunda esperando 403 |
| 6 | **Mails / notificaciones** | El mensaje llegó a una casilla real y se puede abrir | La API devolvió `200 OK` | Casilla de prueba, o log de entrega del proveedor |
| 7 | **Deploy / publicación** | `curl` al dominio público **desde fuera de la máquina**, con la versión nueva | Anda en localhost / el build pasó | `curl -I` al dominio + comparar hash o versión |
| 8 | **Tarea automática / cron** | Corrió **sola**, a su hora, sin nadie mirando, y dejó log | Corrió cuando se la ejecutó a mano | Esperar una corrida real y leer el log con timestamp |
| 9 | **Integración externa** | Respuesta real de la API del tercero, en producción | El mock devolvió lo esperado | Llamada real con credenciales de producción |
| 10 | **Backup** | **Una restauración probada** | El backup existe | Restaurar a un entorno aparte y verificar que los datos están |

Notas:

- La entrada #10 es la falsa prueba más cara que existe, porque se descubre el
  único día en que importa.
- La entrada #1 ("un checkout que da por pagado en el redirect del cliente") ya
  figura como antipatrón en el README de `saas-builder`.
- El catálogo será extensible por proyecto mediante un archivo opcional
  `.proof-catalog.md` en la raíz, que agrega o pisa filas. Diseñado acá,
  **implementado en v1.1** (ver §14): en v1 las diez filas son fijas.

---

## 6. Las piezas

Seis piezas, ninguna grande.

### 6.1 La skill — `proof-first`

Contiene §4 (la escala), §5 (el catálogo) y la regla operativa. Es lo que el
agente lee para saber qué nivel corresponde y cómo se consigue cada prueba.

Se activa cuando el trabajo toca alguna de las diez categorías, o cuando el
usuario pregunta cómo verificar algo.

**Debe funcionar sin los hooks.** La skill es autosuficiente: contiene todo el
criterio. Los hooks solo agregan obligatoriedad. Sin ellos se pierde el capataz,
nunca el método. Ver §12.

### 6.2 El verificador — `the witness`

Un subagente. La pieza que diferencia a PFD de todo lo demás.

**Qué recibe:**

- Una sola afirmación a comprobar ("el checkout cobra de verdad").
- La categoría del catálogo y su fila.
- La lista de archivos involucrados.

**Qué NO recibe:** la conversación donde se construyó. No sabe cómo se resolvió,
qué costó, ni por qué debería andar. El contexto limpio es el requisito, no un
detalle de implementación.

**Consigna invertida:** no se le pide "confirmá que funciona", sino
**"demostrá que esto NO funciona"**. Sale a buscar la falla.

**Sin manos:** no puede editar código del proyecto. Si pudiera arreglar,
arreglaría y después aprobaría lo que él mismo arregló. Separación de poderes:
uno construye, otro comprueba, ninguno hace las dos cosas.

Tiene un único permiso de escritura: `PROOF.md`. Es el escribano — el único que
puede labrar un acta.

**Devuelve una de tres cosas:**

| Veredicto | Significa |
|---|---|
| ✅ `probado` | Con el artefacto crudo y el nivel alcanzado |
| ❌ `refutado` | Encontró la falla, y trae la prueba de la falla |
| ⚠️ `no verificable` | No pudo conseguirlo. Dice exactamente qué falta y quién debe proveerlo |

El tercer veredicto es obligatorio que exista. Sin esa salida, un verificador
acorralado inventa.

**Regla del artefacto crudo:**

> El artefacto se pega literal. Si se resume, no cuenta.

No "verifiqué el pago y funciona". Va la respuesta literal del proveedor, el
`curl` con su status code, el JSON tal cual salió. Un resumen **es** el reporte
del agente, que es justamente lo que no se cree. En el momento en que el agente
cuenta la prueba en vez de mostrarla, se vuelve al nivel 0.

### 6.3 El control de salida — hook `Stop`

Se dispara cuando el agente principal va a dar por terminado el turno. Es un
hook *prompt-based*: razona sobre lo que pasó en el turno en vez de comparar
contra una lista fija de rutas.

**Lógica de decisión, en orden:**

1. ¿Hay algo marcado `🔴 BLOQUEANTE` sin resolver en `PROOF.md`?
   → `block`, indicando qué falta decidir.
2. ¿El turno tocó alguna categoría cara (§4) sin acta vigente que la cubra?
   → `block`, indicando qué categoría y qué nivel se necesita.
3. ¿Algún cambio del turno invalidó un acta existente (§8)?
   → marcar el acta como vencida. Si la categoría es cara, `block`.
4. En cualquier otro caso → `approve`.

**La válvula de escape (crítica para que se use):**

No se puede *esquivar* la pregunta, pero sí se puede *responder que se asume la
deuda*. Si el usuario decide seguir sin probar, se registra en `PROOF.md` bajo
`⚠️ HECHO SIN PROBAR` con fecha y con quién lo decidió, y el hook aprueba.

Declarar la deuda es suficiente para pasar. Ignorarla, no.

Esto evita el fracaso más probable del plugin: que sea insoportable y lo
desinstalen. La disciplina no está en impedir, está en que **quede escrito**.

**Anti-bucle:** una misma afirmación bloquea una sola vez por turno. Al segundo
intento el hook ofrece directamente declarar la deuda.

### 6.4 El parte de arranque — hook `SessionStart`

Imprime el estado del cuaderno al abrir la sesión. Cinco líneas, no más:

```
proof-first · 3 actas vigentes · 1 vencida (tocaste src/auth el 25/08)
🔴 1 bloqueante: falta decidir si el borrado es real o lógico
⚠️ 1 sin probar: checkout Stripe (necesita nivel 5)
```

Sin esto, el cuaderno existe pero nadie lo abre.

### 6.5 El comando — `/proof`

Verificación a pedido, sin esperar al cierre del turno.

- `/proof` — muestra el estado del cuaderno.
- `/proof <afirmación>` — lanza al verificador sobre esa afirmación.
- `/proof deuda` — lista lo que está sin probar, ordenado por costo de error.

### 6.6 El cuaderno — `PROOF.md`

Un archivo markdown en la raíz del proyecto, versionado en git.

**Por qué en el repo y no en una base local:** la evidencia tiene que ser
auditable por un tercero. Tiene que viajar con el proyecto, verse en el diff de
un commit, y poder mostrarse a un cliente. Una base en `~/` no viaja a ningún
lado. Que esté en git no es una limitación: es la característica.

**Formato:**

```markdown
# PROOF

## 🔴 BLOQUEANTE
- Falta decidir si el borrado es real o lógico — impide cerrar auth

## ⬜ ABIERTO
- Recuperar contraseña
- Panel de facturación

## ⚠️ HECHO SIN PROBAR
- Checkout Stripe — necesita nivel 5, tiene nivel 2 — deuda asumida por Tincho 27/08

## ⏸️ POSTERGADO
- Multi-idioma — decidido por Tincho 27/08, va después del lanzamiento

<details>
<summary>▸ PROBADO (12)</summary>

✅ 27/08 · Login con Google · nivel 5
   prueba: sesión creada, user_id 8814 en Auth0 · sesión anónima rechazada 401
   cubre: src/auth/*.ts · huella: a3f9c1

</details>
```

**Reglas del cuaderno:**

- Lo vivo arriba, lo cerrado plegado abajo. Si al abrirlo no se ve en cinco
  segundos dónde se está parado, el archivo falló.
- `⏸️ POSTERGADO` guarda **quién** lo decidió y **cuándo**. La diferencia entre
  "lo postergamos a propósito" y "nos olvidamos" es la información más valiosa
  del archivo, y hoy no la registra nadie.
- **El acta no guarda la prueba: guarda la coordenada de la prueba.** No se
  archivan capturas ni copias —también se pudren, y nadie las mira—. Se guarda
  cómo volver a mirarlo hoy: el ID del cargo, el status, el usuario. Es una cita
  bibliográfica: del extracto bancario no se guarda la fotocopia, se anota el
  número de operación.

---

## 7. Cómo se detecta "lo caro"

El hook `Stop` es prompt-based: un modelo juzga con criterio, no con una lista
de carpetas. Una lista de rutas se rompe con cualquier estructura de proyecto
que no sea la esperada.

**Categorías caras** (nivel 5): cobro/pago, auth/sesión, escritura o borrado de
datos de usuario, permisos, deploy/publicación, envío de mensajes a personas,
backup, tareas programadas, integraciones externas en producción.

**Categorías baratas** (nivel 4): presentación, estilos, textos, refactors sin
cambio de comportamiento, documentación, configuración de desarrollo.

Ante la duda, el hook trata el cambio como caro y pregunta. Es más barato
preguntar de más que dejar pasar un cobro roto.

---

## 8. Vencimiento por huella

Un acta que dice "el pago se verificó el 12/08" es oro hasta que alguien toca el
checkout el 20/08. A partir de ahí sigue diciendo que está probado, y miente. Es
la peor clase de mentira: la que tiene sello.

Es la VTV del auto: el certificado dice que estaba bien en marzo, y no dice nada
de los frenos que se cambiaron en julio.

**Mecanismo:** cada acta guarda la lista de archivos que cubre y una huella de
su contenido.

- Con git: `git hash-object` sobre cada archivo cubierto, combinados.
- Sin git: SHA-256 del contenido concatenado.
- Se guardan los primeros 6 caracteres, suficiente para detectar cambio.

El cálculo se hace en Python (portable entre macOS, Linux y Windows), siguiendo
la convención que ya usa `legal-docs` con `check-vigencia.py`.

Al arrancar la sesión, si la huella no coincide, el acta aparece tachada con la
fecha en que dejó de valer. Sin que nadie se acuerde de nada.

---

## 9. El flujo completo

```
Agente construye el checkout
        │
        ▼
Intenta cerrar el turno
        │
        ▼
Hook Stop: "tocaste pagos, no hay acta vigente" ──► block
        │
        ▼
Agente principal invoca a the witness
        │
        ▼
the witness (contexto limpio, consigna invertida, sin manos)
   consulta la API de Stripe · revisa el log del webhook
        │
        ├── ✅ probado ──► escribe el acta en PROOF.md ──► turno cierra
        │
        ├── ❌ refutado ─► devuelve la falla ──► el agente arregla ──► reintenta
        │
        └── ⚠️ no verificable ─► "faltan credenciales de Stripe"
                                        │
                                        ▼
                        el usuario las provee, o asume la deuda
                                        │
                                        ▼
                          se registra en PROOF.md ──► turno cierra
```

---

## 10. Casos borde

| Situación | Comportamiento |
|---|---|
| El proyecto no usa git | Huella por SHA-256 del contenido |
| `PROOF.md` no existe | Se crea en el primer bloqueo, no antes |
| El turno no tocó nada caro | El plugin es invisible: no imprime, no frena |
| El turno fue solo conversación | No interviene |
| El verificador no tiene credenciales | `no verificable`, con la lista exacta de lo que falta |
| El usuario interrumpe a mitad | El acta no se escribe. No hay actas parciales |
| Bloqueo repetido sobre lo mismo | Al segundo intento se ofrece declarar la deuda |
| Proyecto ajeno sin `PROOF.md` | Funciona igual; propone crearlo, no lo impone |

---

## 11. Relación con otras herramientas

| Herramienta | Relación |
|---|---|
| **`saas-builder`** (propio) | Construye; PFD comprueba. Su README declara el hueco: *"dev process → Superpowers owns this"*, y lo que Superpowers pone ahí es TDD, que es nivel 2. PFD tapa ese hueco. Se declara como complemento opcional en ambos README. |
| **`legal-docs`** (propio) | Ya aplica el principio en su dominio: *"reads the code first, and refuses to write what it can't verify"*. Es la prueba de concepto de PFD antes de que PFD tuviera nombre. Sin cambios. |
| **Superpowers** | Complementario. Aporta proceso (brainstorming, TDD, debugging). PFD no lo duplica; solo señala que su TDD es nivel 2 y necesita compañía cuando hay plata de por medio. |
| **RDD / gentle-ai** | Complementario, no competidor. RDD revisa el código congelado (nivel 3 muy elaborado); PFD sale del código a buscar el artefacto del tercero (nivel 5). Dos etapas distintas de la misma cadena. |
| **engram** | Complementario. Engram es el histórico buscable entre sesiones y proyectos; `PROOF.md` es el estado presente de este proyecto, versionado. Si engram está instalado, el sedimento (§11) puede ir también ahí. **No se implementa en v1**: se documenta el puente y se escribe el día que alguien lo pida. |
| **`CLAUDE.md`** | El manual de la casa (lo estable). `PROOF.md` es el cuaderno de obra (lo vivo). Ritmos distintos, archivos distintos. |

### El sedimento

El cuaderno es el río; `CLAUDE.md` es el sedimento. Cuando algo demuestra ser
permanente —una trampa que mordió dos veces, una decisión que no se va a
revisar— **se promueve al `CLAUDE.md` y sale del cuaderno**. Así el manual crece
solo con lo que se ganó, y el cuaderno se mantiene chico.

En v1 la promoción la propone el agente y la confirma el usuario. No es
automática.

---

## 12. Portabilidad entre CLIs y modelos

PFD tiene que sobrevivir al CLI donde nació. El criterio lo resume bien Alan
Buscaglia en su charla sobre gentle-ai, hablando de por qué su stack funciona en
cualquier modelo: *"funciona para todos los modelos porque es un prompt"*.

### Qué es portable y qué no

| Pieza | Qué es en realidad | Portabilidad |
|---|---|---|
| La escala (§4) | Markdown | Cualquier modelo, cualquier CLI |
| El catálogo (§5) | Markdown | Cualquier modelo, cualquier CLI |
| `the witness` (§6.2) | Un prompt con reglas | Cualquier modelo capaz de correr subagentes |
| `PROOF.md` (§6.6) | Un archivo de texto | Universal |
| El control de salida (§6.3) | **Un hook del CLI** | Solo donde existan hooks con capacidad de bloqueo |
| El parte de arranque (§6.4) | Un hook del CLI | Ídem |

El 90% del plugin es texto plano y ya es agnóstico por construcción. Lo único
atado a Claude Code son los dientes.

### Requisito de degradación

**La skill debe funcionar sin los hooks.** Si alguien la usa en un entorno sin
hooks, tiene que seguir sirviendo: la escala, el catálogo y la consigna del
verificador operan igual — sin capataz, pero con método.

Esto sigue la convención ya establecida en `saas-builder`: *"cada skill funciona
sola con un fallback embebido; se pone mejor con las herramientas opcionales,
pero nunca bloquea sin ellas"*.

Consecuencia práctica de diseño: **ninguna instrucción esencial vive solo dentro
de un hook.** Los hooks refuerzan lo que la skill ya dice; no aportan reglas
propias. Si un hook desaparece, se pierde la obligatoriedad, nunca el criterio.

### Orden de portado

1. **v1 — Claude Code.** Hooks nativos, subagentes nativos. Es donde las
   capacidades aparecen primero.
2. **v1.x — OpenCode.** Corre subagentes vía plugins y adapta rápido lo que sale
   en Claude Code. Es el siguiente destino natural.
3. **Después — Codex, Gemini CLI, Cursor.** Con la skill y el catálogo como
   Agent Skills portables, más el comando `/proof` manual reemplazando al hook.
   Modo sin dientes: el método sin el capataz.

No se implementa nada de esto en v1 (ver §14). Lo que sí se hace en v1 es escribir
el contenido de forma que portarlo después sea cambiar el envase, no reescribir
el contenido.

---

## 13. Cómo se prueba el propio plugin

PFD se verifica con su propia regla, o no vale nada.

**Nivel 4 mínimo, obligatorio antes de publicar.** Una sesión real, grabada, en
un proyecto de verdad, donde:

1. Se toca un archivo de pagos → el hook frena. *(evidencia: la transcripción)*
2. Se invoca al verificador → devuelve `no verificable` por falta de credenciales.
3. Se asume la deuda → queda escrita en `PROOF.md` con fecha. *(evidencia: el diff)*
4. Se toca de nuevo el archivo cubierto por un acta → el acta aparece vencida.

Si alguno de esos cuatro pasos no se puede mostrar en crudo, el plugin no está
terminado.

---

## 14. Fuera de alcance en v1

- Integración escrita con engram (solo se documenta el puente).
- Promoción automática al `CLAUDE.md`.
- Catálogo extensible por archivo `.proof-catalog.md` (se diseña, se implementa
  en v1.1).
- Soporte para otros CLIs (OpenCode, Codex, Cursor). `saas-builder` lo hace vía
  Agent Skills portables; PFD puede seguir el mismo camino después de validar en
  Claude Code.
- Métricas o dashboard de cobertura de evidencia.

---

## 15. Estructura de archivos

```
proof-first/
├── plugin.json
├── README.md                      (inglés, con resumen en español)
├── LICENSE                        (MIT, como los otros dos)
├── skills/
│   └── proof-first/
│       ├── SKILL.md               (la escala + la regla operativa)
│       └── references/
│           └── catalogo.md        (las 10 entradas con el cómo)
├── agents/
│   └── witness.md                 (el verificador)
├── hooks/
│   ├── hooks.json
│   ├── stop-gate.py               (el control de salida)
│   ├── session-report.py          (el parte de arranque)
│   └── huella.py                  (cálculo y chequeo de vencimiento)
└── commands/
    └── proof.md
```

---

## 16. Decisiones tomadas y por qué

| Decisión | Alternativa descartada | Por qué |
|---|---|---|
| Frena solo lo caro | Frenar siempre / solo avisar | Frenar siempre se desinstala; solo avisar no cambia nada |
| El agente busca, el humano confirma | Automático total / manual total | Automático total deja al agente eligiendo qué mirar; manual total se saltea en la práctica |
| Registro solo de lo crítico | Registrar todo / efímero | Registrar todo genera ruido; efímero pierde la memoria entre sesiones |
| `PROOF.md` en el repo | Base local tipo SQLite | La evidencia debe ser auditable por terceros y viajar con el proyecto |
| Verificador sin permiso de escritura de código | Verificador que puede arreglar | Si arregla, aprueba lo que él mismo arregló |
| Coordenada, no copia de la prueba | Archivar capturas | Las copias también se pudren y nadie las mira |
| Hook prompt-based | Lista de rutas por regex | Una lista fija se rompe con cualquier estructura inesperada |
| La skill funciona sin hooks | Hooks obligatorios | Lo que es prompt corre en cualquier modelo; atar el criterio al hook lo encierra en un solo CLI |
| Nombre `proof-first` | `witness`, `receipts`, `oob` | Nombra el método, no solo la herramienta, y contrasta directo con SDD. `receipts` ya está tomado por RDD. `witness` sobrevive como el nombre del verificador |
