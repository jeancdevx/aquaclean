import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  ArrowDown,
  CalendarClock,
  ClipboardCheck,
  Droplets,
  MessageCircleWarning,
  Truck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { AttachmentPreview } from "./AttachmentPreview";
import { ApprovalCard } from "./ApprovalCard";
import { RetailOrderCard } from "./RetailPanel";
import type { Run, Snapshot } from "@/lib/event-types";

const suggestions = [
  { title: "Recibir prendas en mostrador", description: "Cliente nuevo o existente, sin pedido previo", icon: ClipboardCheck, text: "Recibí prendas en mostrador de un cliente nuevo. Ayúdame a registrar la recepción al detalle, sin recojo previo." },
  {
    title: "Programar un recojo",
    description: "Solicitud logística previa, todavía sin orden",
    icon: Truck,
    text: "Quiero programar un recojo. Ayúdame a revisar los datos necesarios.",
  },
  {
    title: "Reprogramar una entrega",
    description: "Revisar alternativas de agenda",
    icon: CalendarClock,
    text: "Necesito reprogramar una entrega de mi pedido. ¿Qué opciones hay?",
  },
  {
    title: "Revisar una observación de calidad",
    description: "Contrastar hallazgos y evidencia",
    icon: ClipboardCheck,
    text: "Quiero revisar una observación de calidad. Indícame qué evidencia falta.",
  },
  {
    title: "Consultar un reclamo",
    description: "Revisar hechos y próximos pasos",
    icon: MessageCircleWarning,
    text: "Quiero consultar un reclamo y revisar qué hace falta para resolverlo.",
  },
];
export function MessageList({
  snapshot,
  live,
  activeRun,
  loading,
  onSuggestion,
  onRun,
  onCorrect,
  onSaved,
  onError,
}: {
  snapshot?: Snapshot;
  live: string;
  activeRun?: string;
  loading: boolean;
  onSuggestion: (s: string) => void;
  onRun: (r: Run) => void;
  onCorrect: () => void;
  onSaved: () => void;
  onError: (s: string) => void;
}) {
  const scroll = useRef<HTMLDivElement>(null),
    end = useRef<HTMLDivElement>(null),
    nearEnd = useRef(true);
  const [jump, setJump] = useState(false);
  useEffect(() => {
    if (nearEnd.current)
      end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    else setJump(true);
  }, [snapshot?.messages.length, live, snapshot?.approvals]);
  const latestApproval = snapshot?.approvals.at(-1);
  const review =
    latestApproval &&
    ["pending", "stale", "expired"].includes(latestApproval.status)
      ? latestApproval
      : undefined;
  return (
    <>
      <main
        id="conversation"
        className="messages"
        ref={scroll}
        onScroll={() => {
          const el = scroll.current;
          if (el) {
            nearEnd.current =
              el.scrollHeight - el.scrollTop - el.clientHeight < 100;
            if (nearEnd.current) setJump(false);
          }
        }}
        aria-label="Conversación"
      >
        <div
          className={`chat-width ${!snapshot?.messages.length ? "empty" : ""}`}
        >
          {loading ? (
            <div aria-label="Cargando conversación">
              <div className="skeleton" />
              <div className="skeleton" style={{ width: "60%" }} />
            </div>
          ) : !snapshot?.messages.length ? (
            <>
              <span className="eyebrow">
                Atención · Logística · Calidad · Incidencias
              </span>
              <h1>
                ¿Qué necesitas
                <br />
                coordinar hoy?
              </h1>
              <p className="muted max-w-lg">
                Un espacio para preparar solicitudes, revisar evidencia y
                coordinar cada caso con supervisión humana.
              </p>
              <div className="suggestions">
                {suggestions.map(({ title, description, icon: Icon, text }) => (
                  <button
                    className="suggestion"
                    key={title}
                    onClick={() => onSuggestion(text)}
                  >
                    <Icon size={20} className="text-primary shrink-0 mt-1" />
                    <div>
                      <strong>{title}</strong>
                      <span>{description}</span>
                    </div>
                  </button>
                ))}
              </div>
              <p className="muted text-xs mt-6">
                Las sugerencias son editables. Ninguna acción se ejecuta al
                pulsarlas.
              </p>
            </>
          ) : (
            snapshot.messages.map((m) => (
              <article
                key={m.id}
                className={`message ${m.role === "user" ? "user" : "assistant"}`}
              >
                <div className="message-header">
                  {m.role === "assistant" && (
                    <Droplets size={16} className="text-primary" />
                  )}
                  <span>
                    {m.role === "user" ? "Operador demo" : "Aqua Clean"}
                  </span>
                  <time>
                    {new Date(m.created_at).toLocaleTimeString("es-PE", {
                      hour: "2-digit",
                      minute: "2-digit",
                      timeZone: "America/Lima",
                    })}
                  </time>
                </div>
                <ReactMarkdown
                  components={{
                    a: ({ href, children }) => (
                      <a
                        href={
                          href?.startsWith("https://") ||
                          href?.startsWith("http://")
                            ? href
                            : undefined
                        }
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary underline"
                      >
                        {children}
                      </a>
                    ),
                  }}
                >
                  {m.content}
                </ReactMarkdown>
                {m.metadata.attachment_ids?.map((id) => {
                  const a = snapshot.attachments.find((x) => x.id === id);
                  return a ? (
                    <AttachmentPreview
                      key={id}
                      attachment={a}
                      caseId={snapshot.case.id}
                      onSaved={onSaved}
                      onError={onError}
                    />
                  ) : null;
                })}
                {m.metadata.rationale_summary && (
                  <details className="text-sm muted mt-4">
                    <summary>Cómo se resolvió</summary>
                    <p>{m.metadata.rationale_summary}</p>
                    {m.metadata.sources?.map((s) => (
                      <details className="notice my-2" key={s.chunk_id}>
                        <summary>
                          {s.title} · sección {s.section}
                          {s.page ? ` · p. ${s.page}` : ""}
                        </summary>
                        <p>{s.content}</p>
                        <p className="technical">
                          v{s.version} · {s.hash.slice(0, 12)}
                        </p>
                      </details>
                    ))}
                  </details>
                )}
                {m.metadata.result &&
                  Object.keys(m.metadata.result).length > 0 && (
                    <div className="notice mt-3">
                      <strong>Resultado guardado</strong>
                      {m.metadata.result.number !== undefined && (
                        <p>Pedido {String(m.metadata.result.number)}</p>
                      )}
                      {m.metadata.result.day !== undefined && (
                        <p>
                          {String(m.metadata.result.day)} ·{" "}
                          {m.metadata.result.shift === "manana"
                            ? "Mañana"
                            : "Tarde"}
                        </p>
                      )}
                    </div>
                  )}
              </article>
            ))
          )}
          {snapshot && <RetailOrderCard snapshot={snapshot} onSaved={onSaved} onError={onError} />}
          {snapshot && review && (
            <ApprovalCard
              key={review.id + review.status}
              approval={review}
              caseData={snapshot.case}
              onRun={onRun}
              onCorrect={onCorrect}
              onError={onError}
            />
          )}
          <div aria-live="polite">
            {live && (
              <article className="message assistant">
                <div className="message-header">
                  <Droplets size={16} />
                  Aqua Clean · Respondiendo
                </div>
                <ReactMarkdown>{live}</ReactMarkdown>
              </article>
            )}
            {activeRun && !live && (
              <p className="status mb-4" role="status">
                Ejecución en curso · revisa Actividad
              </p>
            )}
          </div>
          <div ref={end} />
        </div>
      </main>
      {jump && (
        <Button
          className="jump gap-2"
          variant="outline"
          size="sm"
          onClick={() => {
            nearEnd.current = true;
            setJump(false);
            end.current?.scrollIntoView({ behavior: "smooth" });
          }}
        >
          <ArrowDown size={14} />
          Ir al último mensaje
        </Button>
      )}
    </>
  );
}
