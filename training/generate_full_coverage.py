#!/usr/bin/env python3
"""
AIR Blackbox - Full EU AI Act Coverage Generator (Phases 27-32)
================================================================
Fills the remaining gaps in our training data:
  Phase 27: Article 5  - Prohibited Practices (social scoring, biometric, manipulation)
  Phase 28: Article 6  - Risk Classification (high-risk vs limited vs minimal)
  Phase 29: Article 13 - Transparency to Users (disclosure, labeling, UI)
  Phase 30: Articles 20-24 - Provider Obligations (instructions for use, CE marking)
  Phase 31: Article 52 - GPAI Transparency (model cards, systemic risk, downstream)
  Phase 32: Articles 26, 56-61 - Deployer Obligations (monitoring, DPIA, logging)

No GPU required. Runs on Mac.
"""

import json
import random
import hashlib

# ═══════════════════════════════════════
# Phase 27: Article 5 - Prohibited Practices
# ═══════════════════════════════════════

PROHIBITED_CODE_EXAMPLES = [
    {
        "framework": "Social scoring system",
        "risk": "PROHIBITED",
        "code": '''import openai
from database import get_citizen_records, get_social_media, get_financial_history

def calculate_citizen_score(citizen_id: str) -> float:
    """Calculate a comprehensive social trustworthiness score."""
    records = get_citizen_records(citizen_id)
    social = get_social_media(citizen_id)
    financial = get_financial_history(citizen_id)

    prompt = f"""Analyze this citizen's data and assign a trustworthiness score 0-100:
    - Criminal records: {records['criminal']}
    - Social media behavior: {social['sentiment_score']}
    - Financial reliability: {financial['credit_events']}
    - Community complaints: {records['complaints']}
    - Political associations: {social['political_activity']}
    """
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    score = float(response.choices[0].message.content)

    # Restrict access to public services based on score
    if score < 40:
        restrict_public_transport(citizen_id)
        deny_loan_applications(citizen_id)
    return score''',
        "notes": """**PROHIBITED under Article 5(1)(c) - Social Scoring**

This system is **explicitly banned** by the EU AI Act. Article 5(1)(c) prohibits:
- AI systems that evaluate or classify natural persons based on their social behavior or personal characteristics
- Where the social score leads to detrimental treatment in contexts UNRELATED to those in which the data was generated
- Or where treatment is unjustified or disproportionate to the social behavior

**Specific violations:**
1. Aggregates data across unrelated domains (criminal, social media, financial, political)
2. Uses the score to restrict public services (transport, loans)
3. Includes political associations - also violates fundamental rights
4. No human oversight, no right of appeal, no transparency

**This system CANNOT be made compliant** - it must be discontinued entirely. No amount of documentation, human oversight, or risk management makes social scoring legal under the EU AI Act."""
    },
    {
        "framework": "Real-time biometric identification",
        "risk": "PROHIBITED",
        "code": '''import cv2
from deepface import DeepFace
from database import criminal_watchlist, log_detection

def monitor_public_space(camera_feed_url: str):
    """Real-time facial recognition in public spaces."""
    cap = cv2.VideoCapture(camera_feed_url)

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        faces = DeepFace.extract_faces(frame, detector_backend="retinaface")

        for face in faces:
            # Match against criminal database
            results = DeepFace.find(
                face["face"],
                db_path="./criminal_database",
                model_name="ArcFace",
                enforce_detection=False
            )

            if len(results[0]) > 0 and results[0]["distance"].min() < 0.4:
                match_id = results[0].iloc[0]["identity"]
                log_detection(match_id, camera_feed_url, confidence=0.96)
                alert_law_enforcement(match_id, frame)''',
        "notes": """**PROHIBITED under Article 5(1)(h) - Real-time Remote Biometric Identification**

Article 5(1)(h) prohibits the use of real-time remote biometric identification systems in publicly accessible spaces for law enforcement purposes, except in narrowly defined exceptions (Article 5(2)):
- Search for specific victims of abduction, trafficking, or sexual exploitation
- Prevention of specific, substantial, and imminent threat to life
- Identification of suspects of specific serious criminal offences (listed in Annex IIa)

**Even the exceptions require:**
- Prior judicial authorization (or ex-post within 48 hours in urgent cases)
- Temporal and geographic limitations
- Fundamental rights impact assessment
- Registration in the EU database (Article 49)

**This code violates the prohibition because:**
1. Continuous monitoring of public spaces (no temporal limit)
2. No judicial authorization mechanism
3. No fundamental rights impact assessment
4. No geographic scope limitation
5. Broad "criminal_watchlist" matching - not limited to serious offences in Annex IIa
6. No human review before alert - automated law enforcement notification"""
    },
    {
        "framework": "Subliminal manipulation",
        "risk": "PROHIBITED",
        "code": '''from anthropic import Anthropic
import random

client = Anthropic()

def generate_persuasive_content(user_profile: dict, target_action: str) -> str:
    """Generate subliminal persuasion content tailored to user vulnerabilities."""
    prompt = f"""You are an expert in behavioral psychology and persuasion.

    Target user profile:
    - Age: {user_profile['age']}
    - Known anxieties: {user_profile['anxieties']}
    - Financial stress level: {user_profile['financial_stress']}
    - Emotional state: {user_profile['current_emotion']}
    - Cognitive biases detected: {user_profile['biases']}

    Generate content that exploits their specific vulnerabilities to make them
    {target_action} without them realizing they are being manipulated.
    Use dark patterns and subliminal techniques.
    """
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text

# Target: elderly users with high financial stress
content = generate_persuasive_content(
    {"age": 78, "anxieties": ["health", "loneliness"],
     "financial_stress": "high", "current_emotion": "fearful",
     "biases": ["authority_bias", "scarcity_bias"]},
    "purchase a $5000 supplement package"
)''',
        "notes": """**PROHIBITED under Article 5(1)(a) - Subliminal/Manipulative Techniques**

Article 5(1)(a) prohibits AI systems that deploy subliminal techniques beyond a person's consciousness, or purposefully manipulative or deceptive techniques, with the objective or effect of materially distorting behavior in a way that causes or is reasonably likely to cause significant harm.

**Article 5(1)(b) also applies** - exploiting vulnerabilities of specific groups (age, disability, social/economic situation) to materially distort behavior causing significant harm.

**This code is prohibited because:**
1. Explicitly targets psychological vulnerabilities (anxieties, emotional state)
2. Exploits elderly users (age-based vulnerability - Article 5(1)(b))
3. Exploits financial stress (economic vulnerability)
4. Uses detected cognitive biases as attack vectors
5. Goal is to manipulate without user awareness ("without them realizing")
6. Causes financial harm ($5000 purchase through manipulation)

**This cannot be made compliant.** The entire purpose is manipulation - no amount of transparency, documentation, or human oversight changes the prohibited nature of the system."""
    },
    {
        "framework": "Emotion recognition in workplace",
        "risk": "PROHIBITED",
        "code": '''from transformers import pipeline
import cv2

emotion_detector = pipeline("image-classification", model="emotion-detection-model")

def monitor_employee_emotions(camera_id: str, employee_id: str):
    """Track employee emotional state during work hours."""
    cap = cv2.VideoCapture(camera_id)
    ret, frame = cap.read()

    emotions = emotion_detector(frame)
    dominant_emotion = emotions[0]["label"]
    confidence = emotions[0]["score"]

    log_employee_emotion(employee_id, dominant_emotion, confidence)

    if dominant_emotion in ["angry", "frustrated", "sad"]:
        flag_for_manager_review(employee_id, dominant_emotion)
        adjust_performance_score(employee_id, penalty=-5)

    return {"employee": employee_id, "emotion": dominant_emotion}''',
        "notes": """**PROHIBITED under Article 5(1)(f) - Emotion Recognition in Workplace**

Article 5(1)(f) prohibits the use of emotion recognition systems in the workplace and in education institutions, except where the system is intended to be put into service for medical or safety reasons.

**This code violates the prohibition because:**
1. Emotion recognition deployed in workplace context
2. Not for medical or safety purposes - used for performance management
3. Adjusts performance scores based on detected emotions
4. Flags employees for manager review based on emotional state
5. Continuous monitoring without consent mechanism
6. No legitimate medical/safety justification

**Limited exceptions exist** for:
- Detecting driver drowsiness (safety)
- Medical diagnostic support
- These must still comply with Articles 9-15 as high-risk systems

**This system must be discontinued.** Workplace emotion recognition for performance management is categorically prohibited."""
    },
]

