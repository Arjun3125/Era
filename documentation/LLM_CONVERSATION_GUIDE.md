# LLM-to-LLM Conversation Guide

## Overview

**Direct conversation between User LLM (deepseek-r1:8b) and Program LLM (qwen3:14b).**

This tool enables the two LLMs to have natural, back-and-forth dialogues on any topic. It's useful for:
- Testing dialogue quality and coherence
- Demonstrating system capabilities
- Exploring how two different models interact
- Creating interesting multi-perspective conversations
- Generating diverse conversation data

## Getting Started

### Basic Usage

**Interactive Mode (default)**
```bash
python llm_conversation.py
```
Prompts you to enter topics and have multiple conversations. Can save each one.

**Demo Mode**
```bash
python llm_conversation.py --mode demo
```
Runs a pre-configured demo conversation on an intelligent decision-making topic.

**Topic Mode (specific topic)**
```bash
python llm_conversation.py --mode topic --topic "Your topic here"
```
Example:
```bash
python llm_conversation.py --mode topic --topic "The future of AI in healthcare"
```

### Options

```
--mode {interactive,demo,topic}
    interactive: Multiple Topics with save/load (default)
    demo: Single pre-configured demo
    topic: Specific topic conversation

--topic TEXT
    Topic for discussion (required for --mode topic)
    
--rounds N
    Number of conversation rounds (default: 5)
    
--verbose
    Show detailed output including timing
```

## Conversation Flow

### Per Round

```
1. User LLM speaks
   ↓
2. Program LLM responds to User LLM's point
   ↓
3. User LLM responds to Program LLM's point
   ↓
[Repeat for N rounds]
```

### Total Exchanges

- **5 rounds** (default) = ~10 exchanges
- **10 rounds** = ~20 exchanges
- Configurable via `--rounds` parameter

## Examples

### Example 1: Interactive Mode
```bash
$ python llm_conversation.py

# System starts and you're prompted:
Topic: Should AI systems make important decisions for people?

# [User LLM] starts...
# [Program LLM] responds...
# [User LLM] responds...
# [Program LLM] responds...
# ...

# After conversation:
Save this conversation? (y/n): y
✓ Saved to data/conversations/llm_conversation_20260219_153042.json

# Back to prompt:
Enter topic (or command): quit
```

### Example 2: Demo Mode
```bash
$ python llm_conversation.py --mode demo

# Shows preset conversation on "Intelligent decision systems"
# Automatically saves result
```

### Example 3: Specific Topic with More Rounds
```bash
$ python llm_conversation.py --mode topic \
    --topic "Work-life balance in remote teams" \
    --rounds 8
```

## Output

### Console Display

Each conversation shows:

```
[User LLM]
[Initial thoughts and perspective...]

──────────────────────────────────────────────────────

ROUND 2

──────────────────────────────────────────────────────

[Program LLM]
[Response to User LLM's point...]

[User LLM]
[Thoughtful reply to Program LLM...]

ROUND 3
[continues...]
```

### Saved Format

Conversations saved to: `data/conversations/llm_conversation_YYYYMMDD_HHMMSS.json`

**Structure:**
```json
{
  "timestamp": "2026-02-19T15:30:42.123456",
  "rounds": 5,
  "conversation": [
    {
      "round": 1,
      "speaker": "User LLM",
      "text": "...",
      "role": "initiator"
    },
    {
      "round": 2,
      "speaker": "Program LLM",
      "text": "...",
      "role": "responder"
    },
    ...
  ]
}
```

## Commands in Interactive Mode

### During Conversation
None - conversation runs automatically to `--rounds` limit.

### Between Conversations
```
Enter topic (or command):

Commands:
  <any text>    Start new conversation on that topic
  save          Save current conversation
  show          Display current conversation
  clear         Clear conversation history
  quit          Exit program
```

## Model Personalities

### User LLM (deepseek-r1)
- More exploratory and questioning
- Tends to dig deeper into implications
- Good at asking follow-up questions
- Provides detailed reasoning

### Program LLM (Qwen3)
- More structured and systematic
- Good at synthesizing points
- Provides actionable perspectives
- Builds on previous ideas

## Use Cases

