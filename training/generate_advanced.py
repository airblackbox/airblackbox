#!/usr/bin/env python3
"""
AIR Blackbox - Advanced Training Data Generator (v7 expansion)
==============================================================
Generates high-value training examples that competitors DON'T have:
  Phase 6: Before/after remediation pairs
  Phase 7: EU AI Act Annex III high-risk industry scenarios
  Phase 8: JavaScript/TypeScript agent examples
  Phase 9: Article text Q&A (regulation knowledge)
  Phase 10: Cloud deployment anti-patterns

No GPU required. Runs on any machine.
"""

import json
import random
import hashlib

# ═══════════════════════════════════════
# Phase 6: Before/After Remediation Pairs
# ═══════════════════════════════════════

REMEDIATION_PAIRS = [
    {
        "before": '''from openai import OpenAI

client = OpenAI()
result = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": user_input}],
)
print(result.choices[0].message.content)''',
        "after": '''import logging
from openai import OpenAI
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ValidatedInput(BaseModel):
    """Validated user input."""
    content: str = Field(..., max_length=2000, description="User query")

class ValidatedOutput(BaseModel):
    """Validated model output."""
    response: str
    model_used: str
    token_count: int

client = OpenAI()

def safe_completion(user_input: str) -> ValidatedOutput:
    """Generate completion with full compliance controls."""
    validated = ValidatedInput(content=user_input)
    logger.info(f"Processing request: {validated.content[:50]}...")

    result = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": validated.content}],
        max_tokens=1000,
    )

    output = ValidatedOutput(
        response=result.choices[0].message.content,
        model_used=result.model,
        token_count=result.usage.total_tokens,
    )
    logger.info(f"Response generated: {output.token_count} tokens")
    return output

result = safe_completion(user_input)''',
        "fixes": "Added: input validation (Article 10), logging (Article 12), type annotations and docstrings (Article 11), output validation (Article 15), token limits (Article 14).",
    },
    {
        "before": '''from langchain.agents import create_sql_agent
from langchain_openai import ChatOpenAI
from langchain.sql_database import SQLDatabase

db = SQLDatabase.from_uri("postgresql://admin:password@prod-db:5432/customers")
llm = ChatOpenAI(model="gpt-4", temperature=0)
agent = create_sql_agent(llm=llm, db=db, verbose=True)
result = agent.invoke({"input": user_query})
print(result)''',
        "after": '''import logging
import os
from langchain.agents import create_sql_agent
from langchain_openai import ChatOpenAI
from langchain.sql_database import SQLDatabase
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SQLAgentConfig(BaseModel):
    """Configuration for SQL agent with safety controls."""
    db_url: str = Field(description="Database connection string from env")
    max_iterations: int = Field(default=5, le=10)
    allowed_tables: list[str] = Field(default_factory=list)

config = SQLAgentConfig(
    db_url=os.environ["DATABASE_URL"],  # No hardcoded credentials
    max_iterations=5,
    allowed_tables=["products", "orders"],  # No PII tables
)

db = SQLDatabase.from_uri(
    config.db_url,
    include_tables=config.allowed_tables,  # Restrict table access
)
llm = ChatOpenAI(model="gpt-4", temperature=0, max_tokens=500)

agent = create_sql_agent(
    llm=llm, db=db, verbose=True,
    max_iterations=config.max_iterations,
    handle_parsing_errors=True,
)

logger.info(f"SQL agent query: {user_query[:100]}")
result = agent.invoke({"input": user_query})
logger.info(f"SQL agent result: {str(result)[:200]}")''',
        "fixes": "Added: credentials from env vars (Article 15), table access restrictions (Article 10), iteration limits (Article 14), structured config (Article 11), logging (Article 12), error handling (Article 9).",
    },
    {
        "before": '''from crewai import Agent, Task, Crew

researcher = Agent(role="Researcher", goal="Find data", allow_delegation=True)
writer = Agent(role="Writer", goal="Write report", allow_delegation=True)
crew = Crew(agents=[researcher, writer], tasks=[
    Task(description="Research {topic}", agent=researcher),
    Task(description="Write report", agent=writer),
])
result = crew.kickoff(inputs={"topic": user_topic})''',
        "after": '''import logging
from crewai import Agent, Task, Crew, Process
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

class ResearchOutput(BaseModel):
    """Validated research output with provenance."""
    summary: str = Field(..., max_length=5000)
    sources: list[str] = Field(..., max_length=20)
    confidence: float = Field(..., ge=0.0, le=1.0)

researcher = Agent(
    role="Research Analyst",
    goal="Research topics with cited sources",
    allow_delegation=False,  # Explicit delegation control
    max_iter=5,
    verbose=True,
)

writer = Agent(
    role="Technical Writer",
    goal="Write accurate reports from research",
    allow_delegation=False,
    max_iter=5,
    verbose=True,
)

research_task = Task(
    description="Research {topic} and cite all sources",
    expected_output="Research summary with sources",
    agent=researcher,
    human_input=True,  # Human review gate
)

write_task = Task(
    description="Write a report based on the research",
    expected_output="Structured report",
    agent=writer,
    output_pydantic=ResearchOutput,
    context=[research_task],
)

crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, write_task],
    process=Process.sequential,
    max_rpm=10,  # Rate limiting
)

logger.info(f"Starting crew for topic: {user_topic}")
result = crew.kickoff(inputs={"topic": user_topic})
logger.info(f"Crew complete. Confidence: {result.pydantic.confidence}")''',
        "fixes": "Added: delegation disabled (Article 14), human_input gate (Article 14), max_iter limits (Article 9), output validation with Pydantic (Article 10/15), logging (Article 12), rate limiting (Article 14), type annotations and docstrings (Article 11).",
    },
    {
        "before": '''from anthropic import Anthropic

client = Anthropic()
tools = [
    {"name": "read_file", "description": "Read a file"},
    {"name": "write_file", "description": "Write a file"},
    {"name": "run_bash", "description": "Run a bash command"},
    {"name": "send_email", "description": "Send an email"},
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
        "after": '''import logging
import json
from anthropic import Anthropic
from datetime import datetime
from typing import Literal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOOL_RISK_LEVELS = {
    "read_file": "LOW",
    "web_search": "LOW",
    "write_file": "MEDIUM",
    "send_email": "HIGH",
    "run_bash": "CRITICAL",
}

ALLOWED_TOOLS = ["read_file", "web_search", "write_file"]  # Restricted tool set
REQUIRE_APPROVAL = {"send_email", "run_bash"}

client = Anthropic()
audit_log = []

tools = [
    {"name": "read_file", "description": "Read a file from the allowed directory",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "web_search", "description": "Search the web for information",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
]

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=2048,
    tools=tools,
    messages=[{"role": "user", "content": user_request}],
)

for block in response.content:
    if block.type == "tool_use":
        risk = TOOL_RISK_LEVELS.get(block.name, "HIGH")
        logger.info(f"Tool call: {block.name} (risk: {risk})")
        audit_log.append({"tool": block.name, "risk": risk, "input": block.input, "timestamp": datetime.now().isoformat()})

        if block.name not in ALLOWED_TOOLS:
            logger.warning(f"Blocked disallowed tool: {block.name}")
            continue

        if block.name in REQUIRE_APPROVAL:
            approval = input(f"Approve {block.name}? (y/n): ")
            if approval != "y":
                logger.info(f"Tool {block.name} rejected by human")
                continue

        result = execute_tool(block.name, block.input)
        audit_log.append({"tool": block.name, "result": str(result)[:500], "timestamp": datetime.now().isoformat()})

with open(f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
    json.dump(audit_log, f, indent=2)''',
        "fixes": "Added: tool risk classification (Article 9), restricted tool set (Article 14), human approval for high-risk tools (Article 14), audit logging with timestamps (Article 12), token limits (Article 15), tool input schemas (Article 11).",
    },
    {
        "before": '''from langchain_openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

loader = DirectoryLoader("./documents/", glob="**/*.txt", loader_cls=TextLoader)
documents = loader.load()
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = splitter.split_documents(documents)
embeddings = OpenAIEmbeddings()
vectorstore = FAISS.from_documents(chunks, embeddings)
vectorstore.save_local("./faiss_index")''',
        "after": '''import logging
import json
from datetime import datetime
from langchain_openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IndexingMetadata(BaseModel):
    """Metadata for document indexing operations."""
    source_directory: str
    document_count: int
    chunk_count: int
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    embedding_model: str = "text-embedding-ada-002"

loader = DirectoryLoader("./documents/", glob="**/*.txt", loader_cls=TextLoader)
documents = loader.load()

# Track document provenance
for doc in documents:
    doc.metadata["indexed_at"] = datetime.now().isoformat()
    doc.metadata["source_type"] = "internal_document"
    logger.info(f"Loaded: {doc.metadata.get('source', 'unknown')}")

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = splitter.split_documents(documents)

embeddings = OpenAIEmbeddings()
vectorstore = FAISS.from_documents(chunks, embeddings)
vectorstore.save_local("./faiss_index")

# Save indexing audit trail
metadata = IndexingMetadata(
    source_directory="./documents/",
    document_count=len(documents),
    chunk_count=len(chunks),
)
with open("./faiss_index/indexing_metadata.json", "w") as f:
    json.dump(metadata.model_dump(), f, indent=2)

logger.info(f"Indexed {metadata.chunk_count} chunks from {metadata.document_count} documents")''',
        "fixes": "Added: document provenance tracking (Article 10), indexing metadata (Article 11), audit trail (Article 12), structured logging (Article 12), Pydantic validation (Article 10), source type classification (Article 9).",
    },
    {
        "before": '''from autogen import ConversableAgent, GroupChat, GroupChatManager

config = [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]

planner = ConversableAgent("planner", llm_config={"config_list": config})
coder = ConversableAgent("coder", llm_config={"config_list": config})
executor = ConversableAgent("executor", llm_config={"config_list": config},
    code_execution_config={"work_dir": "coding", "use_docker": False})

groupchat = GroupChat(agents=[planner, coder, executor], messages=[], max_round=20)
manager = GroupChatManager(groupchat=groupchat, llm_config={"config_list": config})
planner.initiate_chat(manager, message="Build a data pipeline")''',
        "after": '''import logging
import os
from autogen import ConversableAgent, GroupChat, GroupChatManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

config = [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]

planner = ConversableAgent(
    "planner",
    llm_config={"config_list": config},
    system_message="You plan tasks. Always explain your reasoning.",
    max_consecutive_auto_reply=3,  # Bounded replies
)

coder = ConversableAgent(
    "coder",
    llm_config={"config_list": config},
    system_message="You write Python code. Include type hints and docstrings.",
    max_consecutive_auto_reply=3,
)

executor = ConversableAgent(
    "executor",
    llm_config={"config_list": config},
    code_execution_config={
        "work_dir": "coding",
        "use_docker": True,  # Sandboxed execution
        "timeout": 30,
    },
    system_message="Execute code in sandbox only.",
    max_consecutive_auto_reply=2,
    human_input_mode="ALWAYS",  # Human oversight
)

groupchat = GroupChat(
    agents=[planner, coder, executor],
    messages=[],
    max_round=8,  # Bounded rounds
)
manager = GroupChatManager(groupchat=groupchat, llm_config={"config_list": config})

logger.info("Starting multi-agent chat with human oversight")
planner.initiate_chat(manager, message="Build a data pipeline")
logger.info("Multi-agent chat complete")''',
        "fixes": "Added: Docker sandboxing (Article 15), human_input_mode ALWAYS (Article 14), bounded rounds and replies (Article 9/14), structured logging (Article 12), system messages with documentation (Article 11), execution timeout (Article 15).",
    },
]

def generate_remediation_examples():
    """Generate before/after remediation training pairs."""
    examples = []

    remediation_instructions = [
        "Show how to fix this code for EU AI Act compliance. Provide the compliant version and explain what changed.",
        "Remediate this AI code for EU AI Act compliance. Show before and after with explanations.",
        "What specific changes are needed to make this code EU AI Act compliant? Provide the fixed code.",
        "Transform this non-compliant AI code into a compliant version. Explain each fix.",
        "Act as an AI compliance engineer. Fix this code to meet Articles 9, 10, 11, 12, 14, and 15.",
        "Provide a pull request that fixes all EU AI Act compliance issues in this code.",
        "Code review: fix all EU AI Act violations and explain the remediation.",
    ]

    for pair in REMEDIATION_PAIRS:
        # Before → After with explanation
        for _ in range(3):
            instruction = random.choice(remediation_instructions)
            output = f"## Remediated Code\n\n```python\n{pair['after']}\n```\n\n## Changes Made\n\n{pair['fixes']}"
            examples.append({
                "instruction": instruction,
                "input": pair["before"],
                "output": output,
            })

        # "What's wrong" analysis of the before code
        analysis_instructions = [
            "Analyze this code for EU AI Act compliance gaps.",
            "What EU AI Act violations exist in this code?",
            "Audit this AI code for regulatory compliance issues.",
        ]
        for _ in range(2):
            instruction = random.choice(analysis_instructions)
            examples.append({
                "instruction": instruction,
                "input": pair["before"],
                "output": f"## Compliance Issues\n\nThis code has multiple EU AI Act violations:\n\n{pair['fixes'].replace('Added: ', 'Missing: ')}\n\nAll of these must be addressed before deployment in the EU.",
            })

        # "Is this compliant" on the after code (positive example)
        compliant_instructions = [
            "Is this code EU AI Act compliant?",
            "Audit this AI code for EU AI Act compliance.",
            "Score this code's EU AI Act compliance.",
        ]
        for _ in range(2):
            instruction = random.choice(compliant_instructions)
            examples.append({
                "instruction": instruction,
                "input": pair["after"],
                "output": f"## Compliance Assessment: PASS\n\nThis code demonstrates strong EU AI Act compliance:\n\n{pair['fixes']}\n\nThe implementation covers all six key articles (9, 10, 11, 12, 14, 15) with appropriate controls.",
            })

    return examples


# ═══════════════════════════════════════
# Phase 7: EU AI Act Annex III High-Risk Scenarios
# ═══════════════════════════════════════

ANNEX_III_SCENARIOS = [
    # 1. Biometric identification
    {
        "code": '''from openai import OpenAI
import base64

client = OpenAI()

def identify_person(image_path: str) -> dict:
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode()

    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": "Identify this person. Return their likely name, age, ethnicity, and emotional state."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}},
            ],
        }],
    )
    return {"identification": response.choices[0].message.content}

