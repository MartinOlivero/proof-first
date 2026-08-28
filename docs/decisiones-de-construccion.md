# Decisiones de construcción

Las 42 decisiones que se tomaron mientras se construía este plugin, con su
motivo y lo que costaba equivocarse. No es documentación del producto: es el
registro de por qué el plugin es como es.

Cada una salió de un hallazgo verificado antes de decidir, no de una opinión.
Ocho de ellas corrigen un texto de este mismo repo que afirmaba algo que el
código no hacía.

---

## Pre-flight scan

### Pares que comparten archivo o interfaz

| Produce | Consume | Qué encontré |
|---|---|---|
| T1 `cuaderno.leer/escribir/agregar_acta/agregar_deuda` | T4 stop_gate, T5 session_report | Firmas coinciden en ambos sentidos. OK |
| T2 `huella.calcular/vencidas` | T4, T5 | OK |
| T3 `deteccion.clasificar/cambios_sin_commitear/CATEGORIAS` | T4 | T4 usa `cat['nombre']` y `cat['nivel']`; T3 los define. OK |
| T4 crea `hooks/hooks.json` | T5 crea `hooks/session_report.py` | **CONFLICTO**: hooks.json declara un script que no existe hasta T5. Entre T4 y T5 el plugin queda roto si alguien lo instala. |
| T6 `references/catalogo.md` | T7 witness, T8 comando | Ambos lo referencian; T6 va antes. OK |
| T3 `CATEGORIAS` (8 claves) | T6 catálogo (10 categorías) | Discrepancia intencional y ya documentada en T6 Step 4: "guardar" y "borrar datos" se funden en `datos`. OK |
| T9 crea `PROOF.md` del propio repo | T4 stop_gate | Ningún archivo del plugin dispara un patrón de `CATEGORIAS` — el hook no se auto-bloquea. Verificado nombre por nombre. OK |

### Coherencia interna de cada tarea

| Tarea | Su texto concuerda consigo mismo |
|---|---|
| T1 | Test usa sólo funciones que la implementación define. El caso "agregar deuda no pisa el acta" está cubierto por el filtrado separado de `actas` y `sin_probar`. OK |
| T2 | OK |
| T3 | El parseo de `git status --porcelain` coincide con el formato que el test genera (`?? nuevo.py` → `linea[3:]`). OK |
| T4 | `sys.path` relativo a `__file__/../lib`; el `__main__` separa `--autotest` de `main()`. OK |
| T5 | OK |
| T6 | **DEFECTO**: el Step 2 dice "copiar las 10 filas de la spec §5" sin incluirlas. Es un placeholder según la propia regla del plan. |
| T7 | OK |
| T8 | **DEFECTO**: el bloque bash usa `~/.claude/plugins/proof-first/lib`, un path de instalación inventado. `${CLAUDE_PLUGIN_ROOT}` no se sustituye en comandos (sólo en hooks y MCP). El comando rompería en silencio. |
| T9 | OK |

## Rulings previos a la ejecución

Ruling A: T4 crea `hooks.json` sólo con el hook `Stop`; T5 lo modifica agregando
`SessionStart`. — Cada tarea tiene que dejar el plugin instalable, y un hook que
apunta a un script inexistente es peor que no tener el hook. — Costo si me
equivoco: mínimo, un archivo se edita dos veces en vez de una.

Ruling B: T8 no ejecuta Python desde un path de instalación. El comando lee
`PROOF.md` directamente y calcula las huellas con `shasum` inline, sin depender
de dónde quedó instalado el plugin. — Es la trampa de `${CLAUDE_PLUGIN_ROOT}` que
ya mordió en otros plugins propios: no se sustituye en comandos y falla sin
avisar. — Costo si me equivoco: el comando podría reportar mal qué actas
vencieron; el hook `SessionStart`, que sí puede usar la ruta del plugin, sigue
siendo la fuente confiable.

Ruling C: el defecto de T6 (las 10 filas sin transcribir) se resuelve pasándole
al implementador la spec §5 como entrada explícita del dispatch, en vez de
inflar el plan con la tabla duplicada. — La spec es la autoridad vinculante y
viaja con el plan; duplicarla crearía dos fuentes que se desincronizan. — Costo
si me equivoco: el catálogo sale incompleto, y el Step 3 de T6 lo detecta
(`grep -c "^### "` tiene que dar 10).


Ruling D: T1, T2 y T3 se despachan en un solo batch. Son tres archivos nuevos
sin superposición (`lib/cuaderno.py`, `lib/huella.py`, `lib/deteccion.py`), de la
misma forma (módulo + autotest + commit) y con el código completo escrito en el
plan: es transcripción más testing, no diseño. — Un subagente por archivo
triplicaría el arranque de contexto para el mismo diff. — Costo si me equivoco:
la review cubre tres archivos en vez de uno, y un fix loop los tocaría juntos.

## Ejecución

Task 1-3: dispatch (batch, haiku) — BASE fdb6111
Task 1-3: implementado — DONE — commits b88e04f, b3188c2, 7afce71
  Autotests reverificados por el controlador, independientes del reporte:
  cuaderno.py OK · huella.py OK · deteccion.py OK
Task 1-3: review despachada (sonnet) — BASE fdb6111 HEAD 7afce71
Task 1-3: review devuelve 4 Important, los 4 plan-mandated (el codigo salio de mi
  propio plan). Verificados por el controlador antes de rulear.

Ruling E: arreglar el round-trip con `cubre` vacio. Un acta sin archivos es
legitima —verificar que el DNS resuelve o que un mail llega no esta atado a
ningun archivo— y `huella.vencidas` ya la contempla (`if not a.get("cubre")`).
`cuaderno.escribir` la emite y `cuaderno.leer` no la matchea: se pierde en
silencio. Comprobado: escribir un acta con cubre=[] y releer devuelve [].
— Costo si me equivoco: ninguno, el regex queda estrictamente mas permisivo.