PROHIBITED_QA_EXAMPLES = [
    {
        "instruction": "What AI practices are completely banned under the EU AI Act?",
        "response": """Article 5 of the EU AI Act establishes a list of **prohibited AI practices** that cannot be deployed under any circumstances (with narrow law enforcement exceptions for biometrics):

**1. Subliminal/Manipulative Techniques (Art. 5(1)(a))**
AI systems using subliminal techniques beyond a person's consciousness, or purposefully manipulative/deceptive techniques, to materially distort behavior causing significant harm.

**2. Exploitation of Vulnerabilities (Art. 5(1)(b))**
AI systems exploiting vulnerabilities due to age, disability, or social/economic situation to materially distort behavior causing significant harm.

**3. Social Scoring (Art. 5(1)(c))**
AI systems evaluating or classifying persons based on social behavior or personal characteristics, where the resulting social score leads to detrimental treatment in unrelated contexts or disproportionate treatment.

**4. Criminal Risk Profiling (Art. 5(1)(d))**
AI systems assessing risk of committing criminal offences based solely on profiling or personality traits, except when augmenting human assessments based on objective, verifiable facts directly linked to criminal activity.

**5. Untargeted Facial Image Scraping (Art. 5(1)(e))**
AI systems creating or expanding facial recognition databases through untargeted scraping of facial images from the internet or CCTV footage.

**6. Emotion Recognition in Workplace/Education (Art. 5(1)(f))**
Emotion recognition systems in workplace and education settings, except for medical or safety reasons.

**7. Biometric Categorization for Sensitive Attributes (Art. 5(1)(g))**
AI systems categorizing persons based on biometric data to deduce race, political opinions, trade union membership, religious beliefs, sex life, or sexual orientation (except lawful labeling of biometric datasets in law enforcement).

**8. Real-time Remote Biometric Identification (Art. 5(1)(h))**
Real-time remote biometric identification in publicly accessible spaces for law enforcement, except for narrowly defined serious crime/threat scenarios requiring prior judicial authorization.

**Key principle:** These systems **cannot be made compliant** through documentation, human oversight, or risk management. They must not be developed or deployed in the EU."""
    },
    {
        "instruction": "I'm building an AI system that analyzes customer facial expressions during sales calls to coach salespeople. Is this allowed under the EU AI Act?",
        "response": """This requires careful analysis depending on your specific deployment context:

**If used in the workplace (employer monitoring employee performance):**
This is **PROHIBITED under Article 5(1)(f)**. Emotion recognition in the workplace is banned unless it serves medical or safety purposes. Using it to coach salespeople or evaluate their performance based on customer emotions falls outside the medical/safety exception.

**If analyzing customer emotions:**
Customers in a sales interaction are not in a workplace or educational institution, so Article 5(1)(f) doesn't directly apply to their side. However:

1. **Article 50(3) - Transparency obligation**: You must inform the customer that an emotion recognition system is being used on them. This requires clear, real-time notification BEFORE the system processes their data.

2. **GDPR implications**: Emotion detection from facial expressions involves processing biometric data (special category under GDPR Article 9). You need explicit consent or another lawful basis.

3. **High-risk classification**: If the system influences decisions about the sales interaction (pricing, offers, escalation), it may fall under Annex III high-risk categories and require full Articles 9-15 compliance.

**Recommendation:** Do not deploy this system for employee coaching purposes. If you want to analyze customer sentiment, consider non-biometric alternatives (e.g., post-call surveys, text sentiment analysis of transcripts with consent) that avoid the prohibited practices and biometric data processing issues."""
    },
    {
        "instruction": "How do I detect if a codebase implements social scoring prohibited under Article 5?",
        "response": """To detect potential social scoring systems in code, scan for these patterns:

**1. Multi-domain data aggregation about individuals:**
```python
# Red flags - combining unrelated personal data sources
get_criminal_records(user_id)
get_social_media_activity(user_id)
get_financial_history(user_id)
get_political_affiliations(user_id)
get_health_records(user_id)
```

**2. Score computation from personal characteristics:**
```python
# Red flags - computing composite "trustworthiness" or "reliability" scores
citizen_score = compute_trustworthiness(aggregated_data)
social_credit = calculate_social_score(person_data)
reliability_rating = assess_person(behavioral_data)
```

**3. Consequence mechanisms based on scores:**
```python
# Red flags - restricting services/access based on computed scores
if score < threshold:
    deny_service(user_id)
    restrict_access(user_id)
    reduce_priority(user_id)
    flag_for_surveillance(user_id)
```

**4. Cross-context detrimental treatment:**
```python
# Red flag - using data from context A to restrict in context B
social_behavior = get_social_media_activity(user)  # Context A
deny_loan_application(user)  # Context B (unrelated)
```

**Key distinction:** Not all scoring systems are prohibited. Credit scoring using financial data for lending decisions is legitimate (though high-risk under Annex III). The prohibition targets systems that aggregate across unrelated contexts to create a general "social" score affecting access to unrelated services.

**Scanner implementation:** Check for functions that (1) aggregate data from 3+ distinct personal data categories, (2) compute a single person-level score, and (3) trigger access restrictions or service denial based on that score."""
    },
]

# ═══════════════════════════════════════
# Phase 28: Article 6 - Risk Classification
# ═══════════════════════════════════════

