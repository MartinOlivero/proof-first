# `stop_gate.py` ejercitado — cuatro situaciones reales

Corrido por el implementador, invocando `hooks/stop_gate.py` exactamente como
lo invoca Claude Code: un JSON por stdin (`{"cwd": "<repo>"}`), la decisión
leída cruda de stdout. Cada repo es un `mktemp -d` con `git init` real (o sin
git, en la situación D), usando `git -c user.name=... -c user.email=...` para
no depender de una identidad de git configurada en la máquina.

Estas son las **cuatro situaciones que se ejercitaron de verdad** — no son
"los cuatro escenarios de la spec §13" (ver PROOF.md y README para el porqué
de esa distinción).

## A — archivo de auth sin probar, sin acta → bloquea

```
$ mkdir -p src/auth && echo "export const login = () => {}" > src/auth/login.ts
$ echo '{"cwd": "<repo>"}' | uv run python3 hooks/stop_gate.py
{"decision": "block", "reason": "Se tocó código caro sin evidencia observable desde afuera:
  · Login / auth (nivel 5): src/auth/login.ts

Nivel 5 significa que un tercero sin interés lo confirma: el cargo en el panel del proveedor, el mail que llegó de verdad, el 401 sin token. Un test propio no alcanza.

Opciones:
1. Lanzá el subagente `witness` para conseguir la prueba y escribir el acta en PROOF.md.
2. Si el usuario decide seguir sin probar, registrá la deuda en PROOF.md con su nombre y la fecha. Declararla alcanza para cerrar."}
```

## B — misma situación, deuda declarada en PROOF.md → aprueba

```
$ echo '{"cwd": "<repo>"}' | uv run python3 hooks/stop_gate.py
{"decision": "approve"}
```

## C — acta con huella vigente, archivo cambiado y **commiteado** → vuelve a bloquear, acta vencida

```
$ echo '{"cwd": "<repo>"}' | uv run python3 hooks/stop_gate.py
{"decision": "block", "reason": "Estas actas quedaron vencidas porque cambiaron los archivos que cubrían:
  · src/auth/login.ts (cubría src/auth/login.ts)

Volvé a verificarlas con el subagente `witness` y actualizá el acta, o declara la deuda en PROOF.md con quién lo decidió."}
```

## D — mismo archivo sin probar, sin `git init` en absoluto → aprueba igual

```
$ echo '{"cwd": "<repo>"}' | uv run python3 hooks/stop_gate.py
{"decision": "approve"}
```
