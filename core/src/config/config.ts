import { readFileSync } from "node:fs";
import { resolve } from "node:path";

export interface IpcConfig {
  readonly routerEndpoint: string;
  readonly pubEndpoint: string;
  readonly heartbeatIntervalMs: number;
  readonly heartbeatTimeoutMs: number;
  readonly invokeTimeoutMs: number;
}

export interface LlmConfig {
  readonly provider: string;
  readonly model: string;
  readonly apiKey?: string;
  readonly baseUrl?: string;
}

export interface MemoryConfig {
  readonly dbPath: string;
  readonly maxInjectionCount: number;
}

export interface SafetyConfig {
  readonly estopCooldownMs: number;
}

export interface ModeConfig {
  readonly speedLimits: Record<string, number>;
}

export interface WebConfig {
  readonly port: number;
  readonly host: string;
}

export interface AppConfig {
  readonly ipc: IpcConfig;
  readonly llm: LlmConfig;
  readonly memory: MemoryConfig;
  readonly safety: SafetyConfig;
  readonly mode: ModeConfig;
  readonly web: WebConfig;
}

const DEFAULT_CONFIG: AppConfig = {
  ipc: {
    routerEndpoint: "ipc:///tmp/mcar-router.sock",
    pubEndpoint: "ipc:///tmp/mcar-pub.sock",
    heartbeatIntervalMs: 5000,
    heartbeatTimeoutMs: 15000,
    invokeTimeoutMs: 10000,
  },
  llm: {
    provider: "google",
    model: "gemini-2.5-flash",
  },
  memory: {
    dbPath: "./data/mcar.db",
    maxInjectionCount: 5,
  },
  safety: {
    estopCooldownMs: 2000,
  },
  mode: {
    speedLimits: {
      normal: 100,
      safety: 50,
      kid: 30,
      debug: 100,
      mute: 100,
    },
  },
  web: {
    port: 8080,
    host: "0.0.0.0",
  },
};

export function loadConfig(overrides?: Partial<AppConfig>): AppConfig {
  return {
    ipc: { ...DEFAULT_CONFIG.ipc, ...overrides?.ipc },
    llm: { ...DEFAULT_CONFIG.llm, ...overrides?.llm },
    memory: { ...DEFAULT_CONFIG.memory, ...overrides?.memory },
    safety: { ...DEFAULT_CONFIG.safety, ...overrides?.safety },
    mode: { ...DEFAULT_CONFIG.mode, ...overrides?.mode },
    web: { ...DEFAULT_CONFIG.web, ...overrides?.web },
  };
}
