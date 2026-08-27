"""Agent 注册表：注册、握手、能力发现。"""

from __future__ import annotations

from agent_runtime.protocol.schema import is_compatible
from agent_runtime.registry.capability import AgentCard, HandshakeResult


class AgentRegistry:
    """维护已注册 Agent 的名片，并支持按能力/动作发现。"""

    def __init__(self) -> None:
        self._cards: dict[str, AgentCard] = {}
        self._by_capability: dict[str, list[str]] = {}
        self._by_action: dict[str, list[str]] = {}

    def handshake(self, card: AgentCard) -> HandshakeResult:
        """协议版本协商。兼容则接受并注册。"""
        if not is_compatible(card.protocol_version):
            return HandshakeResult(
                accepted=False,
                agent_name=card.agent_name,
                reason=f"协议不兼容: {card.protocol_version}",
            )
        self.register(card)
        return HandshakeResult(accepted=True, agent_name=card.agent_name)

    def register(self, card: AgentCard) -> None:
        """注册（或更新）一个 Agent 名片，并建立能力/动作索引。"""
        self._cards[card.agent_name] = card
        for cap in card.capabilities:
            self._by_capability.setdefault(cap, [])
            if card.agent_name not in self._by_capability[cap]:
                self._by_capability[cap].append(card.agent_name)
        for action in card.actions:
            self._by_action.setdefault(action, [])
            if card.agent_name not in self._by_action[action]:
                self._by_action[action].append(card.agent_name)

    def discover(self, capability: str) -> list[str]:
        """返回拥有指定能力的 Agent 名称列表。"""
        return list(self._by_capability.get(capability, []))

    def discover_by_action(self, action: str) -> list[str]:
        return list(self._by_action.get(action, []))

    def get_card(self, agent_name: str) -> AgentCard | None:
        return self._cards.get(agent_name)

    def all_cards(self) -> list[AgentCard]:
        return list(self._cards.values())

    def __contains__(self, agent_name: str) -> bool:
        return agent_name in self._cards


__all__ = ["AgentRegistry"]
