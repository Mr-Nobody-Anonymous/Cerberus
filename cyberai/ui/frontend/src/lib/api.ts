/**
 * Typed API client for the CERBERUS /api/v1 surface.
 * All frontend data flows through these functions.
 */

const BASE = "/api/v1";

class ApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(`API ${status}: ${detail}`);
  }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch { /* non-JSON error */ }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

const get = <T>(path: string) => req<T>(path);
const post = <T>(path: string, body?: unknown) =>
  req<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined });
const patch = <T>(path: string, body: unknown) =>
  req<T>(path, { method: "PATCH", body: JSON.stringify(body) });
const del = <T>(path: string) => req<T>(path, { method: "DELETE" });

/* ---------------------------------------------------------------- types */

export interface ChatSummary {
  id: string;
  title: string;
  status: string;
  mode: string;
  model: string | null;
  message_count: number;
  created_at: string;
  updated_at?: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "system" | "event";
  content: string;
  model: string | null;
  mode: string | null;
  created_at: string;
  metadata?: Record<string, unknown>;
}

export interface SessionRow {
  id: string;
  title: string;
  objective: string;
  target_id: string | null;
  status: string;
  kind: string;
  mode?: string;
  forked_from?: string | null;
  started_at: string | null;
  completed_at: string | null;
  findings_count?: number;
}

export interface Finding {
  id: string;
  session_id: string;
  observation: string;
  source: string;
  status: string;
  created_at?: string;
  [k: string]: unknown;
}

export interface Target {
  id: string;
  host: string;
  port: number;
  allowed: boolean;
  environment?: string;
  protocol?: string;
  description?: string;
  allowed_actions?: string[];
  state: "ACTIVE" | "OFFLINE" | "UNAUTHORIZED";
  reachable: boolean;
  [k: string]: unknown;
}

export interface AgentInfo {
  name: string;
  role: string;
  capability: string;
  calls: number;
  success_rate: number | null;
}

export interface ToolInfo {
  name: string;
  present: boolean;
  category: string;
  description: string;
}

export interface ModelInfo {
  alias: string;
  provider: string;
  model: string;
  status: string;
  purpose: string[];
  capabilities: Record<string, unknown>;
  locality: string;
}

export interface CommandCatalogEntry {
  name: string;
  description: string;
  category: string;
  usage?: string;
}

export interface CommandResultDto {
  ok: boolean;
  command: string;
  error?: string;
  data?: Record<string, unknown>;
  [k: string]: unknown;
}

export interface WorkspaceEntry {
  name: string;
  path: string;
  type: "file" | "directory";
  size?: number;
  children?: WorkspaceEntry[];
}

export interface MissionLaunch {
  status: string;
  objective: string;
  mode: string;
  session_id: string;
}

export interface SecurityCenter {
  policy: {
    mode: string;
    description: string;
    targets_registered: number;
    targets_authorized: number;
  };
  blocked_actions: Array<Record<string, unknown>>;
  approvals_pending: number;
  recent_events: Array<{ type: string; data: Record<string, unknown>; ts?: string }>;
}

export interface Approval {
  id: string;
  action: string;
  reason?: string;
  risk?: string;
  status: string;
  timestamp?: string;
  [k: string]: unknown;
}

/** One memory entry from semantic_search (MemoryEntry.to_dict()). */
export interface MemorySearchResult {
  memory_id: string;
  memory_type: string;
  content: string;
  metadata: Record<string, unknown>;
  confidence: number;
  success_rate: number;
  verification: string;
  timestamp: string;
  last_accessed: string;
  access_count: number;
  similarity?: number;
}

/** One evidence record (EvidenceManager JSON files). */
export interface EvidenceRecord {
  id: string;
  session_id: string;
  type: string;
  source: string;
  verification_status: string;
  confidence: number;
  timestamp: string;
  content: unknown;
  [k: string]: unknown;
}

/* ---------------------------------------------------------------- chats */

