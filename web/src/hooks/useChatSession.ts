import { useCallback, useEffect, useRef, useState } from "react";
import { api, post } from "@/lib/api";
import type {
  Attachment,
  Case,
  PublicEvent,
  Run,
  Session,
  Snapshot,
} from "@/lib/event-types";
import { useRunEvents } from "./useRunEvents";

export function useChatSession() {
  const [session, setSession] = useState<Session>();
  const [cases, setCases] = useState<Case[]>([]);
  const [caseId, setCaseId] = useState<string>();
  const [snapshot, setSnapshot] = useState<Snapshot>();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [activeRun, setActiveRun] = useState<string>();
  const [live, setLive] = useState("");
  const [events, setEvents] = useState<PublicEvent[]>([]);
  const currentCase = useRef(caseId);
  currentCase.current = caseId;
  const lastIntent = useRef<{ key: string; id: string } | undefined>(undefined);
  const refreshCases = useCallback(
    async () => setCases(await api<Case[]>("/cases")),
    [],
  );
  const load = useCallback(async (id: string) => {
    const next = await api<Snapshot>(`/cases/${id}`);
    if (currentCase.current && currentCase.current !== id) return;
    setSnapshot(next);
    setEvents(next.events);
    const running = next.runs.find((r) =>
      ["queued", "running"].includes(r.status),
    );
    setActiveRun(running?.id);
  }, []);
  useEffect(() => {
    const stored = localStorage.getItem("aquaclean-case");
    if (stored) {
      currentCase.current = stored;
      setCaseId(stored);
    }
    Promise.all([api<Session>("/session").then(setSession), refreshCases()])
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [refreshCases]);
  useEffect(() => {
    if (caseId) {
      setLoading(true);
      setLive("");
      setEvents([]);
      load(caseId)
        .catch((e) => setError(e.message))
        .finally(() => setLoading(false));
    } else {
      setSnapshot(undefined);
      setActiveRun(undefined);
      setEvents([]);
    }
  }, [caseId, load]);
  const select = (id?: string) => {
    if (id) localStorage.setItem("aquaclean-case", id);
    else localStorage.removeItem("aquaclean-case");
    currentCase.current = id;
    setCaseId(id);
    setSnapshot(undefined);
    setError("");
    setLive("");
    setActiveRun(undefined);
  };
  const ensureCase = async (clientId?: string, title?: string) => {
    if (caseId) return caseId;
    const next = await post<Case>("/cases", {
      title: title?.slice(0, 100) || "Nueva conversación",
      client_id: clientId || null,
    });
    localStorage.setItem("aquaclean-case", next.id);
    currentCase.current = next.id;
    setCaseId(next.id);
    await refreshCases();
    return next.id;
  };
  const onEvent = (event: PublicEvent) => {
    setEvents((previous) =>
      previous.some((e) => e.event_id === event.event_id)
        ? previous
        : [...previous, event].sort((a, b) => a.sequence - b.sequence),
    );
    if (event.type === "message.delta")
      setLive((previous) => previous + (event.payload.text || ""));
    if (event.type === "message.started") setLive("");
    if (event.type === "run.failed")
      setError(event.payload.message || "Error de integración.");
  };
  const onEnd = async () => {
    setActiveRun(undefined);
    setLive("");
    if (currentCase.current) await load(currentCase.current);
    await refreshCases();
  };
  const connected = useRunEvents(activeRun, onEvent, () => {
    onEnd().catch((e) => setError(e.message));
  });
  // Recovery if a connection ends between terminal status and the final SSE event.
  useEffect(() => {
    if (!activeRun || !caseId) return;
    const timer = setInterval(() => {
      load(caseId).catch(() => {});
    }, 4000);
    return () => clearInterval(timer);
  }, [activeRun, caseId, load]);
  const send = async (
    text: string,
    attachments: Attachment[],
    clientId?: string,
  ) => {
    setError("");
    const cid = await ensureCase(clientId, text);
    const body = { text, attachment_ids: attachments.map((a) => a.id) };
    const key = JSON.stringify({ cid, ...body });
    if (lastIntent.current?.key !== key)
      lastIntent.current = { key, id: crypto.randomUUID() };
    const result = await post<Run>(`/cases/${cid}/runs`, {
      run_id: lastIntent.current!.id,
      ...body,
    });
    setActiveRun(
      ["queued", "running"].includes(result.status) ? result.id : undefined,
    );
    setLive("");
    if (result.status !== "failed") lastIntent.current = undefined;
    await load(cid);
    await refreshCases();
    return result;
  };
  return {
    session,
    cases,
    caseId,
    snapshot,
    error,
    setError,
    loading,
    activeRun,
    live,
    events,
    connected,
    select,
    ensureCase,
    send,
    load,
    refreshCases,
    setActiveRun,
  };
}
