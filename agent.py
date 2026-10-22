"""LangChain agent của stage 01: read_file, write_file."""

from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware
from langchain_openai import ChatOpenAI

from config import MODEL_CALL_LIMIT, TOOL_CALL_LIMIT, Settings
from observer import ObserverMiddleware
from prompts import build_system_prompt
from tools import read_file, write_file
from tools.memory import make_memory_tool

TOOLS = [read_file, write_file]


def build_model(settings: Settings) -> ChatOpenAI:
    kwargs = {"model": settings.model_name, "api_key": settings.api_key}
    if settings.base_url:
        kwargs["base_url"] = settings.base_url
    return ChatOpenAI(**kwargs)


def system_prompt() -> str:
    return build_system_prompt()


def tools_for_session(session_id: str) -> list:
    return [*TOOLS, make_memory_tool(session_id)]


def capabilities() -> dict:
    return {"tools": [t.name for t in TOOLS] + ["update_project_memory"], "skills": [], "skill_diagnostics": []}


def build_agent(model, session_id: str):
    return create_agent(
        model=model,
        tools=tools_for_session(session_id),
        system_prompt=system_prompt(),
        middleware=[
            ModelCallLimitMiddleware(run_limit=MODEL_CALL_LIMIT, exit_behavior="end"),
            ToolCallLimitMiddleware(run_limit=TOOL_CALL_LIMIT),
            ObserverMiddleware(),  # cuối danh sách = sát model/tool invocation nhất
        ],
    )
