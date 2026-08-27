# `stop_gate.py` ejercitado — cinco situaciones reales

Corrido por el implementador, invocando `hooks/stop_gate.py` exactamente como
lo invoca Claude Code: un JSON por stdin (`{"cwd": "<repo>"}`), la decisión
leída cruda de stdout. Cada repo es un `mktemp -d` con `git init` real (o sin
git, en la situación D), con `git config user.name/user.email` locales para no
depender de una identidad de git configurada en la máquina.

Estas son las **cinco situaciones que se ejercitaron de verdad** — no son
"los escenarios de la spec §13" (ver PROOF.md y README para el porqué de esa
distinción).

Nota sobre el intérprete: en la máquina del autor el comando se corrió como
`uv run python3` (un envoltorio de entorno propio de esa máquina). Se
transcribe abajo como `python3`, que es lo que corre el usuario y lo único que
pide el plugin: los scripts son stdlib pura, sin dependencias externas.

Nota sobre el estado inicial: en A, C y E el archivo de auth se commitea antes
de modificarlo. `git status` (con `--untracked-files=normal`, el default)
colapsa una carpeta nueva entera en una sola línea, así que un repo recién
creado y sin ningún commit no muestra los archivos uno por uno. Con historia
—el caso real de cualquier proyecto— sí.

## A — archivo de auth tocado sin probar, sin acta → bloquea

```
$ echo "export const login = (u) => u" > src/auth/login.ts     # sobre la versión commiteada
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

Este es el ciclo completo: bloqueo → se labra el acta con el mismo comando que
corre el testigo → el hook aprueba → cambia el código que el acta cubría → el
acta vence sola y el hook vuelve a bloquear.

```
$ python3 lib/cuaderno.py acta <repo>/PROOF.md --que "src/auth/login.ts" \
    --nivel 5 --prueba "401 sin token en /api/privado" \
    --cubre "src/auth/login.ts" --fecha "27/08"
acta escrita en <repo>/PROOF.md: src/auth/login.ts · nivel 5 · cubre 1 archivo(s) · huella 1b0029

$ echo '{"cwd": "<repo>"}' | python3 hooks/stop_gate.py
{"decision": "approve"}

$ echo "export const login = (u) => ({ u })" > src/auth/login.ts && git add -A && git commit -q -m cambio
$ echo '{"cwd": "<repo>"}' | python3 hooks/stop_gate.py
{"decision": "block", "reason": "Estas actas quedaron vencidas porque cambiaron los archivos que cubrían:\n  · src/auth/login.ts (cubría src/auth/login.ts)\n\nVolvé a verificarlas con el subagente `witness` y actualizá el acta, o declará la deuda en PROOF.md con quién lo decidió."}
```

## D — mismo archivo sin probar, sin `git init` en absoluto → aprueba igual

```
$ echo '{"cwd": "<repo-sin-git>"}' | python3 hooks/stop_gate.py
{"decision": "approve"}
```
