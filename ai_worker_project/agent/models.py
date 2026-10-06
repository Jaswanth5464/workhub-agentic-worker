"""
Phase 4: Data Models and Contracts

Pydantic models for Task, Run, and Step tracking.
This provides the 'Contract' part of the architecture, ensuring memory, state, 
and budgets are strictly typed and persisted.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import uuid

class Step(BaseModel):
    """Represents a single 'Thought -> Action -> Observation' cycle."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    thought: str = ""
    tool_name: str = ""
    tool_args: Dict[str, Any] = Field(default_factory=dict)
    observation: str = ""
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Run(BaseModel):
    """Represents an execution run of a task."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_description: str
    status: str = "pending"  # pending, running, completed, failed, blocked_on_human
    steps: List[Step] = Field(default_factory=list)
    final_answer: Optional[str] = None
    max_steps: int = 100
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def add_step(self, step: Step):
        self.steps.append(step)
        self.updated_at = datetime.now(timezone.utc)

