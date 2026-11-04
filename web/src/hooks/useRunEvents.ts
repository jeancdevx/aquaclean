import { useEffect, useRef, useState } from "react";
import type { PublicEvent } from "@/lib/event-types";

export function useRunEvents(
  runId: string | undefined,
  onEvent: (event: PublicEvent) => void,
  onEnd: () => void,
) {
  const handlers = useRef({ onEvent, onEnd });
  handlers.current = { onEvent, onEnd };
  const [connected, setConnected] = useState(false);
  useEffect(() => {
    if (!runId) {
      setConnected(false);
      return;
    }
    let cursor = 0;
    const source = new EventSource(`/api/runs/${runId}/events`);
    const seen = new Set<string>();
    source.onopen = () => setConnected(true);
    source.onmessage = (message) => {
      const event = JSON.parse(message.data) as PublicEvent;
      if (seen.has(event.event_id) || event.sequence <= cursor) return;
      seen.add(event.event_id);
      cursor = event.sequence;
      handlers.current.onEvent(event);
    };
    source.addEventListener("end", () => {
      source.close();
      setConnected(false);
      handlers.current.onEnd();
    });
    source.onerror = () => setConnected(false); // Native SSE reconnect uses Last-Event-ID and never POSTs.
    return () => {
      source.close();
      setConnected(false);
    };
  }, [runId]);
  return connected;
}
