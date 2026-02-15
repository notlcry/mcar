/**
 * WebServer — Express HTTP + WebSocket server for mcar control console.
 *
 * REST API:
 *   GET  /api/status       — state snapshot
 *   GET  /api/capabilities — capability list
 *   GET  /api/memories     — memory list
 *   POST /api/invoke       — invoke a capability
 *   POST /api/stop         — trigger emergency stop
 *   POST /api/mode         — switch mode
 *   POST /api/chat         — text conversation
 *   GET  /api/audit        — audit log entries
 *
 * WebSocket /ws:
 *   Broadcasts: state changes, audit events, FSM transitions
 *   Receives: chat, stop, mode messages
 */

import { createServer, type Server } from "node:http";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { readFileSync, existsSync } from "node:fs";
import express, { type Request, type Response } from "express";
import { WebSocketServer, type WebSocket } from "ws";

import type { WebConfig } from "../config/config.js";
import type { StateService } from "../state/state-service.js";
import type { CapabilityRegistry } from "../capability/registry.js";
import type { CapabilityExecutor } from "../capability/executor.js";
import type { PolicyEngine } from "../safety/policy-engine.js";
import type { MemoryService } from "../memory/memory-service.js";
import type { StopHandler } from "../safety/stop-handler.js";
import type { ActionDispatcher } from "../orchestrator/action-dispatcher.js";
import type { SessionController } from "../orchestrator/session-controller.js";
import type { ModuleBridge } from "../ipc/module-bridge.js";
import type { AuditLogger } from "../audit/audit-logger.js";
import type { Mode } from "../state/types.js";
import type { SkillEngine } from "../skill/skill-engine.js";
import type { HealthMonitor } from "../health/health-monitor.js";
import type { SessionRecorder } from "../audit/session-recorder.js";
import type { ModuleWatchdog } from "../health/module-watchdog.js";
import type { RuleEngine } from "../automation/rule-engine.js";
import type { PerformanceTracker } from "../observability/performance-tracker.js";
import type { MemoryType } from "../memory/types.js";
import { exportMemories, importMemories, type ExportResult } from "../memory/memory-export.js";
import type { WsMessage, StatusResponse, InvokeRequest, ChatRequest, ModeRequest } from "./types.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

export class WebServer {
  private app: ReturnType<typeof express>;
  private server: Server | null = null;
  private wss: WebSocketServer | null = null;
  private clients = new Set<WebSocket>();

  constructor(
    private readonly config: WebConfig,
    private readonly stateService: StateService,
    private readonly registry: CapabilityRegistry,
    private readonly executor: CapabilityExecutor,
    private readonly policyEngine: PolicyEngine,
    private readonly memoryService: MemoryService,
    private readonly stopHandler: StopHandler,
    private readonly dispatcher: ActionDispatcher,
    private readonly session: SessionController,
    private readonly bridge: ModuleBridge,
    private readonly auditLogger: AuditLogger,
    private readonly skillEngine?: SkillEngine,
    private readonly healthMonitor?: HealthMonitor,
    private readonly sessionRecorder?: SessionRecorder,
    private readonly watchdog?: ModuleWatchdog,
    private readonly ruleEngine?: RuleEngine,
    private readonly performanceTracker?: PerformanceTracker
  ) {
    this.app = express();
    this.setupMiddleware();
    this.setupRoutes();
  }

  async start(): Promise<void> {
    this.server = createServer(this.app);
    this.setupWebSocket();
    this.setupEventForwarding();

    return new Promise((resolve) => {
      this.server!.listen(this.config.port, this.config.host, () => {
        console.log(`[WebServer] Running on http://${this.config.host}:${this.config.port}`);
        resolve();
      });
    });
  }

  async stop(): Promise<void> {
    for (const client of this.clients) {
      client.close();
    }
    this.clients.clear();

    if (this.wss) {
      this.wss.close();
      this.wss = null;
    }

    return new Promise((resolve) => {
      if (this.server) {
        this.server.close(() => resolve());
        this.server = null;
      } else {
        resolve();
      }
    });
  }

