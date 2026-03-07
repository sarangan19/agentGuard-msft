import sys
from datetime import datetime

from agentguard import AgentGuardMiddleware
from agentguard.exceptions import InterventionRequired, SecurityException
from simple_agent import get_agent


def _print_banner():
    banner = r"""
  █████╗  ██████╗ ███████╗███╗   ██╗████████╗ ██████╗ ██╗   ██╗ █████╗ ██████╗ ██████╗
 ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝██╔════╝ ██║   ██║██╔══██╗██╔══██╗██╔══██╗
 ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   ██║  ███╗██║   ██║███████║██████╔╝██║  ██║
 ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   ██║   ██║██║   ██║██╔══██║██╔══██╗██║  ██║
 ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   ╚██████╔╝╚██████╔╝██║  ██║██║  ██║██████╔╝
 ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝
    """
    print(banner)
    print("AgentGuard Terminal Middleware v4.2.14")
    print("Type 'exit' or 'quit' to leave.\n")


def _truncate(text, limit=2000):
    if len(text) <= limit:
        return text
    return text[:limit]




def main():
    _print_banner()

    agent_name = input("Agent name (default: terminal-agent): ").strip() or "terminal-agent"
    middleware = AgentGuardMiddleware(config={"agent_id": agent_name}, verbose=True)
    agent = get_agent()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            return

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye.")
            return

        user_input = _truncate(user_input)
        privacy_result = middleware.intercept_message(user_input)
        anonymized = privacy_result["anonymized_text"]
        entity_map = privacy_result.get("mapping", {})
        metadata = privacy_result.get("metadata", {})
        metadata["entity_count"] = privacy_result.get("entity_count", 0)
        metadata["detection_method"] = privacy_result.get("detection_method", "unknown")

        agent_decision = agent.process(anonymized, metadata=metadata)
        action = agent_decision.get("action", "unknown_action")

        context = {
            "original_text": user_input,
            "anonymized_text": anonymized,
            "metadata": metadata,
            "entity_count": privacy_result.get("entity_count", 0),
        }

        try:
            audit = middleware.validate_action(action, context=context)
            print(f"[AgentGuard] ✓ Decision logged ({audit.get('id')})")
            print("[AgentGuard] ✓ Action approved and recorded")
        except InterventionRequired as exc:
            print("⚠️  HIGH RISK ACTION DETECTED")
            justification = input("Provide justification to proceed: ").strip()
            audit = exc.audit_record or {
                "id": f"terminal-{datetime.now().timestamp()}",
                "session_id": middleware.session_id,
                "agent_id": middleware.agent_id,
                "original_text": user_input[:500],
                "anonymized_text": anonymized[:500],
                "entity_count": privacy_result.get("entity_count", 0),
                "risk_score": exc.risk_score,
                "tier": exc.tier,
                "risk_reasoning": exc.reasoning,
                "agent_action": action,
                "source": "terminal",
            }
            escalated = middleware.confirm_action(audit, justification, action=action)
            department = escalated.get("department", "Security Review")
            reference = escalated.get("id", "unknown")
            print(f"[AgentGuard] ↗ Escalated to {department} for review")
            print(f"Reference: {reference}")
        except SecurityException as exc:
            print("🚨 BLOCKED — action denied")
            print(f"Reason: {exc}")


if __name__ == "__main__":
    main()