result = identify_person("security_camera_feed.jpg")''',
        "category": "Biometric identification (Annex III, 1a)",
        "risk_level": "UNACCEPTABLE/HIGH",
        "notes": "Real-time biometric identification in public spaces is PROHIBITED under Article 5. Even non-real-time biometric categorization is HIGH RISK under Annex III. This code attempts facial identification, emotion recognition, and ethnic categorization - all regulated.",
    },
    # 2. Critical infrastructure management
    {
        "code": '''from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI
from langchain.tools import tool

@tool
def control_valve(valve_id: str, position: float) -> str:
    """Control a water treatment plant valve. Position 0.0-1.0."""
    import requests
    requests.post(f"http://scada-server/valve/{valve_id}", json={"position": position})
    return f"Valve {valve_id} set to {position}"

@tool
def read_sensor(sensor_id: str) -> str:
    """Read water quality sensor data."""
    import requests
    resp = requests.get(f"http://scada-server/sensor/{sensor_id}")
    return resp.json()

llm = ChatOpenAI(model="gpt-4", temperature=0)
agent = create_openai_tools_agent(llm, [control_valve, read_sensor])
executor = AgentExecutor(agent=agent, tools=[control_valve, read_sensor])
result = executor.invoke({"input": "Optimize water treatment process for maximum efficiency"})''',
        "category": "Critical infrastructure (Annex III, 2a)",
        "risk_level": "HIGH",
        "notes": "AI controlling critical infrastructure (water treatment) is HIGH RISK under Annex III. CRITICAL failures: no human oversight for valve control, no safety bounds on valve positions, no risk assessment, no audit trail, direct SCADA access without authentication.",
    },
    # 3. Educational scoring
    {
        "code": '''from openai import OpenAI
