import { useState } from "react";
import { Activity, BookOpen, ClipboardCheck, FileCheck } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { OrderLinkForm } from "./OrderLinkForm";
import { PublicHistorySearch } from "./PublicHistorySearch";
import { post } from "@/lib/api";
import type { PublicEvent, Snapshot } from "@/lib/event-types";

export function ActivityPanel({
  snapshot,
  events,
  onSaved,
  onError,
}: {
  snapshot?: Snapshot;
  events: PublicEvent[];
  onSaved: () => void;
  onError: (s: string) => void;
}) {
  const [kind, setKind] = useState("inspection"),
    [note, setNote] = useState(""),
    [busy, setBusy] = useState(false);
  const sources = [
    ...new Map(
      events
        .flatMap((e) => e.payload.sources || [])
        .map((s) => [s.chunk_id, s]),
    ).values(),
  ];
  return (
    <Tabs defaultValue="activity">
      <TabsList className="w-full">
        <TabsTrigger value="activity">
          <Activity size={14} />
          Actividad
        </TabsTrigger>
        <TabsTrigger value="case">
          <ClipboardCheck size={14} />
          Caso
        </TabsTrigger>
        <TabsTrigger value="sources">
          <BookOpen size={14} />
          Fuentes
        </TabsTrigger>
      </TabsList>
      <TabsContent value="activity">
        <p className="muted text-xs mt-4">
          Eventos públicos persistidos. Se muestran hechos y estados de
          ejecución.
        </p>
        {events
          .filter((e) => e.type !== "message.delta")
          .map((e) => (
            <div className="activity-item" key={e.event_id}>
              <strong>{e.payload.agent || e.payload.name || e.type}</strong>
              <p>
                {e.payload.summary ||
                  e.payload.message ||
                  e.payload.rationale_summary ||
                  e.payload.status ||
                  ""}
              </p>
              <div className="technical muted">
                #{e.sequence} ·{" "}
                {new Date(e.created_at).toLocaleTimeString("es-PE", {
                  timeZone: "America/Lima",
                })}
                {e.payload.duration_ms !== undefined
                  ? ` · ${e.payload.duration_ms} ms`
                  : ""}
              </div>
            </div>
          ))}
        {!events.length && (
          <div className="notice mt-4">
            Todavía no hay actividad. Aparecerán aquí las herramientas realmente
            ejecutadas.
          </div>
        )}
      </TabsContent>
      <TabsContent value="case">
        {snapshot ? (
          <>
            <div className="my-4">
              <span className="status">{snapshot.case.status}</span>
              <p className="technical mt-3">{snapshot.case.id}</p>
              <p className="muted text-xs">
                {snapshot.case.process} · v{snapshot.case.version} · Responsable{" "}
                {snapshot.case.owner}
              </p>
            </div>
            {!snapshot.case.order_id && (
              <OrderLinkForm
                caseData={snapshot.case}
                onSaved={onSaved}
                onError={onError}
              />
            )}
            {snapshot.orders.map((o) => (
              <div className="review-card" key={o.id}>
                <strong>{o.number}</strong>
                <p>
                  {o.status} · v{o.version}
                </p>
              </div>
            ))}
            <h3 className="font-medium mt-6 mb-3 flex gap-2">
              <FileCheck size={18} />
              Registrar tarea humana
            </h3>
            <p className="muted text-xs mb-3">
              Documenta lo observado por el operador. No acredita una tarea
              física realizada por IA.
            </p>
            <label className="text-sm" htmlFor="event-kind">
              Tipo de evidencia
            </label>
            <select
              id="event-kind"
              value={kind}
              onChange={(e) => setKind(e.target.value)}
              className="w-full mb-3"
            >
              {Object.entries({
                inspection: "Inspección",
                reprocess: "Reproceso autorizado",
                customer_acceptance: "Aceptación expresa del cliente",
                fulfillment: "Cumplimiento",
                conformity: "Conformidad / criterio de cierre",
                observation: "Observación",
                pickup: "Recojo físico",
                delivery: "Entrega física",
              }).map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
            <Textarea
              aria-label="Evidencia del operador"
              placeholder="Hecho observado, referencia y resultado…"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={4}
            />
            <Button
              className="w-full mt-3"
              disabled={busy || note.trim().length < 8}
              onClick={async () => {
                setBusy(true);
                try {
                  await post(`/cases/${snapshot.case.id}/operator-events`, {
                    event_id: crypto.randomUUID(),
                    kind,
                    note,
                  });
                  setNote("");
                  onSaved();
                } catch (e) {
                  onError((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              Guardar evidencia
            </Button>
            {snapshot.operator_events.map((e) => (
              <div key={e.id} className="activity-item">
                <strong>{e.kind}</strong>
                <p>{e.note}</p>
                <small className="muted">{e.actor_id}</small>
              </div>
            ))}
            {snapshot.inbox.length > 0 && (
              <div className="notice mt-4">
                {snapshot.inbox.length} notificación(es) en bandeja local. No se
                envió correo real.
              </div>
            )}
          </>
        ) : (
          <p className="notice mt-4">
            Abre o crea una conversación para consultar su expediente.
          </p>
        )}
      </TabsContent>
      <TabsContent value="sources">
        <PublicHistorySearch onError={onError} />
        {sources.map((s) => (
          <details className="activity-item" key={s.chunk_id}>
            <summary>{s.title}</summary>
            <p className="text-xs muted">
              v{s.version} · sección {s.section}
              {s.page ? ` · página ${s.page}` : ""}
            </p>
            <p className="mt-2">{s.content}</p>
            <p className="technical muted">
              {s.chunk_id}
              <br />
              {s.hash.slice(0, 16)}
            </p>
          </details>
        ))}
        {!sources.length && (
          <p className="notice mt-4">
            No hay fragmentos recuperados en este caso. Configura Gemini y
            ejecuta ingest-demo para habilitar RAG.
          </p>
        )}
      </TabsContent>
    </Tabs>
  );
}
