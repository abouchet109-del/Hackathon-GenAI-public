// H-MEM service: exposes the Meterless H-MEM reference implementation over local HTTP
// so the Python agents can use the real engine. One HMEM instance per "space"
// (e.g. eval, demo, default), each persisted under HMEM_DIR/<space>/ (state.json + ledger.jsonl).
//
// Endpoints (JSON in, JSON out):
//   GET  /health
//   POST /add       {space, content, tags, source, confidence, layer, event, supersedes?}
//   POST /list      {space, tag?}   every record (optionally with this tag), superseded ones included
//   POST /query     {space, query, topN, threshold}
//   POST /feedback  {space, id, kind: helpful|not_helpful|wrong}
//   POST /ledger    {space, id}
//   POST /sleep/preview {space}
//   POST /reset     {space}
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { HMEM } from "./vendor/hmem-reference/src/index.ts";

const PORT = Number(process.env.HMEM_PORT ?? 8787);
const HOST = process.env.HMEM_HOST ?? "127.0.0.1";
const BASE_DIR = path.resolve(process.env.HMEM_DIR ?? "./.hmem-data");
const spaces = new Map<string, HMEM>();

function spaceName(raw: unknown): string {
  const name = String(raw ?? "default").replace(/[^a-z0-9_-]/gi, "").slice(0, 40);
  return name || "default";
}

function memory(raw: unknown): HMEM {
  const name = spaceName(raw);
  let mem = spaces.get(name);
  if (!mem) {
    mem = new HMEM({ persistDir: path.join(BASE_DIR, name), actor: "osef-agent" });
    spaces.set(name, mem);
  }
  return mem;
}

function send(res: http.ServerResponse, code: number, body: unknown) {
  res.writeHead(code, { "content-type": "application/json" });
  res.end(JSON.stringify(body));
}

const server = http.createServer(async (req, res) => {
  try {
    if (req.method === "GET" && req.url === "/health") return send(res, 200, { ok: true, engine: "meterless-hmem-reference" });
    if (req.method !== "POST") return send(res, 405, { error: "POST only" });
    let raw = "";
    for await (const chunk of req) raw += chunk;
    const body = raw ? JSON.parse(raw) : {};
    const mem = memory(body.space);

    switch (req.url) {
      case "/add": {
        const rec = mem.add({
          content: String(body.content ?? ""),
          tags: Array.isArray(body.tags) ? body.tags.map(String) : [],
          source: String(body.source ?? ""),
          confidence: typeof body.confidence === "number" ? body.confidence : undefined,
          layer: body.layer ?? "working",
          provenance: { origin: body.event ?? "manual", learnedAt: mem.clock(), label: String(body.source ?? "") },
          supersedes: body.supersedes ? String(body.supersedes) : undefined,
        });
        // An explicit replacement: the old record is kept, marked supersededBy, and penalized in ranking.
        if (rec.supersedes && mem.store.get(rec.supersedes)) {
          mem.store.update(rec.supersedes, { supersededBy: rec.id });
        }
        return send(res, 200, { id: rec.id, layer: rec.layer, confidence: rec.confidence, domain: rec.domain,
                                supersedes: rec.supersedes ?? null });
      }
      case "/query": {
        const result = mem.query(String(body.query ?? ""), {
          topN: typeof body.topN === "number" ? body.topN : 5,
          threshold: typeof body.threshold === "number" ? body.threshold : 0.1,
        });
        return send(res, 200, {
          memories: result.memories.map((m) => ({
            id: m.memory.id, content: m.memory.content, tags: m.memory.tags, source: m.memory.source,
            confidence: m.memory.confidence, layer: m.memory.layer, score: Number(m.relevance.toFixed(3)),
            superseded_by: m.memory.supersededBy ?? null,
          })),
          strategy: result.trace.strategy,
        });
      }
      case "/list": {
        const tag = body.tag ? String(body.tag) : null;
        const records = mem.store.all()
          .filter((m) => !tag || m.tags.includes(tag))
          .sort((a, b) => a.timestamp - b.timestamp || Number(a.id.slice(4)) - Number(b.id.slice(4)))
          .map((m) => ({
            id: m.id, content: m.content, tags: m.tags, source: m.source, confidence: m.confidence,
            layer: m.layer, timestamp: m.timestamp, supersedes: m.supersedes ?? null, superseded_by: m.supersededBy ?? null,
          }));
        return send(res, 200, { memories: records });
      }
      case "/feedback": {
        mem.feedback(String(body.id), body.kind);
        return send(res, 200, { ok: true });
      }
      case "/ledger":
        return send(res, 200, { entries: mem.ledger.history(String(body.id)) });
      case "/sleep/preview":
        return send(res, 200, mem.sleep.preview());
      case "/reset": {
        const name = spaceName(body.space);
        spaces.delete(name);
        fs.rmSync(path.join(BASE_DIR, name), { recursive: true, force: true });
        return send(res, 200, { ok: true });
      }
      default:
        return send(res, 404, { error: "unknown route" });
    }
  } catch (error) {
    return send(res, 400, { error: String(error instanceof Error ? error.message : error) });
  }
});

server.listen(PORT, HOST, () => console.log(`H-MEM service on http://${HOST}:${PORT} (data in ${BASE_DIR})`));
