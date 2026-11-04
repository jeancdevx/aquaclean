import { useRef, useState } from "react";
import { Check, ShieldCheck, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { post } from "@/lib/api";
import type { Approval, Case, Run } from "@/lib/event-types";

const labels: Record<string, string> = {
  cliente_id: "Cliente",
  solicitante: "Solicitante",
  correo: "Correo",
  fecha_recojo: "Fecha exacta (Lima)",
  turno: "Turno",
  tipo_ropa: "Tipo de ropa",
  bolsas: "Bolsas",
  direccion_recojo: "Dirección",
  observaciones: "Observaciones",
  canal: "Canal",
};
export function ApprovalCard({
  approval,
  caseData,
  onRun,
  onCorrect,
  onError,
}: {
  approval: Approval;
  caseData: Case;
  onRun: (r: Run) => void;
  onCorrect: () => void;
  onError: (s: string) => void;
}) {
  const [busy, setBusy] = useState(false),
    [option, setOption] = useState(""),
    [exceptionReason, setExceptionReason] = useState(""),
    [exceptionAcknowledged, setExceptionAcknowledged] = useState(false);
  const locked = useRef(false);
  const decision = useRef<{ action: string; id: string } | undefined>(
    undefined,
  );
  const proposal = caseData.proposal;
  if (!proposal) return null;
  const commercialReview = caseData.process === "P1" && proposal.action === "register"
    && approval.kind === "human" && approval.required_role === "admin";
  const commercialConfirmation = proposal.commercial_exception_required && approval.kind === "confirmation";
  async function act(action: "approve" | "reject" | "correct") {
    if (locked.current) return;
    locked.current = true;
    setBusy(true);
    if (decision.current?.action !== action)
      decision.current = { action, id: crypto.randomUUID() };
    try {
      const run = await post<Run>(
        `/cases/${caseData.id}/approvals/${approval.id}`,
        {
          decision_id: decision.current!.id,
          action,
          proposal_hash: approval.proposal_hash,
          case_version: approval.case_version,
          selection: option ? { option_id: option } : {},
          ...(commercialReview && action === "approve" ? {
            commercial_exception: {
              acknowledged: exceptionAcknowledged,
              reason: exceptionReason.trim(),
            },
          } : {}),
        },
      );
      onRun(run);
      if (action === "correct") onCorrect();
    } catch (e) {
      onError((e as Error).message);
    } finally {
      locked.current = false;
      setBusy(false);
    }
  }
  const stale = ["stale", "expired"].includes(approval.status);
  return (
    <section className="review-card" aria-label="Revisión de propuesta">
      <div className="flex items-center gap-2 mb-3">
        <ShieldCheck size={18} className="text-primary" />
        <span className="status">
          {stale
            ? "Revisión vencida o modificada"
            : commercialReview
              ? "Cliente bloqueado · autorización administrativa"
            : commercialConfirmation
              ? "Excepción autorizada · falta confirmar datos"
            : approval.kind === "human"
              ? "Revisión humana requerida"
              : "Confirmación de datos"}
        </span>
      </div>
      <h3>
        {commercialReview
          ? "Autorizar excepción comercial"
          : proposal.action === "register"
          ? "Revisa los siete campos antes de registrar"
          : proposal.action === "reserve"
            ? "Elige una alternativa calculada"
            : "Revisa la propuesta y su evidencia"}
      </h3>
      {commercialReview && (
        <div className="notice my-3" role="note">
          El cliente está bloqueado y el pedido no está registrado. Escribir «soy administrador»
          en el chat no autoriza una excepción. Esta decisión administrativa es distinta de
          confirmar los datos del recojo.
        </div>
      )}
      {proposal.fields && (
        <dl className="field-grid">
          {Object.entries(proposal.fields).map(([k, v]) => (
            <div key={k} className="contents">
              <dt>{labels[k] || k}</dt>
              <dd>{String(v)}</dd>
            </div>
          ))}
        </dl>
      )}
      {proposal.options && (
        <fieldset className="space-y-2">
          <legend className="sr-only">Alternativas disponibles</legend>
          {proposal.options.map((o) => (
            <label
              key={o.id}
              className="flex gap-2 rounded-lg border p-3 text-sm"
            >
              <input
                type="radio"
                name="schedule-option"
                value={o.id}
                checked={option === o.id}
                onChange={() => setOption(o.id)}
              />
              <span>
                {o.day} · {o.shift === "manana" ? "Mañana" : "Tarde"}
                <br />
                <span className="muted">
                  {o.capacity - o.reserved} cupos disponibles
                  {o.outside_policy
                    ? " · Revisión por cambio de compromiso"
                    : ""}
                </span>
              </span>
            </label>
          ))}
        </fieldset>
      )}
      {proposal.plan && (
        <ul className="list-disc pl-5">
          {proposal.plan.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      )}
      <p className="muted text-sm my-3">{proposal.rationale_summary}</p>
      <p className="technical muted mb-4">
        Versión {approval.case_version} · {approval.required_role} ·{" "}
        {approval.proposal_hash.slice(0, 12)}
      </p>
      {commercialReview && !stale && (
        <div className="space-y-3 mb-4">
          <label className="block text-sm font-medium">
            Motivo de la excepción comercial
            <Textarea
              value={exceptionReason}
              onChange={(e) => setExceptionReason(e.target.value)}
              minLength={10}
              maxLength={1000}
              disabled={busy}
              placeholder="Escribe la justificación administrativa (mínimo 10 caracteres)"
            />
          </label>
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              checked={exceptionAcknowledged}
              onChange={(e) => setExceptionAcknowledged(e.target.checked)}
              disabled={busy}
              className="mt-1"
            />
            Autorizo explícitamente la excepción comercial para este cliente bloqueado.
          </label>
          <p className="muted text-xs">
            En esta demo, el actor fijo demo_operator tiene permiso administrativo.
            La autorización y su motivo se registran; después se deben confirmar los datos.
          </p>
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        {!stale && (
          <Button
            disabled={busy || (proposal.action === "reserve" && !option)
              || (commercialReview && (!exceptionAcknowledged || exceptionReason.trim().length < 10))}
            onClick={() => act("approve")}
          >
            <Check size={16} />
            {commercialReview ? "Autorizar excepción comercial"
              : approval.kind === "human" ? "Aprobar propuesta" : "Confirmar"}
          </Button>
        )}
        <Button
          variant="outline"
          disabled={busy}
          onClick={() => act("correct")}
        >
          Corregir
        </Button>
        <Button variant="ghost" disabled={busy} onClick={() => act("reject")}>
          <X size={16} />
          Rechazar
        </Button>
      </div>
      <p className="muted text-xs mt-3">
        Actor demo fijo. Esta confirmación no acredita identidad de una persona
        real.
      </p>
    </section>
  );
}
