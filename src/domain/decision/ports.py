"""Port for structured decision engines (implemented by Typesafe Jev adapter)."""

from __future__ import annotations

from typing import Protocol

from src.domain.decision.models import DecisionRequest, DecisionResponse


class DecisionPort(Protocol):
    async def evaluate(self, request: DecisionRequest) -> DecisionResponse:
        """Evaluate typed questions against shared state."""

    async def aclose(self) -> None:
        """Release underlying resources if any."""
