import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api, post } from "@/lib/api";
import type { Run, Session, Snapshot } from "@/lib/event-types";

type Item = { garment: string; quantity: number; weight_kg: string; service_code: string; observations: string; evidence_refs: string[] };
const serviceLabel = (code: string) => ({ wash_piece: "Lavado por prenda", wash_kg: "Lavado por kilo", iron_piece: "Planchado por prenda" }[code] || code);
const blankItem = (): Item => ({ garment: "", quantity: 1, weight_kg: "", service_code: "wash_piece", observations: "", evidence_refs: [] });

export function RetailPanel({ snapshot, session, ensureCase, onRun, onSaved, onError }: {
  snapshot?: Snapshot; session?: Session; ensureCase: (client?: string, title?: string) => Promise<string>;
  onRun: (run: Run) => void; onSaved: () => void; onError: (message: string) => void;
}) {
  const [mode, setMode] = useState("receive"), [existing, setExisting] = useState(snapshot?.case.client_id || ""),
    [name, setName] = useState(""), [contact, setContact] = useState(""), [items, setItems] = useState<Item[]>([blankItem()]),
    [evidence, setEvidence] = useState(""), [received, setReceived] = useState(false), [advance, setAdvance] = useState("0.00"),
    [paymentEvidence, setPaymentEvidence] = useState(""), [promised, setPromised] = useState(""),
    [address, setAddress] = useState(""), [day, setDay] = useState(""), [shift, setShift] = useState("manana"), [volume, setVolume] = useState(""),
    [busy, setBusy] = useState(false), [error, setError] = useState(""), [services, setServices] = useState<Record<string, { label: string; unit: string; price: string }>>({});
  const submission = useRef<{ key: string; id: string } | undefined>(undefined);
  useEffect(() => { api<{ services: typeof services }>("/retail/tariffs").then(x => setServices(x.services)).catch(e => onError(e.message)); }, []);
  const customer = existing ? { existing_id: existing } : { name, contact };
  const order = snapshot?.orders[0];
  const pickup = snapshot?.retail?.pickup_request;
  const canReceive = !order && (!pickup || pickup.status === "PICKED_UP");
  return <section className="space-y-4" aria-label="Atención al detalle">
    {error && <p className="error" role="alert">{error}</p>}
    <p className="notice text-sm">Datos sintéticos. El operador declara tareas físicas y cobros; el sistema calcula importes en PEN. Avisos en bandeja local.</p>
    {order ? <RetailOrderCard snapshot={snapshot!} onSaved={onSaved} onError={onError} /> : <>
      {pickup && <div className="review-card"><strong>Solicitud previa de recojo</strong><p>{pickup.id}</p><p>{pickup.status} · v{pickup.version}</p>
        {pickup.status === "SCHEDULED" && <MilestoneForm snapshot={snapshot!} actions={{ pickup_completed: "Declarar recojo realizado" }} version={pickup.version} onSaved={onSaved} onError={onError} />}
        {pickup.status === "REQUESTED" && <p>Solicita por chat «Coordina el recojo de esta solicitud» y elige una alternativa calculada.</p>}
      </div>}
      {canReceive && <form className="space-y-4" onSubmit={async e => {
        e.preventDefault(); if (busy) return; setBusy(true);
        try {
          const cid = await ensureCase(existing || undefined, mode === "receive" ? "Recepción en mostrador · sintética" : "Solicitud previa de recojo · sintética");
          const body = mode === "receive" ? { action: "receive", reception: { customer, received, receipt_evidence: evidence,
            channel: pickup ? "pickup" : "counter", ...(pickup ? { pickup_request_id: pickup.id } : {}),
            items: items.map(i => ({ ...i, weight_kg: i.weight_kg || null })), advance, payment_evidence: paymentEvidence || null,
            promised_at: promised ? promised + ":00-05:00" : null } } : { action: "request_pickup", pickup: { customer, address, day, shift, declared_volume: volume, contact } };
          const key = JSON.stringify(body); if (submission.current?.key !== key) submission.current = { key, id: crypto.randomUUID() };
          const run = await post<Run>(`/cases/${cid}/retail-draft`, { ...body, run_id: submission.current!.id,
            attachment_ids: snapshot?.attachments.filter(a => a.perception_status !== "completed").map(a => a.id) || [] });
          onRun(run);
        } catch (error) { setError((error as Error).message); onError((error as Error).message); } finally { setBusy(false); }
      }}>
        {!pickup && <label className="block">Operación<select aria-label="Operación de Atención" value={mode} onChange={e => setMode(e.target.value)} className="w-full"><option value="receive">Recepción en mostrador</option><option value="request_pickup">Solicitud previa de recojo</option></select></label>}
        <label className="block">Cliente<select aria-label="Cliente de recepción" className="w-full" value={existing} onChange={e => setExisting(e.target.value)}><option value="">Cliente nuevo</option>{session?.customers.map(c => <option key={c.id} value={c.id}>{c.id} · {c.name}</option>)}</select></label>
        {!existing && <label className="block">Nombre del cliente<Input required minLength={2} maxLength={120} value={name} onChange={e => setName(e.target.value)} /></label>}
        {(!existing || mode === "request_pickup") && <label className="block">Contacto necesario<Input required minLength={3} maxLength={160} value={contact} onChange={e => setContact(e.target.value)} placeholder="Teléfono o contacto declarado" /></label>}
        {mode === "receive" ? <>
          <h3 className="font-semibold">Prendas y servicios recibidos</h3>
          {items.map((item, index) => <fieldset key={index} className="review-card space-y-3"><legend>Prenda {index + 1}</legend>
            <label className="block">Prenda<Input required minLength={2} value={item.garment} onChange={e => setItems(items.map((v, n) => n === index ? { ...v, garment: e.target.value } : v))} /></label>
            <label className="block">Cantidad<Input type="number" min="1" max="500" required value={item.quantity} onChange={e => setItems(items.map((v, n) => n === index ? { ...v, quantity: Number(e.target.value) } : v))} /></label>
            <label className="block">Servicio<select className="w-full" value={item.service_code} onChange={e => setItems(items.map((v, n) => n === index ? { ...v, service_code: e.target.value } : v))}>{Object.entries(services).map(([code, service]) => <option key={code} value={code}>{service.label} · PEN {service.price} / {service.unit}</option>)}</select></label>
            {services[item.service_code]?.unit === "kg" && <label className="block">Peso declarado en kg<Input type="number" step="0.001" min="0.001" max="500" required value={item.weight_kg} onChange={e => setItems(items.map((v, n) => n === index ? { ...v, weight_kg: e.target.value } : v))} /></label>}
            <label className="block">Observaciones de recepción<Textarea required minLength={3} value={item.observations} onChange={e => setItems(items.map((v, n) => n === index ? { ...v, observations: e.target.value } : v))} /></label>
            {!!snapshot?.attachments.length && <fieldset><legend>Evidencia de la prenda</legend>{snapshot.attachments.map(a => <label key={a.id} className="flex gap-2 text-sm"><input type="checkbox" checked={item.evidence_refs.includes(a.id)} onChange={e => setItems(items.map((v, n) => n === index ? { ...v, evidence_refs: e.target.checked ? [...v.evidence_refs, a.id] : v.evidence_refs.filter(id => id !== a.id) } : v))} />{a.filename}</label>)}</fieldset>}
          </fieldset>)}
          <Button type="button" variant="outline" disabled={items.length >= 50} onClick={() => setItems([...items, blankItem()])}>Añadir prenda</Button>
          <label className="block">Evidencia de recepción efectiva<Textarea required minLength={8} value={evidence} onChange={e => setEvidence(e.target.value)} /></label>
          <label className="flex gap-2"><input type="checkbox" required checked={received} onChange={e => setReceived(e.target.checked)} />Declaro haber recibido y contado estas prendas.</label>
          <label className="block">Fecha prometida (Lima, opcional)<Input type="datetime-local" value={promised} onChange={e => setPromised(e.target.value)} /><small className="muted">Vacío aplica 48 h del tarifario sintético.</small></label>
          <label className="block">Adelanto declarado PEN<Input type="number" min="0" step="0.01" value={advance} onChange={e => setAdvance(e.target.value)} /></label>
          {Number(advance) > 0 && <label className="block">Evidencia del adelanto<Textarea required minLength={8} value={paymentEvidence} onChange={e => setPaymentEvidence(e.target.value)} /></label>}
        </> : <>
          <label className="block">Dirección de recojo<Input required minLength={8} value={address} onChange={e => setAddress(e.target.value)} /></label>
          <label className="block">Fecha solicitada<Input type="date" required value={day} onChange={e => setDay(e.target.value)} /></label>
          <label className="block">Turno<select value={shift} className="w-full" onChange={e => setShift(e.target.value)}><option value="manana">Mañana</option><option value="tarde">Tarde</option></select></label>
          <label className="block">Volumen declarado<Input required minLength={3} value={volume} onChange={e => setVolume(e.target.value)} /></label>
          <p className="muted text-sm">Esta solicitud no crea orden de servicio. La recepción efectiva se registra después del recojo.</p>
        </>}
        <Button type="submit" disabled={busy}>{busy ? "Preparando revisión…" : "Preparar confirmación"}</Button>
      </form>}
    </>}
  </section>;
}

