// World Model service: the Meterless reference implementation, unchanged,
// served over local HTTP for the project state (agent/world_model.py, task 7).
//
// The reference is loaded from external/meterless (Apache-2.0, not copied in
// this repository: scripts/engine_service.py fetches it). The official
// conformance suite runs against that same module (scripts/engines_conformance.py).
//
// One namespace per project, persisted as an append-only event log in
// .state/world-model/.world/<project>.json. Each state record (role, task,
// milestone, ticket, report, decision, fact) is an entity keyed by its stable
// id, so writing it again is an upsert, never a duplicate (S5). Single-target
// links are bitemporal edges: a task's owner, a report's task and author, the
// decision a decision replaces; a new owner closes the old edge, nothing is
// deleted. The project's version, ingested refs and history are the project
// context. Writes go through the reference's single-writer queue.
//
// Usage: python scripts/engine_service.py world_model
// (WORLD_MODEL_PORT, WORLD_MODEL_DATA_DIR, WORLD_MODEL_REFERENCE)

import http from "node:http";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..", "..");
const referencePath = process.env.WORLD_MODEL_REFERENCE
  ?? path.join(root, "external", "meterless", "engines", "world-model", "reference", "src", "index.ts");
const port = Number(process.env.WORLD_MODEL_PORT ?? 8766);
const dataDir = process.env.WORLD_MODEL_DATA_DIR ?? path.join(root, ".state", "world-model");
const SYSTEM = "atlas";

const { WorldModel, externalId } = await import(pathToFileURL(referencePath).href);

const models = new Map<string, any>();

class BadRequest extends Error {}

function model(project: string): any {
  if (!/^[a-z0-9-]+$/.test(project)) throw new BadRequest(`invalid project name: ${project}`);
  if (!models.has(project)) {
    // Conflicts between decisions are never settled here: the decision rules
    // (agent/decisions.py) and a person arbitrate them (rule 3).
    models.set(project, new WorldModel({ namespace: project, storage: "local", directory: dataDir, conflictPolicy: "manual" }));
  }
  return models.get(project);
}

function entityId(table: string, key: string): string {
  return externalId(table, SYSTEM, key);
}

function readState(project: string): unknown {
  const world = model(project);
  const graph = world.view("graph");
  const records: Record<string, unknown[]> = {};
  for (const entity of graph.query({})) {
    if (entity.attrs.record === undefined) continue;
    (records[entity.type] ??= []).push(entity.attrs.record);
  }
  const context = world.stateShape() as any;
  const meta = (context.contexts ?? []).find((c: any) => c.id === externalId("project", SYSTEM, project));
  return { project, meta: meta?.attrs ?? null, records, events: world.events().length };
}

async function commit(project: string, body: any): Promise<unknown> {
  const world = model(project);
  const at = String(body.at ?? "");
  if (!at) throw new BadRequest("missing field: at");
  const source = { kind: "agent", by: "writer", at, runId: body.runId };
  const before = world.events().length;
  for (const upsert of body.upserts ?? []) {
    await world.upsertEntity({ type: upsert.table, externalKey: { system: SYSTEM, id: upsert.key }, attrs: { record: upsert.record }, source });
  }
  for (const link of body.links ?? []) {
    await world.relate({ from: entityId(link.from.table, link.from.key), type: link.type, to: entityId(link.to.table, link.to.key), source });
  }
  await world.upsertContext({ type: "project", externalKey: { system: SYSTEM, id: project }, attrs: body.meta ?? {}, source });
  return { events: world.events().length - before };
}

function edges(project: string, url: URL): unknown {
  const world = model(project);
  const shape = world.stateShape() as any;
  const type = url.searchParams.get("type");
  return {
    edges: (shape.relationships ?? []).filter((r: any) => !type || r.type === type)
      .map((r: any) => ({ from: r.from, type: r.type, to: r.to, validFrom: r.validFrom, validTo: r.validTo ?? null })),
  };
}

async function route(method: string, url: URL, body: any): Promise<unknown> {
  if (method === "GET" && url.pathname === "/health") return { ok: true, engine: "world-model-reference" };
  const match = url.pathname.match(/^\/projects\/([^/]+)\/(state|commit|edges|audit)$/);
  if (!match) return undefined;
  const [, project, action] = match;
  if (method === "GET" && action === "state") return readState(project);
  if (method === "POST" && action === "commit") return commit(project, body);
  if (method === "GET" && action === "edges") return edges(project, url);
  if (method === "GET" && action === "audit") return { audit: model(project).audit() };
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
    const url = new URL(request.url ?? "/", "http://localhost");
    const result = await route(request.method ?? "GET", url, await readBody(request));
    if (result === undefined) reply(response, 404, { error: `no route for ${request.method} ${url.pathname}` });
    else reply(response, 200, result);
  } catch (error) {
    reply(response, error instanceof BadRequest ? 400 : 500, { error: (error as Error).message });
  }
});

server.listen(port, "127.0.0.1", () => {
  console.log(`World Model service on http://127.0.0.1:${port} (reference: ${referencePath}, data: ${dataDir})`);
});