Ruling F: arreglar los falsos positivos de patrones cortos. El mas grave del
lote. Comprobado por el controlador: `src/controllers/user_controller.py`,
`app/control/index.ts` y `lib/oracle_client.py` se clasifican como `permisos`
nivel 5 (por "cont-ROL-ler" y "or-ACL-e"). En cualquier proyecto MVC el hook
bloquearia en cada turno, que es exactamente el fracaso que el propio modulo
dice querer evitar. Fix: matchear tokens (separando por / _ . -) en vez de
substring crudo. — Costo si me equivoco: algun caso que antes agarraba pasa
desapercibido; aceptable, un falso negativo lo cubre /proof a mano y un falso
positivo cuesta la desinstalacion.

Ruling G: arreglar el dedup por `startswith(que)` en `sin_probar`. Una deuda de
"Pago Stripe" se borraria al labrar el acta de "Pago". — Costo: nulo, el fix es
comparar contra el separador incluido.

Ruling H: los acentos se arreglan PARCIAL. Comentarios y docstrings sin acentos
(consistencia interna). Los strings que se le muestran al usuario —los "nombre"
de CATEGORIAS, que aparecen en el mensaje de bloqueo— llevan ortografia
correcta: es instruccion global del usuario y quitarlos empeora la salida. La
constraint del plan estaba mal formulada y queda corregida asi.
— Derivado: si el source lleva acentos y los hooks imprimen JSON con
ensure_ascii=False, Windows con cp1252 rompe (ya paso en command-center).
Constraint nueva para T4 y T5: los hooks fuerzan UTF-8 en stdout.
— Costo si me equivoco: en Windows la salida del hook sale con caracteres raros.

Task 1-3: minor (deferred): `import os` muerto a nivel modulo en deteccion.py
Task 1-3: minor (deferred): el guard de seccion en cuaderno.leer no cubre la
  linea literal `<details>`; hoy es inocuo porque no empieza con "- "
Task 1-3: fix round 1/5 despachado (resume del implementador original, haiku)
  con los 4 Important y los rulings E-H. Los 2 minor quedan fuera del loop.
PENDIENTE al cierre: portar los fixes de los rulings E-G al texto del plan, para
  que una re-ejecucion desde cero no reproduzca los mismos bugs.
Task 1-3: fix round 1/5 aplicado — commit 726285b. Reverificado por el
  controlador antes de la re-review, no por el reporte:
  · controllers/user_controller.py, app/control/index.ts, oracle_client.py,
    components/Modal.tsx -> [] (antes: los tres primeros daban 'permisos')
  · auth/session.ts -> auth · checkout/stripe_webhook.py -> pago
    migrations/003_add_users.sql -> datos · billing/index.ts -> pago (intactos)
  · acta con cubre=[] sobrevive el round-trip
  · deuda "Pago Stripe" sobrevive al cerrar el acta "Pago"
  · los tres autotests OK
Task 1-3: re-review acotada despachada (sonnet) — 7afce71..726285b
Task 1-3: re-review 1/5 — findings 1, 3 y 4 ADDRESSED. Finding 2 cierra los
  falsos positivos y conserva los verdaderos, pero introduce una regresion.

Ruling I: arreglar la regresion del tokenizador. Al partir por ".", los patrones
que contienen un punto quedaron imposibles de matchear. Verificado por el
controlador: `vercel.json` -> [] y `netlify.toml` -> [] (antes disparaban
`deploy`). Matiz que la re-review no separo: `ci.yml` y `cd.yml` siguen cayendo,
pero por "workflow"/"deploy" en la ruta, no por su propio patron — el patron
igual esta muerto. `vercel.json` es el archivo de deploy real de este usuario
(Vercel es su hosting), asi que la regresion pega justo donde mas duele.
Fix: un patron que contiene un punto es un NOMBRE DE ARCHIVO, no un token — se
compara contra el basename completo, ademas del match por tokens.
— Costo si me equivoco: `deploy` podria dispararse de mas en un archivo que se
llame igual que un manifiesto; barato comparado con no detectar un deploy.

Ruling J: el backslash faltante NO es un minor aparte, es el ruling F aplicado a
medias — entra en el mismo fix round. Verificado: `src\auth\session.ts` -> [].
Impacto real bajo (git normaliza a barras), pero el ruling decia que se parte
por "\" y no se hizo. — Costo: nulo, es un caracter en el separador.
Task 1-3: fix round 2/5 aplicado — commit 69b30ec. Controlador verifico los 14
  casos de clasificacion: 14/14 correctos (4 falsos positivos vacios, 4
  verdaderos intactos, vercel.json/netlify.toml/Dockerfile/ci.yml/cd.yml ->
  deploy, y la ruta con backslash -> auth). Tres autotests OK.
Task 1-3: re-review 2/5 despachada (sonnet) — 726285b..69b30ec
Task 1-3: re-review 2/5 — ambos findings ADDRESSED, sin breakage nuevo.
Task 1-3: minor (deferred): el comentario de deteccion.py:91-92 describe solo el
  match por token, no la rama nueva de basename. Sin efecto funcional.
Task 1-3: complete (commits fdb6111..69b30ec, review clean, 3 minors deferidos)

Task 4: dispatch (haiku) — BASE 69b30ec — hook Stop + hooks.json solo con Stop
Task 4: implementado — DONE — commit 2a72efe. Verificado end-to-end por el
  controlador con el hook invocado como lo invoca Claude Code (JSON por stdin):
  bloquea por auth sin nombrar el css, la valvula de escape libera, sin git
  aprueba. hooks.json contiene solo Stop. La guarda UTF-8 esta presente.
  El implementador confeso una desviacion: escribio test e implementacion
  juntos, sin ciclo RED->GREEN separado. Va a la review como finding.
Task 4: review despachada (sonnet) — 69b30ec..2a72efe
Task 4: review devuelve 3 Critical + 4 Important, todos plan-mandated.
  Los tres criticos reproducidos por el controlador antes de rulear.

Ruling K: arreglar `_cubierto`. Es la falla peor de todas: el porton APRUEBA lo
que deberia frenar. `nombre in d` es un substring contra el texto completo de la
entrada, asi que una deuda declarada para
`packages/legacy-vendor/src/auth/index.ts` "cubre" un `src/auth/index.ts` real
que nunca se menciono. Reproducido: decision -> approve. Fix: extraer el `que`
de la entrada (lo anterior al primer " — ") y comparar rutas exactas.
— Costo si me equivoco: el hook frena de mas cuando la entrada esta escrita a
mano con otro formato; preferible a dejar pasar codigo caro sin probar.

