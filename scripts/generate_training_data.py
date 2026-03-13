#!/usr/bin/env python3
"""
AIR Blackbox Training Data Generator v2.

Generates diverse, high-quality training examples for the compliance
fine-tuned model. Covers:
  - 6 frameworks: LangChain, CrewAI, OpenAI, AutoGen, Haystack, Claude Agent SDK
  - 4 compliance levels: 0/6, 2/6, 4/6, 6/6
  - Edge cases: partial logging, fake compliance, trust layer present
  - Realistic code patterns from real-world projects

Output: JSONL for Unsloth/LoRA fine-tuning.
"""

import json
import random
import itertools
from pathlib import Path

INSTRUCTION = (
    "Analyze this Python code for EU AI Act compliance gaps. "
    "Check against Articles 9, 10, 11, 12, 14, and 15. "
    "Report which technical requirements are met or missing, "
    "with specific recommendations."
)

# ── Article descriptions (pass/fail variants) ──

ARTICLES = {
    9: {
        "title": "Risk Management System",
        "fail": (
            "No risk classification system detected. The agent can invoke "
            "any tool without assessing its risk level. Article 9 requires "
            "identifying and analyzing known and foreseeable risks."
        ),
        "pass": (
            "Risk classification detected. Tool calls are classified by risk "
            "level (LOW/MEDIUM/HIGH/CRITICAL) with gating for dangerous operations. "
            "Meets Article 9 requirement for risk identification and mitigation."
        ),
        "partial": (
            "Basic error handling detected but no systematic risk classification. "
            "Try/except blocks exist but tool calls are not categorized by risk level. "
            "Partially addresses Article 9 but lacks formal risk taxonomy."
        ),
    },
    10: {
        "title": "Data and Data Governance",
        "fail": (
            "No data governance controls detected. Sensitive data (PII, credentials) "
            "can flow directly to the LLM without tokenization or redaction."
        ),
        "pass": (
            "Data governance controls detected. PII scanning active with tokenization "
            "for sensitive fields. Input validation prevents unfiltered data from "
            "reaching the LLM. Meets Article 10 data minimization requirements."
        ),
        "partial": (
            "Some input validation detected but no PII-specific scanning. "
            "Data is validated for format but sensitive fields are not identified "
            "or redacted before LLM processing."
        ),
    },
    11: {
        "title": "Technical Documentation",
        "fail": (
            "No structured documentation system detected. Agent operations "
            "are not logged with timestamps or call graphs."
        ),
        "pass": (
            "Structured documentation detected. Agent operations are logged "
            "with timestamps, model versions, and call graphs. Docstrings and "
            "type hints present throughout. Meets Article 11 requirements."
        ),
        "partial": (
            "Basic docstrings present but no automated operation logging. "
            "Code is documented but runtime behavior is not captured in "
            "structured format for regulatory review."
        ),
    },
    12: {
        "title": "Record-Keeping",
        "fail": (
            "No automatic record-keeping detected. Agent decisions, tool "
            "invocations, and consent outcomes are not being recorded."
        ),
        "pass": (
            "Comprehensive record-keeping detected. All tool calls logged "
            "as structured JSON with HMAC-SHA256 chain integrity. Audit trail "
            "is tamper-evident and regulatory-grade. Meets Article 12."
        ),
        "partial": (
            "Logging present (Python logging module) but records lack structured "
            "format, cryptographic integrity, or tamper-evidence. Standard logs "
            "are insufficient for Article 12 regulatory compliance."
        ),
    },
    14: {
        "title": "Human Oversight",
        "fail": (
            "No human oversight mechanism detected. The agent operates "
            "autonomously without ability for humans to intervene or override."
        ),
        "pass": (
            "Human oversight mechanisms detected. Approval gates for high-risk "
            "operations, kill switch capability, and rate limiting present. "
            "Humans can intervene at critical decision points. Meets Article 14."
        ),
        "partial": (
            "Rate limiting detected but no approval gates for high-risk operations. "
            "System can be stopped but cannot require human approval before "
            "executing critical tool calls."
        ),
    },
    15: {
        "title": "Accuracy, Robustness, and Cybersecurity",
        "fail": (
            "No cybersecurity defenses detected. The agent is vulnerable to "
            "prompt injection attacks with no multi-layer security controls."
        ),
        "pass": (
            "Multi-layer security detected. Prompt injection scanning active "
            "with pattern matching and confidence scoring. Output validation "
            "present. Defense-in-depth architecture. Meets Article 15."
        ),
        "partial": (
            "Basic input sanitization detected but no injection-specific scanning. "
            "Some output validation present but no defense-in-depth or "
            "multi-layer security architecture."
        ),
    },
}