RISK_CLASSIFICATION_QA = [
    {
        "instruction": "How does the EU AI Act classify AI systems by risk level?",
        "response": """The EU AI Act uses a **four-tier risk classification** system:

**1. PROHIBITED (Article 5)**
Systems that pose unacceptable risks. Completely banned. Examples: social scoring, real-time biometric identification in public spaces (with narrow exceptions), subliminal manipulation, emotion recognition in workplaces.

**2. HIGH-RISK (Articles 6-7 + Annex III)**
Systems that must comply with strict requirements (Articles 9-15). Two pathways to high-risk classification:

*Pathway A - Article 6(1):* AI systems that are safety components of products covered by EU harmonisation legislation listed in Annex I (e.g., machinery, medical devices, vehicles, toys, lifts, radio equipment). These require third-party conformity assessment.

*Pathway B - Article 6(2) + Annex III:* Standalone AI systems in specific high-risk use cases:
- Biometric identification and categorization
- Management of critical infrastructure (energy, water, transport, digital)
- Education and vocational training (admissions, assessments)
- Employment (recruitment, promotion, termination, task allocation)
- Access to essential services (credit scoring, insurance, social benefits)
- Law enforcement (risk assessment, polygraphs, evidence analysis)
- Migration and border control (risk assessment, document authentication)
- Administration of justice (legal research, sentencing assistance)

**3. LIMITED RISK (Article 50)**
Systems with specific transparency obligations:
- AI systems that interact with people must disclose they are AI (chatbots)
- Emotion recognition systems must inform subjects
- Deep fakes must be labeled as artificially generated
- AI-generated text published to inform the public must be labeled

**4. MINIMAL RISK**
All other AI systems. No specific obligations beyond voluntary codes of practice. Examples: spam filters, AI in video games, inventory management.

**Important exception - Article 6(3):** A high-risk system listed in Annex III is NOT considered high-risk if it does not pose a significant risk of harm to health, safety, or fundamental rights. The provider must document this assessment and register in the EU database before placing on market."""
    },
    {
        "instruction": "I'm building a resume screening tool that ranks job applicants. What risk level is this under the EU AI Act?",
        "response": """A resume screening tool that ranks job applicants is classified as **HIGH-RISK** under Article 6(2) and Annex III, point 4(a).

**Annex III, Area 4 - Employment, workers management, and access to self-employment:**
Specifically point 4(a) covers: *"AI systems intended to be used for the recruitment or selection of natural persons, in particular to place targeted job advertisements, to screen or filter applications, and to evaluate candidates."*

Your resume screening tool falls squarely under "screen or filter applications" and "evaluate candidates."

**This means you must comply with:**

1. **Article 9 - Risk Management System:** Identify risks of discriminatory outcomes, test for bias across protected characteristics (gender, age, ethnicity, disability), implement mitigation measures.

2. **Article 10 - Data Governance:** Ensure training data is representative, examine for bias, document data collection methodology. Particularly critical - historical hiring data often encodes existing biases.

3. **Article 11 - Technical Documentation:** Document the system's purpose, algorithm design, training data, performance metrics, known limitations.

4. **Article 12 - Record-Keeping:** Log all screening decisions, input CVs, ranking outputs, with sufficient detail for post-hoc auditing.

5. **Article 13 - Transparency:** Inform candidates that AI is being used in the screening process. Provide meaningful information about the logic involved.

6. **Article 14 - Human Oversight:** A human must be able to override the AI's rankings. The system cannot be fully automated for reject decisions.

7. **Article 15 - Accuracy & Robustness:** Test for adversarial manipulation (keyword stuffing), ensure consistent results, validate accuracy across demographic groups.

**Additional obligations:**
- Fundamental rights impact assessment (Article 27) before deployment
- Registration in the EU database (Article 49)
- Conformity assessment (self-assessment per Article 43(2) for Annex III systems)
- Post-market monitoring (Article 72)"""
    },
    {
        "instruction": "How do I determine if my AI system qualifies for the Article 6(3) exception to avoid high-risk classification?",
        "response": """Article 6(3) provides an exception where an Annex III system is NOT high-risk if it does not pose a significant risk of harm. Here's how to evaluate:

**The system is NOT high-risk if it performs a narrow procedural task**, such as:
- Organizing data into categories without influencing decisions
- Detecting document formatting patterns
- Preparing preliminary drafts that are fully reviewed by humans
- A task that is purely assistive with no autonomous decision-making

**Conditions that PREVENT the exception (your system IS high-risk if any apply):**

1. **Profiling:** The system profiles natural persons (Article 6(3)(a))
2. **Consequential decisions:** Output materially influences decisions about natural persons (Article 6(3)(b))
3. **Risk of harm:** Poses a non-negligible risk to health, safety, or fundamental rights (Article 6(3)(c))

**If you claim the exception, you MUST:**
1. Document your assessment explaining why the system does not pose significant risk
2. Register the system in the EU database BEFORE placing it on the market (Article 49(2))
3. Keep the documentation available for competent authorities upon request

**Practical examples:**

*Exception APPLIES:*
- AI that auto-categorizes support tickets by topic (no profiling, no decisions about people)
- AI that detects formatting errors in documents (narrow procedural task)

*Exception does NOT apply:*
- AI that categorizes support tickets AND routes angry customers to retention (influences treatment of individuals)
- AI that screens job applications even as a "first pass" (profiles + influences hiring decisions)
- AI that detects insurance fraud (consequential decisions about individuals)

**Warning:** Regulators will scrutinize exception claims closely. When in doubt, comply with high-risk requirements. The cost of non-compliance (up to €35 million or 7% global turnover) far exceeds the cost of compliance."""
    },
    {
        "instruction": "Can you scan this code and tell me what risk level it would be under the EU AI Act?",
        "response": """To classify code under the EU AI Act risk framework, I analyze several signals:

**Step 1: Check for Prohibited Practices (Article 5)**
- Social scoring patterns (multi-domain aggregation → composite score → service denial)
- Real-time biometric identification in public spaces
- Subliminal manipulation / vulnerability exploitation
- Emotion recognition in workplace/education contexts
- Untargeted facial image scraping

If any match → **PROHIBITED**. System cannot be deployed.

**Step 2: Check for Annex III High-Risk Indicators**
- Biometric processing (face recognition, voice ID, fingerprint matching)
- Critical infrastructure control (energy grids, water systems, traffic management)
- Educational assessment (grading, admissions, proctoring)
- Employment decisions (screening, hiring, firing, task allocation, performance evaluation)
- Credit/insurance scoring or essential service access
- Law enforcement analytics (predictive policing, evidence evaluation)
- Immigration/border systems (risk assessment, document verification)
- Justice system assistance (sentencing, legal analysis)

If any match → **HIGH-RISK**. Must comply with Articles 9-15.

**Step 3: Check for Limited Risk Transparency Triggers (Article 50)**
- Chatbot/conversational AI (must disclose AI interaction)
- Deepfake/synthetic media generation (must label as AI-generated)
- Emotion recognition (must inform subjects)
- AI-generated text for public information (must label)

If any match → **LIMITED RISK**. Must meet transparency requirements.

**Step 4: Default**
If none of the above → **MINIMAL RISK**. No mandatory requirements.

**Code signals I look for:**
```python
# HIGH-RISK signals
from deepface import DeepFace          # Biometric
predict_creditworthiness(applicant)     # Credit scoring
rank_candidates(applications)           # Employment
assess_student_performance(exam)        # Education
predict_recidivism(defendant)           # Law enforcement

# LIMITED RISK signals
chatbot.reply(user_message)             # Chatbot disclosure needed
generate_image(prompt)                  # Synthetic media labeling
detect_emotion(face_image)              # Emotion recognition notice
```

Provide your code and I'll classify it with specific article references."""
    },
]

# ═══════════════════════════════════════
# Phase 29: Article 13 - Transparency to Users
# ═══════════════════════════════════════

TRANSPARENCY_CODE_EXAMPLES = [
    {
        "framework": "Chatbot without AI disclosure",
        "risk": "HIGH",
        "code": '''from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory

llm = ChatOpenAI(model="gpt-4")
memory = ConversationBufferMemory()

def handle_customer_query(user_message: str) -> str:
    """Handle incoming customer support messages."""
    response = llm.invoke(user_message)
    memory.save_context({"input": user_message}, {"output": response.content})
    return response.content

# Deployed as customer support chat widget
app.route("/chat", methods=["POST"])
def chat():
    message = request.json["message"]
    reply = handle_customer_query(message)
    return jsonify({"reply": reply})''',
        "notes": """**Article 50(1) Violation - AI System Transparency**

Article 50(1) requires that providers of AI systems intended to interact directly with natural persons shall design the system so that it **informs the person that they are interacting with an AI system**, unless this is obvious from the circumstances.

**Violations:**
1. No disclosure to users that they are talking to an AI system
2. Deployed as "customer support" chat - user likely assumes they're talking to a human
3. No transparency notice at start of conversation
4. No mechanism to request human handoff

**Required fixes:**
```python
DISCLOSURE = "You are chatting with an AI assistant. You can request a human agent at any time."

def handle_customer_query(user_message: str, is_first_message: bool = False) -> str:
    if is_first_message:
        prefix = DISCLOSURE + "\\n\\n"
    else:
        prefix = ""
    response = llm.invoke(user_message)
    return prefix + response.content
```

Additional requirements:
- Provide a clear "Talk to a human" button
- Log that the disclosure was presented (Article 12)
- Include disclosure in the system's instructions for use (Article 13)"""
    },
    {
        "framework": "Deepfake generation without labeling",
        "risk": "HIGH",
        "code": '''import torch
from diffusers import StableDiffusionPipeline

pipe = StableDiffusionPipeline.from_pretrained("stabilityai/stable-diffusion-xl")
pipe = pipe.to("cuda")

def generate_news_image(headline: str) -> bytes:
    """Generate an image to accompany a news article."""
    prompt = f"Photorealistic news photograph: {headline}"
    image = pipe(prompt, num_inference_steps=50).images[0]

    # Save without any metadata about AI generation
    image.save(f"news_{headline[:20]}.jpg")
    return image

def generate_social_media_post(topic: str) -> dict:
    """Generate a social media post with AI image."""
    image = generate_news_image(topic)
    caption = llm.invoke(f"Write a factual news caption about: {topic}")
    return {"image": image, "caption": caption, "source": "Staff Reporter"}''',
        "notes": """**Article 50(2) and 50(4) Violations - AI-Generated Content Labeling**

Article 50(2) requires providers of AI systems that generate synthetic content (audio, image, video, text) to ensure outputs are **marked in a machine-readable format** and detectable as artificially generated.

Article 50(4) requires deployers using AI to generate or manipulate image, audio, or video content constituting a deep fake to **disclose that content has been artificially generated or manipulated**.

**Violations:**
1. No machine-readable AI-generation markers in image metadata (Article 50(2))
2. No visible labeling of AI-generated images (Article 50(4))
3. Deliberately misleading - "Photorealistic news photograph" prompt
4. Attributes content to "Staff Reporter" - active deception
5. No C2PA or watermarking to enable downstream detection

**Required fixes:**
```python
from PIL import Image
from PIL.ExifTags import Base as ExifBase

def generate_news_image(headline: str) -> bytes:
    image = pipe(prompt, num_inference_steps=50).images[0]

    # Add machine-readable AI generation metadata (Article 50(2))
    metadata = PngInfo()
    metadata.add_text("ai-generated", "true")
    metadata.add_text("ai-model", "stable-diffusion-xl")
    metadata.add_text("generation-date", datetime.now().isoformat())

    # Add visible watermark/label
    draw = ImageDraw.Draw(image)
    draw.text((10, 10), "AI-Generated Image", fill="red")

    image.save(f"news_{headline[:20]}.png", pnginfo=metadata)
    return image
```

Also implement C2PA content credentials for robust provenance tracking."""
    },
]

