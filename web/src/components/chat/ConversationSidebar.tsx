import {
  BookOpen,
  Droplets,
  MessageSquare,
  Plus,
  Search,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import type { Case, Session } from "@/lib/event-types";

export function Brand() {
  return (
    <div className="brand">
      <span className="brand-mark">
        <Droplets size={22} />
      </span>
      <div>
        <strong>Aqua Clean</strong>
        <br />
        <small>ESPACIO DE OPERACIONES</small>
      </div>
    </div>
  );
}
export function ConversationSidebar({
  cases,
  selected,
  session,
  onSelect,
  onKnowledge,
}: {
  cases: Case[];
  selected?: string;
  session?: Session;
  onSelect: (id?: string) => void;
  onKnowledge: () => void;
}) {
  const [search, setSearch] = useState("");
  const [remote, setRemote] = useState<Case[]>();
  useEffect(() => {
    if (!search) {
      setRemote(undefined);
      return;
    }
    const timer = setTimeout(() => {
      api<Case[]>(`/cases?q=${encodeURIComponent(search)}`)
        .then(setRemote)
        .catch(() => {});
    }, 250);
    return () => clearTimeout(timer);
  }, [search]);
  return (
    <>
      <Brand />
      <Button onClick={() => onSelect()} className="w-full justify-start gap-2">
        <Plus size={16} />
        Nueva conversación
      </Button>
      <div className="relative">
        <Search
          size={16}
          className="absolute left-3 top-3 text-muted-foreground"
        />
        <Input
          aria-label="Buscar conversaciones"
          placeholder="Buscar conversaciones"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>
      <nav className="history" aria-label="Historial">
        <p className="eyebrow mb-3">Conversaciones</p>
        {(remote || cases).map((c) => (
          <button
            key={c.id}
            onClick={() => onSelect(c.id)}
            aria-current={selected === c.id ? "page" : undefined}
          >
            <span className="flex items-center gap-2">
              <MessageSquare size={14} />
              <span className="truncate">{c.title}</span>
            </span>
            <small>
              {c.process} · {c.status}
            </small>
          </button>
        ))}
        {!cases.length && (
          <p className="muted text-sm">Tus conversaciones aparecerán aquí.</p>
        )}
      </nav>
      <div className="space-y-3">
        <Button
          variant="ghost"
          onClick={onKnowledge}
          className="w-full justify-start gap-2"
        >
          <BookOpen size={16} />
          Conocimiento y fuentes
        </Button>
        <div className="notice">
          <ShieldCheck size={16} className="mb-2" />
          <strong>Entorno de demostración</strong>
          <br />
          Datos sintéticos. Políticas piloto.
          <br />
          <span className="technical">
            {session?.actor.id || "Conectando…"}
          </span>
        </div>
      </div>
    </>
  );
}