import json

client = OpenAI()

def grade_essay(student_id: str, essay: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Grade this essay A-F. Be strict."},
            {"role": "user", "content": essay},
        ],
        temperature=0,
    )
    grade = response.choices[0].message.content
    return {"student_id": student_id, "grade": grade}

# Grade all students
with open("student_essays.json") as f:
    essays = json.load(f)

grades = [grade_essay(e["id"], e["essay"]) for e in essays]
with open("final_grades.json", "w") as f:
    json.dump(grades, f)''',
        "category": "Education and vocational training (Annex III, 3a)",
        "risk_level": "HIGH",
        "notes": "AI grading students is HIGH RISK under Annex III. Failures: no human teacher review (Article 14), no grading rubric documentation (Article 11), no bias testing (Article 10), no appeal mechanism, bulk automated grading without oversight, student PII without governance.",
    },
    # 4. Employment/recruitment
    {
        "code": '''from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4")

screener = Agent(
    role="Resume Screener",
    goal="Filter candidates for the senior engineer role. Prefer candidates from top-tier universities.",
    llm=llm,
)

interviewer = Agent(
    role="Technical Interviewer",
    goal="Assess technical skills and cultural fit",
    llm=llm,
)

screen_task = Task(
    description="Screen these 200 resumes and shortlist top 10: {resumes}",
    agent=screener,
    expected_output="Top 10 candidate names and rankings",
)

interview_task = Task(
    description="Generate interview questions for shortlisted candidates",
    agent=interviewer,
    expected_output="Custom interview questions per candidate",
)

crew = Crew(agents=[screener, interviewer], tasks=[screen_task, interview_task])
result = crew.kickoff(inputs={"resumes": all_resumes})''',
        "category": "Employment, workers management (Annex III, 4a)",
        "risk_level": "HIGH",
        "notes": "AI recruitment is HIGH RISK under Annex III. CRITICAL: explicit bias in prompt ('top-tier universities' = proxy discrimination). No human review of screening decisions. No bias audit. No transparency to candidates about AI use. Bulk PII processing without governance.",
    },
    # 5. Credit scoring
    {
        "code": '''from openai import OpenAI
import json

client = OpenAI()

def assess_creditworthiness(application: dict) -> dict:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a credit analyst. Assess this loan application and provide a credit score 300-850 and approval recommendation."},
            {"role": "user", "content": json.dumps(application)},
        ],
        temperature=0,
    )
    return {"applicant": application["name"], "ai_assessment": response.choices[0].message.content}

applications = json.load(open("loan_applications.json"))
decisions = [assess_creditworthiness(app) for app in applications]
json.dump(decisions, open("credit_decisions.json", "w"))''',
        "category": "Access to essential private/public services (Annex III, 5a)",
        "risk_level": "HIGH",
        "notes": "AI credit scoring is HIGH RISK under Annex III. Automated financial access decisions with no human review, no explainability, no bias testing, no appeal mechanism. Bulk processing of financial PII. EU AI Act Article 86 requires right to explanation for AI decisions.",
    },
    # 6. Law enforcement
    {
        "code": '''from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI
from langchain.tools import tool

@tool
def query_criminal_database(name: str) -> str:
    """Query criminal records database."""
    import requests
    resp = requests.get(f"https://crime-db.gov/api/search?name={name}")
    return resp.json()

@tool
def predict_recidivism(profile: str) -> str:
    """Predict likelihood of reoffending."""
    llm = ChatOpenAI(model="gpt-4", temperature=0)
    return llm.invoke(f"Based on this profile, predict recidivism risk 0-100%: {profile}").content

llm = ChatOpenAI(model="gpt-4")
tools = [query_criminal_database, predict_recidivism]
agent = create_openai_tools_agent(llm, tools)
executor = AgentExecutor(agent=agent, tools=tools)
result = executor.invoke({"input": f"Assess risk for parole candidate: {inmate_profile}"})''',
        "category": "Law enforcement (Annex III, 6a)",
        "risk_level": "HIGH",
        "notes": "AI recidivism prediction is HIGH RISK under Annex III. CRITICAL: automated risk assessment for justice decisions, potential for racial bias, no human oversight, no explainability, no right to contest. Individual risk assessment by AI in criminal justice is specifically called out in Annex III 6(a).",
    },
    # 7. Immigration/asylum
    {
        "code": '''from openai import OpenAI

