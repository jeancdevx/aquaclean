import { useEffect, useRef, useState } from "react";
import { ArrowUp, Paperclip, Square, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api, post, fileUrl } from "@/lib/api";
import type { Attachment, Session } from "@/lib/event-types";

export function PromptComposer({
  text,
  setText,
  session,
  caseId,
  boundClientId,
  activeRun,
  pending,
  ensureCase,
  onSend,
  onError,
}: {
  text: string;
  setText: (s: string) => void;
  session?: Session;
  caseId?: string;
  boundClientId?: string;
  activeRun?: string;
  pending: boolean;
  ensureCase: (clientId?: string, title?: string) => Promise<string>;
  onSend: (
    text: string,
    attachments: Attachment[],
    clientId?: string,
  ) => Promise<unknown>;
  onError: (s: string) => void;
}) {
  const [attachments, setAttachments] = useState<Attachment[]>([]),
    [uploading, setUploading] = useState(false),
    [sending, setSending] = useState(false),
    [clientId, setClientId] = useState("");
  const file = useRef<HTMLInputElement>(null);
  const lock = useRef(false);
  const previousCase = useRef(caseId);
  useEffect(() => {
    if (previousCase.current && previousCase.current !== caseId) {
      setAttachments([]);
      setClientId("");
    }
    previousCase.current = caseId;
  }, [caseId]);
  useEffect(() => {
    if (boundClientId) setClientId(boundClientId);
  }, [boundClientId]);
  async function send() {
    if (lock.current || (!text.trim() && !attachments.length)) return;
    lock.current = true;
    setSending(true);
    try {
      await onSend(text, attachments, clientId);
      setText("");
      setAttachments([]);
    } catch (e) {
      onError((e as Error).message);
    } finally {
      lock.current = false;
      setSending(false);
    }
  }
  return (
    <div className="composer-wrap">
      <div className="chat-width">
        <div className="composer">
          <div className="flex flex-wrap gap-2">
            {attachments.map((a) => (
              <div className="notice flex items-center gap-2" key={a.id}>
                {caseId && a.mime.startsWith("image/") && (
                  <img
                    src={fileUrl(caseId, a.id)}
                    alt={`Vista previa de ${a.filename}`}
                    className="size-10 rounded object-cover"
                  />
                )}
                {caseId && a.mime.startsWith("audio/") && (
                  <audio
                    controls
                    preload="metadata"
                    src={fileUrl(caseId, a.id)}
                    aria-label={`Vista previa de ${a.filename}`}
                    className="max-w-48 h-10"
                  />
                )}
                {caseId && a.mime === "application/pdf" ? (
                  <a
                    href={fileUrl(caseId, a.id)}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {a.filename} · {a.pages} pág.
                  </a>
                ) : (
                  <span>{a.filename}</span>
                )}
                <button
                  aria-label={`Quitar ${a.filename}`}
                  onClick={() =>
                    setAttachments((previous) =>
                      previous.filter((x) => x.id !== a.id),
                    )
                  }
                >
                  <X size={14} />
                </button>
              </div>
            ))}
          </div>
          <Textarea
            id="chat-input"
            aria-label="Mensaje"
            placeholder={
              pending
                ? "Revisa la propuesta o pulsa Corregir para continuar…"
                : "Escribe una solicitud o adjunta una evidencia…"
            }
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={!!activeRun || pending}
            onKeyDown={(e) => {
              if (
                e.key === "Enter" &&
                !e.shiftKey &&
                !e.nativeEvent.isComposing
              ) {
                e.preventDefault();
                if (!uploading && !sending && !pending) void send();
              }
            }}
          />
          <div className="composer-actions">
            <div className="flex items-center gap-2 min-w-0">
              <input
                ref={file}
                type="file"
                className="sr-only"
                aria-label="Adjuntar imagen PDF o audio"
                accept=".jpg,.jpeg,.png,.webp,.pdf,.mp3,.wav"
                multiple
                onChange={async (e) => {
                  const files = [...(e.target.files || [])];
                  e.target.value = "";
                  if (
                    files.length + attachments.length >
                    (session?.limits.attachments || 5)
                  ) {
                    onError("Máximo cinco adjuntos por mensaje.");
                    return;
                  }
                  setUploading(true);
                  try {
                    const cid = await ensureCase(
                      clientId,
                      text || "Evidencia adjunta",
                    );
                    for (const selected of files) {
                      const body = new FormData();
                      body.append("file", selected);
                      const saved = await api<Attachment>(
                        `/cases/${cid}/uploads`,
                        { method: "POST", body },
                      );
                      setAttachments((previous) => [...previous, saved]);
                    }
                  } catch (e) {
                    onError((e as Error).message);
                  } finally {
                    setUploading(false);
                  }
                }}
              />
              <Button
                variant="ghost"
                size="icon"
                aria-label="Adjuntar archivo"
                title="JPG, PNG, WebP, PDF, MP3 o WAV"
                disabled={uploading || !!activeRun || pending}
                onClick={() => file.current?.click()}
              >
                <Paperclip size={18} />
              </Button>
              {uploading ? (
                <span className="text-xs muted" role="status">
                  Validando archivo…
                </span>
              ) : (
                <select
                  aria-label="Cliente demo verificado por operador"
                  value={clientId}
                  onChange={(e) => setClientId(e.target.value)}
                  className="text-xs max-w-48"
                  disabled={!!activeRun || pending || !!boundClientId}
                >
                  <option value="">Cliente demo (opcional)</option>
                  {session?.customers.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.id}
                      {c.blocked ? " · bloqueado" : ""}
                    </option>
                  ))}
                </select>
              )}
            </div>
            {activeRun ? (
              <Button
                size="icon"
                variant="outline"
                aria-label="Detener respuesta"
                onClick={async () => {
                  try {
                    await post(`/runs/${activeRun}/cancel`, {});
                  } catch (e) {
                    onError((e as Error).message);
                  }
                }}
              >
                <Square size={16} />
              </Button>
            ) : (
              <Button
                size="icon"
                aria-label="Enviar mensaje"
                disabled={
                  sending ||
                  uploading ||
                  pending ||
                  (!text.trim() && !attachments.length)
                }
                onClick={() => void send()}
              >
                <ArrowUp size={20} />
              </Button>
            )}
          </div>
        </div>
        <p className="footer-note">
          Demo sintética · Confirma los datos antes de ejecutar · Enter envía,
          Shift+Enter agrega línea
        </p>
      </div>
    </div>
  );
}
