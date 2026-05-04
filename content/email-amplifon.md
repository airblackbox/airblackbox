# Track B Draft - Amplifon

- **Recipient:** Giuseppe Ficara, Senior Director / Global Head of Data and AI
- **Email:** giuseppe.ficara@amplifon.com
- **Confidence:** HIGH (Amplifon format `[first].[last]@amplifon.com` at 97% per RocketReach)
- **HQ:** Milan, Italy
- **Industry:** Healthcare / Hearing aids (sensitive medical data, MDR adjacency, EU AI Act Article 6 risk)
- **AI signal:** Amplifon launched AmplifAI, a global AI governance program + Agentforce deployment for autonomous customer scheduling, follow-ups, and device-servicing alerts across 26 countries / 20,000 professionals
- **Signal URL:** https://www.startuphub.ai/ai-news/artificial-intelligence/2026/amplifon-s-ai-platform-governance-control-and-discovery
- **Hook article:** Article 10 (Data Governance) - sensitive health data + cross-border transfers across 26 countries
- **Status:** Email Drafted (Gmail draft NOT created - see daily summary, AIR/Enterprise/* labels are missing)

---

## Email 1 (send today)

**Subject:** amplifai + article 10

Hi Giuseppe,

Saw the AmplifAI launch - a Control Tower + Committee structure for governing AI across 26 countries is exactly the right shape for Article 10 evidence under the EU AI Act, and most enterprises that size are still figuring out the data lineage piece.

The specific gap I see most often in healthcare-adjacent deployments: Agentforce's autonomous scheduling and follow-up touch hearing-care PII (audiograms, device telemetry, appointment history) across borders, and Article 10(2) wants documented lineage from data source to model output. That's hard to retrofit.

If it's useful, AIR Blackbox's open-source scanner maps Agentforce data flows to Article 10 + Article 12 evidence requirements automatically. Worth 20 minutes to compare against what AmplifAI is already capturing?

Jason
AIR Blackbox
airblackbox.ai

---

## Email 2 (text, Jason schedules Day 4 if no reply)

**Subject:** one specific check

Hi Giuseppe,

Concrete example from healthcare deployments: the scanner flags any cross-border data transfer in an Agentforce action where the originating data subject's consent scope isn't logged. For Amplifon, that's the difference between an Article 10 finding and clean evidence.

Runs locally against your metadata exports, no data leaves your environment.

Jason
airblackbox.ai

---

## Email 3 (text, Jason schedules Day 9 if no reply)

**Subject:** closing this one

Hi Giuseppe,

Closing the file unless I hear back. The open-source scanner lives at github.com/air-blackbox/gateway if AmplifAI ever wants a second pair of eyes on Article 10 evidence.

Jason
airblackbox.ai

---

## Notes for Jason

- Ficara is the natural buyer - he led the AmplifAI launch and runs the Control Tower. He'll engage on substance, not slideware.
- Hearing aids are a borderline case under EU AI Act / MDR - the device is regulated under MDR, the customer-facing AI is regulated under AI Act. The cross-border framing is the wedge.
- If he asks "isn't AmplifAI doing this already" - the honest answer is governance frameworks define WHAT to capture, AIR Blackbox automates capture. Different layer.
- Italian language is fine if you want to switch on a call; Ficara's bio is bilingual.