client = OpenAI()

def assess_asylum_claim(claim_text: str, country_of_origin: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Assess this asylum claim. Determine credibility and recommend APPROVE or DENY."},
            {"role": "user", "content": f"Country: {country_of_origin}\nClaim: {claim_text}"},
        ],
        temperature=0,
    )
    return {"decision": response.choices[0].message.content}

claims = load_pending_claims()
for claim in claims:
    result = assess_asylum_claim(claim["text"], claim["country"])
    update_case_status(claim["id"], result["decision"])''',
        "category": "Migration, asylum and border control (Annex III, 7a)",
        "risk_level": "HIGH",
        "notes": "AI asylum assessment is HIGH RISK under Annex III. Automated decisions on fundamental rights (asylum) with no human review, potential country-of-origin bias, no explainability, no right to appeal. Article 14 violation: life-altering decisions without human oversight.",
    },
    # 8. Insurance pricing
    {
        "code": '''from litellm import completion
import json

def calculate_premium(customer_data: dict) -> dict:
    response = completion(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Calculate health insurance premium based on the customer profile. Consider age, BMI, pre-existing conditions, location, and lifestyle."},
            {"role": "user", "content": json.dumps(customer_data)},
        ],
    )
    return {"customer_id": customer_data["id"], "premium": response.choices[0].message.content}

customers = json.load(open("customer_profiles.json"))
premiums = [calculate_premium(c) for c in customers]
json.dump(premiums, open("insurance_premiums.json", "w"))''',
        "category": "Access to essential services - insurance (Annex III, 5b)",
        "risk_level": "HIGH",
        "notes": "AI insurance pricing is HIGH RISK under Annex III. Automated pricing of essential services using health data (special category under GDPR). No bias audit, no transparency to customers, no human review, bulk health data processing without governance.",
    },
    # 9. Content moderation for social media
    {
        "code": '''from openai import OpenAI
import json

client = OpenAI()

def moderate_content(post: dict) -> dict:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Moderate this social media post. Decide: ALLOW, REMOVE, or RESTRICT. Be aggressive about removing potentially harmful content."},
            {"role": "user", "content": post["content"]},
        ],
        temperature=0,
    )
    decision = response.choices[0].message.content
    if "REMOVE" in decision:
        delete_post(post["id"])
        ban_user(post["user_id"], duration="30d")
    return {"post_id": post["id"], "decision": decision}

posts = get_flagged_posts()
for post in posts:
    moderate_content(post)''',
        "category": "Recommender systems of very large online platforms (Article 6, 2b)",
        "risk_level": "HIGH",
        "notes": "AI content moderation with automated banning is HIGH RISK for large platforms. Automated speech restriction with no human review, no appeal mechanism, aggressive removal bias, automated user bans without due process. Article 14: no human oversight for account actions.",
    },
    # 10. Emotion recognition in workplace
    {
        "code": '''from openai import OpenAI
import base64

client = OpenAI()

def analyze_employee_emotion(video_frame: bytes) -> dict:
    image_data = base64.b64encode(video_frame).decode()
    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": "Analyze this employee's emotional state, engagement level, and stress indicators. Rate productivity likelihood 1-10."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}},
            ],
        }],
    )
    return {"analysis": response.choices[0].message.content}

# Monitor all employees every 5 minutes
import time
while True:
    for camera_id in office_cameras:
        frame = capture_frame(camera_id)
        analysis = analyze_employee_emotion(frame)
        store_employee_metrics(camera_id, analysis)
    time.sleep(300)''',
        "category": "Emotion recognition in workplace (Article 5, 1f)",
        "risk_level": "UNACCEPTABLE",
        "notes": "PROHIBITED under Article 5(1)(f): emotion recognition in the workplace is BANNED. Continuous surveillance of employees, biometric categorization, emotional state inference, productivity scoring based on facial analysis. This system is explicitly prohibited by the EU AI Act.",
    },
]

def generate_annex_iii_examples():
    """Generate examples for EU AI Act Annex III high-risk categories."""
    examples = []

    instructions = [
        "Analyze this AI code for EU AI Act compliance, paying special attention to risk classification under Annex III.",
        "What risk category does this AI system fall under in the EU AI Act? Analyze for compliance.",
        "Classify this AI system under the EU AI Act risk framework and identify compliance gaps.",
        "Is this AI system HIGH RISK under the EU AI Act? Analyze against Annex III categories.",
        "Perform an EU AI Act conformity assessment of this AI code.",
        "What Annex III category does this code fall under? What compliance requirements apply?",
        "Audit this code against EU AI Act requirements for high-risk AI systems.",
    ]

    for scenario in ANNEX_III_SCENARIOS:
        # Full compliance analysis with risk classification
        for _ in range(4):
            instruction = random.choice(instructions)
            output = f"""## EU AI Act Risk Classification

**Category**: {scenario['category']}
**Risk Level**: {scenario['risk_level']}

## Compliance Analysis

{scenario['notes']}

## Required Actions

This AI system falls under **{scenario['risk_level']}** risk classification per the EU AI Act. {"This system is PROHIBITED under Article 5 and cannot be deployed in the EU." if scenario['risk_level'] == "UNACCEPTABLE" else "As a HIGH-RISK system under Annex III, it must comply with ALL requirements in Articles 9-15 before deployment, including conformity assessment, CE marking, and registration in the EU database."}

### Specific Requirements:
- Article 9: Establish and maintain a risk management system throughout the AI system lifecycle
- Article 10: Implement data governance including training data documentation, bias testing, and data quality measures
- Article 11: Draw up technical documentation demonstrating compliance before placing on market
- Article 12: Automatic recording of events (logs) throughout the AI system's lifecycle
- Article 14: Design for effective human oversight, including ability to override or interrupt
- Article 15: Achieve appropriate levels of accuracy, robustness, and cybersecurity"""
            examples.append({
                "instruction": instruction,
                "input": scenario["code"],
                "output": output,
            })

    return examples


# ═══════════════════════════════════════
# Phase 8: JavaScript/TypeScript Agent Examples
# ═══════════════════════════════════════

JS_AGENT_EXAMPLES = [
    # Vercel AI SDK
    {
        "code": '''import { openai } from "@ai-sdk/openai";
import { generateText, tool } from "ai";
import { z } from "zod";

const result = await generateText({
  model: openai("gpt-4"),
  tools: {
    getWeather: tool({
      description: "Get the weather for a location",
      parameters: z.object({ location: z.string() }),
      execute: async ({ location }) => {
        const resp = await fetch(`https://api.weather.com/${location}`);
        return resp.json();
      },
    }),
    sendEmail: tool({
      description: "Send an email",
      parameters: z.object({ to: z.string(), body: z.string() }),
      execute: async ({ to, body }) => {
        await emailService.send(to, body);
        return "sent";
      },
    }),
  },
  prompt: userInput,
  maxSteps: 10,
});''',
        "framework": "Vercel AI SDK",
        "lang": "typescript",
        "notes": "Vercel AI SDK agent - Article 14: sendEmail tool with no approval gate. Article 15: no input validation on userInput. Article 12: no logging. Article 9: no risk classification per tool.",
    },
    # LangChain.js
    {
        "code": '''import { ChatOpenAI } from "@langchain/openai";
