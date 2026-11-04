import { useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { Source } from "@/lib/event-types";

type Summary = {
  synthetic: { customers: number; orders: number; cases: number };
  external_public: { records: number; first_date: string; last_date: string };
  notice: string;
};
export function PublicHistorySearch({
  onError,
}: {
  onError: (s: string) => void;
}) {
  const [summary, setSummary] = useState<Summary>();
  const [query, setQuery] = useState("Samsung");
  const [records, setRecords] = useState<Source[]>([]);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    api<Summary>("/data-summary")
      .then(setSummary)
      .catch(() => {});
  }, []);
  return (
    <section className="mt-6 border-t pt-4">
      <h3 className="font-medium mb-3">Datos y referencias históricas</h3>
      {summary && (
        <div className="notice mb-4">
          <strong>
            {summary.synthetic.orders.toLocaleString("es-PE")} pedidos
            sintéticos
          </strong>
          <br />
          {summary.synthetic.customers} clientes de demostración.
          <br />
          <strong>
            {summary.external_public.records} registros públicos CPSC
          </strong>
          <br />
          {summary.external_public.first_date} a{" "}
          {summary.external_public.last_date}.
          <p className="mt-2">
            Las referencias externas no acreditan hechos ni políticas de Aqua
            Clean.
          </p>
        </div>
      )}
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          try {
            setRecords(
              await api<Source[]>(`/history?q=${encodeURIComponent(query)}`),
            );
          } catch (error) {
            onError((error as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <label htmlFor="history-query" className="text-xs muted">
          Marca, producto o número de retiro (en inglés)
        </label>
        <Input
          id="history-query"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Samsung, Tide, 17028…"
        />
        <Button
          variant="outline"
          className="w-full mt-2"
          disabled={busy || query.length < 3}
        >
          Consultar fuente pública
        </Button>
      </form>
      {records.map((record) => (
        <details className="activity-item" key={record.chunk_id}>
          <summary>{record.title}</summary>
          <p className="muted text-xs">
            Fecha del aviso: {record.version} · CPSC · hecho externo
          </p>
          <p>{record.content}</p>
          <a
            className="text-primary underline"
            href={record.source_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            Abrir publicación oficial
          </a>
          <p className="technical muted">SHA-256 {record.hash.slice(0, 16)}</p>
        </details>
      ))}
    </section>
  );
}