Ruling L: arreglar el punto ciego del commit. `afectadas` filtra las actas
vencidas por las que ademas aparecen en `cambios_sin_commitear`. Si el cambio ya
se commiteo, el archivo sale de esa lista y el acta vencida se vuelve invisible
para siempre, mientras `_cubierto` la sigue dando por valida. Un acta vencida es
exactamente lo que este plugin existe para detectar: sacar el filtro para las
actas vencidas de categoria cara, esten o no en el diff sin commitear. Y
`_cubierto` deja de considerar cubierta un acta vencida.
— Costo si me equivoco: al abrir un proyecto con deuda vieja el hook frena una
vez; la valvula de escape lo libera declarando la deuda.

Ruling M: arreglar el crash con JSON valido que no es objeto. Reproducido:
`echo '[1,2,3]'` da AttributeError. Viola la constraint de que ningun camino de
falla puede terminar sin aprobar. Fix: validar que la entrada sea dict.
— Costo: nulo.

Ruling N: el bloqueante sin git NO se cambia; la constraint estaba mal
formulada y queda refinada. "Sin git no bloquea" existe porque sin git no se
puede saber que se toco — es una limitacion de conocimiento. Un bloqueante en
PROOF.md no es una inferencia: es una decision que una persona escribio a
proposito, y no depende de git. Ademas no atrapa la sesion: moverlo a POSTERGADO
lo libera, y el agente puede editar PROOF.md.
— Costo si me equivoco: en un proyecto sin git con un bloqueante viejo, el hook
frena hasta que alguien lo resuelva o lo posponga. Es el comportamiento buscado.

Ruling O: arreglar los acentos de los textos `reason`. Son lo que una persona
lee en el momento en que se le frena el turno. Aplica la regla de ortografia
correcta, no la de comentarios. — Costo: nulo.

Task 4: minor (deferred): mezcla de voseo y tuteo en los mensajes de reason
Task 4: minor (deferred): el fallback de `raiz` a os.getcwd() no esta comentado
Observacion: la review dice que saltear el ciclo RED->GREEN dejo pasar estos
  bugs. Discrepo en parte: los tres estaban en el codigo de referencia de MI
  plan, y un RED/GREEN sobre mis propios tests los habria reproducido igual. Lo
  que los encontro fue el revisor adversarial, no el ciclo TDD.
Task 4: fix round 1/5 aplicado — commit afe2fe7. Reverificado por el controlador
  con los mismos repros que fallaban antes:
  · deuda ajena por sufijo -> block (antes: approve)
  · deuda exacta del mismo archivo -> approve (valvula intacta)
  · acta vencida con el cambio ya commiteado -> block (antes: invisible)
  · '[1,2,3]', 'no json' y 'null' -> approve, exit 0 (antes: AttributeError)
  · bloqueante sin git -> block (pin del ruling N)
  · el reason que lee una persona sale con acentos correctos
  · autotest OK, ahora 12 escenarios
Task 4: minor (deferred): un comentario quedo con acento ("no quedó enterrada"),
  contra la convencion de comentarios sin acentos. Sin efecto funcional.
Task 4: re-review acotada despachada (sonnet) — 2a72efe..afe2fe7
Task 4: re-review 1/5 — los 4 findings ADDRESSED, el not-a-fix respetado, sin
  breakage nuevo. La re-review aporta una observacion out-of-scope importante.

Ruling P: arreglar la valvula de escape en la rama de actas vencidas, aunque sea
out-of-scope y preexistente. La rama bloquea incondicionalmente y su propio
mensaje ofrece "declara la deuda en PROOF.md" como alternativa — que no
funciona. Reproducido: acta vencida -> block; declaro la deuda -> block igual.
El plugin esta haciendo exactamente lo que existe para cazar: prometer algo que
el sistema no cumple. Ademas es load-bearing para T9, donde el escenario 3 de la
spec §13 es justamente "asumir la deuda". Fix: esa rama respeta la declaracion
de deuda igual que la rama 3.
— Costo si me equivoco: un acta vencida se puede tapar declarando deuda en vez
de volver a probar; es la misma concesion consciente que ya hace el resto del
plugin, y queda escrita con nombre y fecha.
Task 4: fix round 2/5 despachado
Task 4: fix round 2/5 aplicado — commit c920152. Reverificado por el controlador:
  · acta vencida sin deuda -> block
  · deuda por el 'que' del acta -> approve (la promesa ahora se cumple)
  · deuda por el path de 'cubre' -> approve
  · deuda ajena por sufijo -> block (el porton NO se aflojo)
  · codigo caro sin nada -> block
  · autotest OK, 16 escenarios
Task 4: re-review 2/5 despachada (sonnet) — afe2fe7..c920152
Task 4: re-review 2/5 — ambos findings ADDRESSED, sin breakage nuevo.

Task 4: parked — el ruling P quedo mas generoso de lo necesario: una deuda
declarada por CUALQUIER archivo del `cubre` de un acta limpia el acta entera,
aunque el cambio real haya sido en otro archivo del grupo. La re-review lo marco
y tiene razon: es lo que yo especifique.
  Ruling: se parkea, no se arregla en v1. Para saber cual de los N archivos
  cambio habria que abandonar la huella combinada y calcular una por archivo —
  cambia el modelo de datos del acta. Y el riesgo real es bajo: quien declara la
  deuda es el usuario, a conciencia, con su nombre y la fecha escritos; la
  laxitud habilita un error honesto, no un fraude. Candidato a v1.1.
Task 4: minor (deferred): "o declara la deuda" quedo en tuteo al lado del
  "actualizá" ya corregido, en la misma frase
Task 4: minor (deferred): el conteo de escenarios del reporte esta flojo (dice
  16 contando un duplicado); los tres bloques de test nuevos si ejercitan el fix
Task 4: complete (commits 69b30ec..c920152, review clean, 1 parked, 4 minors)