import { AgentExecutor, createOpenAIToolsAgent } from "langchain/agents";
import { DynamicTool } from "@langchain/core/tools";

const llm = new ChatOpenAI({ model: "gpt-4" });

const sqlTool = new DynamicTool({
  name: "run_sql",
  description: "Run SQL query against production database",
  func: async (query) => {
    const result = await db.query(query);
    return JSON.stringify(result.rows);
  },
});

const agent = await createOpenAIToolsAgent({ llm, tools: [sqlTool] });
const executor = new AgentExecutor({ agent, tools: [sqlTool] });
const result = await executor.invoke({ input: userQuery });
console.log(result.output);''',
        "framework": "LangChain.js",
        "lang": "typescript",
        "notes": "LangChain.js SQL agent - CRITICAL: Article 15 fail (SQL injection risk). Article 14: no human oversight for database queries. Article 12: only console.log. Article 10: direct production DB access without governance.",
    },
    # Next.js AI chatbot
    {
        "code": '''import { OpenAI } from "openai";
import { NextRequest, NextResponse } from "next/server";

const openai = new OpenAI();

export async function POST(req: NextRequest) {
  const { messages } = await req.json();

  const response = await openai.chat.completions.create({
    model: "gpt-4",
    messages,
    stream: true,
  });

  const stream = new ReadableStream({
    async start(controller) {
      for await (const chunk of response) {
        const content = chunk.choices[0]?.delta?.content || "";
        controller.enqueue(new TextEncoder().encode(content));
      }
      controller.close();
    },
  });

  return new NextResponse(stream);
}''',
        "framework": "Next.js + OpenAI",
        "lang": "typescript",
        "notes": "Next.js streaming endpoint - Article 14: no rate limiting or auth. Article 15: no input validation on messages. Article 12: no request logging. Article 10: user messages forwarded without sanitization. Article 11: no API documentation.",
    },
    # Mastra agent framework
    {
        "code": '''import { Agent } from "@mastra/core";
import { openai } from "@ai-sdk/openai";
import { z } from "zod";

const agent = new Agent({
  name: "ResearchAgent",
  instructions: "You are a research assistant. Search the web and compile reports.",
  model: openai("gpt-4"),
  tools: {
    webSearch: {
      description: "Search the web",
      parameters: z.object({ query: z.string() }),
      execute: async ({ query }) => {
        const results = await serpApi.search(query);
        return results;
      },
    },
    saveReport: {
      description: "Save a research report to the database",
      parameters: z.object({ title: z.string(), content: z.string() }),
      execute: async ({ title, content }) => {
        await db.reports.create({ title, content, createdAt: new Date() });
        return "saved";
      },
    },
  },
});

const result = await agent.generate(userPrompt);''',
        "framework": "Mastra",
        "lang": "typescript",
        "notes": "Mastra agent - Article 15: no content validation on web search results saved to DB. Article 12: no logging of agent actions. Article 14: autonomous web research and DB writes with no oversight. Article 10: external data ingestion without governance.",
    },
    # Express.js AI endpoint
    {
        "code": '''const express = require("express");
const { Anthropic } = require("@anthropic-ai/sdk");

const app = express();
app.use(express.json());

const client = new Anthropic();

app.post("/analyze", async (req, res) => {
  const { document, analysisType } = req.body;

  const response = await client.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 4096,
    messages: [
      { role: "user", content: `Perform ${analysisType} analysis on: ${document}` },
    ],
  });

  res.json({ analysis: response.content[0].text });
});

app.listen(3000);''',
        "framework": "Anthropic SDK (Node.js)",
        "lang": "javascript",
        "notes": "Express AI endpoint - Article 14: no authentication or rate limiting. Article 15: no input validation (analysisType could be injection vector). Article 12: no request logging. Article 11: no API documentation. Article 10: arbitrary document analysis without governance.",
    },
    # Compliant Vercel AI SDK
    {
        "code": '''import { openai } from "@ai-sdk/openai";
import { generateText, tool } from "ai";
import { z } from "zod";
import { createLogger } from "./logger";
import { rateLimit } from "./middleware";

const logger = createLogger("ai-agent");

const InputSchema = z.object({
  query: z.string().max(2000),
  userId: z.string().uuid(),
});

const TOOL_RISK_LEVELS = {
  search: "LOW",
  calculate: "LOW",
  sendNotification: "HIGH",
};

