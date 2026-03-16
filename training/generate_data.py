#!/usr/bin/env python3
"""
AIR Blackbox — Training Data Generation Pipeline
=================================================
Generates additional EU AI Act compliance training examples by:
  1. Mining real code from top GitHub AI agent repos
  2. Augmenting existing examples with variations
  3. Generating edge case scenarios

Usage:
    # Phase 1: Mine GitHub repos (requires GITHUB_TOKEN for higher rate limits)
    python generate_data.py mine --output phase1_github.jsonl

    # Phase 2: Augment existing data with variations
    python generate_data.py augment --input training_data_combined_v3.jsonl --output phase2_augmented.jsonl

    # Phase 3: Generate edge cases
    python generate_data.py edges --output phase3_edges.jsonl

    # Combine all into final dataset
    python generate_data.py combine --output training_data_v4.jsonl

No GPU required. Runs on your Mac.
"""

import argparse
import json
import os
import re
import time
import random
import hashlib
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError

GITHUB_API = "https://api.github.com"
GITHUB_RAW = "https://raw.githubusercontent.com"

# ── Top AI agent repos to mine ──
REPOS = [
    # Framework core repos
    ("langchain-ai", "langgraph"),
    ("langchain-ai", "langchain", "libs/langchain/langchain"),
    ("langchain-ai", "langchain", "libs/community/langchain_community"),
    ("langchain-ai", "langchain", "libs/partners"),
    ("crewAIInc", "crewAI", "src/crewai"),
    ("deepset-ai", "haystack", "haystack"),
    ("run-llama", "llama_index", "llama-index-core/llama_index"),
    ("microsoft", "autogen", "autogen"),
    ("microsoft", "semantic-kernel", "python/semantic_kernel"),
    # Agent frameworks
    ("phidatahq", "phidata"),
    ("BerriAI", "litellm", "litellm"),
    ("instructor-ai", "instructor", "instructor"),
    ("dspy-ai", "dspy", "dspy"),
    ("pydantic", "pydantic-ai", "pydantic_ai"),
    ("openai", "openai-python", "src/openai"),
    ("anthropics", "anthropic-sdk-python", "src/anthropic"),
    # Real-world agent apps
    ("Significant-Gravitas", "AutoGPT"),
    ("geekan", "MetaGPT", "metagpt"),
    ("joaomdmoura", "crewAI-examples"),
    ("lobehub", "lobe-chat", "src"),
    ("FlowiseAI", "Flowise", "packages"),
    ("chatchat-space", "Langchain-Chatchat"),
    ("embedchain", "embedchain", "embedchain"),
    # MCP / tool-use patterns
    ("modelcontextprotocol", "python-sdk", "src"),
    ("anthropics", "courses", "tool_use"),
    # Guardrails & safety
    ("guardrails-ai", "guardrails", "guardrails"),
    ("NVIDIA", "NeMo-Guardrails", "nemoguardrails"),
    ("rebuff-ai", "rebuff", "python"),
    # RAG frameworks
    ("weaviate", "verba"),
    ("run-llama", "llama_index", "llama-index-integrations"),
    ("chroma-core", "chroma", "chromadb"),
]

# ── Articles and what to look for ──
ARTICLE_CHECKS = {
    9: {
        "name": "Risk Management",
        "pass_patterns": [
            r"try\b.*?except\b", r"error_handler", r"retry_policy",
            r"fallback", r"backoff", r"with_retry", r"max_retries",
        ],
        "fail_desc": "No error handling or fallback mechanisms for LLM calls",
        "pass_desc": "Error handling and fallback patterns detected",
    },
    10: {
        "name": "Data Governance",
        "pass_patterns": [
            r"pydantic|BaseModel|dataclass|TypedDict|validate",
            r"pii|redact|anonymize|mask|scrub|gdpr|personal_data",
        ],
        "fail_desc": "No input validation or PII handling detected",
        "pass_desc": "Input validation or PII handling patterns detected",
    },
    11: {
        "name": "Technical Documentation",
        "pass_patterns": [
            r'"""', r"'''", r"->",
            r":\s*(str|int|float|bool|List|Dict|Optional)",
        ],
        "fail_desc": "Missing docstrings and type annotations",
        "pass_desc": "Docstrings and type annotations present",
    },
    12: {
        "name": "Record-Keeping",
        "pass_patterns": [
            r"import logging|getLogger|structlog|loguru",
            r"opentelemetry|trace_id|langsmith|langfuse|callbacks",
            r"audit_trail|audit_log|event_log",
        ],
        "fail_desc": "No logging, tracing, or audit trail detected",
        "pass_desc": "Logging and tracing infrastructure detected",
    },
    14: {
        "name": "Human Oversight",
        "pass_patterns": [
            r"human_in_the_loop|human_approval|require_approval",
            r"rate_limit|max_tokens|max_iterations|max_steps|budget",
            r"user_id|user_context|auth_context|delegation",
            r"allowed_tools|tool_whitelist|action_boundary",
        ],
        "fail_desc": "No human oversight or usage controls detected",
        "pass_desc": "Human oversight or usage control patterns detected",
    },
    15: {
        "name": "Accuracy, Robustness & Cybersecurity",
        "pass_patterns": [
            r"retry|backoff|tenacity|exponential",
            r"injection|guardrail|content_filter|moderation|safety",
            r"output_parser|OutputParser|validate_output|response_model",
        ],
        "fail_desc": "No retry logic, injection defense, or output validation",
        "pass_desc": "Security and robustness patterns detected",
    },
}

# ── Instruction templates ──
FULL_ANALYSIS_INSTRUCTIONS = [
    "Analyze this Python code for EU AI Act compliance gaps. Check against Articles 9, 10, 11, 12, 14, and 15. Report which technical requirements are met or missing, with specific recommendations.",
    "Review the following Python AI code for EU AI Act compliance. Assess each article (9, 10, 11, 12, 14, 15) and provide findings with evidence from the code.",
    "Perform a compliance audit of this Python code against EU AI Act Articles 9-15. Identify passes, warnings, and failures with specific code references.",
]

SINGLE_ARTICLE_INSTRUCTIONS = {
    9: [
        "Check this code for EU AI Act Article 9 (Risk Management) compliance.",
        "Assess the risk management practices in this AI code under Article 9.",
        "Identify Article 9 compliance gaps in the following code.",
    ],
    10: [
        "Evaluate this code for Article 10 (Data Governance) compliance.",
        "Check data governance practices in this AI code against Article 10.",
        "Identify data handling compliance issues under Article 10.",
    ],
    11: [
        "Review this code for Article 11 (Technical Documentation) requirements.",
        "Assess documentation quality in this AI code per Article 11.",
        "Check if this code meets Article 11 documentation standards.",
    ],
    12: [
        "Evaluate record-keeping in this code against Article 12.",
        "Check this AI code for Article 12 (Record-Keeping) compliance.",
        "Assess logging and audit trail compliance under Article 12.",
    ],
    14: [
        "Check this code for Article 14 (Human Oversight) compliance.",
        "Evaluate human oversight mechanisms in this AI code per Article 14.",
        "Identify human oversight gaps in this code under Article 14.",
    ],
    15: [
        "Assess this code for Article 15 (Accuracy, Robustness & Cybersecurity).",
        "Check security and robustness in this AI code against Article 15.",
        "Identify cybersecurity compliance gaps under Article 15.",
    ],
}