# ── Code templates by framework and compliance level ──

LANGCHAIN_TEMPLATES = {
    "0/6": [
        # Basic agent, no compliance
        '''from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI
from langchain.tools import tool

llm = ChatOpenAI(model="gpt-4")

@tool
def {tool_name}({param}: str) -> str:
    """{tool_doc}"""
    return {action}

agent = AgentExecutor(
    agent=create_openai_tools_agent(llm, [{tool_name}]),
    tools=[{tool_name}],
)
result = agent.invoke({{"input": "{user_input}"}})''',
        # RAG chain
        '''from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import {vectorstore}

llm = ChatOpenAI(model="{model}")
vectorstore = {vectorstore}(persist_directory="./{db_dir}")
qa_chain = RetrievalQA.from_chain_type(
    llm=llm, retriever=vectorstore.as_retriever()
)
answer = qa_chain.invoke("{query}")''',
        # Multi-tool agent
        '''from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from langchain_community.tools import {tool_class}

llm = ChatOpenAI(temperature=0)
tools = [{tool_class}()]
agent = initialize_agent(
    tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION
)
agent.run("{user_input}")''',
    ],
    "2/6": [
        # Has logging + docstrings (Art 11, 12 partial)
        '''import logging
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI
from langchain.tools import tool

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

llm = ChatOpenAI(model="gpt-4")

@tool
def {tool_name}({param}: str) -> str:
    """{tool_doc}

    Args:
        {param}: The {param_desc}

    Returns:
        str: {return_desc}
    """
    logger.info(f"Tool called: {tool_name} with {{{param}}}")
    try:
        result = {action}
        logger.info(f"Tool result: {{result[:100]}}")
        return result
    except Exception as e:
        logger.error(f"Tool error: {{e}}")
        raise

agent = AgentExecutor(
    agent=create_openai_tools_agent(llm, [{tool_name}]),
    tools=[{tool_name}],
    verbose=True,
)
result = agent.invoke({{"input": "{user_input}"}})''',
    ],
    "4/6": [
        # Has try/except + logging + rate limit + validation
        '''import logging
import time
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langchain_core.callbacks import BaseCallbackHandler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

MAX_CALLS_PER_MINUTE = 10
_call_count = 0
_last_reset = time.time()

class AuditHandler(BaseCallbackHandler):
    """Callback handler that logs all LLM interactions."""

    def on_llm_start(self, serialized, prompts, **kwargs):
        logger.info(f"LLM call: model={{serialized.get('kwargs', {{}}).get('model', 'unknown')}}")
        for prompt in prompts:
            if any(word in prompt.lower() for word in ["ignore previous", "system prompt:"]):
                logger.warning(f"Possible injection detected in prompt")

    def on_llm_end(self, response, **kwargs):
        logger.info(f"LLM response received")

    def on_tool_start(self, serialized, input_str, **kwargs):
        logger.info(f"Tool: {{serialized.get('name')}} input={{input_str[:100]}}")

def check_rate_limit():
    global _call_count, _last_reset
    if time.time() - _last_reset > 60:
        _call_count = 0
        _last_reset = time.time()
    _call_count += 1
    if _call_count > MAX_CALLS_PER_MINUTE:
        raise RuntimeError("Rate limit exceeded")

llm = ChatOpenAI(model="gpt-4", callbacks=[AuditHandler()])

@tool
def {tool_name}({param}: str) -> str:
    """{tool_doc}"""
    check_rate_limit()
    if not {param} or len({param}) > 10000:
        raise ValueError("Invalid input")
    try:
        return {action}
    except Exception as e:
        logger.error(f"Error: {{e}}")
        return f"Error: {{e}}"

agent = AgentExecutor(
    agent=create_openai_tools_agent(llm, [{tool_name}]),
    tools=[{tool_name}],
    max_iterations=5,
    handle_parsing_errors=True,
)
result = agent.invoke({{"input": "{user_input}"}})''',
    ],
    "6/6": [
        # Full AIR trust layer
        '''from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from air_blackbox.trust.langchain import AirLangChainHandler

handler = AirLangChainHandler(
    detect_pii=True,
    detect_injection=True,
    log_to_gateway=True,
)

llm = ChatOpenAI(model="gpt-4", callbacks=[handler])

@tool
def {tool_name}({param}: str) -> str:
    """{tool_doc}"""
    return {action}

agent = AgentExecutor(
    agent=create_openai_tools_agent(llm, [{tool_name}]),
    tools=[{tool_name}],
    max_iterations=5,
    callbacks=[handler],
)
result = agent.invoke({{"input": "{user_input}"}})
print(f"[AIR] Events logged: {{handler.event_count}}")''',
    ],
}