export async function handleQuery(rawInput: unknown) {
  const input = InputSchema.parse(rawInput);
  logger.info({ userId: input.userId, query: input.query.slice(0, 100) }, "Processing query");

  const result = await generateText({
    model: openai("gpt-4"),
    tools: {
      search: tool({
        description: "Search internal knowledge base",
        parameters: z.object({ query: z.string().max(500) }),
        execute: async ({ query }) => {
          logger.info({ tool: "search", query }, "Tool call");
          return knowledgeBase.search(query);
        },
      }),
      calculate: tool({
        description: "Perform mathematical calculation",
        parameters: z.object({ expression: z.string().max(200) }),
        execute: async ({ expression }) => {
          logger.info({ tool: "calculate", expression }, "Tool call");
          return safeEval(expression);
        },
      }),
    },
    prompt: input.query,
    maxSteps: 5,
  });

  logger.info({ userId: input.userId, steps: result.steps.length }, "Query complete");
  return { response: result.text, auditId: generateAuditId() };
}''',
        "framework": "Vercel AI SDK",
        "lang": "typescript",
        "notes": "COMPLIANT Vercel AI SDK: Article 9 pass (risk levels defined). Article 10 pass (Zod input validation). Article 11 pass (TypeScript types, JSDoc). Article 12 pass (structured logging with audit). Article 14 pass (maxSteps limit, no high-risk tools). Article 15 pass (input bounds, safe eval).",
    },
]

def generate_js_examples():
    """Generate JavaScript/TypeScript agent training examples."""
    examples = []

    js_instructions = [
        "Analyze this JavaScript/TypeScript AI code for EU AI Act compliance.",
        "Check this TypeScript agent code for EU AI Act compliance gaps.",
        "Audit this Node.js AI application against EU AI Act Articles 9-15.",
        "What EU AI Act violations exist in this JavaScript AI code?",
        "Is this TypeScript AI agent compliant with the EU AI Act?",
        "Review this Vercel AI SDK code for EU AI Act compliance.",
        "Score this JavaScript AI code on EU AI Act compliance.",
        "What changes are needed to make this JS/TS AI code EU AI Act compliant?",
    ]

    for example in JS_AGENT_EXAMPLES:
        for _ in range(4):
            instruction = random.choice(js_instructions)
            lang = example.get("lang", "typescript")
            framework = example["framework"]

            output = f"""## EU AI Act Compliance Analysis

**Framework**: {framework}
**Language**: {lang}

### Findings

{example['notes']}

### Summary

This {framework} code {"demonstrates strong EU AI Act compliance across all articles." if "COMPLIANT" in example['notes'] else f"has compliance gaps that must be addressed before deployment in the EU. The EU AI Act applies regardless of programming language - TypeScript/JavaScript AI systems have the same compliance obligations as Python."}"""

            examples.append({
                "instruction": instruction,
                "input": example["code"],
                "output": output,
            })

    return examples


# ═══════════════════════════════════════
# Phase 9: Article Text Q&A
# ═══════════════════════════════════════

ARTICLE_QA = [
    # Article 9
    {"q": "What does Article 9 of the EU AI Act require?", "a": "Article 9 requires providers of high-risk AI systems to establish, implement, document, and maintain a risk management system throughout the entire lifecycle of the AI system. This includes: (a) identification and analysis of known and reasonably foreseeable risks, (b) estimation and evaluation of risks that may emerge during use, (c) evaluation of risks based on post-market monitoring data, and (d) adoption of appropriate risk management measures. The risk management system must be a continuous iterative process, updated regularly. Risk management measures must consider the state of the art, including technical standards, and must reduce risks as far as possible through adequate design and development."},
    {"q": "How do you implement Article 9 risk management in code?", "a": "In code, Article 9 risk management translates to: (1) Risk classification per tool or capability - assign LOW/MEDIUM/HIGH/CRITICAL to each tool the AI system can use, (2) Error handling and fallback mechanisms - try/except blocks, retry policies with backoff, circuit breakers, (3) Rate limiting and iteration bounds - max_iterations, max_tokens, timeout parameters, (4) Graceful degradation - fallback responses when the primary model fails, (5) Risk documentation - comments or config files documenting identified risks and mitigations. Example: defining a RISK_MAP dict mapping tool names to risk levels, setting max_iterations=5 on agents, implementing try/except with exponential backoff on LLM calls."},
    {"q": "What is the relationship between Article 9 and risk classification in the EU AI Act?", "a": "Article 9 operates within the EU AI Act's four-tier risk framework: Unacceptable (Article 5, banned), High-risk (Article 6 + Annex III, heavy regulation), Limited risk (transparency obligations), and Minimal risk (no obligations). Article 9 specifically applies to HIGH-RISK systems listed in Annex III. For these systems, risk management must be proportionate to the level of risk. The risk management system must consider risks to health, safety, and fundamental rights. It must also address risks arising from the AI system's intended purpose and reasonably foreseeable misuse."},
    # Article 10
    {"q": "What does Article 10 of the EU AI Act require for data governance?", "a": "Article 10 requires that high-risk AI systems use training, validation, and testing data that meets specific quality criteria. Key requirements include: (a) data governance and management practices covering design choices, data collection, data preparation (annotation, labeling, cleaning, enrichment), (b) examination for possible biases, (c) identification of data gaps or shortcomings, (d) formulation of relevant assumptions about the information the data measures, (e) appropriate statistical properties. Training data must be relevant, representative, free of errors, and complete. Special categories of personal data (Article 10(5)) may only be processed under strict conditions to ensure bias detection and correction."},
    {"q": "How does Article 10 data governance apply to AI agent code?", "a": "In AI agent code, Article 10 data governance translates to: (1) Input validation - using Pydantic BaseModel, TypedDict, or dataclass to validate all inputs, (2) PII handling - detecting and redacting personal data before processing (names, emails, SSNs, phone numbers), (3) Data provenance tracking - recording where each document or data source came from, when it was ingested, and its intended use, (4) Access controls - restricting which database tables, files, or APIs the agent can access, (5) Output validation - validating model outputs before storing or acting on them. Example: using Pydantic models with Field constraints, implementing PII detection before sending data to LLMs, maintaining metadata about document sources in vector stores."},
    # Article 11
    {"q": "What documentation does Article 11 of the EU AI Act require?", "a": "Article 11 requires technical documentation to be drawn up before a high-risk AI system is placed on the market. The documentation must contain: (a) general description of the AI system including intended purpose, (b) detailed description of elements and development process, (c) detailed information about monitoring, functioning, and control, (d) description of the risk management system, (e) description of data governance measures, (f) description of the human oversight measures, (g) information about accuracy, robustness, and cybersecurity, (h) a detailed description of the changes made through the system's lifecycle. The documentation must be kept up to date and be available to national competent authorities upon request."},
    {"q": "How do you implement Article 11 technical documentation in code?", "a": "In code, Article 11 technical documentation translates to: (1) Docstrings - comprehensive function and class docstrings explaining purpose, parameters, and return values, (2) Type annotations - using Python type hints (str, int, List[str], Optional[dict]) or TypeScript types for all function signatures, (3) Model cards - documenting model name, version, training data, intended use, limitations, and known biases, (4) API documentation - clear documentation of all endpoints, parameters, and expected responses, (5) Architecture documentation - README files, system diagrams, data flow documentation, (6) Version tracking - documenting changes between versions. Example: adding -> return type annotations, writing triple-quoted docstrings, maintaining a model_card.json with training metadata."},
    # Article 12
    {"q": "What does Article 12 of the EU AI Act require for record-keeping?", "a": "Article 12 requires high-risk AI systems to have automatic recording of events ('logs') throughout the system's lifetime. These logs must: (a) enable monitoring of the operation of the system, (b) facilitate post-market monitoring, (c) be traceable, (d) record the period of each use, the reference database, the input data, the identification of natural persons involved in verification of results. The logging capabilities must conform to recognised standards or common specifications. Logs must be kept for a period appropriate to the intended purpose, and at minimum 6 months unless otherwise provided by law."},
    {"q": "How do you implement Article 12 record-keeping in AI agent code?", "a": "In code, Article 12 record-keeping translates to: (1) Structured logging - using Python's logging module, structlog, or loguru with INFO/WARNING/ERROR levels, (2) Tracing - OpenTelemetry, LangSmith, LangFuse, or custom trace IDs for request correlation, (3) Audit trails - recording each decision, tool call, and output with timestamps, (4) Callback handlers - using framework-specific callbacks (LangChain callbacks, CrewAI hooks) to capture events, (5) Persistent storage - writing audit logs to files or databases, not just console output. Example: logging.basicConfig(level=logging.INFO), using getLogger(__name__), logging every LLM call, tool invocation, and decision point with timestamps and request IDs."},
    # Article 14
    {"q": "What does Article 14 of the EU AI Act require for human oversight?", "a": "Article 14 requires high-risk AI systems to be designed and developed so they can be effectively overseen by natural persons. Human oversight measures must: (a) be identified and built into the system by the provider, (b) enable the individuals to fully understand the capacities and limitations of the AI system, (c) enable the individuals to correctly interpret the system's output, (d) enable the individuals to decide not to use or to override, (e) enable the individuals to intervene or interrupt the system ('stop button'). The level of human oversight must be commensurate with the risks. For high-risk systems in Annex III point 1 (biometrics), at least two natural persons must verify results before action."},
    {"q": "How do you implement Article 14 human oversight in AI agent code?", "a": "In code, Article 14 human oversight translates to: (1) Human-in-the-loop - requiring human approval for high-risk actions (human_input=True in CrewAI, human_input_mode='ALWAYS' in AutoGen), (2) Iteration limits - max_iterations, max_steps, max_rounds parameters to prevent unbounded execution, (3) Rate limiting - max_rpm, max_tokens to control resource usage, (4) Action boundaries - allowed_tools lists, tool whitelists restricting what the agent can do, (5) Kill switches - ability to interrupt agent execution, (6) Approval gates - checking with a human before sending emails, deleting files, or executing code, (7) Budget controls - max_tokens, max_cost parameters. Example: AgentExecutor(max_iterations=5), Crew(max_rpm=10), if risk == 'HIGH': approval = input('Approve? (y/n)')."},
    # Article 15
    {"q": "What does Article 15 of the EU AI Act require for accuracy, robustness, and cybersecurity?", "a": "Article 15 requires high-risk AI systems to achieve appropriate levels of accuracy, robustness, and cybersecurity. Specifically: (a) Accuracy - the system must achieve declared performance levels, tested against defined benchmarks, (b) Robustness - the system must be resilient to errors, faults, or inconsistencies in inputs, including adversarial attacks, (c) Cybersecurity - the system must be protected against unauthorized access, data poisoning, model poisoning, adversarial inputs, and other vulnerabilities. Technical solutions must address AI-specific cybersecurity risks, including prompt injection, data exfiltration through model outputs, and model manipulation."},
    {"q": "How do you implement Article 15 security in AI agent code?", "a": "In code, Article 15 translates to: (1) Retry logic - tenacity, backoff, or manual retry with exponential backoff for robustness against transient failures, (2) Injection defense - prompt injection detection, input sanitization, content filtering (NeMo Guardrails, Rebuff, custom regex), (3) Output validation - validating model outputs against expected schemas (Pydantic response_model, OutputParser), rejecting unexpected formats, (4) Content filtering - toxicity detection, PII redaction on outputs, (5) Sandboxing - running agent-generated code in Docker containers, not with exec(), (6) Access controls - authentication, authorization, API keys, (7) Input bounds - max_length on inputs, rate limiting on API endpoints. Example: OutputParser with retry, content_filter before returning to user, Docker(use_docker=True) for code execution."},
    # General
    {"q": "What is the EU AI Act and when does it take effect?", "a": "The EU AI Act (Regulation (EU) 2024/1689) is the world's first comprehensive legal framework for artificial intelligence. It was adopted on June 13, 2024 and enters into force in phases: (1) February 2, 2025: Prohibitions on unacceptable risk AI (Article 5), (2) August 2, 2025: Rules for general-purpose AI models, (3) August 2, 2026: Full application of all rules including high-risk AI system requirements. It applies to providers placing AI systems on the EU market, deployers using AI in the EU, and providers/deployers outside the EU whose AI system output is used in the EU. Penalties: up to €35 million or 7% of global annual turnover for violations of prohibited practices, up to €15 million or 3% for other violations."},
    {"q": "What AI practices are prohibited under the EU AI Act?", "a": "Article 5 prohibits the following AI practices: (a) subliminal manipulation techniques that distort behavior causing significant harm, (b) exploiting vulnerabilities of specific groups (age, disability, social/economic situation), (c) social scoring by public authorities based on social behavior, (d) real-time remote biometric identification in public spaces for law enforcement (with limited exceptions), (e) untargeted scraping of facial images from internet/CCTV to build facial recognition databases, (f) emotion recognition in workplace and educational settings, (g) biometric categorization to infer race, political opinions, trade union membership, religious beliefs, sex life, or sexual orientation. These prohibitions took effect February 2, 2025."},
    {"q": "What qualifies as a high-risk AI system under the EU AI Act?", "a": "A high-risk AI system is one that falls under Article 6 criteria: (1) AI systems intended as safety components of products covered by EU harmonisation legislation (e.g., machinery, medical devices, vehicles), OR (2) AI systems with use cases listed in Annex III, which includes: biometric identification and categorization, management of critical infrastructure (water, gas, electricity, transport), education and vocational training (admission, assessment, proctoring), employment (recruitment, screening, task allocation, monitoring), access to essential services (credit scoring, insurance, emergency services), law enforcement (risk assessment, lie detection, crime prediction), migration and border control (asylum assessment, document verification), and administration of justice (legal research applied to concrete facts)."},
    {"q": "Does the EU AI Act apply to open-source AI?", "a": "Yes, with some exceptions. The EU AI Act applies to open-source AI models and systems, but Article 2(12) provides an exemption for AI components released under free and open-source licenses UNLESS they are: (a) high-risk AI systems under Article 6, (b) AI systems that fall under prohibited practices (Article 5), (c) AI systems with transparency obligations (Article 50), or (d) general-purpose AI models. Providers of open-source general-purpose AI models have reduced obligations if the model's parameters are made publicly available, unless the model presents systemic risk. Importantly, the exemption does NOT apply if the open-source component is used within a high-risk system - the deployer is still responsible for compliance."},
    {"q": "What are the penalties for violating the EU AI Act?", "a": "The EU AI Act establishes a tiered penalty structure: (1) Up to €35 million or 7% of worldwide annual turnover (whichever is higher) for violations of prohibited AI practices (Article 5), (2) Up to €15 million or 3% for violations of other provisions including high-risk system requirements, (3) Up to €7.5 million or 1% for supplying incorrect information to authorities. For SMEs and startups, the lower of the two thresholds applies. Member states may set their own penalty rules within these maximums. National market surveillance authorities are responsible for enforcement. The European AI Office oversees general-purpose AI model compliance. These penalties can be combined with GDPR fines for data protection violations."},
]

def generate_article_qa():
    """Generate Article text Q&A training examples."""
    examples = []

    for qa in ARTICLE_QA:
        # Direct Q&A
        examples.append({
            "instruction": qa["q"],
            "input": "",
            "output": qa["a"],
        })

        # Rephrased versions
        rephrasings = [
            f"Explain {qa['q'].lower().replace('what does ', '').replace('what is ', '').replace('?', '')} in detail.",
            f"I need to understand: {qa['q']}",
            f"Can you explain {qa['q'].lower().replace('what does ', '').replace('what is ', '').replace('?', '')}?",
            f"As an AI compliance consultant, answer: {qa['q']}",
            f"Help me understand the EU AI Act: {qa['q']}",
        ]
        for rephrasing in rephrasings:
            examples.append({
                "instruction": rephrasing,
                "input": "",
                "output": qa["a"],
            })

    return examples


# ═══════════════════════════════════════
# Phase 10: Cloud Deployment Anti-Patterns
# ═══════════════════════════════════════

CLOUD_PATTERNS = [
    {
        "code": '''# Dockerfile