### 1. Testing Dialogue Quality
```bash
python llm_conversation.py --mode topic \
    --topic "A complex decision scenario" \
    --rounds 10
```
Run and evaluate how the models handle nuanced discussion.

### 2. Generating Training Data
```bash
for topic in "topic1" "topic2" "topic3"; do
  python llm_conversation.py --mode topic --topic "$topic"
done
```
Creates multiple conversation examples for analysis.

### 3. Demo/Showcase
```bash
python llm_conversation.py --mode demo
```
Show system capabilities to stakeholders.

### 4. Exploring Perspectives
```bash
python llm_conversation.py --mode topic \
    --topic "Your specific question" \
    --rounds 8
```
Get two AI perspectives on a specific issue.

## Saved Conversations

**Location:** `data/conversations/`

**File naming:** `llm_conversation_YYYYMMDD_HHMMSS.json`

### Viewing Saved Conversations
```bash
# List all saved conversations
ls -lh data/conversations/

# View a specific conversation (pretty print)
python -m json.tool data/conversations/llm_conversation_*.json
```

### Analyzing Saved Data
```python
import json

with open("data/conversations/llm_conversation_20260219_153042.json") as f:
    data = json.load(f)
    
for exchange in data["conversation"]:
    print(f"{exchange['speaker']} (Round {exchange['round']}):")
    print(f"  {exchange['text'][:100]}...")
```

## Performance Notes

### LLM Response Times
- **deepseek-r1:8b** (User LLM): ~3-5 seconds per response
- **qwen3:14b** (Program LLM): ~2-4 seconds per response
- **Total per round**: ~10-20 seconds

### Example Timing
- 5 rounds (10 exchanges): ~2-3 minutes
- 10 rounds (20 exchanges): ~4-6 minutes

## Advanced Usage

### Custom Python Script

```python
from llm_conversation import LLMConversation

# Create engine
engine = LLMConversation(max_rounds=8, verbose=True)

# Run specific conversation
engine.start_conversation(topic="Your custom topic")

# Save it
engine._save_conversation()

# Display it
engine._display_conversation()
```

### Batch Processing

```bash
#!/bin/bash

topics=(
  "AI in healthcare"
  "Remote work future"
  "Climate solutions"
  "Education technology"
)

for topic in "${topics[@]}"; do
  echo "Running: $topic"
  python llm_conversation.py --mode topic --topic "$topic" --rounds 5
done
```

## Troubleshooting

### Issue: "Connection refused"
**Solution:** Make sure Ollama is running:
```bash
# Check if Ollama is running
ps aux | grep ollama

# Or start it
ollama serve
```

### Issue: "Model not found"
**Solution:** Pull the models:
```bash
ollama pull deepseek-r1:8b
ollama pull qwen3:14b
```

### Issue: Slow responses
**Solution:** 
- Check system resources (CPU/RAM)
- Reduce `--rounds` to test
- Run during off-peak hours

### Issue: Garbled text in output
**Solution:** Terminal encoding issue:
```bash
export PYTHONIOENCODING=utf-8
python llm_conversation.py
```

## Integration with Main System

This conversation engine integrates with your main Decision Guidance System:

- **Same LLM models** as system_main.py
- **Same runtime** (OllamaRuntime)
- **Saved to** `data/conversations/` (different from `data/sessions/`)
- **Can be called** from system_main.py for interactive dialogue testing

## Demo Conversation Topics

The demo mode includes preset conversation on:
```
"The future of intelligent decision systems"
```

Example flow:
1. User LLM introduces perspectives on AI decision systems
2. Program LLM responds with considerations
3. User LLM builds on those considerations
4. Program LLM synthesizes and adds new angles
5. User LLM reflects and concludes

## Next Steps

1. **Run demo:** `python llm_conversation.py --mode demo`
2. **Try interactive:** `python llm_conversation.py`
3. **Specific topic:** `python llm_conversation.py --mode topic --topic "your question"`
4. **Save conversations:** Review `data/conversations/` folder
5. **Analyze results:** Extract patterns and dialogue quality

---

**Status:** Ready to use ✅
**Requirements:** Ollama + deepseek-r1:8b + qwen3:14b
**Integration:** Works with existing LLM runtime