CREWAI_TEMPLATES = {
    "0/6": [
        '''from crewai import Agent, Task, Crew

{agent_var} = Agent(
    role="{role}",
    goal="{goal}",
    backstory="{backstory}",
    allow_delegation=False,
)

task = Task(
    description="{task_desc}",
    expected_output="{expected_output}",
    agent={agent_var},
)

crew = Crew(agents=[{agent_var}], tasks=[task])
result = crew.kickoff()''',
    ],
    "2/6": [
        '''import logging
from crewai import Agent, Task, Crew

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

{agent_var} = Agent(
    role="{role}",
    goal="{goal}",
    backstory="{backstory}",
    allow_delegation=False,
    verbose=True,
)

task = Task(
    description="""{task_desc}

    Requirements:
    - {req_1}
    - {req_2}
    """,
    expected_output="{expected_output}",
    agent={agent_var},
)

crew = Crew(agents=[{agent_var}], tasks=[task], verbose=True)
logger.info("Starting crew execution")
result = crew.kickoff()
logger.info(f"Crew finished: {{str(result)[:200]}}")''',
    ],
    "4/6": [
        '''import logging
import time
from crewai import Agent, Task, Crew
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

class {tool_class}Input(BaseModel):
    """Input schema for {tool_name}."""
    query: str = Field(description="The search query")

class {tool_class}(BaseTool):
    """Tool that {tool_doc}."""
    name: str = "{tool_name}"
    description: str = "{tool_doc}"
    args_schema: type = {tool_class}Input

    def _run(self, query: str) -> str:
        logger.info(f"Tool {{self.name}} called with: {{query[:100]}}")
        if not query or len(query) > 5000:
            raise ValueError("Invalid query length")
        try:
            result = f"Results for: {{query}}"
            logger.info(f"Tool result: {{result[:100]}}")
            return result
        except Exception as e:
            logger.error(f"Tool error: {{e}}")
            raise

{agent_var} = Agent(
    role="{role}",
    goal="{goal}",
    backstory="{backstory}",
    tools=[{tool_class}()],
    max_iter=5,
    allow_delegation=False,
)

task = Task(
    description="{task_desc}",
    expected_output="{expected_output}",
    agent={agent_var},
)

crew = Crew(agents=[{agent_var}], tasks=[task], verbose=True)
result = crew.kickoff()''',
    ],
    "6/6": [
        '''from crewai import Agent, Task, Crew
from air_blackbox import AirTrust

trust = AirTrust(detect_pii=True, detect_injection=True)

{agent_var} = Agent(
    role="{role}",
    goal="{goal}",
    backstory="{backstory}",
    allow_delegation=False,
)
trust.attach({agent_var})

task = Task(
    description="{task_desc}",
    expected_output="{expected_output}",
    agent={agent_var},
)

crew = Crew(agents=[{agent_var}], tasks=[task])
result = crew.kickoff()''',
    ],
}