Task 5: dispatch (haiku) — BASE c920152 — session_report.py + SessionStart
Task 5: implementado — DONE — commit b5ed98b. Verificado por el controlador:
  · hooks.json conserva Stop Y SessionStart, cada uno a su script
  · sin PROOF.md: silencio absoluto
  · con acta vigente + vencida + bloqueante + deuda: 4 lineas correctas
  · el hook Stop sigue funcionando (sin regresion)
  · ambos autotests OK
  · HALLAZGO DEL CONTROLADOR: `echo '[1,2,3]' | session_report.py` crashea con
    AttributeError, el mismo bug que se arreglo en stop_gate.py en el fix round
    1 de T4. El brief de T5 es anterior a ese fix, asi que no lo llevaba. Viola
    la constraint explicita de que ningun camino de falla puede terminar sin
    salir en silencio con exit 0. Va a la review como finding verificado.
Task 5: review despachada (sonnet) — c920152..b5ed98b
Task 5: review devuelve 1 Critical (el que ya habia encontrado el controlador)
  y 1 Important nuevo.

Ruling Q: arreglar el guard de isinstance. Es el mismo bug que se arreglo en
stop_gate.py en T4; el brief de T5 es anterior. Fix identico al del hermano.
Ademas se le suma la simetria que la review marco como minor: envolver el print
final en try/except como hace stop_gate. No es scope creep — el tema de esta
tarea es justamente lo que un hermano aprendio y el otro no.
— Costo: nulo.

Ruling R: arreglar el presupuesto de lineas. El docstring promete "Cinco lineas,
no mas" y el codigo emite hasta 7 u 8, porque MAX_ITEMS=3 se aplica por
categoria y no al total. Reproducido: 4 bloqueantes + 4 deudas -> 7 lineas.
Y lo peor no es el largo: esconde el 4to bloqueante SIN AVISAR que existe.
Fix: presupuesto total de 5 lineas con prioridad (cabecera, bloqueantes,
deudas, vencidas) y una ultima linea que diga cuantos quedaron afuera.
— Costo si me equivoco: el parte muestra menos detalle del que podria; se
compensa con el contador de lo omitido, que es justo lo que falta hoy.

Observacion: es el TERCER caso del mismo patron en este proyecto — un texto que
promete algo que el codigo no cumple. Antes: el reason ofrecia declarar la deuda
y esa rama no la aceptaba. Ahora: "cinco lineas" que son siete. Ninguno lo
habria visto un test: el texto y la logica son cosas separadas y nadie las
compara. Vale para el video.
Task 5: fix round 1/5 despachado
Task 5: fix round 1/5 aplicado — commit 3634e27. Reverificado por el controlador:
  · '[1,2,3]', 'basura', 'null', '42' -> sin salida, exit 0
  · 4 bloqueantes + 4 deudas + 1 vencida -> exactamente 5 lineas, la ultima dice
    "… y 6 más sin mostrar (mirá PROOF.md)" — ya no oculta en silencio
  · caso que entra en el presupuesto -> no aparece linea de omitidos
  · sin PROOF.md -> silencio
  · ambos autotests OK (el hermano stop_gate no se rompio)
Task 5: re-review acotada despachada (sonnet) — b5ed98b..3634e27
Task 5: re-review 1/5 — ambos findings ADDRESSED, sin breakage nuevo. El
  revisor verifico la aritmetica del contador de omitidos en el caso general,
  no solo en el ejemplo: omitidos = total - mostrados, exacto siempre.
Task 5: minor (deferred): el docstring nuevo no aclara que la linea de vencidas
  compite por el mismo presupuesto y puede ser la que se cae. Cuarto caso del
  mismo patron (texto que no describe lo que el codigo hace); se junta con los
  demas minors para la revision final, no justifica otra ronda por una frase.
Task 5: complete (commits c920152..3634e27, review clean, 1 minor)

Task 6: dispatch (sonnet) — BASE 3634e27 — SKILL.md + catalogo de 10 entradas.
  Es contenido, no codigo: la escala, la regla y las 10 falsas pruebas.
Task 6: implementado — DONE — commit f68beaa. Verificado por el controlador:
  · 10 entradas, 10 falsas pruebas, 10 explicaciones de por que enganan, 20
    bloques de comando
  · las 10 columnas de falsa prueba coinciden TEXTUALMENTE con la spec §5
  · SKILL.md: frontmatter en ingles, cuerpo en espanol con acentos
  · unica URL concreta del catalogo: api.stripe.com/v1/charges (existe)
  · entrada 10 (backup) es un restore real en base descartable, no un ls
  · el implementador declaro los 2 comandos que dejo genericos en vez de
    inventar el endpoint (estado de mail en Resend, integracion generica)
Task 6: review despachada (sonnet) — 3634e27..f68beaa
Task 6: review devuelve 1 Important real y 2 Minor.

Ruling S: unificar las listas de categorias caras. Reproducido: hay CUATRO
versiones de la misma lista y no coinciden.
  spec §4      : 5 categorias (plata, auth, datos, permisos, deploy)
  spec §7      : 9 categorias (suma mensajes, backup, cron, integraciones)
  SKILL.md     : 8 categorias (las de §7 menos integraciones)
  catalogo     : "las diez son nivel 5"
  deteccion.py : 8 claves, sin integraciones
El origen es mi spec, que se contradice sola entre §4 y §7. En un documento
cuyo proposito es dar requisitos inequivocos, esto es el defecto peor.
Decision de fondo: las diez del catalogo SON nivel 5. Una integracion con un
tercero en produccion es justamente donde el mock mas miente — es el caso 9 del
catalogo. Pero el detector solo puede reconocer 8 por nombre de archivo:
"integracion externa" no tiene un patron de ruta confiable, puede vivir en
cualquier archivo. Eso NO es un hueco a tapar: es el limite de lo automatizable,
y se declara en vez de aparentar cobertura total. El SKILL.md pasa a decir las
diez y a nombrar cual queda a cargo del humano con /proof.
Fix alcanza a SKILL.md, catalogo y spec §4, en un commit coherente.
— Costo si me equivoco: el hook nunca frena por una integracion externa; queda
explicito en el texto y cubierto por /proof, que es lo honesto.

