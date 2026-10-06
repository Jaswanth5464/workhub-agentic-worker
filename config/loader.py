import os
import yaml
from dataclasses import dataclass, field
from typing import List

@dataclass
class AgentConfig:
    max_steps: int = 100
    default_budget: float = 10.0

@dataclass
class SafetyConfig:
    allow_unsafe_writes: bool = False
    require_approval_for_writes: bool = True
    allowed_domains: List[str] = field(default_factory=list)

@dataclass
class AppSettings:
    domain: str = "hr"
    agent: AgentConfig = field(default_factory=AgentConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)

def load_settings(path: str = "config/settings.yaml") -> AppSettings:
    if not os.path.exists(path):
        return AppSettings()
    with open(path, 'r') as f:
        data = yaml.safe_load(f) or {}
    
    agent_data = data.get('agent', {})
    safety_data = data.get('safety', {})
    
    return AppSettings(
        domain=data.get('domain', 'hr'),
        agent=AgentConfig(**agent_data),
        safety=SafetyConfig(**safety_data)
    )

settings = load_settings()