export const chatsApi = {
  list: (q = "") =>
    get<{ chats: ChatSummary[]; total: number }>(`/chats${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  create: (title?: string, mode = "SIMULATE", model?: string) =>
    post<{ chat: ChatSummary }>("/chats", { title, mode, model }),
  get: (id: string) => get<{ chat: ChatSummary; messages: ChatMessage[] }>(`/chats/${id}`),
  patch: (id: string, body: { title?: string; status?: string }) =>
    patch<{ chat: ChatSummary }>(`/chats/${id}`, body),
  remove: (id: string) => del<{ deleted: string }>(`/chats/${id}`),
  messages: (id: string) => get<{ messages: ChatMessage[] }>(`/chats/${id}/messages`),
  send: (id: string, content: string) =>
    post<{ user_message: ChatMessage; assistant_message: ChatMessage }>(
      `/chats/${id}/messages`, { content }),
  fork: (id: string, title?: string) =>
    post<{ chat: ChatSummary; forked_from: string }>(`/chats/${id}/fork`, { title }),
};

/* ------------------------------------------------------------- sessions */

export const sessionsApi = {
  list: (params: { q?: string; status?: string; kind?: string } = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v) as [string, string][]);
    const s = qs.toString();
    return get<{ sessions: SessionRow[]; total: number }>(`/sessions${s ? `?${s}` : ""}`);
  },
  get: (id: string) => get<Record<string, unknown>>(`/sessions/${id}`),
  rename: (id: string, title: string) =>
    patch<{ session: SessionRow }>(`/sessions/${id}`, { title }),
  fork: (id: string, title?: string) =>
    post<{ session: SessionRow }>(`/sessions/${id}/fork`, { title }),
};

/* ------------------------------------------------------------- missions */

export const missionsApi = {
  list: (q = "") =>
    get<{ missions: SessionRow[]; total: number }>(`/missions${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  launch: (objective: string, mode = "SIMULATE", targetId?: string) =>
    post<MissionLaunch>("/missions", { objective, mode, target_id: targetId }),
  get: (id: string) =>
    get<{ session: SessionRow; findings: Finding[]; live: unknown; mode: string }>(`/missions/${id}`),
  stop: (id: string) => post<{ status: string }>(`/missions/${id}/stop`),
  resume: (id: string) => post<{ status: string }>(`/missions/${id}/resume`),
};

/* ------------------------------------------------------------- findings */

export const findingsApi = {
  list: (params: { status?: string; q?: string; session_id?: string; limit?: number } = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== "")
        .map(([k, v]) => [k, String(v)]) as [string, string][]);
    const s = qs.toString();
    return get<{ findings: Finding[]; total: number }>(`/findings${s ? `?${s}` : ""}`);
  },
  updateStatus: (id: string, status: string) =>
    patch<{ id: string; status: string }>(`/findings/${id}`, { status }),
  /** Alias kept for readability at call sites. */
  setStatus: (id: string, status: string) =>
    patch<{ id: string; status: string }>(`/findings/${id}`, { status }),
};

/* -------------------------------------------------------------- targets */

export const targetsApi = {
  list: () => get<{ targets: Target[]; total: number }>("/targets"),
  setAllowed: (id: string, allowed: boolean) =>
    patch<{ id: string; allowed: boolean }>(`/targets/${id}`, { allowed }),
  authorize: (id: string) =>
    patch<{ id: string; allowed: boolean }>(`/targets/${id}`, { allowed: true }),
  revoke: (id: string) =>
    patch<{ id: string; allowed: boolean }>(`/targets/${id}`, { allowed: false }),
};

/* --------------------------------------------------------------- agents */

export const agentsApi = {
  list: () => get<{ agents: AgentInfo[] }>("/agents"),
  get: (name: string) => get<AgentInfo & { performances: unknown }>(`/agents/${name}`),
};

/* ---------------------------------------------------------------- tools */

