# `stop_gate.py` ejercitado — seis situaciones reales

Corrido por el implementador, invocando `hooks/stop_gate.py` exactamente como
lo invoca Claude Code: un JSON por stdin (`{"cwd": "<repo>"}`), la decisión
leída cruda de stdout. Cada repo es un `mktemp -d` con `git init` real (o sin
git, en la situación D), con `git config user.name/user.email` locales para no
depender de una identidad de git configurada en la máquina.

Estas son las **seis situaciones que se ejercitaron de verdad** — no son
"los escenarios de la spec §13" (ver PROOF.md y README para el porqué de esa
distinción).

Nota sobre el intérprete: en la máquina del autor el comando se corrió como
`uv run python3` (un envoltorio de entorno propio de esa máquina). Se
transcribe abajo como `python3`, que es lo que corre el usuario y lo único que
pide el plugin: los scripts son stdlib pura, sin dependencias externas.

Nota sobre lo que ve el detector: el hook lee `git status --porcelain
--untracked-files=all`. Con el default de git (`=normal`) **cualquier** carpeta
enteramente sin trackear se colapsa en una sola línea —`?? src/`—, también en un
repo con historia, y el hook quedaba ciego a un `src/auth/login.ts` recién
creado. Con `=all` se ven los archivos uno por uno, y el ruido (`node_modules`,
`.venv`, `dist`, `build`, `target`, `vendor`, `.next`, `__pycache__`, `.git`) se
descarta después por nombre de carpeta. En A y E abajo, `src/auth/` es una
carpeta **nueva y entera** en un repo que ya tiene un commit: es exactamente el
caso que antes se aprobaba sin evidencia.

## A — carpeta `src/auth/` nueva y entera, sin acta → bloquea

```
$ git log --oneline | wc -l          # el repo YA tiene historia
       1
$ mkdir -p src/auth && echo "export const login = () => {}" > src/auth/login.ts
$ git status --porcelain -unormal
?? src/
$ git status --porcelain -uall
?? src/auth/login.ts

$ echo '{"cwd": "<repo>"}' | python3 hooks/stop_gate.py
{"decision": "block", "reason": "Se tocó código caro sin evidencia observable desde afuera:\n  · Login / auth (nivel 5): src/auth/login.ts\n\nNivel 5 significa que un tercero sin interés lo confirma: el cargo en el panel del proveedor, el mail que llegó de verdad, el 401 sin token. Un test propio no alcanza.\n\nOpciones:\n1. Lanzá el subagente `witness` para conseguir la prueba y escribir el acta en PROOF.md.\n2. Si el usuario decide seguir sin probar, registrá la deuda en PROOF.md con su nombre y la fecha. Declararla alcanza para cerrar."}
```

## E — la misma situación, con `stop_hook_active: true` → aprueba igual

El hook ya frenó este turno una vez. La invariante manda: no se vuelve a
frenar, pero lo que quedó sin probar se dice, no se pierde.

```
$ echo '{"cwd": "<repo>", "stop_hook_active": true}' | python3 hooks/stop_gate.py
{"decision": "approve", "systemMessage": "proof-first: ya frené este turno una vez y no lo vuelvo a frenar. Cierra igual, pero esto quedó sin evidencia y sin deuda declarada:\nSe tocó código caro sin evidencia observable desde afuera:\n  · Login / auth (nivel 5): src/auth/login.ts"}
```

## B — misma situación, deuda declarada con la CLI del cuaderno → aprueba

```
$ python3 lib/cuaderno.py deuda <repo>/PROOF.md --que "src/auth/login.ts" \
    --motivo "sin nivel 5" --quien "Tincho" --fecha "27/08"
deuda registrada en <repo>/PROOF.md: src/auth/login.ts — asumida por Tincho 27/08

$ echo '{"cwd": "<repo>"}' | python3 hooks/stop_gate.py
{"decision": "approve"}
```

## C — acta escrita por la CLI, después el archivo cambia y se commitea → vuelve a bloquear, acta vencida

El ciclo completo: bloqueo → se labra el acta con el mismo comando que corre el
testigo → el hook aprueba → cambia el código que el acta cubría → el acta vence
sola y el hook vuelve a bloquear. El `--que` es el nombre humano de la
afirmación; los archivos van en `--cubre`, que es lo que hace vencer el acta.

```
$ python3 lib/cuaderno.py acta <repo>/PROOF.md --que "El login rechaza sin token" \
    --nivel 5 --prueba "401 en /api/privado sin cookie" \
    --cubre "src/auth/login.ts" --fecha "27/08"
acta escrita en <repo>/PROOF.md: El login rechaza sin token · nivel 5 · cubre 1 archivo(s) · huella 1b0029

$ echo '{"cwd": "<repo>"}' | python3 hooks/stop_gate.py
{"decision": "approve"}

$ echo "export const login = (u) => ({admin:true})" > src/auth/login.ts && git add -A && git commit -q -m cambio
$ echo '{"cwd": "<repo>"}' | python3 hooks/stop_gate.py
{"decision": "block", "reason": "Estas actas quedaron vencidas porque cambiaron los archivos que cubrían:\n  · El login rechaza sin token (cubría src/auth/login.ts)\n\nVolvé a verificarlas con el subagente `witness` y actualizá el acta, o declará la deuda en PROOF.md con quién lo decidió."}
```

## D — mismo archivo sin probar, sin `git init` en absoluto → aprueba igual

```
$ echo '{"cwd": "<repo-sin-git>"}' | python3 hooks/stop_gate.py
{"decision": "approve"}
```

## F — el acta inmortal se rechaza

Un `--que` con forma de ruta y sin `--cubre` cubriría ese archivo para siempre,
sin huella detrás que la haga vencer. El comando no la escribe:

```
$ python3 lib/cuaderno.py acta <repo>/PROOF.md --que "src/auth/login.ts" --nivel 5 --prueba "confia en mi"
proof-first: «src/auth/login.ts» parece una ruta de archivo y el acta no cubre ningún archivo. Un acta así nunca vencería: pasá los archivos en --cubre, o nombrá la afirmación en términos humanos ("El login rechaza sin token").
$ echo $?
2
```

Y el hook tampoco la acepta si aparece en un `PROOF.md` escrito por otro lado:
`_cubierto` solo mira `cubre`, nunca el `que` (autotest en `stop_gate.py`).
