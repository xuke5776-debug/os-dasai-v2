"""能力描述与 Agent 名片（用于注册、握手与能力发现）。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from agent_runtime import PROTOCOL_VERSION


class Capability(BaseModel):
    """单项能力描述。"""

    name: str
    description: str = ""
    input_schema: dict = Field(default_factory=dict)
    output_schema: dict = Field(default_factory=dict)


class AgentCard(BaseModel):
    """Agent 名片：注册与能力发现的依据。"""

    agent_name: str
    protocol_version: str = PROTOCOL_VERSION
    capabilities: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    description: str = ""


class HandshakeResult(BaseModel):
    """握手结果。"""

    accepted: bool
    agent_name: str
    server_protocol: str = PROTOCOL_VERSION
    reason: str = ""


__all__ = ["Capability", "AgentCard", "HandshakeResult"]