export const toolsApi = {
  list: () => get<{ tools: ToolInfo[]; total: number }>("/tools"),
  get: (name: string) => get<Record<string, unknown>>(`/tools/${name}`),
  /** Per-tool health check (GET /tools/{name} returns {health: string}). */
  health: (name: string) =>
    get<{ name: string; present: boolean; health: string }>(`/tools/${name}`),
};

/* --------------------------------------------------------------- models */

export const modelsApi = {
  list: () => get<{ models: ModelInfo[] }>("/models"),
  routing: () => get<{ routes: Record<string, string> }>("/models/routing"),
  getRouting: () => get<{ routes: Record<string, string> }>("/models/routing"),
  setRoute: (taskType: string, modelAlias: string) =>
    patch<{ ok: boolean; routes: Record<string, string> }>("/models/routing",
      { task_type: taskType, model_alias: modelAlias }),
  setRouting: (taskType: string, modelAlias: string) =>
    patch<{ ok: boolean; routes: Record<string, string> }>("/models/routing",
      { task_type: taskType, model_alias: modelAlias }),
};

/* ------------------------------------------------------------- security */

export const securityApi = {
  center: () => get<SecurityCenter>("/security"),
  approvals: () => get<{ pending: Approval[]; decided: Approval[] }>("/security/approvals"),
  approve: (id: string) => post<{ id: string; status: string }>(`/security/approvals/${id}/approve`),
  deny: (id: string) => post<{ id: string; status: string }>(`/security/approvals/${id}/deny`),
};

/* --------------------------------------------------------------- memory */

export const memoryApi = {
  stats: () => get<{ stats: { total: number; by_type: Record<string, number> } }>("/memory/stats"),
  search: (q: string, limit = 20) =>
    get<{ results: MemorySearchResult[]; query: string }>(
      `/memory/search?q=${encodeURIComponent(q)}&limit=${limit}`),
};

/* --------------------------------------------------------------- events */

export interface EventDto {
  type: string;
  data: Record<string, unknown>;
  ts?: number | string; // epoch seconds on the SSE stream
  timestamp?: string;   // ISO-8601 on the pollable feed (Event.to_dict)
  [k: string]: unknown;
}

export const eventsApi = {
  feed: (since = "", limit = 200) =>
    get<{ events: EventDto[]; stats: Record<string, unknown> }>(
      `/events${since ? `?since=${encodeURIComponent(since)}` : `?limit=${limit}`}`),
};

/** Subscribe to the live SSE stream. Returns a disposer. */
export function subscribeEvents(onEvent: (ev: EventDto) => void,
                                 onStatus?: (up: boolean) => void): () => void {
  const es = new EventSource(`${BASE}/events/stream`);
  es.onopen = () => onStatus?.(true);
  es.onerror = () => onStatus?.(false);
  es.onmessage = (m) => {
    try { onEvent(JSON.parse(m.data)); } catch { /* malformed frame */ }
  };
  return () => es.close();
}

/* ------------------------------------------------------------ workspace */

export const workspaceApi = {
  tree: (path = "", depth = 2) =>
    get<{ path: string; entries: WorkspaceEntry[] }>(
      `/workspace/tree?path=${encodeURIComponent(path)}&depth=${depth}`),
  file: (path: string) => req<string>(`/workspace/file?path=${encodeURIComponent(path)}`),
};

/* ------------------------------------------------------------ commands */

export const commandsApi = {
  catalog: () =>
    get<{ commands: CommandCatalogEntry[]; categories: Record<string, CommandCatalogEntry[]>; total: number }>(
      "/commands"),
  get: (name: string) => get<{ command: Record<string, unknown> }>(`/commands/${name}`),
  execute: (input: string) => post<CommandResultDto>("/commands/execute", { input }),
};

/* ------------------------------------------------------------- evidence */

export const evidenceApi = {
  list: (sessionId = "", limit = 100) =>
    get<{ evidence: EvidenceRecord[]; total: number }>(
      `/evidence${sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : `?limit=${limit}`}`),
  get: (id: string) => get<EvidenceRecord>(`/evidence/${id}`),
};