OPENAI_TEMPLATES = {
    "0/6": [
        '''from openai import OpenAI

client = OpenAI()
response = client.chat.completions.create(
    model="{model}",
    messages=[
        {{"role": "system", "content": "{system_prompt}"}},
        {{"role": "user", "content": "{user_input}"}},
    ],
)
print(response.choices[0].message.content)''',
    ],
    "2/6": [
        '''import logging
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = OpenAI()

def chat(user_message: str, system_prompt: str = "{system_prompt}") -> str:
    """Send a chat message and return the response.

    Args:
        user_message: The user's input
        system_prompt: System instructions

    Returns:
        The model's response text
    """
    logger.info(f"Chat request: {{user_message[:100]}}")
    try:
        response = client.chat.completions.create(
            model="{model}",
            messages=[
                {{"role": "system", "content": system_prompt}},
                {{"role": "user", "content": user_message}},
            ],
        )
        result = response.choices[0].message.content
        logger.info(f"Tokens used: {{response.usage.total_tokens}}")
        return result
    except Exception as e:
        logger.error(f"API error: {{e}}")
        raise

print(chat("{user_input}"))''',
    ],
    "6/6": [
        '''from air_blackbox.trust.openai_agents import air_openai_client

client = air_openai_client()
response = client.chat.completions.create(
    model="{model}",
    messages=[
        {{"role": "system", "content": "{system_prompt}"}},
        {{"role": "user", "content": "{user_input}"}},
    ],
)
print(response.choices[0].message.content)''',
    ],
}

CLAUDE_AGENT_TEMPLATES = {
    "0/6": [
        '''import asyncio
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

async def main():
    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Write", "Bash"],
    )
    async with ClaudeSDKClient(options=options) as client:
        await client.query("{user_input}")
        async for message in client.receive_response():
            print(message)

asyncio.run(main())''',
        '''import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

async def main():
    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        allowed_tools=["Read", "Write", "Bash", "Agent"],
    )
    async for message in query(
        prompt="{user_input}",
        options=options,
    ):
        print(message)

asyncio.run(main())''',
    ],
    "2/6": [
        '''import asyncio
import logging
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, HookMatcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def log_tool_use(input_data, tool_use_id, context):
    """Log every tool call for audit trail."""
    logger.info(f"Tool: {{input_data.get('tool_name')}} id={{tool_use_id}}")
    return {{}}

async def main():
    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Write", "Bash"],
        hooks={{
            "PostToolUse": [HookMatcher(hooks=[log_tool_use])],
        }},
    )
    async with ClaudeSDKClient(options=options) as client:
        await client.query("{user_input}")
        async for message in client.receive_response():
            print(message)

asyncio.run(main())''',
    ],
    "4/6": [
        '''import asyncio
import logging
import json
import os
from datetime import datetime
from claude_agent_sdk import (
    ClaudeSDKClient, ClaudeAgentOptions, HookMatcher,
    PermissionResultAllow, PermissionResultDeny,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
os.makedirs("./audit", exist_ok=True)

DANGEROUS_COMMANDS = ["rm -rf", "sudo", "chmod 777", "mkfs"]

async def block_dangerous_bash(input_data, tool_use_id, context):
    """Block dangerous bash commands."""
    if input_data.get("tool_name") == "Bash":
        cmd = input_data.get("tool_input", {{}}).get("command", "")
        for pattern in DANGEROUS_COMMANDS:
            if pattern in cmd:
                logger.warning(f"Blocked dangerous command: {{cmd}}")
                return {{
                    "hookSpecificOutput": {{
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": f"Dangerous: {{pattern}}",
                    }}
                }}
    return {{}}

async def audit_log(input_data, tool_use_id, context):
    """Log every tool result to audit directory."""
    record = {{
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "tool": input_data.get("tool_name"),
        "tool_use_id": tool_use_id,
    }}
    fname = f"./audit/{{tool_use_id or 'unknown'}}.json"
    with open(fname, "w") as f:
        json.dump(record, f)
    return {{}}

async def permission_handler(tool_name, input_data, context):
    """Risk-based permission handler."""
    if tool_name == "Bash":
        cmd = input_data.get("command", "")
        if any(p in cmd for p in DANGEROUS_COMMANDS):
            return PermissionResultDeny(message="Blocked by policy")
    return PermissionResultAllow(updated_input=input_data)

async def main():
    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Write", "Bash"],
        can_use_tool=permission_handler,
        max_turns=10,
        hooks={{
            "PreToolUse": [
                HookMatcher(matcher="Bash", hooks=[block_dangerous_bash]),
            ],
            "PostToolUse": [HookMatcher(hooks=[audit_log])],
        }},
    )
    async with ClaudeSDKClient(options=options) as client:
        await client.query("{user_input}")
        async for message in client.receive_response():
            print(message)

asyncio.run(main())''',
    ],
    "6/6": [
        '''import asyncio
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from air_blackbox.trust.claude_agent import air_claude_hooks, air_permission_handler

async def main():
    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Write", "Bash"],
        hooks=air_claude_hooks(
            runs_dir="./audit",
            detect_pii=True,
            detect_injection=True,
        ),
        can_use_tool=air_permission_handler(
            runs_dir="./audit",
            block_critical=True,
        ),
        max_turns=15,
    )
    async with ClaudeSDKClient(options=options) as client:
        await client.query("{user_input}")
        async for message in client.receive_response():
            print(message)

asyncio.run(main())''',
    ],
}