FROM python:3.11-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
EXPOSE 8080
CMD ["python", "server.py"]

# server.py
from fastapi import FastAPI
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent

app = FastAPI()
llm = ChatOpenAI(model="gpt-4")

@app.post("/query")
async def query(prompt: str):
    agent = create_openai_tools_agent(llm, tools)
    executor = AgentExecutor(agent=agent, tools=tools)
    return executor.invoke({"input": prompt})''',
        "notes": "Docker deployment with no security - no health checks, no resource limits, no auth, no HTTPS, root user, no logging, no rate limiting. All articles fail.",
    },
    {
        "code": '''# kubernetes deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-agent
spec:
  replicas: 5
  template:
    spec:
      containers:
      - name: ai-agent
        image: mycompany/ai-agent:latest
        ports:
        - containerPort: 8080
        env:
        - name: OPENAI_API_KEY
          value: "sk-proj-xxxxxxxxxxxxx"
        - name: DATABASE_URL
          value: "postgresql://admin:password@db:5432/prod"''',
        "notes": "Kubernetes deployment with hardcoded secrets - API keys and database credentials in plaintext YAML. No resource limits, no health probes, no network policies, running as root, 'latest' tag (not reproducible). Article 15 critical fail, Article 12 fail (no log collection).",
    },
    {
        "code": '''# AWS Lambda function
