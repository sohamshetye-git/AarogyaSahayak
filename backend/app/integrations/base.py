from abc import ABC, abstractmethod
from typing import Any, Dict
from app.config import settings

class BaseIntegrationAdapter(ABC):
    """
    Base contract for all external AI and Government integrations.
    Every integration MUST support both deterministic 'mock' and live modes.
    """
    def __init__(self, mode: str = "mock"):
        self.mode = mode or settings.INTEGRATION_MODE

    @property
    def is_mock(self) -> bool:
        return self.mode.lower() == "mock" or settings.INTEGRATION_MODE.lower() == "mock"