TRANSPARENCY_QA_EXAMPLES = [
    {
        "instruction": "What are the transparency requirements under Article 50 of the EU AI Act?",
        "response": """Article 50 establishes transparency obligations for specific AI system categories:

**Article 50(1) - AI interacting with persons:**
AI systems designed to interact directly with natural persons must be designed so the person is informed they are interacting with an AI system. Exception: where it's obvious from the circumstances and context of use.

**Article 50(2) - Synthetic content generation:**
Providers of AI systems that generate synthetic audio, image, video, or text content must ensure outputs are marked in a machine-readable format and are detectable as artificially generated or manipulated. The technical solution must be effective, interoperable, robust, and reliable.

**Article 50(3) - Emotion recognition and biometric categorization:**
Deployers of emotion recognition or biometric categorization systems must inform natural persons exposed to the system about its operation and process personal data in accordance with GDPR and the Law Enforcement Directive.

**Article 50(4) - Deep fakes:**
Deployers using AI to generate or manipulate image, audio, or video content that constitutes a deep fake must disclose that content has been artificially generated or manipulated. Exception: AI-generated content that assists editorial or creative work where a human reviews and takes editorial responsibility.

**Article 50(5) - AI-generated text on public interest:**
Deployers using AI to generate or manipulate text published for the purpose of informing the public on matters of public interest must disclose that the content was AI-generated. Exception: where content undergoes human review and a person holds editorial responsibility.

**Implementation in code:**
- Chatbots: Display "You are talking to an AI" notice before first interaction
- Image generators: Embed C2PA/watermark metadata, add visible labels
- Emotion recognition: Display notice + privacy policy before processing
- Text generation for news: Add "AI-generated" label or ensure human editorial review"""
    },
    {
        "instruction": "How should I implement Article 13 transparency requirements in my high-risk AI system?",
        "response": """Article 13 requires high-risk AI systems to be designed and developed so that their operation is sufficiently transparent to enable deployers to interpret the system's output and use it appropriately. Here's a practical implementation guide:

**1. Instructions for Use (Article 13(3)):**
Your system must ship with documentation that includes:
```python
SYSTEM_INSTRUCTIONS = {
    "intended_purpose": "Resume screening for software engineering roles",
    "intended_users": "HR teams at companies with 50+ employees",
    "technical_capabilities": [
        "Keyword matching against job requirements",
        "Experience level classification",
        "Skills extraction and matching"
    ],
    "known_limitations": [
        "May underweight non-traditional career paths",
        "Trained primarily on English-language resumes",
        "Does not assess soft skills or cultural fit"
    ],
    "performance_metrics": {
        "precision": 0.87,
        "recall": 0.82,
        "demographic_parity_gap": 0.04
    },
    "human_oversight_measures": "All AI-filtered candidates must be reviewed by a human recruiter before rejection",
    "foreseeable_misuse": [
        "Using as sole decision-maker without human review",
        "Applying to roles outside the trained domain"
    ]
}
```

**2. Output Interpretability (Article 13(1)):**
```python
def screen_resume(resume: str, job_description: str) -> dict:
    score = model.predict(features)

    return {
        "score": score,
        "confidence": 0.85,
        "key_factors": [
            {"factor": "python_experience", "weight": 0.3, "match": True},
            {"factor": "years_experience", "weight": 0.2, "match": True},
            {"factor": "education_level", "weight": 0.15, "match": False}
        ],
        "recommendation": "REVIEW",  # Not just pass/fail
        "explanation": "Strong technical match but education requirement not met. Human review recommended.",
        "limitations_warning": "This assessment does not evaluate soft skills."
    }
```

**3. Logging for Auditability (Article 13 + Article 12):**
Every decision must be traceable with enough context for a human to understand why the system reached its conclusion."""
    },
]

# ═══════════════════════════════════════
# Phase 30: Articles 20-24 - Provider Obligations
# ═══════════════════════════════════════