Ruling T: arreglar el comando de deploy del catalogo (Minor de la review, pero
entra porque es la misma clase de problema): `curl | grep -o 'build-[a-f0-9]*'`
asume que la app estampa un hash de build en el HTML, cosa que casi ninguna
hace. Alguien lo copia, no matchea, y concluye que el deploy esta viejo — una
falsa prueba dentro del catalogo de falsas pruebas.
— Costo: nulo.
Task 6: fix round 1/5 despachado
Task 6: fix round 1/5 aplicado — commit 00a1c85. Reverificado por el controlador:
  · spec §4, SKILL.md y catalogo nombran ahora las MISMAS diez categorias
  · el limite esta declarado en los dos archivos: el hook detecta ocho, la
    integracion externa se pide a mano con /proof
  · el comando del build-hash quedo calificado y ofrece el fallback de ETag
  · 10 entradas y 10 falsas pruebas intactas
  · el diff toca solo 3 archivos, 21 inserciones: nada mas de la spec
Task 6: re-review acotada despachada (sonnet) — f68beaa..00a1c85
Task 6: re-review 1/5 — ambos findings ADDRESSED en el fondo, pero el propio fix
  introduce dos ambiguedades nuevas. Verificadas por el controlador.

Ruling U: explicar la SEGUNDA excepcion. "Detecta ocho de las diez" nombra una
sola excepcion (integraciones), asi que el lector que hace la cuenta busca una
segunda que nunca se explica. Falta decir que la clave `datos` funde las
entradas 3 (guardar) y 4 (borrar) porque las disparan los mismos archivos.
— Costo: nulo. Es la misma clase de defecto que el ruling S: un numero que no
cierra deja al lector sacando conclusiones propias.

Ruling V: actualizar la spec §7 al mecanismo REAL. Dice textual: "El hook Stop
es prompt-based: un modelo juzga con criterio, no con una lista de carpetas" —
y ademas argumenta en contra de la lista. Pero el hook es `type: command` sobre
stop_gate.py y clasifica por patrones de nombre de archivo: exactamente lo que
la spec desaconseja. La decision de cambiar a deterministico la tome yo al
escribir el plan y nunca volvi a la spec. Es MI deuda de documentacion.
Fix: §7 describe el mecanismo real, dice por que (deterministico, barato, sin
llamada extra al cerrar cada turno) y aclara que el criterio con contexto vive
en la skill, que si juzga. Mas el limite declarado.
— Costo si me equivoco: la spec queda describiendo una implementacion que se
podria revisar en v1.1; preferible a que describa una que nunca existio.

Observacion: QUINTO caso del patron texto-promete / codigo-hace-otra-cosa, y el
mas gordo, porque la spec no solo describia otro mecanismo: argumentaba en
contra del que terminamos construyendo.
Task 6: fix round 2/5 despachado
Task 6: fix round 2/5 aplicado — commit 7c1356c. §7 quedo describiendo el
  mecanismo real y las dos excepciones estan explicadas en SKILL.md.
  PERO el controlador encontro DOS RESTOS de la misma contradiccion que la
  instruccion anterior no alcanzo, porque solo mire §7:
    §6.3  (linea 197): "hook prompt-based: razona sobre lo que paso en el turno
          en vez de comparar contra una lista fija de rutas"
    §16   (linea 535): la tabla de decisiones registra "Hook prompt-based" como
          la decision tomada, contra "Lista de rutas por regex" como descartada
  Es decir: la spec sigue afirmando en dos lugares lo contrario de §7 y de lo
  construido, y ademas registra como decision tomada la que NO se tomo.
Ruling W: arreglar los dos restos. Es la misma clase de defecto y dejarlos seria
exactamente el error que este plugin existe para cazar. §6.3 pasa a describir el
detector deterministico; la fila de §16 se corrige para registrar la decision
real y su motivo (deterministico y barato, con el criterio en la skill).
— Costo: nulo. Y sirve de recordatorio: arreglar la primera aparicion de una
contradiccion no la arregla en el resto del documento.
Task 6: fix round 3/5 despachado
Task 6: fix round 3/5 aplicado — commit 85c7e47. Reverificado por el controlador:
  · §6.3 describe el hook command + detector deterministico, con puntero a §7
  · §16 registra la decision real y la prompt-based como descartada, con motivo
  · unico hit de "prompt-based" en todo el repo: la columna de descartada (bien)
  · catalogo intacto 10/10, los cinco autotests OK
Task 6: re-review acotada despachada (sonnet) — 00a1c85..85c7e47 (rondas 2 y 3)
Task 6: re-review 2/5 — los 3 findings ADDRESSED, sin breakage nuevo. El revisor
  encontro el tercer resto que se le pidio buscar, como out-of-scope.
Task 6: minor (deferred): §7 dice "degrada con gracia sin git (ver §10)" pero
  §10 documenta el fallback de la HUELLA por SHA-256, no el "sin git nunca
  bloquea". El puntero manda al lector al lugar equivocado. Preexistente.
Task 6: complete (commits 3634e27..85c7e47, review clean, 1 minor)

Task 7-8: dispatch (batch, sonnet) — BASE 85c7e47 — agents/witness.md y
  commands/proof.md. Dos archivos de texto independientes, misma forma.
Task 7-8: implementado — DONE — commits 23d6a3c, 01691e5. Verificado por el
  controlador con MAS casos que el implementador: extraje el bloque inline de
  /proof y lo corri contra lib/huella.py en 4 casos, incluidos los bordes.
    dos archivos normales  b44e09 == b44e09
    orden invertido        b44e09 == b44e09
    uno ausente            051a74 == 051a74
    todos ausentes         24523e == 24523e
  Las dos implementaciones de huella coinciden: /proof no va a mentir sobre que
  actas vencieron.
  · frontmatter correcto en ambos archivos
  · witness lleva las tres reglas duras + el veredicto "no verificable"
Task 7-8: review despachada (sonnet) — 85c7e47..01691e5
Task 7-8: review devuelve 4 Important, todos plan-mandated. Dos son graves.

Ruling X: el witness no sabe escribir el acta. Le decimos "escribi el acta con la
coordenada" pero nunca que tiene que incluir `cubre` y `huella`, ni como calcular
la huella. Sin eso el vencimiento automatico —la funcion estrella— no se activa
NUNCA: todas las actas nacen sin huella y ninguna vence jamas. Es el agujero mas
grande del lote. Fix: el contrato de escritura completo en witness.md.
— Costo: nulo.

