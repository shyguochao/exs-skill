# exs-skill

> Distill one ex? No — I want to distill **ten**.

Every person you've ever loved told you something, without even knowing it — **exactly what you're looking for**.

The problem? Those answers are buried in tens of thousands of chat messages, sandwiched between "hey" and "ok". Nobody ever sorted them out for you.

Until now.

**exs-skill** is a Skill that runs inside Claude Code. Feed it your chat history with every ex, and it figures out: which conversations made you happier the longer they went, what they said or did that made you burst out laughing, what kind of person made you want to text first. It then aggregates all those traits across every ex and distills your personal **Ideal Partner Profile**.

> Classic proof that quantity leads to quality — the more exes, the sharper the portrait.

---

**Table of Contents**

- [What It Does](#what-it-does)
- [How It Works](#how-it-works)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Data Privacy](#data-privacy)
- [License](#license)

---

## What It Does

| Command | Description |
|---------|-------------|
| `/analyze-ex` | Import a new ex's chat history and update the ideal profile |
| `/ideal-chat` | Chat with your ideal partner AI (learns and evolves over time) |
| `/export-template` | Export the latest partner template |
| `/advisor` | Love advisor mode — analyze new matches or ask for advice |
| `/show-profile` | View a summary of your current ideal partner profile |
| `/list-exes` | View all imported exes and their contribution breakdown |
| `/rollback {version}` | Roll back to a previous version of the ideal profile |

---

## How It Works

One-liner: **it doesn't analyze your exes — it analyzes you**.

Here's what happens under the hood:

1. Drop in a chat export. The system scans every reply you sent for emotional signals — emoji count, filler words, reply speed, reply length
2. It finds the conversation segments where your mood kept climbing, and tags them as "quality conversations"
3. From those segments, it extracts: what the other person said and did that triggered your good mood
4. All traits from every ex are merged using a weighted formula — `chemistry score × quality conversation ratio` — to produce your ideal profile

> A dream dreamed ten thousand times might just come true — the more data you feed in, the sharper the outline of "the perfect one" becomes.

---

## Installation

```bash
# Install globally
npx skills add <owner/repo@exs-skill> -g -y

# Install Python dependencies
pip install -r requirements.txt
```

---

## Quick Start

1. Export your WeChat or QQ chat history (supports txt / json / csv / html and more)
2. Run `/analyze-ex` and follow the prompts to upload the chat file
3. Once analysis is done, run `/ideal-chat` to start a conversation
4. Run `/export-template` anytime to export your latest partner template — print it out and stick it on your wall if you want

More exes = more accurate profile. This might be the only context in human history where having more exes is genuinely an advantage.

---

## Data Privacy

All data is stored locally in the `data/` directory. Nothing is uploaded to any server.

Your story belongs to you alone.

---

## License

MIT © 2026 [shyguochao](https://github.com/shyguochao)

This project is open source under the MIT License. Feel free to use, modify, and distribute it — just remember:
use it to treat the next person a little better.