PROVIDER_OBLIGATIONS_QA = [
    {
        "instruction": "What are the provider obligations for high-risk AI systems under Articles 16-24?",
        "response": """Providers of high-risk AI systems have extensive obligations under the EU AI Act:

**Article 16 - General Provider Obligations:**
- Ensure compliance with Articles 9-15
- Have a quality management system (Article 17)
- Maintain technical documentation (Article 11)
- Keep automatically generated logs (Article 12)
- Ensure conformity assessment is carried out (Article 43)
- Register in the EU database (Article 49)
- Take corrective action for non-conforming systems
- Affix CE marking (Article 48)

**Article 17 - Quality Management System:**
Must cover:
- Compliance strategy and regulatory procedures
- Design and development techniques
- Data management (collection, preparation, labeling, storage)
- Risk management (integration with Article 9)
- Post-market monitoring procedures
- Incident reporting procedures
- Communication with authorities
- Record-keeping

**Article 18 - Technical Documentation:**
Draw up documentation BEFORE the system is placed on market. Must demonstrate compliance with Articles 9-15. Keep updated throughout system lifetime.

**Article 19 - Automatically Generated Logs:**
Must be designed to retain logs for a period appropriate to the intended purpose (minimum 6 months unless otherwise specified by Union or national law).

**Article 20 - Corrective Actions:**
If a system is non-conforming, providers must immediately take corrective action (bring into conformity, withdraw, recall). Must inform distributors, deployers, and authorities.

**Article 21 - Cooperation with Competent Authorities:**
Must provide all information and documentation requested, in a language the authority can understand. Grant access to logs and source code where necessary.

**Article 22 - Authorised Representatives:**
Providers established outside the EU must appoint an authorised representative in the EU BEFORE placing system on the market.

**Article 23 - Obligations of Importers:**
Verify the provider has carried out conformity assessment, has technical documentation, has CE marking. If non-conforming, do not place on market.

**Article 24 - Obligations of Distributors:**
Verify CE marking exists, provider and importer have complied with their obligations, storage/transport conditions don't compromise compliance.

**Code implementation tip:** Build a compliance checklist into your CI/CD pipeline:
```python
PRE_RELEASE_CHECKS = {
    "technical_documentation": check_docs_complete(),
    "conformity_assessment": check_assessment_done(),
    "eu_database_registration": check_registered(),
    "ce_marking": check_ce_marking(),
    "logging_enabled": check_auto_logging(),
    "risk_management": check_rms_current(),
    "quality_management": check_qms_current()
}
```"""
    },
    {
        "instruction": "What must be included in the instructions for use that ship with a high-risk AI system?",
        "response": """Article 13(3) specifies that instructions for use must include, at minimum:

**1. Provider Identity:**
- Name, address, contact details of the provider
- Authorized representative (if applicable)

**2. System Characteristics:**
- Intended purpose of the AI system
- Level of accuracy, robustness, and cybersecurity (Article 15) including known limitations
- Performance metrics validated against specific demographic groups (where applicable)
- Any foreseeable misuse that could lead to risks

**3. Technical Specifications:**
- Hardware and software requirements for deploying the system
- Input data specifications (what data the system expects)
- Output format and interpretation guidance
- System architecture overview sufficient for deployers to understand operation

**4. Human Oversight:**
- Measures enabling human oversight (Article 14)
- Technical measures that facilitate interpretation of outputs
- How to override, interrupt, or stop the system
- Known automation bias risks and mitigation

**5. Expected Lifetime and Maintenance:**
- Expected system lifetime
- Software update policy and schedule
- Hardware maintenance requirements

**6. Change Log:**
- Record of changes to the system since initial conformity assessment
- Pre-determined changes vs. substantial modifications

**7. Data Logging:**
- What data is automatically logged (Article 12)
- Log format and access methods
- Retention period

**Implementation:**
```python
# Generate instructions-for-use documentation programmatically
class InstructionsForUse:
    def __init__(self, system_config):
        self.provider = system_config['provider']
        self.intended_purpose = system_config['purpose']
        self.performance_metrics = system_config['metrics']
        self.limitations = system_config['limitations']
        self.human_oversight = system_config['oversight_measures']
        self.input_specs = system_config['input_specifications']
        self.output_specs = system_config['output_specifications']
        self.logging_config = system_config['logging']

    def generate_document(self) -> str:
        # Auto-generate structured IFU document
        # that stays in sync with actual system config
        pass

    def validate_completeness(self) -> List[str]:
        # Check all Article 13(3) requirements are addressed
        missing = []
        if not self.provider.get('name'):
            missing.append("Provider name required (Art. 13(3)(a))")
        if not self.performance_metrics:
            missing.append("Performance metrics required (Art. 13(3)(b))")
        if not self.limitations:
            missing.append("Known limitations required (Art. 13(3)(b))")
        return missing
```"""
    },
    {
        "instruction": "What is the CE marking requirement for high-risk AI systems?",
        "response": """**CE Marking (Article 48 + Article 49)**

The CE marking indicates that a high-risk AI system conforms with the EU AI Act requirements. It's mandatory before placing the system on the EU market.

**What it means:**
- The provider declares the system complies with Articles 9-15
- A conformity assessment has been carried out (Article 43)
- Technical documentation is complete (Article 11)
- The system is registered in the EU database (Article 49)

**How to affix:**
- CE marking must be visible, legible, and indelible on the AI system or its packaging/documentation
- For software-only AI systems: include in the digital documentation, user interface, or accompanying materials
- Must follow the format specified in Annex V

**Conformity Assessment pathways (Article 43):**

*Self-assessment (Article 43(2)):* For most Annex III high-risk systems, providers can perform internal conformity assessment following Annex VI. This covers:
- Employment AI (resume screening, performance evaluation)
- Credit scoring
- Insurance risk assessment
- Most other Annex III use cases

*Third-party assessment (Article 43(1)):* Required for:
- Biometric identification/categorization systems (Annex III, point 1)
- Critical infrastructure AI (Annex III, point 2) - if the AI is a safety component
- Systems covered by Annex I harmonization legislation requiring third-party assessment

**Registration in EU Database (Article 49):**
Before placing on market, register in the EU database with:
- Provider details
- System name and description
- Intended purpose
- Conformity assessment results
- Member States where placed on market

**Code implementation:**
```python
class ConformityDeclaration:
    def __init__(self):
        self.provider_name = "Company Name"
        self.system_name = "AI System Name"
        self.intended_purpose = "Description"
        self.conformity_procedure = "Annex VI (self-assessment)"
        self.standards_applied = ["ISO 42001", "ISO 23894"]
        self.assessment_date = datetime.now()
        self.eu_database_id = None  # Assigned upon registration

    def generate_declaration(self) -> str:
        # EU Declaration of Conformity per Annex V
        return f\"\"\"
        EU DECLARATION OF CONFORMITY
        Provider: {self.provider_name}
        AI System: {self.system_name}
        This AI system conforms with the requirements of
        Regulation (EU) 2024/1689 (EU AI Act).
        Assessment: {self.conformity_procedure}
        Date: {self.assessment_date}
        \"\"\"
```"""
    },
]

# ═══════════════════════════════════════
# Phase 31: Article 52 - GPAI Transparency
# ═══════════════════════════════════════

GPAI_CODE_EXAMPLES = [
    {
        "framework": "GPAI model without transparency documentation",
        "risk": "HIGH",
        "code": '''import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Fine-tuned model deployed as API
model = AutoModelForCausalLM.from_pretrained("./my-fine-tuned-llm")
tokenizer = AutoTokenizer.from_pretrained("./my-fine-tuned-llm")

@app.route("/generate", methods=["POST"])
def generate():
    prompt = request.json["prompt"]
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(**inputs, max_new_tokens=512)
    text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return jsonify({"text": text})

# No model card
# No training data documentation
# No downstream provider notification
# No copyright policy
# No technical documentation summary''',
        "notes": """**Article 53 Violations - GPAI Model Provider Obligations**

If you're making a general-purpose AI model available (including via API), Article 53 requires:

**1. Technical Documentation (Article 53(1)(a) + Annex XI):**
- Model architecture description
- Training methodology and techniques
- Data curation and preparation processes
- Computational resources used for training
- Training energy consumption and carbon footprint
- Evaluation results on standardized benchmarks

**2. Instructions and Information to Downstream Providers (Article 53(1)(b)):**
- Integration guide for downstream providers
- Capabilities and limitations of the model
- Sufficient information for downstream providers to comply with their own obligations

**3. Copyright Compliance Policy (Article 53(1)(c)):**
- Policy to comply with EU copyright law (Directive 2019/790)
- Particularly the text and data mining exception (Article 4 of the Directive)
- Identification and compliance with rights reservations expressed by rights holders

**4. Publicly Available Summary (Article 53(1)(d)):**
- Sufficiently detailed summary of the content used for training
- Following the template provided by the AI Office

**Required additions to this code:**
```python
MODEL_CARD = {
    "model_name": "MyFineTunedLLM",
    "base_model": "llama-3.1-8b",
    "provider": "Company Name",
    "training_data_summary": "Fine-tuned on 50K examples of...",
    "capabilities": ["text generation", "summarization"],
    "limitations": ["Not suitable for medical advice", "English only"],
    "evaluation_results": {"mmlu": 0.72, "hellaswag": 0.81},
    "compute_used": "8x A100 GPUs for 24 hours",
    "copyright_policy": "https://company.com/copyright-policy",
    "contact": "ai-compliance@company.com"
}
```"""
    },
]