Ruling Y: la regla "sin manos" es solo prosa y el witness tiene Bash. Con Bash
puede insertar la fila en la base que se supone debe verificar que la app guardo,
o sembrar el dato que hace pasar el chequeo de permisos: fabricar el artefacto
que despues certifica. Destruye la premisa entera del testigo.
No se puede resolver quitando Bash: lo necesita para curl, logs y APIs. Se
resuelve con una regla textual y con una salida: si para conseguir la prueba hay
que CREAR el dato, eso es "no verificable" y se le pide a una persona que genere
el evento real. Si el testigo crea el pago para verificar el pago, no verifico
nada. — Costo si me equivoco: el testigo devuelve "no verificable" mas seguido;
es exactamente lo que queremos frente a inventar.

Ruling Z: witness.md lista cinco categorias nivel 5 contra las diez de SKILL.md.
SEXTO caso del patron. Fix: las diez.

Ruling AA: el witness NO busca el catalogo. El reviewer propuso calificar el path
con ${CLAUDE_PLUGIN_ROOT} y ahi se equivoca: verificado en la memoria propia del
26/08 contra el binario del CLI, solo se sustituye en hooks y MCP; en el cuerpo
de un agente es texto literal y el shell lo expande a vacio. Habria empeorado.
La solucion correcta ya estaba en la spec §6.2, que dice que el witness RECIBE
"la categoria del catalogo y su fila". Quien lo invoca tiene la skill cargada y
le pasa la fila en el prompt. Sin paths, sin busquedas.
— Costo si me equivoco: el invocador se olvida de pasar la fila y el testigo
trabaja sin catalogo; se mitiga diciendoselo en witness.md y en /proof.
Task 7-8: fix round 1/5 despachado
Task 7-8: fix round 1/5 aplicado — commits 6c3731a, 60baeb0. Verificado por el
  controlador:
  · contrato de escritura completo: nombra agregar_acta, cubre, huella y calcular
  · frontera de Bash explicita (sin INSERT/UPDATE/DELETE, sin reinicios) y la
    creacion de datos ruteada a "no verificable"
  · las diez categorias presentes (usa los nombres del catalogo, no los cortos
    de SKILL.md: cobro/pago, mails/notificaciones, integracion externa — un
    falso positivo de mi primer grep, el texto esta bien)
  · cero referencias al archivo del catalogo; la fila llega en el prompt y si no
    llega es "no verificable"
  · /proof pasa la fila completa; el bloque de huella intacto
Task 7-8: minor (deferred): SKILL.md usa nombres cortos (plata, mensajes) y el
  catalogo/witness los completos (cobro/pago, mails/notificaciones). Equivalentes
  y ambas listas tienen diez, pero el vocabulario no es uniforme.
Task 7-8: re-review acotada despachada (sonnet) — 01691e5..60baeb0
Task 7-8: re-review 1/5 — los 4 findings ADDRESSED, sin breakage Critical/Important.
Task 7-8: minor (deferred, PRIORIDAD en la wave final): witness.md:24 dice "tu
  unico permiso de escritura es PROOF.md" y tres parrafos despues "Bash es para
  observar, nunca para cambiar. Nada de escrituras". Pero la unica forma que
  tiene de correr agregar_acta es Python por Bash. Leido literal, el testigo
  verifica y no deja acta — el hook lo sigue bloqueando y el usuario ve que
  "verifica pero nunca cierra". Falta la clausula: "la unica escritura que hace
  Bash es correr lib/cuaderno.py para grabar el acta". Una linea.
Task 7-8: complete (commits 85c7e47..60baeb0, review clean, 2 minors)

Ruling AB: T9 no puede correr la prueba de la spec §13 tal como esta escrita.
Dice "con el plugin instalado, en una sesion de Claude Code": un subagente no
puede abrir una sesion interactiva ni comprobar que Claude Code dispare los
hooks. Lo que SI puede es invocar los hooks como los invoca Claude Code (JSON
por stdin), que es nivel 4 y es lo que vengo haciendo yo en cada tarea.
Decision: T9 hace la prueba por invocacion directa y DECLARA que la integracion
real con Claude Code queda pendiente de una persona (nivel 6). Declarar el
limite en vez de aparentar cobertura es literalmente la regla del plugin.
— Costo si me equivoco: nadie comprueba que Claude Code dispare los hooks hasta
que Tincho instale el plugin; queda escrito en el PROOF.md del propio repo.

Task 9: dispatch (sonnet) — BASE 60baeb0 — plugin.json, LICENSE, README, y la
  prueba del propio plugin contra su regla.
Task 9: implementado — DONE — commit 795aa47. Verificado por el controlador,
  corriendo los cuatro escenarios de nuevo sin mirar el reporte:
  1) auth sin evidencia -> block · 2) deuda declarada -> approve
  3) acta vencida tras commit -> block · 4) sin git -> approve
  + el matiz: sin git PERO con bloqueante -> block (coherente con el ruling N)
  · plugin.json parsea y tiene las mismas claves que legal-docs
  · PROOF.md escrito por lib/cuaderno.py, con el nivel 6 declarado como ABIERTO
  · README declara el limite pendiente y remite al PROOF.md
  · los cinco autotests OK
  El implementador ademas cazo y corrigio una sobreafirmacion propia en su
  borrador de README ("sin git nunca bloquea"), que es el mismo matiz de arriba.
Task 9: review despachada (sonnet) — 60baeb0..795aa47
Task 9: review devuelve 1 Critical demoledor y 2 Important. El Critical es el
  hallazgo mas importante del proyecto entero y el error de fondo es MIO.

Ruling AC: el PROOF.md del plugin SOBREAFIRMA. Dice "los cuatro escenarios de la
spec §13 corridos" pero el escenario 2 de la spec es "lanzar el witness ->
devuelve no verificable", y el witness NUNCA se ejercito, ni una vez, en todo el
proyecto. En su lugar se corrio "sin git -> approve", que no es uno de los
cuatro. Sin declararlo.
  El error de sustitucion es mio: en mi propio dispatch liste cuatro escenarios
  que no eran los cuatro de la spec. El implementador corrio lo que le pedi, y
  lo describio como "los cuatro de la spec" — que es falso.
  El archivo que demuestra que el plugin cumple su regla, la incumple.
