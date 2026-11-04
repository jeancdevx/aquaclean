import { useState } from "react";
import { FileText, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api, fileUrl } from "@/lib/api";
import type { Attachment } from "@/lib/event-types";

export function AttachmentPreview({
  attachment: a,
  caseId,
  onSaved,
  onError,
}: {
  attachment: Attachment;
  caseId: string;
  onSaved: () => void;
  onError: (s: string) => void;
}) {
  const [edit, setEdit] = useState(false),
    [text, setText] = useState(a.observation),
    [saving, setSaving] = useState(false);
  const url = fileUrl(caseId, a.id);
  return (
    <div className="attachment">
      <div className="flex items-center justify-between gap-2 mb-2">
        <a href={url} target="_blank" rel="noreferrer">
          {a.filename}
        </a>
        <span className="muted">
          {Math.ceil(a.size / 1024)} KB{a.pages ? ` · ${a.pages} pág.` : ""}
        </span>
      </div>
      {a.mime.startsWith("image/") ? (
        <a href={url} target="_blank" rel="noreferrer">
          <img src={url} alt={`Evidencia adjunta: ${a.filename}`} />
        </a>
      ) : a.mime.startsWith("audio/") ? (
        <audio controls preload="metadata" src={url} aria-label={a.filename} />
      ) : (
        <div className="flex gap-2 muted">
          <FileText size={20} />
          PDF · Abrir documento autorizado
        </div>
      )}
      {a.observation ? (
        <details className="mt-3">
          <summary>
            Observación / transcripción editable · sin confirmar
          </summary>
          {edit ? (
            <>
              <Textarea
                aria-label="Corregir observación"
                value={text}
                onChange={(e) => setText(e.target.value)}
              />
              <Button
                size="sm"
                className="mt-2"
                disabled={saving}
                onClick={async () => {
                  setSaving(true);
                  try {
                    await api(`/cases/${caseId}/attachments/${a.id}`, {
                      method: "PATCH",
                      body: JSON.stringify({
                        observation: text,
                        expected_version: a.observation_version,
                      }),
                    });
                    setEdit(false);
                    onSaved();
                  } catch (e) {
                    onError((e as Error).message);
                  } finally {
                    setSaving(false);
                  }
                }}
              >
                <Save size={14} />
                Guardar corrección
              </Button>
            </>
          ) : (
            <>
              <p className="whitespace-pre-wrap">{a.observation}</p>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setText(a.observation);
                  setEdit(true);
                }}
              >
                Corregir texto
              </Button>
            </>
          )}
        </details>
      ) : (
        <p className="muted mt-2">
          Percepción pendiente: se analizará con el proveedor al enviar.
        </p>
      )}
    </div>
  );
}