GPAI_QA_EXAMPLES = [
    {
        "instruction": "What are the obligations for providers of general-purpose AI models under the EU AI Act?",
        "response": """The EU AI Act (Chapter V, Articles 51-56) establishes specific obligations for providers of general-purpose AI (GPAI) models:

**All GPAI Model Providers (Article 53):**

1. **Technical documentation** (Annex XI): Prepare and maintain documentation covering model architecture, training process, data governance, evaluation results, computational resources, and energy consumption.

2. **Downstream provider information**: Provide sufficient information and documentation to enable downstream providers who integrate the GPAI model into their own AI systems to understand the model's capabilities and limitations and comply with their own obligations.

3. **Copyright compliance**: Put in place a policy to comply with EU copyright law, particularly regarding text and data mining. Respect rights reservations expressed by rights holders (Article 4(3) of Directive 2019/790).

4. **Training data summary**: Make publicly available a sufficiently detailed summary of the content used for training the model, following the template provided by the AI Office.

**GPAI Models with Systemic Risk (Article 55):**

A GPAI model is classified as having systemic risk if:
- It has high impact capabilities (evaluated based on benchmarks and indicators)
- The cumulative amount of compute used for training exceeds 10^25 FLOPS
- Or designated by Commission decision based on Annex XIII criteria

Additional obligations for systemic risk models:
1. **Model evaluation**: Perform standardized model evaluations including adversarial testing
2. **Systemic risk assessment and mitigation**: Assess and mitigate possible systemic risks at Union level
3. **Incident tracking and reporting**: Track, document, and report serious incidents to the AI Office and relevant national authorities without undue delay
4. **Cybersecurity**: Ensure adequate cybersecurity protections for the model and its physical infrastructure

**Codes of Practice (Article 56):**
The AI Office facilitates drawing up codes of practice for GPAI providers to detail compliance. Adherence to approved codes creates a presumption of conformity.

**Open-source exception (Article 53(2)):**
Providers of free and open-source GPAI models (weights publicly available) are exempt from all obligations EXCEPT the training data summary and copyright policy. This exception does NOT apply to models with systemic risk."""
    },
    {
        "instruction": "How do I determine if my GPAI model has systemic risk?",
        "response": """**Systemic Risk Classification (Article 51(2) + Annex XIII):**

Your GPAI model is presumed to have systemic risk if the cumulative amount of compute used for its training exceeds **10^25 floating point operations (FLOPS)**.

**Annex XIII criteria for assessment:**
1. Number of parameters
2. Quality and size of training dataset
3. Compute used for training (FLOPS threshold)
4. Input and output modalities (multimodal models get extra scrutiny)
5. Benchmarks and evaluation results (especially on reasoning, coding, scientific tasks)
6. Number of registered users or downstream integrations
7. Potential reach and impact across the EU single market

**Practical FLOPS estimation:**
```python
def estimate_training_flops(
    num_parameters: float,
    num_tokens: float,
    num_epochs: int = 1
) -> float:
    # Approximation: 6 * N * D for transformer training
    # N = parameters, D = tokens processed
    flops = 6 * num_parameters * num_tokens * num_epochs
    return flops

# Example: 70B model trained on 2T tokens
flops = estimate_training_flops(70e9, 2e12)
# = 8.4e23 FLOPS - below 10^25 threshold

# Example: 400B model trained on 15T tokens
flops = estimate_training_flops(400e9, 15e12)
# = 3.6e25 FLOPS - ABOVE threshold → systemic risk
```

**If your model exceeds the threshold:**
1. Notify the European Commission without delay (Article 52(1))
2. Perform model evaluations including adversarial testing (Article 55(1)(a))
3. Assess and mitigate systemic risks (Article 55(1)(b))
4. Track and report serious incidents (Article 55(1)(c))
5. Ensure adequate cybersecurity (Article 55(1)(d))
6. Keep documentation and logs available for at least 10 years

**Commission can also designate** a model as systemic risk even below the FLOPS threshold, based on the Annex XIII criteria, via a reasoned decision.

**Models currently presumed systemic risk:** GPT-4, Claude 3 Opus/Sonnet, Gemini Ultra, and similar frontier models likely exceed 10^25 FLOPS."""
    },
    {
        "instruction": "What does the open-source exception for GPAI models actually cover?",
        "response": """**Article 53(2) - Open-Source GPAI Exception:**

Providers of GPAI models released under a free and open-source licence (as defined: model weights, architecture, and usage information are publicly available) are exempt from MOST provider obligations.

**What open-source GPAI providers STILL must do:**
1. **Training data summary** (Article 53(1)(d)): Make publicly available a sufficiently detailed summary of training data content
2. **Copyright compliance** (Article 53(1)(c)): Maintain a copyright policy complying with EU copyright law

**What open-source GPAI providers are EXEMPT from:**
- Full technical documentation requirements (Annex XI)
- Providing integration documentation to downstream providers
- Quality management systems for the model itself

**CRITICAL EXCEPTION: Systemic risk models get NO open-source exemption.**
If your open-source model exceeds 10^25 FLOPS or is designated as systemic risk, you must comply with ALL GPAI obligations including Article 55 (model evaluation, systemic risk assessment, incident reporting, cybersecurity).

**Practical implications for open-source AI developers:**

```python
# Minimum required: training data summary
TRAINING_DATA_SUMMARY = {
    "model": "my-open-source-llm-7b",
    "license": "Apache-2.0",
    "training_data": {
        "sources": [
            "Wikipedia (English, 6.4M articles)",
            "Common Crawl (filtered subset, 500GB)",
            "GitHub code (permissively licensed repos)",
            "StackExchange (CC-BY-SA content)"
        ],
        "total_tokens": "1.2T tokens",
        "languages": ["English (85%)", "Code (10%)", "Other (5%)"],
        "filtering": "Deduplication, toxicity filtering, PII removal",
        "cutoff_date": "2024-06-01"
    },
    "copyright_policy": "https://github.com/org/model/COPYRIGHT.md"
}
```

**Note for downstream deployers:** Even though the model provider has reduced obligations, if you integrate an open-source GPAI model into a high-risk AI system, YOU (as the deployer/provider of the high-risk system) must still comply with Articles 9-15. The open-source exception applies to the model provider, not to you."""
    },
    {
        "instruction": "I'm building on top of GPT-4 via the API. What are my obligations vs. OpenAI's under the GPAI rules?",
        "response": """This is a common scenario. The EU AI Act distinguishes between the **GPAI model provider** (OpenAI) and the **downstream provider** (you) who integrates the model into an AI system.

**OpenAI's obligations as GPAI provider (Article 53 + Article 55):**
- Provide technical documentation about GPT-4
- Provide YOU with sufficient information about capabilities, limitations, and integration guidance
- Comply with copyright law
- Publish training data summary
- Since GPT-4 likely has systemic risk: model evaluation, risk assessment, incident reporting, cybersecurity

**Your obligations as downstream provider:**
Depend on what you're building:

**If your system is HIGH-RISK (Annex III):**
You are the provider of the high-risk AI system and must comply with Articles 9-15:
- Article 9: Risk management (including risks from the underlying GPT-4 model)
- Article 10: Data governance (your prompts, fine-tuning data, RAG data)
- Article 11: Technical documentation (your system architecture including GPT-4 integration)
- Article 12: Logging (log all API calls, inputs, outputs)
- Article 13: Transparency (document that your system uses GPT-4)
- Article 14: Human oversight (especially important since you don't control GPT-4's internals)
- Article 15: Robustness (handle API failures, validate outputs, defend against prompt injection)

**If your system is LIMITED RISK:**
- Article 50 transparency obligations (AI disclosure, synthetic content labeling)

**If your system is MINIMAL RISK:**
- No mandatory requirements, but voluntary codes of practice

**Key responsibility split:**
```
OpenAI (GPAI provider)          You (downstream provider)
├── Model safety                ├── System-level safety
├── Training data governance    ├── Application data governance
├── Model documentation         ├── System documentation
├── Systemic risk mitigation    ├── Use-case risk management
├── Copyright compliance        ├── Human oversight design
└── Model evaluation            ├── Output validation
                                ├── Logging & monitoring
                                └── Conformity assessment
```

**Practical tip:** Request OpenAI's downstream provider documentation (Article 53(1)(b)) and incorporate it into your own technical documentation. If OpenAI doesn't provide sufficient information for you to comply, document this gap - regulators will look at the full supply chain."""
    },
]

# ═══════════════════════════════════════
# Phase 32: Articles 26, 56-61 - Deployer Obligations
# ═══════════════════════════════════════

