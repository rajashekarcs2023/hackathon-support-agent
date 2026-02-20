# Request for Proposal: Hackathon Q&A Bot Configuration

We provide an AI-powered Q&A bot that answers participant questions about your hackathon using information you supply. The bot looks up answers from a knowledge base and, when it cannot answer or when a participant needs human help, can escalate to your team. This document describes what we need from you to configure the bot and how we handle escalation.

---

## 1. What We Need From You

### 1.1 Hackathon Information (Required)

We need a **complete dump of all hackathon-related information** your team has. Our system will parse and index this on our side, so **the format does not matter**. You may provide it in any of the following (or similar):

- A single PDF document
- A Google Doc (with view access)
- A Notion page
- A structured document (e.g. Markdown or plain text)
- Any other single place that contains the full set of details below

The important requirement is that **everything is in one place** so we can ingest it reliably.

Please ensure your materials include information covering at least the following areas (where applicable to your event). If a topic does not apply, you may omit it; we will only use what you provide.

| Topic                      | What to include (examples)                                                           |
| -------------------------- | ------------------------------------------------------------------------------------ |
| **Event identity**         | Event name, tagline, edition, official website                                       |
| **Dates and times**        | Start/end of event, when hacking starts, submission deadline (with timezone)         |
| **Check-in**               | Where and when to check in, what to bring, registration process                      |
| **Venue**                  | Address, building(s), key rooms or floors, parking                                   |
| **Schedule**               | Full schedule of activities (times, titles, locations, short descriptions)           |
| **Teams**                  | Min/max team size, whether solo is allowed, how to register a team                   |
| **Eligibility**            | Who can participate, age or enrollment requirements, guest policy                    |
| **Tracks / themes**        | Competition tracks or themes and what they mean                                      |
| **Prizes**                 | Prize tiers, amounts, sponsor prizes, how they are awarded                           |
| **Judging**                | How projects are judged, criteria, judging process                                   |
| **Submissions**            | What must be submitted, platform (e.g. Devpost), deadlines, required links or videos |
| **Workshops**              | Workshops and tech talks: times, titles, hosts, locations, skill level               |
| **Sponsors**               | Sponsor list, tiers, what they offer to participants (credits, swag, etc.)           |
| **Resources / APIs**       | Tools, APIs, cloud credits, hardware, or SDKs available to hackers                   |
| **Meals and food**         | Meal times, locations, menus, dietary options                                        |
| **Wi‑Fi and connectivity** | Network name, password (if you share it), where to get help                          |
| **Code of conduct**        | Summary, prohibited behavior, how to report incidents                                |
| **Contact and support**    | How to reach organizers, help desk location, Slack/Discord, emergency contact        |
| **FAQ**                    | Any other frequent questions (sleeping, travel, parking, hardware, etc.)             |

Again: we parse this on our end. You do not need to follow a specific structure or format—just ensure the content is complete and in one place.

---

## 2. Escalation When the Bot Cannot Answer

A core requirement is handling the case when the bot **cannot answer** a question or when a participant needs **human help** (e.g. urgent issues, live/operational questions). We need to know how you want those cases to be escalated.

### 2.1 Flow on Our Side

- The bot will try to answer from the knowledge base.
- When it cannot answer confidently, or when the participant is in distress or reporting something urgent, the bot will **offer** to escalate to a human organizer.
- Escalation is only performed **after the participant confirms** (e.g. by saying “yes” or “please escalate”).
- Once confirmed, we trigger whatever escalation method you have chosen (see below).

### 2.2 Escalation Method We Need From You

We **strongly recommend Discord** for the "ask a question" / escalation path. Our implemented flow works as follows:

- **Discord (recommended):** We create a new thread in a designated channel with the participant’s question (and any relevant context), then send the participant a **link to that thread** so they can follow the conversation and get a direct response from your organizers. This has been used successfully at past events.

Other options are possible if your event does not use Discord:

- **Slack:** e.g. post to a channel or create a thread and provide a link to the participant.
- **Other:** If you use another platform (e.g. Discord, Slack, or a ticketing system), tell us what you prefer and we can discuss integration.

In your response, please state:

1. Which platform you use for organizer communication (e.g. Discord, Slack).
2. How you would like escalated questions to appear (e.g. thread + link, channel message).
3. Any constraints (e.g. specific channel, role to ping).

We will use this to configure the escalation path for your event.

---

## 3. Summary

| Item                      | Your action                                                                                                                                                    |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Hackathon information** | Provide a single document (PDF, Google Doc, etc.) containing all event info listed in Section 1.1. Format is flexible; we will parse it.                       |
| **Escalation method**     | Tell us how you want unanswered or urgent questions escalated (we recommend Discord thread + link; Slack or other options available), and any platform-specific details we need. |

If you have questions about this request or need clarification on any section, please reach out. We will use your responses to configure the bot and escalation flow for your hackathon.