AUTOGEN_TEMPLATES = {
    "0/6": [
        '''from autogen import ConversableAgent

assistant = ConversableAgent(
    name="{agent_name}",
    llm_config={{"model": "{model}"}},
    system_message="{system_prompt}",
)

user = ConversableAgent(
    name="user",
    human_input_mode="NEVER",
)

user.initiate_chat(assistant, message="{user_input}")''',
    ],
    "2/6": [
        '''import logging
from autogen import ConversableAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

assistant = ConversableAgent(
    name="{agent_name}",
    llm_config={{"model": "{model}"}},
    system_message="""{system_prompt}

    You must log all actions and explain your reasoning step by step.
    """,
    max_consecutive_auto_reply=5,
)

user = ConversableAgent(
    name="user",
    human_input_mode="NEVER",
)

logger.info(f"Starting chat with {{assistant.name}}")
result = user.initiate_chat(assistant, message="{user_input}")
logger.info(f"Chat completed with {{len(result.chat_history)}} messages")''',
    ],
    "6/6": [
        '''from autogen import ConversableAgent
from air_blackbox import AirTrust

trust = AirTrust()

assistant = ConversableAgent(
    name="{agent_name}",
    llm_config={{"model": "{model}"}},
    system_message="{system_prompt}",
)
trust.attach(assistant)

user = ConversableAgent(name="user", human_input_mode="NEVER")
user.initiate_chat(assistant, message="{user_input}")''',
    ],
}

HAYSTACK_TEMPLATES = {
    "0/6": [
        '''from haystack import Pipeline
from haystack.components.generators import OpenAIGenerator
from haystack.components.builders import PromptBuilder

template = \"""Given the context: {{{{context}}}}
Answer: {{{{question}}}}\"""

pipeline = Pipeline()
pipeline.add_component("prompt_builder", PromptBuilder(template=template))
pipeline.add_component("llm", OpenAIGenerator(model="{model}"))
pipeline.connect("prompt_builder", "llm")

result = pipeline.run({{
    "prompt_builder": {{"context": "{context}", "question": "{user_input}"}}
}})
print(result["llm"]["replies"][0])''',
    ],
    "2/6": [
        '''import logging
from haystack import Pipeline
from haystack.components.generators import OpenAIGenerator
from haystack.components.builders import PromptBuilder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

template = \"""Given the context: {{{{context}}}}
Answer the question: {{{{question}}}}
Provide sources for your claims.\"""

pipeline = Pipeline()
pipeline.add_component("prompt_builder", PromptBuilder(template=template))
pipeline.add_component("llm", OpenAIGenerator(model="{model}"))
pipeline.connect("prompt_builder", "llm")

logger.info("Running Haystack pipeline")
try:
    result = pipeline.run({{
        "prompt_builder": {{"context": "{context}", "question": "{user_input}"}}
    }})
    logger.info(f"Pipeline completed, tokens: {{result.get('llm', {{}}).get('meta', [{{}}])[0].get('usage', {{}})}}")
    print(result["llm"]["replies"][0])
except Exception as e:
    logger.error(f"Pipeline error: {{e}}")
    raise''',
    ],
}


# ── Fill-in values ──

TOOL_NAMES = [
    "query_database", "search_web", "send_email", "read_file",
    "write_report", "analyze_data", "fetch_api", "process_payment",
    "update_record", "generate_image", "translate_text", "summarize_doc",
    "extract_entities", "classify_text", "run_sql", "call_endpoint",
]