DEPLOYER_CODE_EXAMPLES = [
    {
        "framework": "Deployer without required monitoring",
        "risk": "HIGH",
        "code": '''from ai_vendor import ResumeScreener

# Deploy vendor's high-risk AI system
screener = ResumeScreener(api_key="sk-xxx")

def process_applications(applications: list) -> list:
    results = []
    for app in applications:
        score = screener.screen(app["resume"], app["job_id"])
        results.append({"applicant": app["name"], "score": score})

    # Auto-reject bottom 80%
    threshold = sorted([r["score"] for r in results])[int(len(results) * 0.8)]
    for r in results:
        if r["score"] < threshold:
            send_rejection_email(r["applicant"])
        else:
            forward_to_recruiter(r["applicant"])

    return results''',
        "notes": """**Multiple Deployer Obligation Violations (Articles 26, 29):**

As a deployer of a high-risk AI system (resume screening = Annex III area 4), you have specific obligations:

**Article 26(1) - Use in accordance with instructions:**
Violation: Auto-rejecting 80% of applicants without human review likely violates the provider's instructions for use, which almost certainly require human oversight for rejection decisions.

**Article 26(2) - Human oversight:**
Violation: No human reviews the AI's screening decisions before rejection emails are sent. Article 26(2) requires deployers to assign human oversight to natural persons who have the competence, training, and authority to fulfill that role.

**Article 26(5) - Monitoring:**
Violation: No monitoring of the system's outputs for accuracy, bias, or drift. Deployers must monitor operation based on the instructions for use and inform the provider of any serious incidents.

**Article 26(9) - DPIA under GDPR:**
Missing: For employment AI, deployers must carry out a Data Protection Impact Assessment per GDPR Article 35 before deployment.

**Required fixes:**
```python
def process_applications(applications: list) -> list:
    results = []
    for app in applications:
        score = screener.screen(app["resume"], app["job_id"])
        results.append({
            "applicant": app["name"],
            "score": score,
            "reviewed_by": None,
            "decision": "pending_review"
        })

    # Log all scores for monitoring (Article 26(5))
    log_screening_results(results)

    # Flag for human review - NO auto-rejection
    for r in results:
        assign_to_human_reviewer(r)

    # Monitor for bias (Article 26(5))
    check_demographic_parity(results)

    return results
```"""
    },
    {
        "framework": "Deployer missing fundamental rights impact assessment",
        "risk": "HIGH",
        "code": '''from credit_ai import CreditScorer

scorer = CreditScorer(model="v3.2")

def evaluate_loan_application(applicant_data: dict) -> dict:
    """Evaluate loan application using AI credit scoring."""
    result = scorer.predict(applicant_data)

    if result["score"] > 700:
        return {"decision": "approved", "rate": calculate_rate(result["score"])}
    else:
        return {"decision": "denied", "reason": result["top_factors"]}

# Deployed without:
# - Fundamental rights impact assessment (Article 27)
# - Data protection impact assessment (GDPR Article 35)
# - Informing affected persons (Article 26(11))
# - Monitoring system outputs for bias
# - Registration in EU database (Article 49(3))''',
        "notes": """**Deployer Obligation Violations (Articles 26, 27):**

**Article 27 - Fundamental Rights Impact Assessment (FRIA):**
Before deploying a high-risk AI system, deployers that are bodies governed by public law or private entities providing public services, AND deployers of systems in Annex III areas 1(a), 2, 3, 4, 5(b)(c), 7, 8, MUST carry out an assessment of the impact on fundamental rights.

Credit scoring falls under Annex III area 5(a), so FRIA requirements apply.

The FRIA must include:
1. Description of the deployer's processes using the AI system
2. Period and frequency of AI system use
3. Categories of natural persons and groups likely affected
4. Specific risks of harm to those groups
5. Human oversight measures implemented
6. Measures to act on AI system outputs
7. Measures to address identified risks

**Article 26(11) - Informing Affected Persons:**
Deployers of high-risk AI systems that make decisions about natural persons must inform those persons that they are subject to AI-assisted decision making. For credit scoring, applicants must be told AI is being used.

**Article 26(8) - EU Database Registration:**
Deployers must register their use of the high-risk AI system in the EU database (Article 49(3)).

**Required additions:**
```python
class CreditScoringDeployment:
    def __init__(self):
        self.fria_completed = True
        self.fria_date = "2026-01-15"
        self.dpia_completed = True
        self.eu_database_registered = True

    def evaluate(self, applicant_data, applicant_id):
        # Inform applicant (Article 26(11))
        notify_applicant_of_ai_use(applicant_id)

        result = scorer.predict(applicant_data)

        # Log for monitoring (Article 26(5))
        log_decision(applicant_id, result)

        # Human review for denials
        if result["score"] <= 700:
            return assign_to_human_reviewer(applicant_id, result)

        return result
```"""
    },
]

