import sqlite3
import os
from pathlib import Path
from pydantic import BaseModel, Field
from .base import Tool, RiskLevel, ToolResult

# Setup Memory DB
MEMORY_DB_PATH = Path(os.environ.get("MEMORY_DB_PATH", "agent_memory.sqlite"))

def _init_db():
    with sqlite3.connect(MEMORY_DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT UNIQUE,
                fact TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

_init_db()

def get_all_memories():
    try:
        with sqlite3.connect(MEMORY_DB_PATH) as conn:
            cur = conn.execute("SELECT topic, fact FROM memory")
            return [{"topic": r[0], "fact": r[1]} for r in cur.fetchall()]
    except:
        return []

class MemorySaveSchema(BaseModel):
    topic: str = Field(..., description="A short, unique keyword or phrase representing the topic (e.g., 'Company X Policy', 'HR Email').")
    fact: str = Field(..., description="The detailed information or fact you want to remember for future runs.")

class MemorySaveTool(Tool):
    name = "memorize_fact"
    description = "Saves important information into the agent's long-term memory database so it can be recalled in future tasks."
    parameters = MemorySaveSchema.model_json_schema()
    risk_level = RiskLevel.LOW

    async def execute(self, **kwargs) -> ToolResult:
        topic = kwargs.get("topic")
        fact = kwargs.get("fact")
        
        try:
            with sqlite3.connect(MEMORY_DB_PATH) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO memory (topic, fact) VALUES (?, ?)",
                    (topic, fact)
                )
            return ToolResult(success=True, data=f"Successfully saved to long-term memory under topic '{topic}'.")
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to save to memory: {e}")

class MemoryRecallSchema(BaseModel):
    search_query: str = Field(..., description="The topic or keyword to search the memory database for (e.g., 'Company X'). Leave empty to list all memorized topics.")

class MemoryRecallTool(Tool):
    name = "recall_fact"
    description = "Searches the agent's long-term memory database for previously saved facts or context."
    parameters = MemoryRecallSchema.model_json_schema()
    risk_level = RiskLevel.LOW

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("search_query", "")
        
        try:
            with sqlite3.connect(MEMORY_DB_PATH) as conn:
                if query.strip():
                    cur = conn.execute("SELECT topic, fact FROM memory WHERE topic LIKE ? OR fact LIKE ?", (f"%{query}%", f"%{query}%"))
                else:
                    cur = conn.execute("SELECT topic, fact FROM memory LIMIT 10")
                    
                rows = cur.fetchall()
                if not rows:
                    return ToolResult(success=True, data=f"No memories found matching '{query}'.")
                
                results = ["--- Long Term Memory Results ---"]
                for row in rows:
                    results.append(f"Topic: {row[0]}\nFact: {row[1]}\n")
                    
                return ToolResult(success=True, data="\n".join(results))
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to recall from memory: {e}")
