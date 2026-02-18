/**
 * mcar — main entry point.
 *
 * Initializes all services, starts Python module processes,
 * and provides a CLI text interaction loop.
 */

import { createInterface } from "node:readline";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { existsSync, mkdirSync } from "node:fs";
import { config as loadEnv } from "dotenv";

import { loadConfig } from "./config/config.js";
import { ModuleBridge } from "./ipc/module-bridge.js";
import { CapabilityRegistry } from "./capability/registry.js";
import { CapabilityExecutor } from "./capability/executor.js";
import { PolicyEngine } from "./safety/policy-engine.js";
import { StopHandler } from "./safety/stop-handler.js";
import { MemoryService } from "./memory/memory-service.js";
import { StateService } from "./state/state-service.js";
import { AuditLogger } from "./audit/audit-logger.js";
import { PromptBuilder } from "./agent/prompt-builder.js";
import { AgentRuntime } from "./agent/agent-runtime.js";
import { SessionController } from "./orchestrator/session-controller.js";
import { ActionDispatcher } from "./orchestrator/action-dispatcher.js";
import { VoiceLoop } from "./orchestrator/voice-loop.js";
import { WebServer } from "./web/server.js";
import { SkillEngine } from "./skill/skill-engine.js";
import { BUILTIN_SKILLS } from "./skill/builtin-skills.js";
import { AuditStore } from "./audit/audit-store.js";
import { HealthMonitor } from "./health/health-monitor.js";
import { SessionRecorder } from "./audit/session-recorder.js";
import { CleanupScheduler } from "./health/cleanup-scheduler.js";
import { ModuleWatchdog } from "./health/module-watchdog.js";
import { RuleEngine } from "./automation/rule-engine.js";
import { PerformanceTracker } from "./observability/performance-tracker.js";
import { IncidentRecorder } from "./observability/incident-recorder.js";
import { ContextBuilder } from "./orchestrator/context-builder.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

