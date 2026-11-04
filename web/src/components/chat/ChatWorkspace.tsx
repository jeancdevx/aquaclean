import { useEffect, useState } from "react";
import {
  Activity,
  AlertCircle,
  Menu,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  Sun,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { useChatSession } from "@/hooks/useChatSession";
import { ConversationSidebar } from "./ConversationSidebar";
import { MessageList } from "./MessageList";
import { PromptComposer } from "./PromptComposer";
import { ActivityPanel } from "./ActivityPanel";

export default function ChatWorkspace() {
  const chat = useChatSession();
  const [text, setText] = useState(""),
    [sidebar, setSidebar] = useState(true),
    [mobileHistory, setMobileHistory] = useState(false),
    [inspector, setInspector] = useState(false),
    [wide, setWide] = useState(false),
    [dark, setDark] = useState(false);
  useEffect(() => {
    const query = matchMedia("(min-width:1100px)");
    const update = () => setWide(query.matches);
    update();
    query.addEventListener("change", update);
    const theme = localStorage.getItem("aquaclean-theme") === "dark";
    setDark(theme);
    document.documentElement.classList.toggle("dark", theme);
    return () => query.removeEventListener("change", update);
  }, []);
  const reload = () => {
    if (chat.caseId)
      void chat.load(chat.caseId).catch((e) => chat.setError(e.message));
    void chat.refreshCases();
  };
  const select = (id?: string) => {
    chat.select(id);
    setText("");
    setMobileHistory(false);
  };
  const activity = (
    <ActivityPanel
      snapshot={chat.snapshot}
      events={chat.events}
      onSaved={reload}
      onError={chat.setError}
    />
  );
  const history = (
    <ConversationSidebar
      cases={chat.cases}
      selected={chat.caseId}
      session={chat.session}
      onSelect={select}
      onKnowledge={() => {
        setInspector(true);
        setMobileHistory(false);
      }}
    />
  );
  const pending = ["pending", "stale", "expired"].includes(
    chat.snapshot?.approvals.at(-1)?.status || "",
  );
  const activeEvent = [...chat.events]
    .reverse()
    .find(
      (e) =>
        e.run_id === chat.activeRun &&
        [
          "agent.started",
          "agent.completed",
          "tool.started",
          "tool.completed",
        ].includes(e.type),
    );
  return (
    <>
      <a href="#chat-input" className="skip-link">
        Ir al compositor
      </a>
      <div className="app-shell">
        {sidebar && (
          <aside className="sidebar desktop-sidebar">{history}</aside>
        )}
        <section className="workspace">
          <header className="topbar">
            <div className="flex items-center gap-2 min-w-0">
              <Button
                className="mobile-only"
                variant="ghost"
                size="icon"
                aria-label="Abrir historial"
                onClick={() => setMobileHistory(true)}
              >
                <Menu size={18} />
              </Button>
              <Button
                className="hidden md:inline-flex"
                variant="ghost"
                size="icon"
                aria-label={
                  sidebar ? "Contraer barra lateral" : "Expandir barra lateral"
                }
                onClick={() => setSidebar(!sidebar)}
              >
                {sidebar ? (
                  <PanelLeftClose size={18} />
                ) : (
                  <PanelLeftOpen size={18} />
                )}
              </Button>
              <span className="text-sm font-medium topbar-title">
                {chat.snapshot?.case.title || "Nueva conversación"}
              </span>
            </div>
            <div className="flex items-center gap-1">
              <span
                className="hidden lg:inline text-xs muted mr-2 whitespace-nowrap"
                title={chat.session?.ai.model}
              >
                {chat.activeRun
                  ? String(
                      activeEvent?.payload.agent ||
                        activeEvent?.payload.name ||
                        "En cola",
                    )
                  : chat.session?.ai.configured
                    ? "Gemini configurado"
                    : "IA no disponible"}
              </span>
              <span className="status hidden sm:inline-flex whitespace-nowrap">
                Demo local
              </span>
              <Button
                variant="ghost"
                size="icon"
                aria-label={dark ? "Activar tema claro" : "Activar tema oscuro"}
                onClick={() => {
                  const next = !dark;
                  setDark(next);
                  document.documentElement.classList.toggle("dark", next);
                  localStorage.setItem(
                    "aquaclean-theme",
                    next ? "dark" : "light",
                  );
                }}
              >
                {dark ? <Sun size={18} /> : <Moon size={18} />}
              </Button>
              <Button
                variant={inspector ? "secondary" : "ghost"}
                size="sm"
                aria-label="Abrir actividad y caso"
                aria-expanded={inspector}
                onClick={() => setInspector(!inspector)}
              >
                <Activity size={16} />
                <span className="hidden sm:inline">Actividad</span>
              </Button>
            </div>
          </header>
          {chat.session && !chat.session.ai.configured && (
            <div
              className="notice mx-4 mt-3 flex gap-2 items-start"
              role="status"
            >
              <AlertCircle size={16} className="shrink-0 mt-0.5" />
              <span>
                <strong>IA y embeddings no disponibles.</strong> Configura
                GEMINI_API_KEY en el backend para interpretar mensajes, analizar
                medios y consultar conocimiento. Historial y datos demo
                disponibles.
              </span>
            </div>
          )}
          {chat.error && (
            <div className="error mx-4" role="alert">
              {chat.error}
              <Button
                variant="ghost"
                size="sm"
                className="ml-2"
                onClick={() => chat.setError("")}
              >
                Cerrar
              </Button>
            </div>
          )}
          <div className="main-row">
            <div className="chat-area">
              <MessageList
                snapshot={chat.snapshot}
                loading={chat.loading}
                live={chat.live}
                activeRun={chat.activeRun}
                onSuggestion={(s) => {
                  setText(s);
                  document.getElementById("chat-input")?.focus();
                }}
                onRun={(r) => {
                  chat.setActiveRun(r.id);
                  reload();
                }}
                onCorrect={() => {
                  setText(
                    "Quiero corregir los datos de la propuesta anterior: ",
                  );
                  document.getElementById("chat-input")?.focus();
                }}
                onSaved={reload}
                onError={chat.setError}
              />
              <PromptComposer
                caseId={chat.caseId}
                boundClientId={chat.snapshot?.case.client_id}
                text={text}
                setText={setText}
                session={chat.session}
                activeRun={chat.activeRun}
                pending={pending}
                ensureCase={chat.ensureCase}
                onSend={chat.send}
                onError={chat.setError}
              />
            </div>
            {inspector && wide && (
              <aside
                className="inspector desktop-panel"
                aria-label="Inspector de caso"
              >
                {activity}
              </aside>
            )}
          </div>
        </section>
      </div>
      <Sheet open={mobileHistory} onOpenChange={setMobileHistory}>
        <SheetContent side="left" className="w-[280px] p-0">
          <SheetHeader className="sr-only">
            <SheetTitle>Historial de conversaciones</SheetTitle>
            <SheetDescription>
              Navegación del espacio de operaciones
            </SheetDescription>
          </SheetHeader>
          <div className="sidebar h-full w-full pt-12">{history}</div>
        </SheetContent>
      </Sheet>
      <Sheet open={inspector && !wide} onOpenChange={setInspector}>
        <SheetContent side="right" className="w-[min(100vw,380px)] p-0">
          <SheetHeader className="sr-only">
            <SheetTitle>Actividad y expediente</SheetTitle>
            <SheetDescription>
              Eventos, evidencia y fuentes del caso
            </SheetDescription>
          </SheetHeader>
          <aside className="inspector w-full h-full pt-12">{activity}</aside>
        </SheetContent>
      </Sheet>
    </>
  );
}
