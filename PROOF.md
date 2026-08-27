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
   prueba: stop_gate.py invocado con JSON por stdin, 4 situaciones: auth sin acta -> {"decision":"block","reason":"...Login / auth (nivel 5): src/auth/login.ts..."} · con deuda declarada -> {"decision":"approve"} · acta vencida tras commit -> {"decision":"block","reason":"...quedaron vencidas porque cambiaron los archivos...src/auth/login.ts..."} · sin git -> {"decision":"approve"}
   cubre: hooks/stop_gate.py, lib/deteccion.py, lib/cuaderno.py, lib/huella.py · huella: 14c97b

✅ 27/08 · El testigo (witness) en dos casos reales: REFUTADO y NO VERIFICABLE · nivel 4
   prueba: witness corrido 2 veces: caso 1 REFUTADO sobre handler vacio "if(evento.type==='checkout.session.completed'){ /* TODO */ } return new Response('ok')", hallazgo propio: firma del webhook nunca verificada · caso 2 NO VERIFICABLE sobre el mismo webhook ya corregido, sin credenciales: mcp__stripe__stripe_api_read GetCharges -> "Error: Your API key does not have the required permissions for 'GetCharges'.", listo 5 cosas que faltan y quien las provee, "No fabrico el pago ni el log para poder verificar"
   cubre: agents/witness.md · huella: c7d83a

</details>
