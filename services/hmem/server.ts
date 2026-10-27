// H-MEM service: the Meterless reference implementation, unchanged, served
// over local HTTP for the Python agents (agent/hmem.py, decision D11 bis).
//
// The reference is loaded from external/meterless (Apache-2.0, not copied in
// this repository: scripts/hmem-service.ps1 fetches it). The official
// conformance suite runs against that same module (scripts/hmem-conformance.ps1).
//
// What the service adds around the engine, and nothing else:
// - an external id per memory (tag "ext:<id>"), so writes are idempotent;
// - "supersedes" by external id: the old memory is marked supersededBy the
//   new one with store.update(), so the change is in the trust ledger. This is
//   the controller's validated replacement, not the engine's conflict
//   resolution: conflicts.resolve() and the sleep cycle are never called, so
//   no decision is ever settled automatically (architecture, section 6);
// - a request clock ("at", ms): records carry the date of the decision, and
//   the same requests give the same state.
//
// Usage: npx tsx services/hmem/server.ts   (HMEM_PORT, HMEM_DATA_DIR, HMEM_REFERENCE)

import http from "node:http";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..", "..");
const referencePath = process.env.HMEM_REFERENCE
  ?? path.join(root, "external", "meterless", "engines", "hmem", "reference", "src", "index.ts");
const port = Number(process.env.HMEM_PORT ?? 8765);
const dataDir = process.env.HMEM_DATA_DIR ?? path.join(root, ".state", "hmem");
const ACTOR = "atlas";

const { HMEM, DEFAULTS } = await import(pathToFileURL(referencePath).href);

let now = Date.now();
const hmem = new HMEM({ clock: () => now, persistDir: dataDir, actor: ACTOR });

class BadRequest extends Error {}

function byExternalId(externalId: string): any {
  const tag = `ext:${externalId}`;
  return hmem.store.all().find((m: any) => m.tags.includes(tag));
}

function withoutEmbedding(memory: any): any {
  const { embedding, ...rest } = memory;
  return rest;
}

function required(body: any, field: string): any {
  if (body[field] === undefined || body[field] === null) throw new BadRequest(`missing field: ${field}`);
  return body[field];
}

function addMemory(body: any): { memory: any; created: boolean } {
  const externalId = String(required(body, "externalId"));
  const existing = byExternalId(externalId);
  if (existing) return { memory: withoutEmbedding(existing), created: false };
  const old = body.supersedesExternalId ? byExternalId(body.supersedesExternalId) : undefined;
  const provenance = required(body, "provenance");
  let memory;
  try {
    memory = hmem.add({
      content: String(required(body, "content")),
      layer: required(body, "layer"),
      tags: [`ext:${externalId}`, ...(body.tags ?? [])],
      confidence: Number(required(body, "confidence")),
      source: String(body.source ?? ""),
      provenance: { origin: provenance.origin, label: provenance.label, refs: provenance.refs ?? [], learnedAt: now },
      supersedes: old?.id,
    });
  } catch (error) {
    // The engine rejects a record with no source by construction.
    throw new BadRequest((error as Error).message);
  }
  if (old) hmem.store.update(old.id, { supersededBy: memory.id });
  return { memory: withoutEmbedding(memory), created: true };
}

function findMemories(tags: string[]): any[] {
  return hmem.store.all()
    .filter((m: any) => tags.every((t) => m.tags.includes(t)))
    .map(withoutEmbedding);
}

// The reference ranking formula (retrieval.scoreOne), restricted to one layer
// so a lesson of the organisation is never mixed with the project's facts.
function query(body: any): { memories: any[] } {
  const text = String(required(body, "query"));
  const topN = Number(body.topN ?? DEFAULTS.retrievalTopN);
  const threshold = Number(body.threshold ?? DEFAULTS.retrievalThreshold);
  const scored = hmem.store.all()
    .filter((m: any) => !body.layer || m.layer === body.layer)
    .map((m: any) => ({ memory: m, relevance: hmem.retrieval.scoreOne(m, text) }))
    .filter((s: any) => s.relevance >= threshold)
    .sort((a: any, b: any) => b.relevance - a.relevance || a.memory.id.localeCompare(b.memory.id))
    .slice(0, topN);
  for (const { memory } of scored) {
    hmem.store.touch(memory.id);
    hmem.ledger.log(memory.id, "read", ACTOR, { details: { query: text } });
  }
  hmem.store.persist();
  return {
    memories: scored.map((s: any) => ({ memory: withoutEmbedding(s.memory), relevance: Number(s.relevance.toFixed(4)) })),
  };
}

function route(method: string, url: URL, body: any): unknown {
  if (method === "GET" && url.pathname === "/health") {
    return { ok: true, engine: "hmem-reference", memories: hmem.store.all().length, ledger: hmem.ledger.all().length };
  }
  if (method === "POST" && url.pathname === "/memories") return addMemory(body);
  if (method === "GET" && url.pathname === "/memories") return { memories: findMemories(url.searchParams.getAll("tag")) };
  if (method === "GET" && url.pathname === "/ledger") {
    const ids = new Set(url.searchParams.getAll("memoryId"));
    return { entries: hmem.ledger.all().filter((e: any) => ids.has(e.memoryId)) };
  }
  const feedback = url.pathname.match(/^\/memories\/([^/]+)\/feedback$/);
  if (method === "POST" && feedback) {
    const kind = required(body, "kind");
    if (!["helpful", "not_helpful", "wrong"].includes(kind)) throw new BadRequest(`unknown feedback kind: ${kind}`);
    if (!hmem.store.get(feedback[1])) throw new BadRequest(`unknown memory id ${feedback[1]}`);
    hmem.feedback(feedback[1], kind);
    return { memory: withoutEmbedding(hmem.store.get(feedback[1])) };
  }
  if (method === "POST" && url.pathname === "/query") return query(body);
  return undefined;
}

function readBody(request: http.IncomingMessage): Promise<any> {
  return new Promise((resolve, reject) => {
    let data = "";
    request.on("data", (chunk) => (data += chunk));
    request.on("end", () => {
      try {
        resolve(data ? JSON.parse(data) : {});
      } catch {
        reject(new BadRequest("body is not valid JSON"));
      }
    });
    request.on("error", reject);
  });
}

function reply(response: http.ServerResponse, status: number, payload: unknown): void {
  response.writeHead(status, { "Content-Type": "application/json" });
  response.end(JSON.stringify(payload));
}

const server = http.createServer(async (request, response) => {
  try {
    const body = await readBody(request);
    // One request at a time (Node runs this handler to the end without
    // yielding), so setting the clock here cannot leak into another request.
    now = typeof body.at === "number" ? body.at : Date.now();
    const url = new URL(request.url ?? "/", "http://localhost");
    const result = route(request.method ?? "GET", url, body);
    if (result === undefined) reply(response, 404, { error: `no route for ${request.method} ${url.pathname}` });
    else reply(response, 200, result);
  } catch (error) {
    reply(response, error instanceof BadRequest ? 400 : 500, { error: (error as Error).message });
  }
});

server.listen(port, "127.0.0.1", () => {
  console.log(`H-MEM service on http://127.0.0.1:${port} (reference: ${referencePath}, data: ${dataDir})`);
});
