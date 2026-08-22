import type {
  ApiRecord,
  CreateProjectInput,
  GenerateScriptInput,
  Project,
  StreamEvent,
} from "./types";

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

export function mediaUrl(path: string): string {
  if (!path) return "";
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

export async function getShowcase(): Promise<{
  project_id: string;
  name: string;
  topic: string;
  avatar_vibe: string;
  tone: string;
  script: string;
  entities: Record<string, string>;
  files: Record<string, string>;
}> {
  return json("/api/showcase", { cache: "no-store" });
}

async function request(path: string, init?: RequestInit): Promise<Response> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      Accept: "application/json, text/event-stream",
      ...(!(init?.body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(detail || `Request failed with status ${response.status}`);
  }
  return response;
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await request(path, init);
  return response.json() as Promise<T>;
}

export async function consumeSSE(
  response: Response,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  if (!response.body) throw new Error("The server returned an empty stream.");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const emit = (block: string) => {
    const data = block
      .split(/\r?\n/)
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart())
      .join("\n");
    if (!data || data === "[DONE]") return;
    try {
      onEvent(JSON.parse(data) as StreamEvent);
    } catch {
      onEvent({ type: "message", message: data });
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const blocks = buffer.split(/\r?\n\r?\n/);
    buffer = blocks.pop() || "";
    blocks.forEach(emit);
    if (done) break;
  }
  if (buffer.trim()) emit(buffer);
}

export async function getCollection(path: string): Promise<ApiRecord[]> {
  const payload = await json<unknown>(path, { cache: "no-store" });
  if (Array.isArray(payload)) return payload as ApiRecord[];
  if (payload && typeof payload === "object") {
    const record = payload as Record<string, unknown>;
    for (const key of ["items", "data", "results", "projects", "avatars", "templates", "history"]) {
      if (Array.isArray(record[key])) return record[key] as ApiRecord[];
    }
  }
  return [];
}

export const getProject = (id: string) =>
  json<Project>(`/api/projects/${encodeURIComponent(id)}`, { cache: "no-store" });

export const createProject = (input: CreateProjectInput) =>
  json<Project>("/api/projects", {
    method: "POST",
    body: JSON.stringify(input),
  });

export const updateProject = (id: string, input: Partial<CreateProjectInput>) =>
  json<Project>(`/api/projects/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });

export async function generateScript(
  input: GenerateScriptInput,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await request("/api/generate-script", {
    method: "POST",
    body: JSON.stringify({
      target_prompt: input.topic,
      avatar_vibe: input.avatar_vibe,
      tone: input.tone,
      project_id: input.project_id,
    }),
    signal,
  });
  await consumeSSE(response, onEvent);
}

export async function renderVideo(
  formData: FormData,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await request("/api/render-video", { method: "POST", body: formData, signal });
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("text/event-stream")) {
    await consumeSSE(response, onEvent);
    return;
  }
  const payload = (await response.json()) as StreamEvent;
  onEvent(payload);
}

export async function generateAvatar(input: {
  name: string;
  prompt: string;
  vibe?: string;
}): Promise<ApiRecord> {
  return json<ApiRecord>("/api/avatars/generate", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function uploadAvatar(formData: FormData): Promise<ApiRecord> {
  const response = await request("/api/avatars/upload", {
    method: "POST",
    body: formData,
  });
  return response.json() as Promise<ApiRecord>;
}

export async function deleteAvatar(id: string): Promise<void> {
  await request(`/api/avatars/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}