def github_get(url, token=None):
    """Fetch from GitHub API with rate limit handling."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AIR-Blackbox-DataGen/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        if e.code == 403:
            print(f"  Rate limited. Waiting 60s...")
            time.sleep(60)
            return github_get(url, token)  # retry once
        raise


def github_raw(owner, repo, branch, path):
    """Fetch raw file content from GitHub."""
    url = f"{GITHUB_RAW}/{owner}/{repo}/{branch}/{path}"
    req = Request(url, headers={"User-Agent": "AIR-Blackbox-DataGen/1.0"})
    try:
        with urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return None


def analyze_code_for_articles(code):
    """Run pattern checks against code, return dict of article -> pass/fail."""
    results = {}
    for article, config in ARTICLE_CHECKS.items():
        passed = False
        for pattern_group in config["pass_patterns"]:
            if re.search(pattern_group, code, re.IGNORECASE | re.DOTALL):
                passed = True
                break
        results[article] = passed
    return results


def detect_framework(code):
    """Detect which AI framework the code uses."""
    checks = [
        ("LangChain", r"from langchain|import langchain|from langgraph"),
        ("CrewAI", r"from crewai|import crewai"),
        ("Haystack", r"from haystack|import haystack"),
        ("LlamaIndex", r"from llama_index|import llama_index"),
        ("AutoGen", r"from autogen|import autogen|ConversableAgent"),
        ("Semantic Kernel", r"from semantic_kernel|import semantic_kernel"),
        ("OpenAI SDK", r"from openai|import openai|client\.chat\.completions"),
        ("Anthropic SDK", r"from anthropic|import anthropic"),
        ("LiteLLM", r"from litellm|import litellm"),
        ("Instructor", r"from instructor|import instructor"),
    ]
    for name, pattern in checks:
        if re.search(pattern, code, re.IGNORECASE):
            return name
    return None


def generate_full_analysis(code, filepath, framework):
    """Generate a full 6-article compliance analysis for a code snippet."""
    results = analyze_code_for_articles(code)
    passing = sum(1 for v in results.values() if v)
    total = len(results)

    lines = []
    lines.append("## EU AI Act Compliance Analysis\n")
    lines.append(f"**Framework detected**: {framework or 'Unknown'}")
    lines.append(f"**Technical compliance coverage**: {passing}/{total} articles\n")
    lines.append("### Findings\n")

    for article, passed in results.items():
        config = ARTICLE_CHECKS[article]
        status = "PASS" if passed else "FAIL"
        desc = config["pass_desc"] if passed else config["fail_desc"]
        lines.append(f"**Article {article} — {config['name']}**: {status}")
        lines.append(f"{desc}")
        if not passed:
            lines.append(f"Recommendation: Address {config['name'].lower()} requirements to comply with Article {article}.")
        lines.append("")

    lines.append("### Summary")
    if passing == total:
        lines.append(f"This {framework or 'AI'} code has full compliance coverage across all {total} articles.")
    elif passing == 0:
        lines.append(f"This {framework or 'AI'} code has no EU AI Act compliance controls. All {total} articles need attention.")
    else:
        failing_articles = [str(a) for a, v in results.items() if not v]
        lines.append(f"This {framework or 'AI'} code has partial compliance ({passing}/{total} articles). Key gaps in Articles {', '.join(failing_articles)}.")

    return "\n".join(lines)


def generate_single_article_finding(code, filepath, framework, article):
    """Generate a single-article finding as a structured dict."""
    results = analyze_code_for_articles(code)
    passed = results.get(article, False)
    config = ARTICLE_CHECKS[article]

    return {
        "FINDING": config["pass_desc"] if passed else config["fail_desc"],
        "ARTICLE": article,
        "SEVERITY": "LOW" if passed else "HIGH",
        "EVIDENCE": f"Code in {filepath}" if passed else f"No {config['name'].lower()} patterns found in {filepath}",
        "RECOMMENDATION": f"Continue maintaining {config['name'].lower()} practices." if passed else f"Add {config['name'].lower()} controls to comply with Article {article}.",
    }


# ═══════════════════════════════════════
# Phase 1: Mine GitHub repos
# ═══════════════════════════════════════

def mine_repos(output_path, token=None):
    """Fetch Python files from top AI repos and generate training examples."""
    print(f"Phase 1: Mining GitHub repos → {output_path}")
    examples = []
    seen_hashes = set()

    for repo_info in REPOS:
        owner = repo_info[0]
        repo = repo_info[1]
        subpath = repo_info[2] if len(repo_info) > 2 else None

        print(f"\n  Mining {owner}/{repo}{'/' + subpath if subpath else ''}...")

        # Get default branch
        try:
            repo_data = github_get(f"{GITHUB_API}/repos/{owner}/{repo}", token)
            branch = repo_data.get("default_branch", "main")
        except Exception as e:
            print(f"    Error fetching repo info: {e}")
            continue

        # Get file tree
        try:
            tree_data = github_get(
                f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1",
                token,
            )
        except Exception as e:
            print(f"    Error fetching tree: {e}")
            continue

        # Filter Python files
        skip = r"(test_|_test\.py|conftest|setup\.py|__pycache__|\.egg|node_modules|\.git|venv|dist/|build/|deprecated|archived)"
        py_files = [
            f for f in (tree_data.get("tree") or [])
            if f["type"] == "blob"
            and f["path"].endswith(".py")
            and not re.search(skip, f["path"])
            and (not subpath or f["path"].startswith(subpath))
        ]

        # Sample up to 50 files per repo
        sampled = random.sample(py_files, min(50, len(py_files)))
        fetched = 0

        for f in sampled:
            content = github_raw(owner, repo, branch, f["path"])
            if not content or len(content) < 100 or len(content) > 15000:
                continue

            # Detect framework
            framework = detect_framework(content)
            if not framework:
                continue  # Skip non-AI files

            # Dedup by content hash
            h = hashlib.md5(content.encode()).hexdigest()
            if h in seen_hashes:
                continue
            seen_hashes.add(h)

            # Truncate very long files to keep training manageable
            if len(content) > 5000:
                lines = content.split("\n")
                content = "\n".join(lines[:150])

            rel_path = f["path"]
            if subpath and rel_path.startswith(subpath):
                rel_path = rel_path[len(subpath):].lstrip("/")

            # Generate full analysis (70% of examples)
            if random.random() < 0.7:
                output = generate_full_analysis(content, rel_path, framework)
                instruction = random.choice(FULL_ANALYSIS_INSTRUCTIONS)
                examples.append({
                    "instruction": instruction,
                    "input": content,
                    "output": output,
                })
            else:
                # Generate single-article finding (30%)
                article = random.choice(list(ARTICLE_CHECKS.keys()))
                output = generate_single_article_finding(content, rel_path, framework, article)
                instruction = random.choice(SINGLE_ARTICLE_INSTRUCTIONS[article])
                examples.append({
                    "instruction": instruction,
                    "input": content,
                    "output": output,
                })

            fetched += 1

        print(f"    Got {fetched} examples from {owner}/{repo}")
        time.sleep(1)  # Be nice to GitHub

    # Write output
    with open(output_path, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")

    print(f"\nPhase 1 complete: {len(examples)} examples → {output_path}")
    return examples


# ═══════════════════════════════════════
# Phase 2: Augment with variations
# ═══════════════════════════════════════

FRAMEWORK_SWAPS = {
    "LangChain": {
        "from langchain": "from crewai",
        "ChatOpenAI": "CrewAgent",
        "AgentExecutor": "Crew",
        "langchain": "crewai",
    },
    "CrewAI": {
        "from crewai": "from langchain",
        "Crew(": "AgentExecutor(",
        "Agent(": "create_openai_tools_agent(",
        "crewai": "langchain",
    },
    "OpenAI": {
        "from openai": "from anthropic",
        "OpenAI(": "Anthropic(",
        "ChatCompletion": "Messages",
        "gpt-4": "claude-3-opus",
        "openai": "anthropic",
    },
}

VARIABLE_RENAMES = [
    ("agent", "bot"),
    ("llm", "model"),
    ("chain", "pipeline"),
    ("tool", "action"),
    ("prompt", "instruction"),
    ("response", "result"),
    ("output", "answer"),
    ("handler", "processor"),
]


def augment_data(input_path, output_path, multiplier=2):
    """Generate variations of existing training examples."""
    print(f"Phase 2: Augmenting {input_path} → {output_path}")

    with open(input_path) as f:
        originals = [json.loads(line) for line in f]

    augmented = []
    seen_hashes = set()

    for orig in originals:
        code = orig.get("input", "")
        if not code or len(code) < 50:
            continue

        for _ in range(multiplier):
            new_code = code

            # Random variable renames (pick 1-3)
            renames = random.sample(VARIABLE_RENAMES, min(3, len(VARIABLE_RENAMES)))
            for old, new in renames:
                if random.random() < 0.5:
                    new_code = re.sub(r'\b' + old + r'\b', new, new_code)

            # Random style changes
            if random.random() < 0.3:
                # Add/remove blank lines
                lines = new_code.split("\n")
                new_lines = []
                for line in lines:
                    new_lines.append(line)
                    if random.random() < 0.1:
                        new_lines.append("")
                new_code = "\n".join(new_lines)

            if random.random() < 0.2:
                # Swap print → logger.info
                new_code = new_code.replace("print(", "logger.info(")

            # Dedup
            h = hashlib.md5(new_code.encode()).hexdigest()
            if h in seen_hashes or h == hashlib.md5(code.encode()).hexdigest():
                continue
            seen_hashes.add(h)

            # Detect new framework (may have changed via swap)
            framework = detect_framework(new_code) or "Unknown"
            output = generate_full_analysis(new_code, "augmented.py", framework)

            augmented.append({
                "instruction": random.choice(FULL_ANALYSIS_INSTRUCTIONS),
                "input": new_code,
                "output": output,
            })

    # Write
    with open(output_path, "w") as f:
        for ex in augmented:
            f.write(json.dumps(ex) + "\n")

    print(f"Phase 2 complete: {len(augmented)} augmented examples → {output_path}")
    return augmented


# ═══════════════════════════════════════
# Phase 3: Edge cases
# ═══════════════════════════════════════

EDGE_CASE_TEMPLATES = [
    # Multi-agent delegation
    {
        "code": '''from crewai import Agent, Task, Crew

researcher = Agent(role="Researcher", goal="Find data", allow_delegation=True)
writer = Agent(role="Writer", goal="Write report", allow_delegation=True)
reviewer = Agent(role="Reviewer", goal="Review output")

task1 = Task(description="Research market trends", agent=researcher)
task2 = Task(description="Write analysis report", agent=writer)
task3 = Task(description="Review for accuracy", agent=reviewer)

crew = Crew(agents=[researcher, writer, reviewer], tasks=[task1, task2, task3])
result = crew.kickoff()''',
        "framework": "CrewAI",
        "notes": "Multi-agent with delegation — Article 14 concern: who is accountable when agents delegate?",
    },
    # RAG with external data
    {
        "code": '''from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI

embeddings = OpenAIEmbeddings()
vectorstore = Chroma(persist_directory="./data", embedding_function=embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

qa_chain = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(model="gpt-4", temperature=0),
    chain_type="stuff",
    retriever=retriever,
)
answer = qa_chain.invoke({"query": user_input})''',
        "framework": "LangChain",
        "notes": "RAG pipeline — Article 10 concern: external data governance, PII in vector store. Article 15: no input sanitization on user_input.",
    },
    # Agent writing and executing code
    {
        "code": '''from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain.tools import tool

@tool
def execute_python(code: str) -> str:
    """Execute arbitrary Python code and return the result."""
    exec_globals = {}
    exec(code, exec_globals)
    return str(exec_globals.get("result", "No result"))

llm = ChatOpenAI(model="gpt-4")
agent = create_openai_tools_agent(llm, [execute_python])
executor = AgentExecutor(agent=agent, tools=[execute_python])
result = executor.invoke({"input": "Calculate the average salary from the database"})''',
        "framework": "LangChain",
        "notes": "Code execution agent — CRITICAL: Article 15 fail (arbitrary code execution), Article 14 fail (no approval gate for exec), Article 9 fail (no risk classification).",
    },
    # TypeScript-style agent (Python wrapper)
    {
        "code": '''import subprocess
import json

def run_ts_agent(prompt: str) -> dict:
    """Run a TypeScript AI agent via subprocess."""
    result = subprocess.run(
        ["npx", "ts-node", "agent.ts", "--prompt", prompt],
        capture_output=True, text=True, timeout=60,
    )
    return json.loads(result.stdout)

output = run_ts_agent("Summarize all customer complaints from last month")''',
        "framework": "Unknown",
        "notes": "Subprocess agent — all articles fail: no logging, no oversight, no error handling, shell injection risk.",
    },
    # Agent with MCP server tools
    {
        "code": '''from anthropic import Anthropic

client = Anthropic()

tools = [
    {"name": "read_file", "description": "Read a file from disk"},
    {"name": "write_file", "description": "Write content to a file"},
    {"name": "run_bash", "description": "Execute a bash command"},
    {"name": "send_email", "description": "Send an email to any address"},
]

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    tools=tools,
    messages=[{"role": "user", "content": user_request}],
)

for block in response.content:
    if block.type == "tool_use":
        result = execute_tool(block.name, block.input)''',
        "framework": "Anthropic SDK",
        "notes": "Tool-use agent with powerful capabilities — Article 14: no approval for send_email or run_bash. Article 9: no risk classification per tool.",
    },
    # Fine-tuned model deployment without model card
    {
        "code": '''from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

model = AutoModelForCausalLM.from_pretrained("./my-finetuned-model")
tokenizer = AutoTokenizer.from_pretrained("./my-finetuned-model")

def generate(prompt: str) -> str:
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(**inputs, max_new_tokens=512)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

# API endpoint
from flask import Flask, request
app = Flask(__name__)

@app.route("/predict", methods=["POST"])
def predict():
    return {"result": generate(request.json["prompt"])}''',
        "framework": "Unknown",
        "notes": "Deployed fine-tuned model — Article 11: no model card, no documentation of training data or intended use. Article 10: no input validation on API endpoint.",
    },
    # Agent with database access
    {
        "code": '''from langchain.agents import create_sql_agent
from langchain_openai import ChatOpenAI
from langchain.sql_database import SQLDatabase

db = SQLDatabase.from_uri("postgresql://admin:password@prod-db:5432/customers")
llm = ChatOpenAI(model="gpt-4", temperature=0)

agent = create_sql_agent(llm=llm, db=db, verbose=True)
result = agent.invoke({"input": user_query})
print(result)''',
        "framework": "LangChain",
        "notes": "SQL agent with production database — CRITICAL: credentials in code, Article 10 fail (PII access without governance), Article 15 fail (SQL injection risk).",
    },
    # Compliant agent with all controls
    {
        "code": '''import logging
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from pydantic import BaseModel, Field
from air_blackbox.trust.langchain import AirLangChainHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SearchInput(BaseModel):
    """Validated search input."""
    query: str = Field(..., max_length=500, description="Search query")
    max_results: int = Field(default=5, le=20)

trust = AirLangChainHandler(
    runs_dir="./audit",
    detect_pii=True,
    detect_injection=True,
    consent_mode="BLOCK_HIGH_AND_CRITICAL",
)

llm = ChatOpenAI(model="gpt-4", callbacks=[trust], max_tokens=1000)

@tool
def safe_search(input: SearchInput) -> str:
    """Search with validated, bounded input."""
    logger.info(f"Search: {input.query}")
    return f"Results for: {input.query}"

agent = AgentExecutor(
    agent=create_openai_tools_agent(llm, [safe_search]),
    tools=[safe_search],
    max_iterations=5,
    handle_parsing_errors=True,
    callbacks=[trust],
)
result = agent.invoke({"input": "Find recent AI governance papers"})''',
        "framework": "LangChain",
        "notes": "FULLY COMPLIANT: logging, PII detection, injection defense, input validation, rate limiting, trust layer, error handling.",
    },
    # ── NEW EDGE CASES (v5 expansion) ──
    # 9. Streaming agent with no output validation
    {
        "code": '''from openai import OpenAI

client = OpenAI()

def stream_agent(prompt: str):
    stream = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    full_response = ""
    for chunk in stream:
        if chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            print(content, end="", flush=True)
            full_response += content
    return full_response

result = stream_agent(user_input)
save_to_database(result)''',
        "framework": "OpenAI SDK",
        "notes": "Streaming without output validation — Article 15: unvalidated output saved directly to DB. Article 12: no logging of streamed content. Article 10: no input sanitization.",
    },
    # 10. Autonomous web scraping agent
    {
        "code": '''from crewai import Agent, Task, Crew
from crewai_tools import ScrapeWebsiteTool, SerperDevTool

scraper = ScrapeWebsiteTool()
search = SerperDevTool()

researcher = Agent(
    role="Web Researcher",
    goal="Scrape competitor websites and extract pricing data",
    tools=[scraper, search],
    allow_delegation=False,
    verbose=True,
)

task = Task(
    description="Find and scrape pricing pages from these competitors: {competitors}",
    expected_output="JSON with competitor pricing data",
    agent=researcher,
)

crew = Crew(agents=[researcher], tasks=[task])
result = crew.kickoff(inputs={"competitors": competitor_list})''',
        "framework": "CrewAI",
        "notes": "Web scraping agent — Article 10: scraping external data with no governance. Article 14: no human approval for what gets scraped. Article 15: no content filtering on scraped data.",
    },
    # 11. LangGraph stateful agent with memory
    {
        "code": '''from langgraph.graph import StateGraph, MessagesState
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4")

def chatbot(state: MessagesState):
    return {"messages": [llm.invoke(state["messages"])]}

graph = StateGraph(MessagesState)
graph.add_node("chatbot", chatbot)
graph.set_entry_point("chatbot")
app = graph.compile()

# Persistent memory across sessions
from langgraph.checkpoint.sqlite import SqliteSaver
memory = SqliteSaver.from_conn_string(":memory:")
app = graph.compile(checkpointer=memory)

config = {"configurable": {"thread_id": "user_123"}}
result = app.invoke({"messages": [("human", user_input)]}, config)''',
        "framework": "LangChain",
        "notes": "Stateful agent with persistent memory — Article 10: user data stored without governance. Article 12: no audit of conversation history. Article 14: no session limits or memory bounds.",
    },
    # 12. Multi-model orchestration
    {
        "code": '''from litellm import completion

def multi_model_decision(prompt: str) -> str:
    """Ask multiple models and take majority vote."""
    models = ["gpt-4", "claude-3-opus-20240229", "gemini-pro"]
    responses = []
    for model in models:
        resp = completion(model=model, messages=[{"role": "user", "content": prompt}])
        responses.append(resp.choices[0].message.content)

    # Naive majority vote
    from collections import Counter
    votes = Counter(responses)
    return votes.most_common(1)[0][0]

decision = multi_model_decision("Should we approve this loan application?")
execute_decision(decision)''',
        "framework": "LiteLLM",
        "notes": "Multi-model voting on high-stakes decision — Article 14: automated loan decision with no human review. Article 9: no risk assessment for financial decisions. Article 12: no audit trail of which model decided what.",
    },
    # 13. Agent with file system access
    {
        "code": '''from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI
from langchain.tools import tool
import os
import shutil

@tool
def list_files(directory: str) -> str:
    """List all files in a directory."""
    return str(os.listdir(directory))

@tool
def read_file(path: str) -> str:
    """Read contents of any file."""
    with open(path) as f:
        return f.read()

@tool
def delete_file(path: str) -> str:
    """Delete a file or directory."""
    if os.path.isdir(path):
        shutil.rmtree(path)
    else:
        os.remove(path)
    return f"Deleted {path}"

llm = ChatOpenAI(model="gpt-4")
agent = create_openai_tools_agent(llm, [list_files, read_file, delete_file])
executor = AgentExecutor(agent=agent, tools=[list_files, read_file, delete_file])
result = executor.invoke({"input": "Clean up all temporary files in /tmp"})''',
        "framework": "LangChain",
        "notes": "File system agent with delete capability — CRITICAL: Article 9 fail (destructive operations without risk classification). Article 14: no approval gate for delete. Article 15: path traversal risk.",
    },
    # 14. Healthcare AI agent
    {
        "code": '''from openai import OpenAI

client = OpenAI()

def diagnose_symptoms(symptoms: str, patient_history: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a medical diagnosis assistant."},
            {"role": "user", "content": f"Patient symptoms: {symptoms}\\nHistory: {patient_history}\\nProvide diagnosis and treatment recommendations."},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content

diagnosis = diagnose_symptoms(patient_symptoms, patient_medical_history)
send_to_patient_portal(diagnosis)''',
        "framework": "OpenAI SDK",
        "notes": "Healthcare AI — HIGH RISK: Article 9 fail (medical decisions require highest risk management). Article 14 fail (no physician review). Article 10 fail (patient data handling, HIPAA). Article 11 fail (no model limitations documented).",
    },
    # 15. Autonomous hiring/screening agent
    {
        "code": '''from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI
from langchain.tools import tool

@tool
def score_resume(resume_text: str) -> dict:
    """Score a resume on a 1-10 scale."""
    llm = ChatOpenAI(model="gpt-4", temperature=0)
    result = llm.invoke(f"Score this resume 1-10 for a senior engineer role: {resume_text}")
    return {"score": result.content}

@tool
def send_rejection(email: str, name: str) -> str:
    """Send automated rejection email."""
    send_email(email, f"Dear {name}, unfortunately...")
    return f"Rejection sent to {email}"

llm = ChatOpenAI(model="gpt-4")
tools = [score_resume, send_rejection]
agent = create_openai_tools_agent(llm, tools)
executor = AgentExecutor(agent=agent, tools=tools, max_iterations=20)
result = executor.invoke({"input": f"Screen these 50 resumes and reject anyone below 7: {resumes}"})''',
        "framework": "LangChain",
        "notes": "Automated hiring — HIGH RISK: Article 14 fail (automated employment decisions). Article 9 fail (bias risk in scoring). Article 10 fail (PII in resumes without governance). Article 12 fail (no audit of rejection decisions).",
    },
    # 16. Agent deploying infrastructure
    {
        "code": '''import subprocess
from anthropic import Anthropic

client = Anthropic()

def run_command(cmd: str) -> str:
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout + result.stderr

tools = [
    {"name": "run_command", "description": "Execute shell command on production server",
     "input_schema": {"type": "object", "properties": {"cmd": {"type": "string"}}}}
]

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    system="You are a DevOps engineer. Deploy the latest code to production.",
    tools=tools,
    messages=[{"role": "user", "content": "Deploy v2.3.1 to production cluster"}],
)''',
        "framework": "Anthropic SDK",
        "notes": "Production deployment agent — CRITICAL: shell=True with arbitrary commands. Article 9: no risk classification for production changes. Article 14: no human approval for deployments. Article 15: command injection risk.",
    },
    # 17. PII extraction agent
    {
        "code": '''from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

llm = ChatOpenAI(model="gpt-4", temperature=0)
extract_prompt = PromptTemplate(
    template="Extract all personal information from this text including names, emails, phone numbers, SSNs, and addresses:\\n\\n{text}\\n\\nReturn as JSON.",
    input_variables=["text"],
)

chain = LLMChain(llm=llm, prompt=extract_prompt)
pii_data = chain.invoke({"text": document_content})

import json
with open("extracted_pii.json", "w") as f:
    json.dump(pii_data, f)''',
        "framework": "LangChain",
        "notes": "PII extraction and storage — CRITICAL: Article 10 fail (extracting and storing PII without governance). Article 15 fail (no encryption, plaintext PII to disk). Article 12 fail (no audit of data access).",
    },
    # 18. Haystack RAG pipeline with web retrieval
    {
        "code": '''from haystack import Pipeline
from haystack.components.retrievers.in_memory import InMemoryBM25Retriever
from haystack.components.generators import OpenAIGenerator
from haystack.components.builders import PromptBuilder
from haystack.document_stores.in_memory import InMemoryDocumentStore

document_store = InMemoryDocumentStore()

retriever = InMemoryBM25Retriever(document_store=document_store)
prompt_builder = PromptBuilder(template="Answer based on context: {{documents}} Question: {{query}}")
generator = OpenAIGenerator(model="gpt-4")

rag_pipeline = Pipeline()
rag_pipeline.add_component("retriever", retriever)
rag_pipeline.add_component("prompt_builder", prompt_builder)
rag_pipeline.add_component("generator", generator)
rag_pipeline.connect("retriever", "prompt_builder.documents")
rag_pipeline.connect("prompt_builder", "generator")

result = rag_pipeline.run({"retriever": {"query": user_query}, "prompt_builder": {"query": user_query}})''',
        "framework": "Haystack",
        "notes": "Haystack RAG — Article 10: no document provenance tracking. Article 12: no logging of retrieval decisions. Article 15: no input validation on user_query.",
    },
    # 19. AutoGen multi-agent conversation
    {
        "code": '''from autogen import ConversableAgent, GroupChat, GroupChatManager

config_list = [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]

planner = ConversableAgent("planner", llm_config={"config_list": config_list},
    system_message="You plan tasks for the team.")
coder = ConversableAgent("coder", llm_config={"config_list": config_list},
    system_message="You write Python code.")
executor = ConversableAgent("executor", llm_config={"config_list": config_list},
    code_execution_config={"work_dir": "coding", "use_docker": False},
    system_message="You execute code.")

groupchat = GroupChat(agents=[planner, coder, executor], messages=[], max_round=20)
manager = GroupChatManager(groupchat=groupchat, llm_config={"config_list": config_list})

planner.initiate_chat(manager, message="Build a web scraper for product prices")''',
        "framework": "AutoGen",
        "notes": "AutoGen multi-agent with code execution — Article 14: no human in the loop for 20 rounds. Article 9: code execution without Docker (use_docker=False). Article 15: web scraping with no content filtering.",
    },
    # 20. Semantic Kernel with plugins
    {
        "code": '''import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

kernel = sk.Kernel()
kernel.add_service(OpenAIChatCompletion(service_id="chat", ai_model_id="gpt-4"))

# Add plugins
from semantic_kernel.core_plugins import FileIOPlugin, HttpPlugin, MathPlugin
kernel.add_plugin(FileIOPlugin(), "file")
kernel.add_plugin(HttpPlugin(), "http")
kernel.add_plugin(MathPlugin(), "math")

# Run with planner
from semantic_kernel.planners import SequentialPlanner
planner = SequentialPlanner(kernel)
plan = await planner.create_plan("Read customer data from file, calculate totals, and send HTTP report")
result = await plan.invoke(kernel)''',
        "framework": "Semantic Kernel",
        "notes": "SK planner with file/HTTP plugins — Article 14: autonomous planning with no approval. Article 10: reading customer data without governance. Article 9: no risk classification for HTTP calls.",
    },
    # 21. Instructor structured extraction (partially compliant)
    {
        "code": '''import instructor
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List

client = instructor.from_openai(OpenAI())

class UserProfile(BaseModel):
    """Extracted user profile data."""
    name: str = Field(description="Full name")
    email: str = Field(description="Email address")
    age: int = Field(ge=0, le=150, description="Age")
    interests: List[str] = Field(max_length=20, description="User interests")

profile = client.chat.completions.create(
    model="gpt-4",
    response_model=UserProfile,
    messages=[{"role": "user", "content": f"Extract profile from: {raw_text}"}],
    max_retries=3,
)
store_in_database(profile)''',
        "framework": "Instructor",
        "notes": "Instructor with validation — PARTIAL: Article 10 pass (Pydantic validation), Article 11 pass (type annotations), but Article 10 fail (PII extraction without consent), Article 12 fail (no logging), Article 14 fail (no human review of extracted data).",
    },
    # 22. DSPy optimization pipeline
    {
        "code": '''import dspy
from dspy.teleprompt import BootstrapFewShotWithRandomSearch

lm = dspy.OpenAI(model="gpt-4", max_tokens=500)
dspy.settings.configure(lm=lm)

class ContentModerator(dspy.Signature):
    """Determine if content violates community guidelines."""
    content = dspy.InputField(desc="User-generated content to moderate")
    decision = dspy.OutputField(desc="APPROVE or REJECT with reason")

class ModerationModule(dspy.Module):
    def __init__(self):
        self.moderate = dspy.ChainOfThought(ContentModerator)

    def forward(self, content):
        return self.moderate(content=content)

moderator = ModerationModule()
optimizer = BootstrapFewShotWithRandomSearch(metric=lambda x, y: y.decision.startswith("APPROVE"))
optimized = optimizer.compile(moderator, trainset=training_data)
result = optimized(content=user_post)''',
        "framework": "Unknown",
        "notes": "DSPy content moderation — Article 14: automated content decisions with no human review. Article 9: optimizer biased toward APPROVE (metric rewards approval). Article 11: no documentation of moderation criteria.",
    },
    # 23. FastAPI AI endpoint with no auth
    {
        "code": '''from fastapi import FastAPI
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import tool

app = FastAPI()
llm = ChatOpenAI(model="gpt-4")

@tool
def query_database(sql: str) -> str:
    """Run SQL query against the database."""
    import sqlite3
    conn = sqlite3.connect("production.db")
    return str(conn.execute(sql).fetchall())

agent = create_openai_tools_agent(llm, [query_database])
executor = AgentExecutor(agent=agent, tools=[query_database])

@app.post("/ask")
async def ask(question: str):
    result = executor.invoke({"input": question})
    return {"answer": result["output"]}''',
        "framework": "LangChain",
        "notes": "Public API with SQL access — CRITICAL: no authentication, no rate limiting. Article 15: SQL injection via natural language. Article 14: no access control. Article 10: direct database access without governance.",
    },
    # 24. Embedding pipeline with no data provenance
    {
        "code": '''from langchain_openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

loader = DirectoryLoader("./documents/", glob="**/*.txt", loader_cls=TextLoader)
documents = loader.load()

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = splitter.split_documents(documents)

embeddings = OpenAIEmbeddings()
vectorstore = FAISS.from_documents(chunks, embeddings)
vectorstore.save_local("./faiss_index")

print(f"Indexed {len(chunks)} chunks from {len(documents)} documents")''',
        "framework": "LangChain",
        "notes": "Embedding pipeline — Article 10: no tracking of document sources or data lineage. Article 11: no documentation of what data is indexed. Article 12: no audit trail of indexing operations.",
    },
    # 25. Guardrails-wrapped agent (partially compliant)
    {
        "code": '''import guardrails as gd
from guardrails.hub import ToxicLanguage, DetectPII, ReadingLevel
from openai import OpenAI

client = OpenAI()

guard = gd.Guard().use_many(
    ToxicLanguage(on_fail="exception"),
    DetectPII(pii_entities=["EMAIL_ADDRESS", "PHONE_NUMBER"], on_fail="fix"),
    ReadingLevel(level=8, on_fail="reask"),
)

raw_response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": user_query}],
)

validated_response = guard.validate(raw_response.choices[0].message.content)
return validated_response.validated_output''',
        "framework": "Unknown",
        "notes": "Guardrails-wrapped output — PARTIAL: Article 15 pass (toxicity filter, PII redaction), Article 10 partial (PII detection but not on input), Article 12 fail (no logging of guard actions), Article 14 fail (no human review).",
    },
    # 26. CrewAI with custom tool and memory
    {
        "code": '''from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field

class WebSearchInput(BaseModel):
    query: str = Field(description="Search query")

class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = "Search the internet for current information"
    args_schema: Type[BaseModel] = WebSearchInput

    def _run(self, query: str) -> str:
        import requests
        resp = requests.get(f"https://api.serper.dev/search", params={"q": query})
        return resp.json()

analyst = Agent(
    role="Market Analyst",
    goal="Analyze market trends and provide investment recommendations",
    tools=[WebSearchTool()],
    memory=True,
    verbose=True,
)

task = Task(
    description="Analyze {stock} and recommend buy/sell/hold",
    expected_output="Investment recommendation with rationale",
    agent=analyst,
)

crew = Crew(agents=[analyst], tasks=[task], process=Process.sequential, memory=True)
result = crew.kickoff(inputs={"stock": ticker_symbol})''',
        "framework": "CrewAI",
        "notes": "Investment recommendation agent — HIGH RISK: Article 14 fail (financial advice without human advisor). Article 9 fail (no risk classification for financial decisions). Article 11 pass (Pydantic schema). Article 12 fail (verbose logging but no structured audit).",
    },
    # 27. Phidata agent with knowledge base
    {
        "code": '''from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.pgvector import PgVector
from phi.tools.email import EmailTools

knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://example.com/policy.pdf"],
    vector_db=PgVector(table_name="policies", db_url="postgresql://localhost/ai"),
)
knowledge_base.load()

agent = Agent(
    model=OpenAIChat(id="gpt-4"),
    knowledge=knowledge_base,
    tools=[EmailTools(sender_name="AI Assistant", sender_email="ai@company.com")],
    instructions=["Always be helpful", "Email results to the user"],
    show_tool_calls=True,
)

agent.print_response("What is our refund policy? Email it to customer@example.com")''',
        "framework": "Unknown",
        "notes": "Phidata agent with email — Article 14: automated email sending with no approval. Article 10: external PDF ingestion without governance. Article 15: no validation of email recipients. Article 9: no risk classification for email tool.",
    },
    # 28. LlamaIndex agent with query engine
    {
        "code": '''from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.llms.openai import OpenAI
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import QueryEngineTool, ToolMetadata

Settings.llm = OpenAI(model="gpt-4", temperature=0)

documents = SimpleDirectoryReader("./company_data/").load_data()
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine()

tools = [
    QueryEngineTool(
        query_engine=query_engine,
        metadata=ToolMetadata(name="company_search", description="Search company documents"),
    ),
]

agent = ReActAgent.from_tools(tools, verbose=True)
response = agent.chat("What were our Q3 revenue numbers and how do they compare to competitors?")''',
        "framework": "LlamaIndex",
        "notes": "LlamaIndex ReAct agent — Article 10: company data indexed without access controls. Article 12: verbose but no structured logging. Article 11: no documentation of data sources. Article 14: financial data access without authorization.",
    },
    # 29. NeMo Guardrails config (compliant example)
    {
        "code": '''from nemoguardrails import RailsConfig, LLMRails
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = RailsConfig.from_content(
    yaml_content=\"\"\"
    models:
      - type: main
        engine: openai
        model: gpt-4
    rails:
      input:
        flows:
          - check jailbreak
          - check input toxicity
          - check pii
      output:
        flows:
          - check output toxicity
          - check factual accuracy
          - check hallucination
    \"\"\",
    colang_content=\"\"\"
    define user ask about harmful topics
      "How to hack"
      "How to make weapons"

    define bot refuse harmful request
      "I cannot help with that request."

    define flow check harmful
      user ask about harmful topics
      bot refuse harmful request
    \"\"\"
)

rails = LLMRails(config)

response = rails.generate(messages=[{"role": "user", "content": user_input}])
logger.info(f"Guardrailed response generated: {response}")''',
        "framework": "Unknown",
        "notes": "NeMo Guardrails — HIGH COMPLIANCE: Article 15 pass (input/output filtering, jailbreak detection, toxicity checks). Article 12 pass (logging). Article 9 partial (guardrails but no explicit risk classification). Article 14 fail (no human fallback for edge cases).",
    },
    # 30. Batch processing agent (no rate limits)
    {
        "code": '''from openai import OpenAI
import asyncio
import aiohttp

client = OpenAI()

async def process_all_customers(customers: list):
    """Process all customer records through AI analysis."""
    results = []
    for customer in customers:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": f"Analyze this customer profile and assign a credit score: {customer}"}],
        )
        score = response.choices[0].message.content
        results.append({"customer_id": customer["id"], "ai_score": score})
    return results

# Process 10,000 customers
import json
with open("customers.json") as f:
    all_customers = json.load(f)

scores = asyncio.run(process_all_customers(all_customers))
with open("credit_scores.json", "w") as f:
    json.dump(scores, f)''',
        "framework": "OpenAI SDK",
        "notes": "Batch credit scoring — HIGH RISK: Article 14 fail (automated credit decisions for 10K people). Article 9 fail (no risk assessment for financial scoring). Article 10 fail (bulk PII processing). Article 12 fail (no per-decision audit trail).",
    },
    # 31. Agent with environment variable secrets
    {
        "code": '''import os
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import tool

@tool
def access_aws(action: str, resource: str) -> str:
    """Access AWS resources."""
    import boto3
    session = boto3.Session(
        aws_access_key_id=os.environ["AWS_ACCESS_KEY"],
        aws_secret_access_key=os.environ["AWS_SECRET_KEY"],
    )
    s3 = session.client("s3")
    if action == "list":
        return str(s3.list_objects_v2(Bucket=resource))
    elif action == "delete":
        return str(s3.delete_object(Bucket=resource, Key="data"))

llm = ChatOpenAI(model="gpt-4")
agent = create_openai_tools_agent(llm, [access_aws])
executor = AgentExecutor(agent=agent, tools=[access_aws])
result = executor.invoke({"input": "List all files in the customer-data bucket and delete old backups"})''',
        "framework": "LangChain",
        "notes": "AWS access agent with delete capability — CRITICAL: Article 9 fail (destructive cloud operations). Article 14 fail (no approval for delete). Article 15 fail (no access boundary on S3 operations). Article 12 fail (no audit of cloud actions).",
    },
    # 32. Compliant CrewAI with full controls
    {
        "code": '''import logging
from crewai import Agent, Task, Crew, Process
from pydantic import BaseModel, Field
from typing import Optional
from air_crewai_trust import AirTrustHook

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

class ResearchOutput(BaseModel):
    """Validated research output."""
    summary: str = Field(..., max_length=2000)
    sources: list[str] = Field(..., max_length=10)
    confidence: float = Field(..., ge=0, le=1)

trust_hook = AirTrustHook(
    audit_dir="./audit",
    detect_pii=True,
    detect_injection=True,
    max_iterations=10,
    human_approval_required=True,
)

researcher = Agent(
    role="Research Analyst",
    goal="Research topics thoroughly with cited sources",
    backstory="You are a careful researcher who always cites sources.",
    max_iter=5,
    verbose=True,
)

task = Task(
    description="Research {topic} and provide a summary with sources",
    expected_output="Structured research summary",
    agent=researcher,
    output_pydantic=ResearchOutput,
    human_input=True,
)

crew = Crew(
    agents=[researcher],
    tasks=[task],
    process=Process.sequential,
    max_rpm=10,
)

logger.info("Starting research crew")
result = crew.kickoff(inputs={"topic": "EU AI Act compliance requirements"})
logger.info(f"Research complete: confidence={result.pydantic.confidence}")''',
        "framework": "CrewAI",
        "notes": "FULLY COMPLIANT CrewAI: Article 9 pass (max_iter limits). Article 10 pass (Pydantic output validation). Article 11 pass (docstrings, type annotations). Article 12 pass (structured logging + trust hook audit). Article 14 pass (human_input=True). Article 15 pass (PII detection, injection defense, rate limiting).",
    },
    # 33. Chatbot with no safety rails
    {
        "code": '''from anthropic import Anthropic

client = Anthropic()
conversation_history = []

def chat(user_message: str) -> str:
    conversation_history.append({"role": "user", "content": user_message})
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8096,
        messages=conversation_history,
    )
    assistant_msg = response.content[0].text
    conversation_history.append({"role": "assistant", "content": assistant_msg})
    return assistant_msg

# Run forever
while True:
    user_input = input("You: ")
    print(f"Bot: {chat(user_input)}")''',
        "framework": "Anthropic SDK",
        "notes": "Unbounded chatbot — Article 14: no conversation limits (runs forever, unbounded history). Article 12: no logging. Article 15: no input filtering or output validation. Article 9: no risk management for growing context.",
    },
    # 34. Compliant OpenAI agent with full stack
    {
        "code": '''import logging
import json
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ToolCall(BaseModel):
    tool_name: str
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    requires_approval: bool
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

RISK_MAP = {
    "search": "LOW",
    "read_file": "MEDIUM",
    "send_email": "HIGH",
    "delete_data": "CRITICAL",
}

client = OpenAI()

def safe_agent(prompt: str, max_turns: int = 5) -> str:
    """Agent with full compliance controls."""
    messages = [{"role": "user", "content": prompt}]
    audit_log = []

    for turn in range(max_turns):
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            max_tokens=1000,
        )

        content = response.choices[0].message.content
        logger.info(f"Turn {turn+1}/{max_turns}: {content[:100]}...")
        audit_log.append({"turn": turn, "response": content, "timestamp": datetime.now().isoformat()})

        if "TOOL:" not in content:
            break

        tool_name = content.split("TOOL:")[1].strip().split()[0]
        risk = RISK_MAP.get(tool_name, "HIGH")
        call = ToolCall(tool_name=tool_name, risk_level=risk, requires_approval=risk in ("HIGH", "CRITICAL"))
        audit_log.append(call.model_dump())

        if call.requires_approval:
            logger.warning(f"Tool {tool_name} requires human approval (risk: {risk})")
            approval = input(f"Approve {tool_name}? (y/n): ")
            if approval != "y":
                break

    # Save audit log
    with open(f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
        json.dump(audit_log, f, indent=2, default=str)

    return content

result = safe_agent("Search for recent AI governance papers")''',
        "framework": "OpenAI SDK",
        "notes": "FULLY COMPLIANT OpenAI agent: Article 9 pass (risk map, risk classification per tool). Article 10 pass (Pydantic validation). Article 11 pass (docstrings, type hints). Article 12 pass (structured audit log). Article 14 pass (human approval for high-risk tools, max_turns limit). Article 15 pass (bounded iterations, risk-gated execution).",
    },
]


def generate_edges(output_path):
    """Generate edge case training examples."""
    print(f"Phase 3: Generating edge cases → {output_path}")

    examples = []

    for template in EDGE_CASE_TEMPLATES:
        code = template["code"]
        framework = template["framework"]

        # Full analysis
        output = generate_full_analysis(code, "edge_case.py", framework)
        examples.append({
            "instruction": random.choice(FULL_ANALYSIS_INSTRUCTIONS),
            "input": code,
            "output": output,
        })

        # Single-article findings for each article
        for article in ARTICLE_CHECKS:
            finding = generate_single_article_finding(code, "edge_case.py", framework, article)
            instruction = random.choice(SINGLE_ARTICLE_INSTRUCTIONS[article])
            examples.append({
                "instruction": instruction,
                "input": code,
                "output": finding,
            })

    with open(output_path, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")

    print(f"Phase 3 complete: {len(examples)} edge case examples → {output_path}")
    return examples


# ═══════════════════════════════════════
# Phase 4: Instruction Diversity
# ═══════════════════════════════════════

DIVERSE_INSTRUCTIONS = [
    # Audit-style questions
    "Perform a compliance audit of this Python code against EU AI Act Articles 9-15.",
    "Run a full EU AI Act compliance check on this code.",
    "Audit this AI system code for EU AI Act compliance gaps.",
    "What EU AI Act violations exist in this code?",
    "Is this code compliant with the EU AI Act? Explain why or why not.",
    "Grade this AI code on EU AI Act compliance from A to F with justification.",
    "If this code were deployed in the EU, what compliance issues would arise?",
    "Act as an AI compliance auditor. Review this code against Articles 9, 10, 11, 12, 14, and 15.",
    # Specific role prompts
    "You are a regulatory compliance officer reviewing AI code for EU AI Act readiness. Analyze this code.",
    "As a CTO preparing for EU AI Act enforcement in August 2026, evaluate this code.",
    "You are a security engineer. What EU AI Act compliance gaps exist in this AI code?",
    "Review this code as if preparing it for an EU AI Act conformity assessment.",
    # Recommendation-focused
    "What changes would make this code EU AI Act compliant?",
    "How would you fix this code to meet EU AI Act requirements?",
    "Provide a remediation plan for making this code EU AI Act compliant.",
    "What is missing from this code to satisfy Articles 9, 10, 11, 12, 14, and 15 of the EU AI Act?",
    "List the top 5 compliance improvements needed for this AI code.",
    # Risk-focused
    "What are the regulatory risks if this AI code is deployed in the EU?",
    "Classify the risk level of this AI system under the EU AI Act.",
    "What is the risk classification of this code under the EU AI Act risk framework?",
    "Identify high-risk compliance gaps in this AI code.",
    # Framework-specific
    "Check this LangChain code for EU AI Act compliance.",
    "Evaluate this CrewAI agent for EU AI Act compliance.",
    "Is this OpenAI SDK code compliant with the EU AI Act?",
    "Review this AutoGen multi-agent system for EU AI Act compliance.",
    "Assess this Haystack pipeline against EU AI Act requirements.",
    "Check this LlamaIndex agent for EU AI Act compliance gaps.",
    # Comparison/scoring
    "Score this code's EU AI Act compliance on a scale of 0-100.",
    "Rate this AI code's compliance maturity: None, Basic, Intermediate, Advanced, or Full.",
    "Compare this code against EU AI Act best practices.",
    "How does this code measure up against ISO 42001 and EU AI Act standards?",
    # Quick check
    "Quick compliance check: is this code safe to deploy in the EU?",
    "Red flags in this AI code for EU AI Act compliance?",
    "EU AI Act compliance summary for this code — pass or fail?",
    "Thumbs up or thumbs down on this code's EU AI Act compliance? Explain.",
]


def generate_instruction_diversity(input_path, output_path):
    """Take existing examples and regenerate with diverse instruction phrasings."""
    print(f"Phase 4: Generating instruction diversity from {input_path} → {output_path}")

    with open(input_path) as f:
        originals = [json.loads(line) for line in f]

    new_examples = []
    seen_hashes = set()

    for orig in originals:
        code = orig.get("input", "")
        if not code or len(code) < 100:
            continue

        # Generate 2 new instruction variants per example
        for _ in range(2):
            new_instruction = random.choice(DIVERSE_INSTRUCTIONS)

            # Skip if same instruction
            if new_instruction == orig.get("instruction", ""):
                continue

            framework = detect_framework(code) or "Unknown"
            output = generate_full_analysis(code, "diversity.py", framework)

            example = {
                "instruction": new_instruction,
                "input": code,
                "output": output,
            }

            h = hashlib.md5(json.dumps(example, sort_keys=True).encode()).hexdigest()
            if h not in seen_hashes:
                seen_hashes.add(h)
                new_examples.append(example)

    with open(output_path, "w") as f:
        for ex in new_examples:
            f.write(json.dumps(ex) + "\n")

    print(f"Phase 4 complete: {len(new_examples)} instruction-diverse examples → {output_path}")
    return new_examples


# ═══════════════════════════════════════
# Combine all phases
# ═══════════════════════════════════════

def combine(output_path):
    """Combine all phases + original into final dataset."""
    print(f"\nCombining all data → {output_path}")

    files = [
        "training_data_combined_v3.jsonl",  # Original 4,159
        "phase1_github.jsonl",              # 397 mined
        "phase1_augmented.jsonl",           # 612 augmented mined
        "phase2_augmented_v2.jsonl",        # 8,675 augmented v3
        "phase3_edges_v2.jsonl",            # 238 edge cases
        "phase3_edges_augmented.jsonl",     # 307 augmented edges
        "phase4_instruction_diversity.jsonl",  # instruction variants
    ]

    all_examples = []
    seen_hashes = set()

    for fpath in files:
        if not os.path.exists(fpath):
            print(f"  Skipping {fpath} (not found)")
            continue
        count = 0
        with open(fpath) as f:
            for line in f:
                h = hashlib.md5(line.encode()).hexdigest()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    all_examples.append(line.strip())
                    count += 1
        print(f"  {fpath}: {count} unique examples")

    # Shuffle
    random.shuffle(all_examples)

    with open(output_path, "w") as f:
        for line in all_examples:
            f.write(line + "\n")

    print(f"\nFinal dataset: {len(all_examples)} examples → {output_path}")


# ═══════════════════════════════════════
# CLI
# ═══════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="AIR Blackbox Training Data Generator")
    sub = parser.add_subparsers(dest="command")

    p1 = sub.add_parser("mine", help="Phase 1: Mine GitHub repos")
    p1.add_argument("--output", default="phase1_github.jsonl")
    p1.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"))

    p2 = sub.add_parser("augment", help="Phase 2: Augment existing data")
    p2.add_argument("--input", default="training_data_combined_v3.jsonl")
    p2.add_argument("--output", default="phase2_augmented.jsonl")
    p2.add_argument("--multiplier", type=int, default=2)

    p3 = sub.add_parser("edges", help="Phase 3: Generate edge cases")
    p3.add_argument("--output", default="phase3_edges.jsonl")

    p4 = sub.add_parser("diversity", help="Phase 4: Instruction diversity")
    p4.add_argument("--input", default="training_data_combined_v3.jsonl")
    p4.add_argument("--output", default="phase4_instruction_diversity.jsonl")

    pc = sub.add_parser("combine", help="Combine all into final dataset")
    pc.add_argument("--output", default="training_data_v4.jsonl")

    pa = sub.add_parser("all", help="Run all phases")
    pa.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"))

    args = parser.parse_args()

    if args.command == "mine":
        mine_repos(args.output, args.token)
    elif args.command == "augment":
        augment_data(args.input, args.output, args.multiplier)
    elif args.command == "edges":
        generate_edges(args.output)
    elif args.command == "diversity":
        generate_instruction_diversity(args.input, args.output)
    elif args.command == "combine":
        combine(args.output)
    elif args.command == "all":
        mine_repos("phase1_github.jsonl", args.token)
        augment_data("training_data_combined_v3.jsonl", "phase2_augmented.jsonl")
        generate_edges("phase3_edges.jsonl")
        combine("training_data_v4.jsonl")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