TOOL_DOCS = [
    "Query the customer database for records",
    "Search the web for relevant information",
    "Send an email notification to the user",
    "Read and parse a file from disk",
    "Write an analytical report to file",
    "Analyze structured data for patterns",
    "Fetch data from an external API endpoint",
    "Process a payment transaction",
    "Update a database record with new values",
    "Generate an image from a text description",
    "Translate text between languages",
    "Summarize a long document into key points",
    "Extract named entities from text",
    "Classify text into predefined categories",
    "Execute a SQL query against the database",
    "Call an external REST API endpoint",
]

MODELS = ["gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo", "claude-3-5-sonnet-20241022"]
VECTORSTORES = ["Chroma", "FAISS", "Pinecone", "Weaviate"]
TOOL_CLASSES = ["DuckDuckGoSearchRun", "WikipediaQueryRun", "ArxivQueryRun", "PubmedQueryRun"]

ROLES = [
    "Senior Research Analyst", "Data Engineer", "Customer Support Agent",
    "Content Writer", "Financial Advisor", "Code Reviewer",
    "Marketing Strategist", "Legal Compliance Officer",
    "DevOps Engineer", "Security Analyst",
]

GOALS = [
    "Find market trends in AI compliance",
    "Build data pipelines for analytics",
    "Resolve customer issues efficiently",
    "Create engaging technical content",
    "Analyze financial risk factors",
    "Review code for security vulnerabilities",
    "Develop marketing campaigns",
    "Ensure regulatory compliance",
    "Automate deployment workflows",
    "Detect and respond to security threats",
]

USER_INPUTS = [
    "Show me all customer emails from last month",
    "Find the latest EU AI regulation news",
    "What is our refund policy?",
    "Summarize the quarterly earnings report",
    "Analyze the security vulnerabilities in our API",
    "Generate a marketing plan for Q2",
    "Review the latest pull request for bugs",
    "Calculate the risk score for this portfolio",
    "Deploy the staging environment to production",
    "Search for compliance requirements for fintech",
    "Create a report on hiring trends in AI",
    "Process the pending invoice payments",
    "Translate the user manual to Spanish",
    "Classify these support tickets by priority",
    "Extract all PII from this dataset for review",
    "Run the monthly data quality checks",
]

SYSTEM_PROMPTS = [
    "You help customers with refund requests.",
    "You are an expert code reviewer for Python.",
    "You analyze financial data and provide insights.",
    "You help users find relevant research papers.",
    "You are a security analyst reviewing code for vulnerabilities.",
    "You help with data analysis and visualization.",
    "You are a compliance officer reviewing AI systems.",
    "You help draft marketing copy and campaigns.",
]

CONTEXTS = [
    "Our company processes over 10,000 transactions daily.",
    "The EU AI Act requires compliance by August 2026.",
    "Healthcare AI systems are classified as high-risk.",
    "Financial services must implement risk management frameworks.",
    "Customer data must be handled per GDPR requirements.",
]

AGENT_NAMES = [
    "research_assistant", "code_reviewer", "data_analyst",
    "support_agent", "writer_bot", "compliance_checker",
]


def random_fill(template: str) -> str:
    """Fill template placeholders with random values."""
    replacements = {
        "{tool_name}": random.choice(TOOL_NAMES),
        "{tool_doc}": random.choice(TOOL_DOCS),
        "{tool_class}": random.choice(TOOL_CLASSES),
        "{model}": random.choice(MODELS),
        "{vectorstore}": random.choice(VECTORSTORES),
        "{user_input}": random.choice(USER_INPUTS),
        "{system_prompt}": random.choice(SYSTEM_PROMPTS),
        "{role}": random.choice(ROLES),
        "{goal}": random.choice(GOALS),
        "{backstory}": f"Expert with {random.randint(3, 15)} years of experience in the field",
        "{agent_var}": random.choice(["researcher", "analyst", "agent", "assistant", "worker"]),
        "{agent_name}": random.choice(AGENT_NAMES),
        "{task_desc}": random.choice(GOALS),
        "{expected_output}": random.choice(["A detailed report", "JSON analysis", "Summary document", "Action items list"]),
        "{param}": random.choice(["query", "text", "data", "input_text", "prompt"]),
        "{param_desc}": random.choice(["search query", "input text", "data to process", "user prompt"]),
        "{return_desc}": random.choice(["The query results", "Processed output", "Analysis results"]),
        "{action}": random.choice([
            'f"Results for: {query}"',
            'db.execute(query)',
            'requests.get(f"https://api.example.com/{query}").text',
            'f"Processed: {text}"',
        ]).replace("{query}", "{" + random.choice(["query", "text"]) + "}"),
        "{db_dir}": random.choice(["chroma_db", "vector_store", "embeddings"]),
        "{query}": random.choice(USER_INPUTS),
        "{context}": random.choice(CONTEXTS),
        "{req_1}": "Include specific data sources",
        "{req_2}": "Provide actionable recommendations",
    }

    result = template
    for key, val in replacements.items():
        result = result.replace(key, val)
    return result