import json
import boto3
from openai import OpenAI

client = OpenAI()

def lambda_handler(event, context):
    body = json.loads(event["body"])
    prompt = body["prompt"]

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
    )

    # Store result in S3
    s3 = boto3.client("s3")
    s3.put_object(
        Bucket="ai-results",
        Key=f"result-{context.aws_request_id}.json",
        Body=json.dumps({"prompt": prompt, "response": response.choices[0].message.content}),
    )

    return {
        "statusCode": 200,
        "body": json.dumps({"response": response.choices[0].message.content}),
    }''',
        "notes": "AWS Lambda AI endpoint - stores raw prompts and responses (potential PII) in S3 without encryption. No input validation, no auth on API Gateway, no rate limiting, no error handling. Article 10 fail (PII storage), Article 15 fail (no auth), Article 12 partial (S3 storage but unstructured).",
    },
    {
        "code": '''# GitHub Actions CI/CD with AI
name: AI Code Review
on: [pull_request]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: AI Review
        run: |
          curl -X POST https://api.openai.com/v1/chat/completions \\
            -H "Authorization: Bearer ${{ secrets.OPENAI_API_KEY }}" \\
            -H "Content-Type: application/json" \\
            -d '{
              "model": "gpt-4",
              "messages": [{"role": "user", "content": "Review this code and auto-merge if it looks good: '"$(cat $(git diff --name-only HEAD~1))"'"}]
            }'
      - name: Auto Merge
        if: contains(steps.review.outputs.result, 'APPROVE')
        run: gh pr merge --auto''',
        "notes": "CI/CD auto-merge with AI - CRITICAL: AI reviewing and auto-merging code with no human review. Article 14 fail (automated deployment decisions). Article 15 fail (prompt injection via code content). Article 9 fail (no risk assessment for auto-merge). Full codebase exposed to API.",
    },
]

def generate_cloud_examples():
    """Generate cloud deployment anti-pattern examples."""
    examples = []

    cloud_instructions = [
        "Audit this cloud deployment configuration for EU AI Act compliance.",
        "What EU AI Act compliance issues exist in this deployment?",
        "Is this AI deployment configuration compliant with the EU AI Act?",
        "Review this infrastructure-as-code for EU AI Act compliance gaps.",
        "What security and compliance issues does this AI deployment have?",
        "Assess this cloud deployment against EU AI Act Articles 9-15.",
    ]

    for pattern in CLOUD_PATTERNS:
        for _ in range(4):
            instruction = random.choice(cloud_instructions)
            output = f"""## EU AI Act Deployment Compliance Analysis

### Findings

{pattern['notes']}

### Key Requirement: EU AI Act applies to DEPLOYMENT, not just code

The EU AI Act's requirements for high-risk systems extend to how AI systems are deployed, not just how they're coded. Infrastructure, secrets management, access controls, monitoring, and logging are all within scope. A compliant AI model deployed on non-compliant infrastructure is still non-compliant."""

            examples.append({
                "instruction": instruction,
                "input": pattern["code"],
                "output": output,
            })

    return examples


# ═══════════════════════════════════════
# Main: Run all phases and combine
# ═══════════════════════════════════════

if __name__ == "__main__":
    all_new = []

    print("Phase 6: Remediation pairs...")
    remediation = generate_remediation_examples()
    all_new.extend(remediation)
    print(f"  Generated {len(remediation)} examples")

    print("Phase 7: Annex III high-risk scenarios...")
    annex = generate_annex_iii_examples()
    all_new.extend(annex)
    print(f"  Generated {len(annex)} examples")

    print("Phase 8: JavaScript/TypeScript agents...")
    js = generate_js_examples()
    all_new.extend(js)
    print(f"  Generated {len(js)} examples")

    print("Phase 9: Article Q&A...")
    qa = generate_article_qa()
    all_new.extend(qa)
    print(f"  Generated {len(qa)} examples")

    print("Phase 10: Cloud deployment patterns...")
    cloud = generate_cloud_examples()
    all_new.extend(cloud)
    print(f"  Generated {len(cloud)} examples")

    # Write all new
    with open("phase6_to_10_advanced.jsonl", "w") as f:
        for ex in all_new:
            f.write(json.dumps(ex) + "\n")

    total = len(all_new)
    print(f"\nTotal new examples: {total}")
    print(f"Written to: phase6_to_10_advanced.jsonl")

    # Now combine with v6
    print("\nCombining with v6 dataset...")
    import hashlib

    all_examples = []
    seen = set()

    for fpath in ["training_data_v6.jsonl", "phase6_to_10_advanced.jsonl"]:
        count = 0
        with open(fpath) as f:
            for line in f:
                h = hashlib.md5(line.strip().encode()).hexdigest()
                if h not in seen:
                    seen.add(h)
                    all_examples.append(line.strip())
                    count += 1
        print(f"  {fpath}: {count} unique")

    random.shuffle(all_examples)

    with open("training_data_v7.jsonl", "w") as f:
        for line in all_examples:
            f.write(line + "\n")

    print(f"\n{'='*50}")
    print(f"FINAL DATASET: {len(all_examples)} examples → training_data_v7.jsonl")
    print(f"{'='*50}")
