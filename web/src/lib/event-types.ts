export type EventType =
  | "message.started"
  | "run.started"
  | "message.delta"
  | "agent.started"
  | "agent.completed"
  | "tool.started"
  | "tool.completed"
  | "decision.summary"
  | "approval.requested"
  | "approval.resolved"
  | "run.completed"
  | "run.failed";
export interface PublicEvent {
  sequence: number;
  event_id: string;
  run_id: string;
  case_id: string;
  type: EventType;
  created_at: string;
  payload: {
    text?: string;
    agent?: string;
    name?: string;
    status?: string;
    summary?: string;
    message?: string;
    rationale_summary?: string;
    duration_ms?: number;
    sources?: Source[];
    [key: string]: unknown;
  };
}
export interface Source {
  source_url?: string;
  source_kind?: string;
  chunk_id: string;
  document_id: string;
  title: string;
  section: string;
  page?: number;
  content: string;
  version: string;
  hash: string;
  distance?: number;
}
export interface Attachment {
  id: string;
  filename: string;
  mime: string;
  size: number;
  observation: string;
  observation_version: number;
  perception_status: string;
  pages?: number;
  duration?: number;
}
export interface Message {
  id: string;
  role: string;
  content: string;
  metadata: {
    rationale_summary?: string;
    sources?: Source[];
    result?: Record<string, unknown>;
    attachment_ids?: string[];
    error?: string;
  };
  created_at: string;
}
export interface Proposal {
  commercial_exception_required?: boolean;
  action: string;
  response: string;
  rationale_summary: string;
  fields?: Record<string, string | number>;
  sources?: Source[];
  options?: {
    id: string;
    day: string;
    shift: string;
    reserved: number;
    capacity: number;
    outside_policy: boolean;
  }[];
  plan?: string[];
  findings?: string[];
  facts?: string[];
  discrepancies?: string[];
}
export interface Case {
  id: string;
  title: string;
  process: string;
  status: string;
  version: number;
  client_id?: string;
  proposal?: Proposal;
  proposal_hash?: string;
  order_id?: string;
  owner: string;
}
export interface Approval {
  id: string;
  status: string;
  kind: string;
  required_role: string;
  proposal_hash: string;
  case_version: number;
  actor_id?: string;
}
export interface Run {
  id: string;
  status: string;
  cancelled: boolean;
}
export interface Snapshot {
  case: Case;
  messages: Message[];
  attachments: Attachment[];
  approvals: Approval[];
  events: PublicEvent[];
  runs: Run[];
  orders: {
    id: string;
    number: string;
    status: string;
    version: number;
    fields: Record<string, unknown>;
  }[];
  operator_events: {
    id: string;
    kind: string;
    note: string;
    actor_id: string;
  }[];
  inbox: { event_id: string; payload: Record<string, unknown> }[];
}
export interface Session {
  actor: { id: string; organization_id: string; roles: string[] };
  auth_mode: string;
  synthetic: boolean;
  ai: { configured: boolean; verified: boolean; model: string; status: string };
  customers: { id: string; name: string; blocked: boolean }[];
  limits: { upload_mb: number; attachments: number };
}