def generate_output(framework: str, level: str, code: str) -> str:
    """Generate the compliance analysis output."""
    # Determine which articles pass/fail/partial based on level
    if level == "0/6":
        statuses = {a: "fail" for a in [9, 10, 11, 12, 14, 15]}
    elif level == "2/6":
        # Typically: Art 11 partial (docs), Art 12 partial (logging)
        statuses = {9: "fail", 10: "fail", 11: "partial", 12: "partial", 14: "fail", 15: "fail"}
    elif level == "4/6":
        # Art 9 pass (risk mgmt), Art 11 pass (docs), Art 12 partial, Art 14 partial
        statuses = {9: "pass", 10: "fail", 11: "pass", 12: "partial", 14: "partial", 15: "fail"}
    elif level == "6/6":
        statuses = {a: "pass" for a in [9, 10, 11, 12, 14, 15]}
    else:
        statuses = {a: "fail" for a in [9, 10, 11, 12, 14, 15]}

    pass_count = sum(1 for s in statuses.values() if s == "pass")
    partial_count = sum(1 for s in statuses.values() if s == "partial")

    # Framework display names
    fw_names = {
        "langchain": "LangChain",
        "crewai": "CrewAI",
        "openai": "OpenAI SDK",
        "claude_agent": "Claude Agent SDK",
        "autogen": "AutoGen",
        "haystack": "Haystack",
    }
    fw_display = fw_names.get(framework, framework)

    trust_detected = "Detected" if level == "6/6" else "Not detected"

    lines = [
        "## EU AI Act Compliance Analysis",
        f"",
        f"**Framework detected**: {fw_display}",
        f"**AIR Blackbox trust wrapper**: {trust_detected}",
        f"**Technical compliance coverage**: {pass_count}/6 articles"
        + (f" ({partial_count} partial)" if partial_count else ""),
        "",
        "### Findings",
    ]

    for art_num in [9, 10, 11, 12, 14, 15]:
        status = statuses[art_num]
        art = ARTICLES[art_num]
        status_label = {"pass": "PASS", "fail": "FAIL", "partial": "PARTIAL"}[status]
        description = art[status]

        rec = ""
        if status == "fail":
            if art_num == 9:
                rec = "Recommendation: Add risk classification with ConsentGate or equivalent risk taxonomy."
            elif art_num == 10:
                rec = "Recommendation: Add PII scanning and data tokenization before LLM processing."
            elif art_num == 11:
                rec = "Recommendation: Add structured operation logging with timestamps and call graphs."
            elif art_num == 12:
                rec = "Recommendation: Add tamper-evident audit logging with HMAC-SHA256 chain integrity."
            elif art_num == 14:
                rec = "Recommendation: Add human approval gates for high-risk operations and kill switch capability."
            elif art_num == 15:
                rec = "Recommendation: Add multi-layer injection scanning and output validation."
        elif status == "partial":
            if art_num == 11:
                rec = "Recommendation: Upgrade from basic docstrings to automated structured operation logging."
            elif art_num == 12:
                rec = "Recommendation: Upgrade from standard logging to structured JSON with HMAC integrity chain."
            elif art_num == 14:
                rec = "Recommendation: Add formal approval gates beyond basic rate limiting."
            else:
                rec = "Recommendation: Strengthen existing controls to meet full Article requirements."

        lines.append(f"")
        lines.append(f"**Article {art_num} — {art['title']}**: {status_label}")
        lines.append(description)
        if rec:
            lines.append(rec)

    # Summary
    if level == "6/6":
        install_hint = f"`pip install air-blackbox`"
        lines.append("")
        lines.append("### Summary")
        lines.append(
            f"This {fw_display} agent has full EU AI Act compliance coverage via the "
            f"AIR Blackbox trust layer. All 6 articles are addressed with risk "
            f"classification, PII scanning, injection defense, structured audit "
            f"trails, and human oversight mechanisms."
        )
    elif level == "0/6":
        pkg = {
            "langchain": "air-langchain-trust",
            "crewai": "air-crewai-trust",
            "openai": "air-blackbox[openai]",
            "autogen": "air-blackbox[autogen]",
            "claude_agent": "air-blackbox[claude]",
            "haystack": "air-blackbox",
        }.get(framework, "air-blackbox")
        lines.append("")
        lines.append("### Summary")
        lines.append(
            f"This {fw_display} agent has no EU AI Act compliance controls. "
            f"It lacks risk classification (Art. 9), data governance (Art. 10), "
            f"technical documentation (Art. 11), record-keeping (Art. 12), "
            f"human oversight (Art. 14), and cybersecurity defenses (Art. 15). "
            f"To address the technical requirements, install: `pip install {pkg}`"
        )
    else:
        lines.append("")
        lines.append("### Summary")
        lines.append(
            f"This {fw_display} agent has partial EU AI Act compliance coverage "
            f"({pass_count}/6 articles, {partial_count} partial). "
            f"Key gaps remain in "
            + ", ".join(
                f"Art. {a}" for a, s in statuses.items() if s == "fail"
            )
            + ". Install the AIR Blackbox trust layer to close all gaps: "
            f"`pip install air-blackbox`"
        )

    return "\n".join(lines)


