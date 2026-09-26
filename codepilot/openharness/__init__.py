"""
OpenHarness Integration for CodePilot.
Connects CodePilot with the Autonomous Machine Provider Protocol and
Domain-Specific Harnesses (DSH).
"""
from codepilot.openharness.protocol import (
    EVENT_KINDS,
    TERMINAL_KINDS,
    ERROR_CODES,
    ProviderEvent,
    ProviderError,
    AgentDescriptor,
)
from codepilot.openharness.dsh import (
    DSHDefinition,
    DSHRegistry,
)
from codepilot.openharness.provider import (
    OpenHarnessStore,
    OpenHarnessProviderHandler,
    start_openharness_provider_server,
)
from codepilot.openharness.client import OpenHarnessClient

__all__ = [
    "EVENT_KINDS",
    "TERMINAL_KINDS",
    "ERROR_CODES",
    "ProviderEvent",
    "ProviderError",
    "AgentDescriptor",
    "DSHDefinition",
    "DSHRegistry",
    "OpenHarnessStore",
    "OpenHarnessProviderHandler",
    "start_openharness_provider_server",
    "OpenHarnessClient",
]