function MilestoneForm({ snapshot, actions, version, onSaved, onError }: { snapshot: Snapshot; actions: Record<string, string>; version: number; onSaved: () => void; onError: (message: string) => void }) {
  const [action, setAction] = useState(Object.keys(actions)[0]), [evidence, setEvidence] = useState(""), [amount, setAmount] = useState(""), [receiver, setReceiver] = useState(""), [conformity, setConformity] = useState(false), [busy, setBusy] = useState(false);
  const command = useRef<{ key: string; id: string } | undefined>(undefined);
  return <form className="space-y-3 mt-4" onSubmit={async e => { e.preventDefault(); if (busy) return; setBusy(true);
    try { const actual = actions[action] ? action : Object.keys(actions)[0]; const body = { action: actual, expected_version: version, evidence, amount: actual === "payment" ? amount : null, receiver: receiver || null, conformity };
      const key = JSON.stringify(body); if (command.current?.key !== key) command.current = { key, id: crypto.randomUUID() };
      await post(`/cases/${snapshot.case.id}/retail-operations`, { ...body, command_id: command.current!.id }); setEvidence(""); onSaved();
    } catch (error) { onError((error as Error).message); } finally { setBusy(false); }
  }}><label className="block">Hito declarado<select className="w-full" value={actions[action] ? action : Object.keys(actions)[0]} onChange={e => setAction(e.target.value)}>{Object.entries(actions).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
    <label className="block">Evidencia del hito<Textarea required minLength={8} value={evidence} onChange={e => setEvidence(e.target.value)} /></label>
    {action === "payment" && <label className="block">Importe declarado PEN<Input type="number" step="0.01" min="0.01" required value={amount} onChange={e => setAmount(e.target.value)} /></label>}
    {action === "deliver" && <label className="block">Receptor declarado<Input required minLength={2} value={receiver} onChange={e => setReceiver(e.target.value)} /></label>}
    {["deliver", "confirm_delivery"].includes(action) && <label className="flex gap-2"><input type="checkbox" checked={conformity} onChange={e => setConformity(e.target.checked)} />Conformidad explícita de recepción</label>}
    <Button type="submit" disabled={busy}>{busy ? "Guardando…" : "Registrar hito humano"}</Button><p className="muted text-xs">No ejecuta producción física, pago bancario ni comprobante fiscal.</p>
  </form>;
}

export function RetailOrderCard({ snapshot, onSaved, onError }: { snapshot: Snapshot; onSaved: () => void; onError: (message: string) => void }) {
  const [incidentDescription, setIncidentDescription] = useState(""), [incidentBusy, setIncidentBusy] = useState(false);
  const incidentCommand = useRef<{ key: string; id: string } | undefined>(undefined);
  const order = snapshot.orders[0], retail = snapshot.retail;
  if (!order || order.kind !== "retail_v2" || !retail) return null;
  const actions: Record<string, string> = order.status === "CLOSED" ? {} : { payment: "Registrar cobro declarado",
    ...({ RECEIVED: { start_processing: "Declarar inicio de procesamiento" }, IN_PROCESSING: { finish_processing: "Declarar fin de procesamiento" }, READY: { deliver: "Registrar entrega", delivery_pending: "Preparar entrega" }, DELIVERY_PENDING: { deliver: "Registrar entrega" }, DELIVERED: { confirm_delivery: "Registrar conformidad posterior", close: "Cerrar servicio con comprobante demo" } }[order.status] || {}) };
  return <section className="review-card space-y-3" aria-label="Orden al detalle persistida"><strong>{order.number}</strong><p>{order.status} · PEN {order.total} · Saldo PEN {retail.balance}</p>
    <ul>{retail.items.map(i => <li key={i.id}>{i.quantity} × {i.garment} · {serviceLabel(i.service_code)} · PEN {i.amount}</li>)}</ul>
    {retail.receipts.map(r => <details key={r.id}><summary>Comprobante de demostración · {r.kind}</summary><div className="notice space-y-2 mt-3"><strong>{String(r.payload.label)}</strong><p>Número: {String(r.payload.number)}</p><p>Total PEN {String(r.payload.total ?? (r.payload.quote as Record<string, unknown> | undefined)?.total ?? "Sin dato")}</p><p>Saldo PEN {String(r.payload.balance ?? (r.payload.quote as Record<string, unknown> | undefined)?.balance ?? "Sin dato")}</p><p className="muted text-sm">Registro local de cobro declarado por el operador. Sin pago bancario ni validez fiscal.</p></div></details>)}
    {Object.keys(actions).length > 0 && <MilestoneForm key={order.status} snapshot={snapshot} actions={actions} version={order.version} onSaved={onSaved} onError={onError} />}
    <details><summary>Abrir expediente separado de incidencia</summary><form className="space-y-3 mt-3" onSubmit={async e => { e.preventDefault(); setIncidentBusy(true); try {
      const key = JSON.stringify({ description: incidentDescription, version: order.version }); if (incidentCommand.current?.key !== key) incidentCommand.current = { key, id: crypto.randomUUID() };
      const result = await post<{ incident_case_id: string }>(`/cases/${snapshot.case.id}/incidents`, { command_id: incidentCommand.current!.id, expected_version: order.version, description: incidentDescription });
      localStorage.setItem("aquaclean-case", result.incident_case_id); window.location.reload();
    } catch (error) { onError((error as Error).message); } finally { setIncidentBusy(false); } }}>
      <label className="block">Observación o reclamo<Textarea required minLength={8} value={incidentDescription} onChange={e => setIncidentDescription(e.target.value)} /></label><Button type="submit" disabled={incidentBusy}>Abrir caso de incidencia</Button>
      <p className="muted text-xs">Abre un expediente vinculado. Investigar y aprobar el plan son pasos posteriores.</p>
    </form></details>
    {order.status === "QUALITY_PENDING" && <p className="muted text-sm">Registra inspección y conformidad en Actividad → Caso. Solicita después por chat la revisión de Calidad.</p>}
  </section>;
}
