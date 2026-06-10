"""Capability registry for in-process robot modules."""

from __future__ import annotations

from dataclasses import dataclass

from .adapters import RobotModule
from .models import CapabilitySpec, CapabilitySummary, ModuleSummary


@dataclass(frozen=True)
class RegisteredCapability:
    spec: CapabilitySpec
    module_id: str
    module: RobotModule


class CapabilityRegistry:
    def __init__(self, modules: list[RobotModule]) -> None:
        self._modules: dict[str, RobotModule] = {}
        self._capabilities: dict[str, RegisteredCapability] = {}
        for module in modules:
            self.register(module)

    def register(self, module: RobotModule) -> None:
        manifest = module.manifest()
        module_id = manifest["module_id"]
        self._modules[module_id] = module
        for raw in module.capabilities():
            spec = CapabilitySpec.model_validate(raw)
            self._capabilities[spec.capability_id] = RegisteredCapability(
                spec=spec,
                module_id=module_id,
                module=module,
            )

    def get(self, capability_id: str) -> RegisteredCapability | None:
        return self._capabilities.get(capability_id)

    def summaries(self) -> list[CapabilitySummary]:
        return [
            CapabilitySummary(
                capability_id=cap.spec.capability_id,
                name=cap.spec.name,
                module_id=cap.module_id,
                description=cap.spec.description,
                risk_level=cap.spec.risk_level,
            )
            for cap in self._capabilities.values()
        ]

    def modules(self) -> list[ModuleSummary]:
        summaries: list[ModuleSummary] = []
        for module in self._modules.values():
            manifest = module.manifest()
            summaries.append(
                ModuleSummary(
                    module_id=manifest["module_id"],
                    version=manifest["module_version"],
                    description=manifest["description"],
                    capabilities=list(manifest["capabilities"]),
                    enabled=True,
                )
            )
        return summaries
