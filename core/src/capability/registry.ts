/**
 * CapabilityRegistry — module discovery and capability registration.
 *
 * On startup, queries each connected Python module for its manifest
 * and capabilities, validates them, and maintains an in-memory index.
 */

import type { ModuleBridge } from "../ipc/module-bridge.js";
import { ModuleProxy } from "../ipc/module-proxy.js";
import type {
  CapabilitySpec,
  ModuleManifest,
  RegisteredModule,
  RegisteredCapability,
} from "./types.js";

export class CapabilityRegistry {
  private modules = new Map<string, RegisteredModule>();
  private capabilities = new Map<string, RegisteredCapability>();
  private proxies = new Map<string, ModuleProxy>();

  constructor(private readonly bridge: ModuleBridge) {}

  /**
   * Discover and register a module that just connected.
   */
  async registerModule(moduleId: string): Promise<void> {
    const proxy = new ModuleProxy(moduleId, this.bridge);
    this.proxies.set(moduleId, proxy);

    const manifestData = await proxy.manifest();
    const manifest = manifestData as unknown as ModuleManifest;

    const capsData = await proxy.capabilities();
    const caps = capsData as unknown as CapabilitySpec[];

    // Validate capability IDs match manifest
    const declaredIds = new Set(manifest.capabilities);
    for (const cap of caps) {
      if (!declaredIds.has(cap.capability_id)) {
        console.warn(
          `[Registry] Capability ${cap.capability_id} not declared in manifest for ${moduleId}`
        );
      }
    }

    this.modules.set(moduleId, {
      manifest,
      capabilities: caps,
      enabled: true,
    });

    for (const cap of caps) {
      this.capabilities.set(cap.capability_id, {
        spec: cap,
        moduleId,
      });
    }
  }

  /**
   * Unregister a module (e.g., on disconnect).
   */
  unregisterModule(moduleId: string): void {
    const mod = this.modules.get(moduleId);
    if (!mod) return;

    for (const cap of mod.capabilities) {
      this.capabilities.delete(cap.capability_id);
    }
    this.modules.delete(moduleId);
    this.proxies.delete(moduleId);
  }

  /**
   * Enable/disable a module at runtime.
   */
  setModuleEnabled(moduleId: string, enabled: boolean): void {
    const mod = this.modules.get(moduleId);
    if (mod) {
      mod.enabled = enabled;
    }
  }

  /**
   * Get a capability spec by ID.
   */
  getCapability(capabilityId: string): RegisteredCapability | undefined {
    return this.capabilities.get(capabilityId);
  }

  /**
   * Get the proxy for a module (for invoking capabilities).
   */
  getProxy(moduleId: string): ModuleProxy | undefined {
    return this.proxies.get(moduleId);
  }

  /**
   * List all registered capabilities (optionally filter by enabled modules).
   */
  listCapabilities(enabledOnly = true): RegisteredCapability[] {
    const result: RegisteredCapability[] = [];
    for (const [, cap] of this.capabilities) {
      if (enabledOnly) {
        const mod = this.modules.get(cap.moduleId);
        if (!mod?.enabled) continue;
      }
      result.push(cap);
    }
    return result;
  }

  /**
   * List all registered modules.
   */
  listModules(): RegisteredModule[] {
    return [...this.modules.values()];
  }

  /**
   * Get a capability spec suitable for Agent tool description.
   */
  getCapabilitySummaries(): Array<{
    capability_id: string;
    name: string;
    description: string;
    risk_level: string;
    inputs_schema: Record<string, unknown>;
  }> {
    return this.listCapabilities().map((c) => ({
      capability_id: c.spec.capability_id,
      name: c.spec.name,
      description: c.spec.description,
      risk_level: c.spec.risk_level,
      inputs_schema: c.spec.inputs_schema,
    }));
  }
}
