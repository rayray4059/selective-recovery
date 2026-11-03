from pathlib import Path

from pydantic import BaseModel

TASKS_DIR = Path(__file__).resolve().parent


class Fact(BaseModel):
    text: str
    doc: str
    key: str
    role: str = "deciding"


class Message(BaseModel):
    channel: str
    keywords: list[str]


class Expected(BaseModel):
    hidden_test: str
    publish: list[str] = []
    messages: list[Message] = []


class Allowed(BaseModel):
    tools: list[str]
    paths: list[str]


class Task(BaseModel):
    id: str
    title: str
    instruction: str
    target_files: list[str]
    facts: list[Fact]
    expected: Expected
    allowed: Allowed


def load_tasks(path=TASKS_DIR / "dev.jsonl"):
    return [Task.model_validate_json(line) for line in Path(path).read_text().splitlines() if line.strip()]
