# Track B Draft - ENGIE

- **Recipient:** Sébastien Arbola, EVP Data, Digital & IT, Strategy and Research & Innovation
- **Email:** sebastien.arbola@engie.com
- **Confidence:** HIGH (ENGIE format `[first].[last]@engie.com` at 97.4% per RocketReach)
- **HQ:** Courbevoie, France (suburb of Paris)
- **Industry:** Energy / Utilities (critical infrastructure under EU AI Act Annex III(2), NIS2 overlay)
- **AI signal:** ENGIE deployed Agentforce in Belgium (with Capgemini) achieving 71% autonomous case resolution for billing, contracts, smart meter, and EV charging questions. Future plans include field technician + sales + billing/trading agents
- **Signal URL:** https://www.salesforce.com/customer-stories/engie/
- **Hook article:** Article 11 (Technical Documentation) + Article 12 (Record-Keeping) - autonomous resolution at 71% means the audit trail IS the compliance evidence
- **Status:** Email Drafted (Gmail draft NOT created - see daily summary, AIR/Enterprise/* labels are missing)

---

## Email 1 (send today)

**Subject:** 71% auto-resolution + article 12

Hi Sébastien,

The Belgium Agentforce rollout hitting 71% autonomous resolution in a few weeks is one of the cleaner agentic deployments published this year. The flip side: at 71% auto-resolution on billing, smart meter, and EV charging questions, the audit trail becomes the compliance evidence, and Article 12 of the EU AI Act is specific about what that trail has to contain.

Most utilities I look at are missing one piece in particular: tamper-evident chaining on the agent's decision sequence, so a regulator (or an internal audit) can prove the log wasn't backfilled. Field technician and trading agents make this harder once they ship.

Worth 20 minutes to walk through what Article 11 + 12 evidence looks like for the next-wave agents before they're in production?

Jason
AIR Blackbox
airblackbox.ai

---

## Email 2 (text, Jason schedules Day 4 if no reply)

**Subject:** one example

Hi Sébastien,

Concrete: AIR Blackbox attaches an HMAC-SHA256 audit chain to any Agentforce action sequence so each entry is provably ordered and unmodifiable. For ENGIE that turns Article 12 from "we have logs" into "we have evidence."

Open source, runs locally. Worth a look?

Jason
airblackbox.ai

---

## Email 3 (text, Jason schedules Day 9 if no reply)

**Subject:** closing this one

Hi Sébastien,

Closing the file. github.com/air-blackbox/gateway if it's useful when the trading agents go live.

Jason
airblackbox.ai

---

## Notes for Jason

- Arbola owns Data + Digital + IT + Strategy + R&I - unusually consolidated portfolio. He's the right buyer AND the right strategist.
- The Belgium Agentforce case is a public Salesforce reference, so referencing it is fair game and shows you're paying attention.
- The "next-wave agents" framing matters - once trading and field technician agents ship, Article 9 (Risk Management) + Article 15 (Accuracy/Robustness) become much harder to retrofit. Push timing.
- Backup contact if Arbola doesn't engage: Julia Maris, EVP Group Corporate Secretariat (Legal & Ethics owner), `julia.maris@engie.com`. GC angle, less technical, slower to close.
