"""
AIR Blackbox — AI governance control plane.

One install. Four commands. 79% automated compliance.

    pip install air-blackbox

    air-blackbox discover    # Shadow AI inventory + AI-BOM
    air-blackbox comply      # EU AI Act compliance from live traffic
    air-blackbox replay      # Incident reconstruction from audit chain
    air-blackbox export      # Signed evidence bundle for auditors
"""

__version__ = "1.3.0"
__all__ = ["AirBlackbox", "AirTrust"]


class AirBlackbox:
    """Main entry point for AIR Blackbox SDK.

    Wraps your LLM client with automatic audit trails, compliance
    monitoring, and tamper-evident logging.

    Usage:
        from air_blackbox import AirBlackbox

        air = AirBlackbox()
        client = air.wrap(openai.OpenAI())
        # Every LLM call is now HMAC-logged
    """

    def __init__(self, gateway_url=None, config=None):
        self.gateway_url = gateway_url or "http://localhost:8080"
        self.config = config or {}

    def wrap(self, client):
        """Wrap an LLM client to route through the AIR gateway.

        Args:
            client: An OpenAI, Anthropic, or compatible LLM client.

        Returns:
            The same client, reconfigured to use the AIR gateway.
        """
        # Detect client type and reconfigure base_url
        if hasattr(client, "base_url"):
            # OpenAI-compatible client
            client.base_url = self.gateway_url + "/v1"
        return client


class AirTrust:
    """Auto-detecting trust layer for AI agent frameworks.

    Detects which framework is in use (LangChain, CrewAI, ADK, etc.)
    and attaches the appropriate trust layer automatically.

    Usage:
        from air_blackbox import AirTrust

        trust = AirTrust()
        trust.attach(your_agent)
        # Framework auto-detected. Audit trails active.
    """

    def __init__(self, gateway_url=None):
        self.gateway_url = gateway_url or "http://localhost:8080"
        self._detected_framework = None

    def attach(self, agent):
        """Attach trust layer to an agent.

        Auto-detects the framework and applies the appropriate
        callback handler / middleware.

        Args:
            agent: A LangChain chain, CrewAI crew, ADK agent, etc.
        """
        framework = self._detect_framework(agent)
        self._detected_framework = framework

        if framework == "langchain":
            from air_blackbox.trust.langchain import attach_trust
            return attach_trust(agent, self.gateway_url)
        elif framework == "crewai":
            from air_blackbox.trust.crewai import attach_trust
            return attach_trust(agent, self.gateway_url)
        elif framework == "openai":
            from air_blackbox.trust.openai_agents import attach_trust
            return attach_trust(agent, self.gateway_url)
        elif framework == "autogen":
            from air_blackbox.trust.autogen import attach_trust
            return attach_trust(agent, self.gateway_url)
        elif framework == "claude_agent":
            from air_blackbox.trust.claude_agent import attach_trust
            return attach_trust(agent, self.gateway_url)
        else:
            print(f"[AIR] Framework not auto-detected. Using generic wrapper.")
            return agent

    def _detect_framework(self, agent):
        """Detect which AI framework the agent belongs to."""
        agent_type = type(agent).__module__

        if "langchain" in agent_type or "langgraph" in agent_type:
            return "langchain"
        elif "crewai" in agent_type:
            return "crewai"
        elif "openai" in agent_type:
            return "openai"
        elif "autogen" in agent_type:
            return "autogen"
        elif "google" in agent_type and "adk" in agent_type:
            return "adk"
        elif "claude_agent_sdk" in agent_type or "claude_agent" in agent_type:
            return "claude_agent"

        return "unknown"