  private setupMiddleware(): void {
    this.app.use(express.json());

    // Serve static files
    const publicDir = resolve(__dirname, "public");
    if (existsSync(publicDir)) {
      this.app.use(express.static(publicDir));
    }
  }

  private setupRoutes(): void {
    // GET /api/status
    this.app.get("/api/status", (_req: Request, res: Response) => {
      const snapshot = this.stateService.getSnapshot();
      const status: StatusResponse = {
        ...snapshot,
        registeredModules: this.bridge.getRegisteredModules(),
      };
      res.json(status);
    });

    // GET /api/capabilities
    this.app.get("/api/capabilities", (_req: Request, res: Response) => {
      const caps = this.registry.getCapabilitySummaries();
      res.json(caps);
    });

    // GET /api/memories
    this.app.get("/api/memories", (_req: Request, res: Response) => {
      const memories = this.memoryService.listSummaries();
      res.json(memories);
    });

    // POST /api/invoke
    this.app.post("/api/invoke", async (req: Request, res: Response) => {
      const body = req.body as InvokeRequest;
      if (!body.capability_id) {
        res.status(400).json({ error: "capability_id required" });
        return;
      }
      try {
        const result = await this.executor.execute(body.capability_id, body.params ?? {});
        res.json(result);
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        res.status(500).json({ success: false, error: message });
      }
    });

    // POST /api/stop
    this.app.post("/api/stop", async (_req: Request, res: Response) => {
      await this.stopHandler.triggerStop("web");
      res.json({ ok: true, message: "Emergency stop triggered" });
    });

    // POST /api/mode
    this.app.post("/api/mode", (req: Request, res: Response) => {
      const body = req.body as ModeRequest;
      const validModes: Mode[] = ["normal", "safety", "kid", "debug", "mute"];
      if (!validModes.includes(body.mode)) {
        res.status(400).json({ error: `Invalid mode: ${body.mode}` });
        return;
      }
      this.stateService.setMode(body.mode);
      res.json({ ok: true, mode: body.mode });
    });

    // POST /api/chat
    this.app.post("/api/chat", async (req: Request, res: Response) => {
      const body = req.body as ChatRequest;
      if (!body.text) {
        res.status(400).json({ error: "text required" });
        return;
      }
      try {
        const response = await this.dispatcher.dispatch(body.text);
        res.json({ response });
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        res.status(500).json({ error: message });
      }
    });

    // GET /api/audit
    this.app.get("/api/audit", (_req: Request, res: Response) => {
      const entries = this.auditLogger.getRecent(100);
      res.json(entries);
    });

    // ─── Memory management endpoints ──────────────────────────

    // GET /api/memories/search?q=keyword&type=preference
    this.app.get("/api/memories/search", (req: Request, res: Response) => {
      const q = req.query.q as string | undefined;
      if (!q) {
        res.status(400).json({ error: "query parameter 'q' required" });
        return;
      }
      const typeFilter = req.query.type as string | undefined;
      const types = typeFilter ? [typeFilter as MemoryType] : undefined;
      const results = this.memoryService.searchByKeywords(q, types);
      res.json(results);
    });

    // DELETE /api/memories/:id
    this.app.delete("/api/memories/:id", (req: Request, res: Response) => {
      const id = req.params.id;
      const entry = this.memoryService.getById(id);
      if (!entry) {
        res.status(404).json({ error: "Memory not found" });
        return;
      }
      this.memoryService.delete(id);
      this.auditLogger.info("web", "memory.delete", { id, summary: entry.summary });
      res.json({ ok: true, deleted: id });
    });

    // POST /api/memories/clear
    this.app.post("/api/memories/clear", (req: Request, res: Response) => {
      const body = req.body as { type?: string };
      if (!body.type) {
        res.status(400).json({ error: "type required" });
        return;
      }
      const validTypes = ["preference", "fact", "rule", "device", "location", "task", "incident", "skill_state", "other"];
      if (!validTypes.includes(body.type)) {
        res.status(400).json({ error: `Invalid type: ${body.type}` });
        return;
      }
      const count = this.memoryService.clearByType(body.type as MemoryType);
      this.auditLogger.info("web", "memory.clear", { type: body.type, count });
      res.json({ ok: true, cleared: count });
    });

    // GET /api/memories/export
    this.app.get("/api/memories/export", (_req: Request, res: Response) => {
      const exported = exportMemories(this.memoryService);
      res.json(exported);
    });

    // POST /api/memories/import
    this.app.post("/api/memories/import", (req: Request, res: Response) => {
      const data = req.body as ExportResult;
      if (!data.version || !data.entries) {
        res.status(400).json({ error: "Invalid import data" });
        return;
      }
      const result = importMemories(this.memoryService, data);
      this.auditLogger.info("web", "memory.import", result);
      res.json(result);
    });

    // ─── Module management endpoints ──────────────────────────

    // GET /api/modules
    this.app.get("/api/modules", (_req: Request, res: Response) => {
      const modules = this.registry.listModules().map((m) => ({
        module_id: m.manifest.module_id,
        version: m.manifest.module_version,
        description: m.manifest.description,
        capabilities: m.manifest.capabilities,
        enabled: m.enabled,
      }));
      res.json(modules);
    });

    // POST /api/modules/:id/enable
    this.app.post("/api/modules/:id/enable", (req: Request, res: Response) => {
      const moduleId = req.params.id;
      this.registry.setModuleEnabled(moduleId, true);
      this.auditLogger.info("web", "module.enable", { moduleId });
      res.json({ ok: true, moduleId, enabled: true });
    });

    // POST /api/modules/:id/disable
    this.app.post("/api/modules/:id/disable", (req: Request, res: Response) => {
      const moduleId = req.params.id;
      this.registry.setModuleEnabled(moduleId, false);
      this.auditLogger.info("web", "module.disable", { moduleId });
      res.json({ ok: true, moduleId, enabled: false });
    });

    // ─── Skill endpoints ──────────────────────────────────────

    // GET /api/skills
    this.app.get("/api/skills", (_req: Request, res: Response) => {
      if (!this.skillEngine) {
        res.json([]);
        return;
      }
      const skills = this.skillEngine.listSkills().map((s) => ({
        skill_id: s.skill_id,
        name: s.name,
        description: s.description,
        risk_level: s.risk_level,
        parameters: s.parameters,
        steps_count: s.steps.length,
      }));
      res.json(skills);
    });

    // POST /api/skills/:id/execute
    this.app.post("/api/skills/:id/execute", async (req: Request, res: Response) => {
      if (!this.skillEngine) {
        res.status(404).json({ error: "Skill engine not available" });
        return;
      }
      const skillId = req.params.id;
      const params = req.body?.params ?? {};
      try {
        const result = await this.skillEngine.execute(skillId, params);
        res.json(result);
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        res.status(500).json({ success: false, error: message });
      }
    });

    // ─── Health endpoint ───────────────────────────────────────

    // GET /api/health
    this.app.get("/api/health", (_req: Request, res: Response) => {
      if (!this.healthMonitor) {
        res.json({ overall: "unknown", modules: [], uptime_ms: 0, timestamp: new Date().toISOString() });
        return;
      }
      res.json(this.healthMonitor.getSystemHealth());
    });

    // GET /api/audit/export
    this.app.get("/api/audit/export", (_req: Request, res: Response) => {
      const entries = this.auditLogger.getRecent(10000);
      res.json({
        version: "1.0.0",
        exported_at: new Date().toISOString(),
        count: entries.length,
        entries,
      });
    });

    // ─── Session replay endpoints ────────────────────────────────

    // GET /api/sessions
    this.app.get("/api/sessions", (_req: Request, res: Response) => {
      if (!this.sessionRecorder) {
        res.json([]);
        return;
      }
      const limit = parseInt((_req.query.limit as string) || "20", 10);
      res.json(this.sessionRecorder.listSessions(limit));
    });

    // GET /api/sessions/:id/replay
    this.app.get("/api/sessions/:id/replay", (req: Request, res: Response) => {
      if (!this.sessionRecorder) {
        res.status(404).json({ error: "Session recorder not available" });
        return;
      }
      const replay = this.sessionRecorder.getReplay(req.params.id);
      if (!replay) {
        res.status(404).json({ error: "Session not found" });
        return;
      }
      res.json(replay);
    });

    // ─── Watchdog endpoints ──────────────────────────────────

    // GET /api/watchdog
    this.app.get("/api/watchdog", (_req: Request, res: Response) => {
      if (!this.watchdog) {
        res.json([]);
        return;
      }
      res.json(this.watchdog.getStatus());
    });

    // ─── Metrics endpoint ─────────────────────────────────

    // GET /api/metrics
    this.app.get("/api/metrics", (_req: Request, res: Response) => {
      if (!this.performanceTracker) {
        res.json([]);
        return;
      }
      res.json(this.performanceTracker.getAllMetrics());
    });

    // ─── Rule engine endpoints ─────────────────────────────

    // GET /api/rules/status
    this.app.get("/api/rules/status", (_req: Request, res: Response) => {
      if (!this.ruleEngine) {
        res.json({ available: false });
        return;
      }
      res.json({ available: true });
    });

    // POST /api/rules/evaluate
    this.app.post("/api/rules/evaluate", (_req: Request, res: Response) => {
      if (!this.ruleEngine) {
        res.status(404).json({ error: "Rule engine not available" });
        return;
      }
      const triggered = this.ruleEngine.evaluate();
      res.json({ triggered });
    });

    // Fallback: serve index.html for SPA
    this.app.get("/", (_req: Request, res: Response) => {
      const indexPath = resolve(__dirname, "public", "index.html");
      if (existsSync(indexPath)) {
        res.sendFile(indexPath);
      } else {
        res.status(200).send("mcar Web Console - public/index.html not found");
      }
    });
  }

