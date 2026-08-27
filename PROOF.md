# PROOF

Cuaderno de obra. Lo vivo arriba, lo probado plegado abajo.
Generado y mantenido por proof-first.

## 🔴 BLOQUEANTE

## ⬜ ABIERTO
- El tercer veredicto del testigo, PROBADO, no se ejercitó: hace falta un sistema real corriendo con credenciales reales — es el mismo hueco de nivel 6 de abajo, no uno nuevo.
- Confirmar que Claude Code dispara los hooks Stop y SessionStart de este plugin en una sesión interactiva real (nivel 6) — la evidencia de arriba prueba la lógica de los scripts invocándolos con el mismo contrato JSON que usa el harness, no que el harness los dispare de verdad. Pendiente de una persona, en su propia sesión de Claude Code.

## ⚠️ HECHO SIN PROBAR

## ⏸️ POSTERGADO

<details>
<summary>▸ PROBADO (2)</summary>

✅ 27/08 · El hook Stop en cuatro situaciones reales (no las 4 de la spec §13) · nivel 4
   prueba: A bloquea, reason incluye "Login / auth (nivel 5): src/auth/login.ts" · B aprueba con deuda declarada: {"decision": "approve"} · C vuelve a bloquear, reason incluye "quedaron vencidas porque cambiaron los archivos que cubrían" · D aprueba sin git: {"decision": "approve"} — las 4 corridas completas, crudas, en docs/evidencia/hook-runs.md
   cubre: hooks/stop_gate.py, lib/deteccion.py, lib/cuaderno.py, lib/huella.py · huella: 14c97b

✅ 27/08 · El testigo (witness), corrido a mano por el controlador, en dos casos reales: REFUTADO y NO VERIFICABLE · nivel 4
   prueba: Corrido a mano por el controlador, fuera de la maquinaria del plugin — caso 1: "VEREDICTO DEVUELTO: ❌ REFUTADO" sobre "// TODO: marcar el pedido como pagado", hallazgo propio: firma del webhook nunca verificada · caso 2: "VEREDICTO DEVUELTO: ⚠️ NO VERIFICABLE", "Error: Your API key does not have the required permissions for 'GetCharges'.", listó 5 cosas concretas y quién las provee — raws completos en docs/evidencia/witness-run-1.md y docs/evidencia/witness-run-2.md
   cubre: agents/witness.md · huella: c7d83a

</details>