DEPLOYER_QA_EXAMPLES = [
    {
        "instruction": "What are the key obligations for deployers of high-risk AI systems?",
        "response": """Deployers (organizations that USE high-risk AI systems under their authority) have significant obligations under Article 26:

**1. Use According to Instructions (Article 26(1)):**
Use the AI system in accordance with the provider's instructions for use. Don't repurpose the system for uses outside its intended purpose.

**2. Human Oversight (Article 26(2)):**
Assign human oversight to natural persons who have:
- Necessary competence, training, and authority
- Ability to properly interpret the system's output
- Ability to decide not to use the system or override/reverse outputs
- Awareness of automation bias tendency

**3. Input Data Quality (Article 26(4)):**
Ensure input data is relevant and sufficiently representative for the intended purpose (to the extent you have control over inputs).

**4. Monitoring (Article 26(5)):**
Monitor operation of the AI system based on the instructions for use. If you have reason to believe the system presents a risk, suspend use and inform the provider. Report any serious incidents to the provider and authorities.

**5. Logging Retention (Article 26(6)):**
Keep automatically generated logs for a period appropriate to the intended purpose (minimum 6 months), to the extent under your control.

**6. Workers Council Notification (Article 26(7)):**
Inform workers' representatives and affected workers that they will be subject to a high-risk AI system. Provide information per Articles 13 and GDPR.

**7. DPIA for Employment & Public Services (Article 26(9)):**
Use information from the provider to carry out a Data Protection Impact Assessment under GDPR Article 35, where required.

**8. Inform Affected Persons (Article 26(11)):**
Persons subject to decisions or assistance from high-risk AI must be informed of that fact, including the provider identity and the system's purpose.

**9. Fundamental Rights Impact Assessment (Article 27):**
Required for certain deployers (public bodies, public service providers) using systems in specified Annex III areas. Must be completed BEFORE first deployment.

**10. EU Database Registration (Article 49(3)):**
Register your deployment of the high-risk system in the EU database."""
    },
    {
        "instruction": "What's the difference between a provider and a deployer under the EU AI Act? When does a deployer become a provider?",
        "response": """**Provider vs. Deployer - Key Definitions:**

**Provider (Article 3(3)):** A natural or legal person that develops an AI system or GPAI model, or has one developed, and places it on the market or puts it into service under its own name or trademark.

**Deployer (Article 3(4)):** A natural or legal person that uses an AI system under its authority, except where the system is used in a personal, non-professional activity.

**When a deployer BECOMES a provider (Article 25):**

You transition from deployer to provider if you do ANY of the following:

1. **Put your name/trademark on it:** Place your name or trademark on a high-risk AI system already on the market (Article 25(1)(a))

2. **Make a substantial modification:** Make a substantial modification to a high-risk AI system already on the market (Article 25(1)(b))

3. **Change the intended purpose:** Modify the intended purpose of an AI system (including a GPAI system) in a way that makes it high-risk (Article 25(1)(c))

**What counts as "substantial modification"?**
A change to the AI system after placing on market which:
- Was not foreseen or planned by the original provider
- Changes the system's compliance with the requirements of the Act
- Affects the system's intended purpose

**Practical examples:**

*You remain a deployer:*
- Using GPT-4 via API for customer support chatbot (no modification to the model)
- Deploying a vendor's resume screener as-is
- Fine-tuning within the provider's documented parameters

*You become a provider:*
- Fine-tuning a vendor's model significantly and deploying under your brand name
- Taking an open-source model, modifying it, and selling it as your product
- Repurposing a general text classifier as a medical diagnostic tool (changing intended purpose to high-risk)

**Why this matters:**
Providers have much heavier obligations - full Articles 9-15 compliance, conformity assessment, CE marking, quality management system. If you accidentally become a provider, you inherit ALL of these obligations.

**Code check for provider status:**
```python
def assess_provider_status(deployment):
    if deployment.uses_own_brand:
        return "PROVIDER"  # Article 25(1)(a)
    if deployment.model_substantially_modified:
        return "PROVIDER"  # Article 25(1)(b)
    if deployment.intended_purpose_changed:
        return "PROVIDER"  # Article 25(1)(c)
    if deployment.purpose_is_high_risk and deployment.purpose != deployment.original_purpose:
        return "PROVIDER"  # Article 25(1)(c)
    return "DEPLOYER"
```"""
    },
    {
        "instruction": "How do I scan code for deployer obligation compliance?",
        "response": """Scanning for deployer compliance focuses on different patterns than provider compliance. Here's what to check:

**1. Human Oversight Implementation (Article 26(2)):**
```python
# GOOD - human review before consequential decisions
result = ai_system.predict(data)
human_decision = assign_to_reviewer(result)
execute_decision(human_decision)

# BAD - fully automated consequential decisions
result = ai_system.predict(data)
execute_decision(result)  # No human in loop
```
Scan for: direct execution of AI outputs without human review in high-risk contexts.

**2. Monitoring Implementation (Article 26(5)):**
```python
# GOOD - systematic monitoring
log_prediction(input_data, output, timestamp)
check_accuracy_drift(recent_predictions)
check_demographic_parity(recent_predictions)
alert_if_anomaly_detected()

# BAD - fire and forget
result = ai_system.predict(data)
return result  # No logging, no monitoring
```
Scan for: presence of logging, drift detection, accuracy monitoring.

**3. Input Data Validation (Article 26(4)):**
```python
# GOOD - validate inputs match expected format
def process(data):
    validate_schema(data, expected_schema)
    check_data_quality(data)
    result = ai_system.predict(data)

# BAD - pass anything through
def process(data):
    result = ai_system.predict(data)  # No validation
```

**4. Person Notification (Article 26(11)):**
```python
# GOOD - inform affected persons
notify_user("This decision was assisted by an AI system.")
provide_system_info(system_name, provider, purpose)

# BAD - no notification
decision = ai_system.decide(user_data)
apply_decision(user_id, decision)  # User never told AI was involved
```

**5. Incident Reporting Mechanism (Article 26(5)):**
```python
# GOOD - incident detection and reporting
if prediction_confidence < THRESHOLD:
    log_incident(severity="warning")
    notify_provider(incident_details)
if harm_detected:
    report_serious_incident(authorities, provider)

# BAD - no incident handling
result = ai_system.predict(data)
```

**Scanner check summary:**
| Deployer Obligation | Code Pattern to Detect |
|---|---|
| Human oversight | AI output → human review → action (not AI → action) |
| Monitoring | Logging + drift detection + accuracy tracking |
| Input validation | Schema checks before AI inference |
| Person notification | User-facing AI disclosure messages |
| Incident reporting | Error thresholds + provider notification + authority reporting |
| FRIA completed | Configuration flag or documentation reference |"""
    },
]


# ═══════════════════════════════════════
# Combine all examples and write JSONL
# ═══════════════════════════════════════

def format_code_example(example: dict) -> dict:
    """Format a code+notes example into chat format."""
    return {
        "messages": [
            {"role": "system", "content": "You are AIR Blackbox, an EU AI Act compliance expert. Analyze code for compliance with the EU AI Act (Regulation 2024/1689)."},
            {"role": "user", "content": f"Analyze this code for EU AI Act compliance:\n\n```python\n{example['code']}\n```"},
            {"role": "assistant", "content": example["notes"]}
        ]
    }

def format_qa_example(example: dict) -> dict:
    """Format a Q&A example into chat format."""
    return {
        "messages": [
            {"role": "system", "content": "You are AIR Blackbox, an EU AI Act compliance expert. Provide accurate, actionable guidance on EU AI Act compliance."},
            {"role": "user", "content": example["instruction"]},
            {"role": "assistant", "content": example["response"]}
        ]
    }

def dedup(examples: list) -> list:
    """Remove duplicates based on content hash."""
    seen = set()
    unique = []
    for ex in examples:
        h = hashlib.md5(json.dumps(ex, sort_keys=True).encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            unique.append(ex)
    return unique

def main():
    all_examples = []

    # Phase 27: Prohibited Practices
    print("Phase 27: Article 5 - Prohibited Practices")
    for ex in PROHIBITED_CODE_EXAMPLES:
        all_examples.append(format_code_example(ex))
    for ex in PROHIBITED_QA_EXAMPLES:
        all_examples.append(format_qa_example(ex))
    print(f"  {len(PROHIBITED_CODE_EXAMPLES)} code + {len(PROHIBITED_QA_EXAMPLES)} QA = {len(PROHIBITED_CODE_EXAMPLES) + len(PROHIBITED_QA_EXAMPLES)} examples")

    # Phase 28: Risk Classification
    print("Phase 28: Article 6 - Risk Classification")
    for ex in RISK_CLASSIFICATION_QA:
        all_examples.append(format_qa_example(ex))
    print(f"  {len(RISK_CLASSIFICATION_QA)} QA examples")

    # Phase 29: Transparency
    print("Phase 29: Article 13/50 - Transparency to Users")
    for ex in TRANSPARENCY_CODE_EXAMPLES:
        all_examples.append(format_code_example(ex))
    for ex in TRANSPARENCY_QA_EXAMPLES:
        all_examples.append(format_qa_example(ex))
    print(f"  {len(TRANSPARENCY_CODE_EXAMPLES)} code + {len(TRANSPARENCY_QA_EXAMPLES)} QA = {len(TRANSPARENCY_CODE_EXAMPLES) + len(TRANSPARENCY_QA_EXAMPLES)} examples")

    # Phase 30: Provider Obligations
    print("Phase 30: Articles 16-24 - Provider Obligations")
    for ex in PROVIDER_OBLIGATIONS_QA:
        all_examples.append(format_qa_example(ex))
    print(f"  {len(PROVIDER_OBLIGATIONS_QA)} QA examples")

    # Phase 31: GPAI Transparency
    print("Phase 31: Article 52-56 - GPAI Transparency")
    for ex in GPAI_CODE_EXAMPLES:
        all_examples.append(format_code_example(ex))
    for ex in GPAI_QA_EXAMPLES:
        all_examples.append(format_qa_example(ex))
    print(f"  {len(GPAI_CODE_EXAMPLES)} code + {len(GPAI_QA_EXAMPLES)} QA = {len(GPAI_CODE_EXAMPLES) + len(GPAI_QA_EXAMPLES)} examples")

    # Phase 32: Deployer Obligations
    print("Phase 32: Articles 26, 56-61 - Deployer Obligations")
    for ex in DEPLOYER_CODE_EXAMPLES:
        all_examples.append(format_code_example(ex))
    for ex in DEPLOYER_QA_EXAMPLES:
        all_examples.append(format_qa_example(ex))
    print(f"  {len(DEPLOYER_CODE_EXAMPLES)} code + {len(DEPLOYER_QA_EXAMPLES)} QA = {len(DEPLOYER_CODE_EXAMPLES) + len(DEPLOYER_QA_EXAMPLES)} examples")

    # Deduplicate
    all_examples = dedup(all_examples)

    # Write seed examples
    output_file = "training/phase27_to_32_full_coverage.jsonl"
    with open(output_file, "w") as f:
        for ex in all_examples:
            f.write(json.dumps(ex) + "\n")

    print(f"\nTotal seed examples: {len(all_examples)}")
    print(f"Written to: {output_file}")

if __name__ == "__main__":
    main()