async function main(): Promise<void> {
  // Load environment
  loadEnv({ path: resolve(__dirname, "../../.ai_pet_env") });
  loadEnv(); // Also try .env

  const config = loadConfig({
    llm: {
      provider: process.env.LLM_PROVIDER ?? "google",
      model: process.env.LLM_MODEL ?? "gemini-2.5-flash",
      apiKey: process.env.GEMINI_API_KEY,
    },
  });

  // Ensure data directory exists
  const dataDir = resolve(__dirname, "../../data");
  if (!existsSync(dataDir)) {
    mkdirSync(dataDir, { recursive: true });
  }
  const dbPath = resolve(dataDir, "mcar.db");

  // ─── Initialize services ────────────────────────────────

  const bridge = new ModuleBridge(config.ipc);
  const stateService = new StateService();
  const auditLogger = new AuditLogger();
  const auditStore = new AuditStore(resolve(dataDir, "audit.db"));
  auditLogger.setStore(auditStore);
  const stopHandler = new StopHandler(bridge, config.safety);
  const memoryService = new MemoryService({ ...config.memory, dbPath });
  const performanceTracker = new PerformanceTracker();
  const registry = new CapabilityRegistry(bridge);
  const executor = new CapabilityExecutor(registry);
  executor.setPerformanceTracker(performanceTracker);
  const incidentRecorder = new IncidentRecorder(memoryService, auditLogger);
  const policyEngine = new PolicyEngine(stopHandler, stateService, memoryService);
  const contextBuilder = new ContextBuilder(memoryService, stateService, registry);
  const promptBuilder = new PromptBuilder(contextBuilder);
  const agentRuntime = new AgentRuntime(
    config.llm,
    promptBuilder,
    registry,
    executor,
    policyEngine,
    auditLogger,
    memoryService,
    incidentRecorder
  );
  const sessionController = new SessionController(stateService, stopHandler);
  const dispatcher = new ActionDispatcher(
    sessionController,
    agentRuntime,
    auditLogger,
    stopHandler,
    performanceTracker,
    memoryService
  );
  const skillEngine = new SkillEngine(executor, policyEngine, registry, stateService, auditLogger);
  for (const skill of BUILTIN_SKILLS) {
    skillEngine.registerSkill(skill);
  }

  const healthMonitor = new HealthMonitor(registry, bridge, stateService, auditLogger);
  const sessionRecorder = new SessionRecorder(auditStore);
  const cleanupScheduler = new CleanupScheduler(memoryService, auditStore, auditLogger);

  const ruleEngine = new RuleEngine(memoryService, stateService, executor, auditLogger);

  const voiceLoop = new VoiceLoop(
    sessionController,
    dispatcher,
    bridge,
    executor,
    stopHandler,
    stateService,
    auditLogger
  );

  // ─── Start IPC bridge ───────────────────────────────────

  await bridge.start();
  console.log("[mcar] IPC bridge started");

  // Auto-register modules as they connect
  bridge.onRegister(async (moduleId) => {
    console.log(`[mcar] Module connected: ${moduleId}`);
    try {
      await registry.registerModule(moduleId);
      console.log(`[mcar] Module registered: ${moduleId}`);
    } catch (err) {
      console.error(`[mcar] Failed to register module ${moduleId}:`, err);
    }
  });

  // Forward module events to audit log + handle emergency_stop
  bridge.onEvent(async (event) => {
    auditLogger.info("system", `module.event.${event.event_type}`, {
      source: event.source,
      data: event.data,
    });

    // Physical button emergency stop
    if (event.event_type === "emergency_stop") {
      console.log("[mcar] Physical button emergency stop!");
      await stopHandler.triggerStop("button");
    }
  });

  // ─── Start Python module processes (with watchdog) ─────

  const modulesDir = resolve(__dirname, "../../modules");
  const moduleNames = ["mock", "voice", "display", "motion", "sensor", "button"];
  const watchdog = new ModuleWatchdog(modulesDir, config.ipc, auditLogger);
  watchdog.setIncidentRecorder(incidentRecorder);
  contextBuilder.setWatchdog(watchdog);
  const startedModules = watchdog.startModules(moduleNames);
  console.log(`[mcar] Started modules: ${startedModules.join(", ")}`);

  // Wait for modules to register
  await new Promise<void>((resolveWait) => {
    const timeout = setTimeout(() => {
      console.warn("[mcar] Not all modules registered, proceeding...");
      resolveWait();
    }, 5000);

    const checkModules = () => {
      const registered = bridge.getRegisteredModules();
      if (moduleNames.every((name) => registered.includes(name))) {
        clearTimeout(timeout);
        resolveWait();
      }
    };

    bridge.onRegister(checkModules);
    checkModules();
  });

  console.log("[mcar] All modules ready");
  console.log("[mcar] Available capabilities:");
  for (const cap of registry.getCapabilitySummaries()) {
    console.log(`  - ${cap.name} (${cap.capability_id}) [${cap.risk_level}]`);
  }
  console.log("");

  // Start voice loop, health monitor, and cleanup scheduler
  voiceLoop.start();
  healthMonitor.start();
  cleanupScheduler.start();
  ruleEngine.start();
  console.log("[mcar] Voice loop started");
  console.log("[mcar] Health monitor started");
  console.log("[mcar] Cleanup scheduler started");
  console.log("[mcar] Rule engine started");

  // Start web server
  const webServer = new WebServer(
    config.web,
    stateService,
    registry,
    executor,
    policyEngine,
    memoryService,
    stopHandler,
    dispatcher,
    sessionController,
    bridge,
    auditLogger,
    skillEngine,
    healthMonitor,
    sessionRecorder,
    watchdog,
    ruleEngine,
    performanceTracker
  );
  await webServer.start();

  let shuttingDown = false;
  const shutdown = async () => {
    if (shuttingDown) return;
    shuttingDown = true;
    console.log("\n[mcar] Shutting down...");

    // Shut down module processes
    await watchdog.shutdown();

    // Clean up
    ruleEngine.stop();
    cleanupScheduler.stop();
    healthMonitor.stop();
    voiceLoop.stop();
    await webServer.stop();
    memoryService.close();
    auditStore.close();
    await bridge.stop();

    console.log("[mcar] Goodbye!");
    process.exit(0);
  };

  const onSignal = () => { void shutdown(); };
  process.on("SIGINT", onSignal);
  process.on("SIGTERM", onSignal);

  if (!process.stdin.isTTY || !process.stdout.isTTY) {
    console.log("[mcar] Ready! Non-interactive mode (CLI disabled).");
    return;
  }

  // ─── CLI text interaction loop ──────────────────────────

  const rl = createInterface({
    input: process.stdin,
    output: process.stdout,
    prompt: "mcar> ",
  });

  console.log("[mcar] Ready! Type your message or 'quit' to exit.");
  rl.prompt();

  rl.on("line", async (line) => {
    const input = line.trim();
    if (!input) {
      rl.prompt();
      return;
    }

    if (input === "quit" || input === "exit") {
      rl.close();
      return;
    }

    if (input === "/status") {
      const snapshot = stateService.getSnapshot();
      console.log("State:", JSON.stringify(snapshot, null, 2));
      rl.prompt();
      return;
    }

    if (input === "/capabilities") {
      for (const cap of registry.getCapabilitySummaries()) {
        console.log(`  ${cap.name} (${cap.capability_id}) [${cap.risk_level}]: ${cap.description}`);
      }
      rl.prompt();
      return;
    }

    if (input === "/memories") {
      const summaries = memoryService.listSummaries();
      if (summaries.length === 0) {
        console.log("  (no memories)");
      } else {
        for (const s of summaries) {
          console.log(`  [${s.type}] ${s.summary}`);
        }
      }
      rl.prompt();
      return;
    }

    try {
      const response = await dispatcher.dispatch(input);
      console.log(`\n${response}\n`);
    } catch (err) {
      console.error("Error:", err);
    }

    rl.prompt();
  });

  rl.on("close", () => {
    void shutdown();
  });
}

main().catch((err) => {
  console.error("[mcar] Fatal error:", err);
  process.exit(1);
});
