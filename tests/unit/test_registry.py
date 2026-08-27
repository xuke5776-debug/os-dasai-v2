"""注册表单元测试：注册、握手、能力发现。"""

from __future__ import annotations

from agent_runtime.registry.capability import AgentCard
from agent_runtime.registry.registry import AgentRegistry


def test_handshake_accepts_compatible():
    reg = AgentRegistry()
    card = AgentCard(agent_name="planner", capabilities=["task_planning"], actions=["plan"])
    result = reg.handshake(card)
    assert result.accepted is True
    assert "planner" in reg


def test_handshake_rejects_incompatible_protocol():
    reg = AgentRegistry()
    card = AgentCard(
        agent_name="legacy",
        protocol_version="99.9",
        capabilities=["x"],
    )
    result = reg.handshake(card)
    assert result.accepted is False
    assert "legacy" not in reg


def test_capability_discovery():
    reg = AgentRegistry()
    reg.register(AgentCard(agent_name="retriever", capabilities=["retrieval", "semantic_search"]))
    reg.register(AgentCard(agent_name="executor", capabilities=["execute"]))
    assert reg.discover("retrieval") == ["retriever"]
    assert reg.discover("execute") == ["executor"]
    assert reg.discover("missing") == []


def test_agent_card_generation_from_agent():
    from agent_runtime.agents import PlannerAgent

    card = PlannerAgent().card()
    assert card.agent_name == "planner"
    assert "task_planning" in card.capabilities
    assert "plan" in card.actions