  private setupWebSocket(): void {
    if (!this.server) return;

    this.wss = new WebSocketServer({ server: this.server, path: "/ws" });

    this.wss.on("connection", (ws: WebSocket) => {
      this.clients.add(ws);

      // Send current state on connect
      const snapshot = this.stateService.getSnapshot();
      this.sendToClient(ws, { type: "state_change", data: snapshot as any });

      ws.on("message", (data: Buffer) => {
        try {
          const msg = JSON.parse(data.toString()) as WsMessage;
          this.handleWsMessage(ws, msg);
        } catch {
          // Ignore invalid messages
        }
      });

      ws.on("close", () => {
        this.clients.delete(ws);
      });
    });
  }

  private handleWsMessage(ws: WebSocket, msg: WsMessage): void {
    switch (msg.type) {
      case "chat":
        this.dispatcher
          .dispatch(msg.data.text as string)
          .then((response) => {
            this.sendToClient(ws, { type: "chat", data: { response } });
          })
          .catch((err) => {
            this.sendToClient(ws, {
              type: "chat",
              data: { error: err instanceof Error ? err.message : String(err) },
            });
          });
        break;
      case "stop":
        this.stopHandler.triggerStop("web");
        break;
      case "mode":
        this.stateService.setMode(msg.data.mode as Mode);
        break;
    }
  }

  private setupEventForwarding(): void {
    // Forward state changes to all WS clients
    this.stateService.onChange((key, value) => {
      this.broadcast({ type: "state_change", data: { key, value } });
    });

    // Forward FSM transitions
    this.session.onTransition((from, to) => {
      this.broadcast({ type: "fsm_transition", data: { from, to } });
    });
  }

  private broadcast(msg: WsMessage): void {
    const payload = JSON.stringify(msg);
    for (const client of this.clients) {
      if (client.readyState === 1) {
        // WebSocket.OPEN
        client.send(payload);
      }
    }
  }

  private sendToClient(ws: WebSocket, msg: WsMessage): void {
    if (ws.readyState === 1) {
      ws.send(JSON.stringify(msg));
    }
  }
}