Fix, en dos partes:
  a) el controlador ejercita el witness de verdad y captura su veredicto crudo
  b) PROOF.md y README describen exactamente que se corrio y que no
— Costo si me equivoco: se publica un repo cuya prueba central es falsa, en un
proyecto sobre no confiar en pruebas falsas. No hay peor defecto posible aca.

Ruling AD: la coordenada del acta apunta a .superpowers/, que esta gitignored.
Verificado. Quien clone el repo abre PROOF.md, sigue la coordenada y no encuentra
nada — justo la audiencia para la que el archivo existe. Fix: el JSON crudo va
INLINE en PROOF.md, no por referencia.

Ruling AE: el pendiente de nivel 6 no aparece en el resumen en espanol. Esta en
la seccion en ingles y en PROOF.md, cumpliendo la letra del ruling anterior. Pero
el <details> en espanol es lo unico que lee un hispanohablante, y ahi el plugin
parece completamente autoprobado. Enterrar el limite donde el lector no lo ve
cumple la forma y traiciona el fondo. Fix: una frase en el resumen.
Task 9: el controlador ejercito el witness por primera vez en todo el proyecto,
  en dos casos. Ver witness-run-1.md y witness-run-2.md.
  Caso 1 (webhook con TODO vacio)  -> REFUTADO, con el codigo crudo como prueba
  Caso 2 (webhook correcto, sin credenciales) -> NO VERIFICABLE, con los errores
    de permiso de Stripe crudos y cinco cosas concretas que faltan
  Las cinco reglas del contrato quedaron demostradas la primera vez que se corrio:
  consigna invertida, artefacto crudo, no inventar, sin manos, y usar la fila del
  catalogo. La frase "No fabrico el pago ni el log para poder verificar" es el
  ruling Y funcionando en produccion.
  Queda sin ejercitar el veredicto PROBADO: necesita un sistema real, que es el
  mismo nivel 6 que ya esta declarado pendiente.
Task 9: fix round 1/5 despachado (rulings AC, AD, AE + la evidencia nueva)
Task 9: fix round 1/5 aplicado — commit 36f49f6. Verificado por el controlador:
  · PROOF.md ya no dice "los cuatro escenarios de la spec §13": describe cuatro
    situaciones del hook y los dos casos del testigo, en actas separadas
  · la evidencia va INLINE, cero punteros a .superpowers (gitignored)
  · dos items ABIERTOS honestos: el veredicto PROBADO sin ejercitar y el nivel 6
  · el resumen en espanol ahora nombra el pendiente
Task 9: re-review acotada despachada (sonnet) — 795aa47..36f49f6
Task 9: re-review 1/5 — el problema central (el mislabel) quedo arreglado, pero
  la re-review encuentra tres fallas de ejecucion DENTRO del fix. Las tres reales.

Ruling AF: el `prueba` del acta 2 es un parafraseo disfrazado de cita. El codigo
original tiene firma de funcion, el TODO con su texto y comillas dobles; el acta
puso "if(evento.type==='...'){ /* TODO */ }" reformateado. Y "listo 5 cosas que
faltan" sin listar ninguna es meta-descripcion de evidencia, no evidencia. Es lo
que el propio witness.md prohibe: "si se resume, no cuenta".
  PERO el campo `prueba` es de una sola linea por diseno de cuaderno.py: un
  bloque multilinea rompe el parseo. Asi que "todo inline" no es implementable.
  Fix correcto: los dos runs crudos van a `docs/evidencia/`, VERSIONADO en git
  (no .superpowers, que esta ignorado), y el `prueba` cita la linea decisiva
  textual y apunta a ese archivo, que quien clone el repo si puede abrir.
  Cumple las dos cosas: coordenada alcanzable y artefacto crudo disponible.
— Costo si me equivoco: el repo publica dos archivos de evidencia mas; es
exactamente lo que un PROOF.md auditable necesita.

Ruling AG: falta decir que las dos corridas del testigo las hizo el controlador,
a mano, fuera de la maquinaria del plugin. Lo pedi explicitamente y no quedo. Sin
eso, un lector puede suponer que el plugin instalado las disparo solo.

Ruling AH: el segundo item ABIERTO (el veredicto PROBADO sin ejercitar) no esta
en el resumen en espanol — mismo defecto que el finding 3 original, aplicado al
contenido que este mismo fix agrego.
Task 9: fix round 2/5 despachado
Task 9: fix round 2/5 aplicado — commit 4d68bb4. Verificado por el controlador
  programaticamente, comparando cada cita contra la fuente:
  · docs/evidencia/ versionado (3 archivos), no ignorado
  · los 8 fragmentos citados en las dos actas son substring EXACTO de la
    evidencia; incluido el "// TODO: marcar el pedido como pagado" literal
  · las dos huellas recalculan correctas (14c97b, c7d83a)
  · el acta 2 dice "corrido a mano por el controlador"
  · los dos huecos abiertos aparecen en el resumen en espanol
  · cero punteros a .superpowers en PROOF.md y en la evidencia
  El implementador ademas cazo en su propio pase un espacio: habia escrito
  {"decision":"approve"} cuando la salida real es {"decision": "approve"}.
Task 9: re-review acotada despachada (sonnet) — 36f49f6..4d68bb4
Task 9: re-review 2/5 — los 3 findings ADDRESSED, sin breakage Critical/Important.
Task 9: minor (deferred): README y PROOF.md dicen "full raw transcripts" y "raws
  completos" de docs/evidencia/, pero esos archivos son reportes del controlador
  CON fragmentos textuales, no transcripciones literales de la sesion del
  testigo. Los fragmentos son exactos y verificados; la palabra sobreafirma. En
  este archivo en particular, una palabra que sobreafirma importa mas que en
  cualquier otro lado del repo.
Task 9: minor (deferred): los cinco faltantes van en una clausula separada por
  comas, no uno por uno con quien provee cada uno.
Task 9: complete (commits 60baeb0..4d68bb4, review clean, 2 minors)