def generate_all():
    """Generate the full training dataset."""
    all_templates = {
        "langchain": LANGCHAIN_TEMPLATES,
        "crewai": CREWAI_TEMPLATES,
        "openai": OPENAI_TEMPLATES,
        "claude_agent": CLAUDE_AGENT_TEMPLATES,
        "autogen": AUTOGEN_TEMPLATES,
        "haystack": HAYSTACK_TEMPLATES,
    }

    examples = []
    target_per_framework = 400  # 6 frameworks × 400 = 2400

    for framework, templates in all_templates.items():
        count = 0
        levels = list(templates.keys())

        # Weight toward 0/6 (most common in real world) but include all levels
        level_weights = {"0/6": 0.35, "2/6": 0.25, "4/6": 0.25, "6/6": 0.15}

        while count < target_per_framework:
            # Pick level with weighting
            available = [l for l in levels if l in level_weights]
            weights = [level_weights.get(l, 0.1) for l in available]
            level = random.choices(available, weights=weights, k=1)[0]

            tmpl_list = templates[level]
            template = random.choice(tmpl_list)
            code = random_fill(template)

            output = generate_output(framework, level, code)

            examples.append({
                "instruction": INSTRUCTION,
                "input": code,
                "output": output,
            })
            count += 1

    # Shuffle for training
    random.shuffle(examples)
    return examples


if __name__ == "__main__":
    random.seed(42)  # Reproducible

    output_dir = Path(__file__).parent.parent / "training"
    output_dir.mkdir(exist_ok=True)

    examples = generate_all()

    output_path = output_dir / "training_data_v3.jsonl"
    with open(output_path, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")

    print(f"Generated {len(examples)} training examples → {output_path}")

    # Stats
    from collections import Counter
    levels = Counter()
    frameworks = Counter()
    for ex in examples:
        code = ex["input"]
        output = ex["output"]
        if "6/6 articles" in output:
            levels["6/6"] += 1
        elif "4/6" in output:
            levels["4/6"] += 1
        elif "2/6" in output or "partial" in output.lower():
            levels["2/6"] += 1
        else:
            levels["0/6"] += 1

        for fw in ["LangChain", "CrewAI", "OpenAI", "Claude Agent SDK", "AutoGen", "Haystack"]:
            if fw in output:
                frameworks[fw] += 1
                break

    print(f"\nCompliance levels: {dict(levels)}")
    print(f"Frameworks: {dict(frameworks)}")
