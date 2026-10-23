#!/usr/bin/env bash
# Corre los hooks REALES por la misma puerta que Claude Code (JSON por stdin),
# sobre repos temporales. No usa los autotests: mira solo lo que sale por stdout.
# Uso: bash docs/evidencia/correr-1.1.sh [python]   (por defecto: python3)
set -u
PY="${1:-python3}"
P="$(cd "$(dirname "$0")/../.." && pwd)"
stop() { echo "{\"session_id\":\"$2\",\"cwd\":\"$1\",\"stop_hook_active\":${3:-false}}" | $PY "$P/hooks/stop_gate.py"; echo; }
arranque() { echo "{\"session_id\":\"$2\",\"cwd\":\"$1\",\"source\":\"startup\"}" | $PY "$P/hooks/session_report.py"; echo; }
repo() { local d; d=$(mktemp -d); git -C "$d" init -q; git -C "$d" config user.email t@t; git -C "$d" config user.name T
         echo x > "$d/README.md"; git -C "$d" add .; git -C "$d" commit -qm base; echo "$d"; }

echo "### G · solo capturas, un informe y un test: aprueba"
d=$(repo); mkdir -p "$d/videos/snapshots" "$d/docs" "$d/tests"
touch "$d/videos/snapshots/f1.png" "$d/docs/reporte-logout.md" "$d/tests/test_login.py"
stop "$d" s1

echo "### H · aparece código caro de verdad sin commitear: frena"
mkdir -p "$d/src/auth"; echo a > "$d/src/auth/login.ts"; stop "$d" s1

echo "### D · sin git: aprueba"
stop "$(mktemp -d)" s1

echo "### L · NUEVO: el webhook de cobro se commitea dentro del turno: frena igual"
d=$(repo); arranque "$d" s2
mkdir -p "$d/functions/stripe-webhook"; echo 1 > "$d/functions/stripe-webhook/index.ts"
git -C "$d" add .; git -C "$d" commit -qm webhook
echo "(git status: '$(git -C "$d" status --porcelain)')"; stop "$d" s2

echo "### M · NUEVO: el agente no hace nada; segunda vuelta aprueba y lo anota"
stop "$d" s2 true
sed -n '/ABIERTO/,/SIN PROBAR/p' "$d/PROOF.md"; echo

echo "### N · NUEVO: el turno siguiente arranca limpio; la sesión nueva lo muestra"
stop "$d" s2
arranque "$d" s3

echo "### O · NUEVO: otra sesión en el mismo repo no hereda la marca de la primera"
d=$(repo); arranque "$d" s4
mkdir -p "$d/src/pagos"; echo 1 > "$d/src/pagos/cobro.ts"; git -C "$d" add .; git -C "$d" commit -qm cobro
echo "(sesión s4)"; stop "$d" s4
echo "(sesión s5, sin marca: sólo git status)"; stop "$d" s5

echo "### P · NUEVO: un nombre con tilde (src/sesión.ts) frena como auth"
d=$(repo); mkdir -p "$d/src"; echo 1 > "$d/src/sesión.ts"; stop "$d" s6

C="$P/lib/cuaderno.py"
echo "### I · el agente, solo, declara las dos deudas a confirmar: aprueba"
d=$(repo); mkdir -p "$d/src/auth" "$d/db"; echo a > "$d/src/auth/login.ts"; echo b > "$d/db/schema.sql"
$PY "$C" deuda "$d/PROOF.md" --que src/auth/login.ts --motivo "sin credenciales" --quien "Claude (a confirmar por Tincho)" --fecha 09/10
$PY "$C" deuda "$d/PROOF.md" --que db/schema.sql --motivo "sin base de prueba" --quien "Claude (a confirmar por Tincho)" --fecha 09/10
stop "$d" s7

echo "### J · parte de arranque de la sesión siguiente"
arranque "$d" s8

echo "### K · la persona confirma una; confirmar dos veces la misma falla"
$PY "$C" confirmar "$d/PROOF.md" --que src/auth/login.ts --quien Tincho; echo "exit $?"
$PY "$C" confirmar "$d/PROOF.md" --que src/auth/login.ts --quien Tincho; echo "exit $?"
grep "deuda" "$d/PROOF.md"; echo

echo "### C · acta escrita por la CLI aprueba; al cambiar y commitear el archivo, vence y frena"
d=$(repo); mkdir -p "$d/src/auth"; echo a > "$d/src/auth/login.ts"
$PY "$C" acta "$d/PROOF.md" --que "El login rechaza sin token" --nivel 5 --prueba "401 con curl sin token" --cubre src/auth/login.ts
stop "$d" s9
echo b > "$d/src/auth/login.ts"; git -C "$d" add .; git -C "$d" commit -qm cambio; stop "$d" s9

echo "### F · acta sin cubre cuyo que es una ruta: rechazada"
$PY "$C" acta "$d/PROOF.md" --que src/auth/login.ts --nivel 5 --prueba "confiá"; echo "exit $?"