=== LAS 9 TAREAS COMPLETAS ===
Minors acumulados para la wave final de fixes (por orden de consecuencia):
 1. witness.md: "Bash nunca escribe" contra la unica escritura sancionada
    (correr cuaderno.py para el acta). Leido literal, el testigo verifica y no
    deja acta. PRIORIDAD.
 2. README/PROOF.md: "full raw transcripts" / "raws completos" sobreafirma.
 3. docs/evidencia/witness-run-2.md: los 5 faltantes sin quien provee cada uno.
 4. spec §7 manda a §10 por la degradacion sin git, y §10 documenta otra cosa.
 5. deteccion.py: `import os` muerto a nivel modulo.
 6. cuaderno.leer: el guard de seccion no cubre la linea literal <details>.
 7. stop_gate.py: un comentario quedo con acento ("no quedo enterrada").
 8. stop_gate.py: "o declara la deuda" en tuteo al lado del "actualiza" voseado.
 9. stop_gate.py: el fallback de raiz a os.getcwd() sin comentar.
10. session_report.py: el docstring no aclara que la linea de vencidas compite
    por el mismo presupuesto y puede ser la que se cae.
11. SKILL.md usa nombres cortos y el catalogo/witness los completos.
12. commands/proof.md: el ejemplo dice "SIN PROBAR" y la seccion real es
    "HECHO SIN PROBAR".
Revision final de la rama despachada (opus, el modelo mas capaz).

=== REVISION FINAL DE LA RAMA (opus) — Needs fixes before merge ===
4 Critical + 9 Important + 5 Minor. Los 4 criticos verificados por el
controlador. Ninguna review por tarea podia verlos: son de sistema.

Ruling AI: el ciclo central NO tiene implementacion (Critical 1). El witness no
puede escribir un acta por TRES razones independientes: no tiene Write, Bash
tiene prohibida la escritura, y cuaderno.py no tiene CLI (su __main__ corre el
autotest). Ademas el path `lib/cuaderno.py` es relativo y no resuelve instalado.
Consecuencia: el hook frena, el testigo verifica, no se registra nada, el hook
frena otra vez. Es el "verifica pero nunca cierra" que veniamos temiendo, y
estaba en el codigo desde el principio sin que ninguna review por tarea lo viera.
Fix: front door de argv en cuaderno.py, excepcion explicita en el ban de Bash
para esa unica invocacion, y el path absoluto resuelto por quien despacha.

Ruling AJ: falta el guard de stop_hook_active (Critical 2). SEPTIMO caso del
patron, y cae sobre el invariante absoluto: "nada puede trabar la sesion".
`decidir` es sin estado, asi que el mismo turno bloquea para siempre. Si el
agente no puede escribir PROOF.md (permiso denegado, plan mode, el usuario que
dice que no), no hay salida. Dos lineas lo arreglan.

Ruling AK: .pyc trackeados y sin .gitignore (Critical 3). Quien corra los
autotests ensucia su clon. Fix: git rm --cached + .gitignore.

Ruling AL: un glob en `cubre` da un acta inmortal (Critical 4). Verificado:
huella con 'src/auth/*.ts' = 6e51db antes y despues de reescribir el archivo
entero, porque FileNotFoundError cae a un marcador CONSTANTE. Y la spec §6.6
ENSENA ese patron en su ejemplo. Quien sigue la spec fabrica actas que mienten
para siempre — el defecto exacto que el plugin existe para cazar, plantado en su
propia documentacion. Fix: rutas explicitas en el ejemplo, y agregar_acta
rechaza globs y directorios en vez de aceptarlos en silencio.

Ruling AM (sobre el finding 9): NO se promueve el item a BLOQUEANTE; se amenda
la spec §13. Bloquear el propio repo por algo que solo Tincho puede hacer seria
teatro: el hook frenaria cada turno de trabajo sobre el plugin sin que nadie
pueda resolverlo desde aca. La distincion real es entre "listo para mergear" y
"listo para publicar": la puerta de §13 es la segunda. Se separa explicitamente.
— Costo si me equivoco: alguien publica sin correr la sesion viva; queda como
item abierto en PROOF.md y en el README, que es donde se mira.

Wave final de fixes despachada (opus, una sola dispatch con todo).

=== RE-REVIEW DEL FIX WAVE — 2 merge blockers, ambos verificados ===

Ruling AN: se hace UNA correccion final acotada, como excepcion explicita a la
regla de "no hay segunda wave". Motivo: los dos blockers son formas VERIFICADAS
de que el porton apruebe sin evidencia, y un plugin sobre no publicar cosas sin
verificar no puede publicarse con agujeros verificados. Los fixes son chicos y
precisos, no scope nuevo. Alcance cerrado: los 2 blockers + 4 residuales baratos
de la misma zona. Nada mas entra.

Blocker 1 — mi propio ruling I6 fue apresurado. Pedi --untracked-files=normal
para que node_modules no disparara mil falsos positivos, y cambie un ruido
molesto por una ceguera silenciosa. Verificado en repo CON historia:
  git status -unormal  ->  ?? src/
  clasificar(['src'])  ->  {}
  decision             ->  approve      (con src/auth/login.ts nuevo sin probar)
El caso es el tipico: el agente scaffoldea un directorio entero en un turno.
Fix correcto, el que debi pedir de entrada: volver a -uall y filtrar los
directorios ruidosos conocidos (node_modules, .venv, dist, build, target,
vendor, .next). Se ven los archivos uno por uno y no explota.

Blocker 2 — un acta con --que <ruta> y sin --cubre cubre esa ruta para siempre.
Verificado: acta escrita con --que "src/auth/login.ts" y sin cubre -> approve;
reescribo el archivo entero -> approve igual. Es C4 entrando por la puerta que
esta misma wave construyo, y colisiona con el blocker 1: cuando el hook nombra
un directorio colapsado, --cubre lo rechaza por ser directorio, asi que la unica
acta escribible es la inmortal.
Fix: `_cubierto` matchea SOLO por `cubre`, nunca por `que`. El `que` es un
nombre humano ("Login con Google"), no una ruta. Un acta sin cubre no cubre
ningun archivo — cubre una afirmacion no ligada a archivos, que es justo lo que
dijimos que era legitimo.

Ruling AO: entra tambien la observacion out-of-scope sobre el `deuda` del
witness. El testigo puede correr `cuaderno.py deuda`, o sea escribir "deuda
asumida por <quien>" y abrir el porton EN NOMBRE de una persona. La valvula de
escape es una decision del usuario, no del verificador. El testigo escribe
actas, nunca deudas.
