# PROOF

Cuaderno de obra. Lo vivo arriba, lo probado plegado abajo.
Generado y mantenido por proof-first.

## 🔴 BLOQUEANTE

## ⬜ ABIERTO
- Confirmar que Claude Code dispara los hooks Stop y SessionStart de este plugin en una sesión interactiva real (nivel 6) — la evidencia de arriba prueba la lógica del hook invocándolo con el mismo contrato JSON que usa el harness, no que el harness lo dispare de verdad. Pendiente de una persona, en su propia sesión de Claude Code.

## ⚠️ HECHO SIN PROBAR

## ⏸️ POSTERGADO

<details>
<summary>▸ PROBADO (1)</summary>

✅ 27/08 · Los cuatro escenarios de la spec §13 corridos contra el hook Stop real · nivel 4
   prueba: JSON crudo de stdin/stdout de stop_gate.py en 4 repos temporales (mktemp -d + git init real) — ver .superpowers/sdd/2026-08-27-proof-first-v1/task-9-report.md
   cubre: hooks/stop_gate.py, hooks/session_report.py, lib/deteccion.py, lib/cuaderno.py, lib/huella.py · huella: 4893bf

</details>
