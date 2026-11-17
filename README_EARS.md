# Ambient Sensory Memory Module — Setup

## What you got

```
ears/                       # Drop this folder into C:\era\ alongside persona/, ml/, hse/
├── config.py
├── daemon.py                # ← run this
├── requirements.txt
├── capture/
│   ├── android_bridge.py    # FastAPI backend the phone posts transcripts to
│   └── mic_stream.py        # OPTIONAL: test on your PC's own mic first
├── privacy/
│   ├── consent_state.py     # SOLO vs ANNOUNCED_RECORDING toggle
│   └── redaction.py         # The privacy gate — read this before anything else
├── extraction/
│   └── fact_extractor.py    # Calls your existing local Ollama model
└── memory_bridge/
    └── episodic_writer.py   # Writes into Memory/YYYY-MM-DD_episodes.jsonl

ears_mobile_reference/       # NOT a finished app — Kotlin starting point for
├── ForegroundMicService.kt  #   Android Studio. Needs real Deepgram WebSocket
└── AndroidManifest_snippet.xml  # wiring filled in (marked with TODOs).
```

## How the privacy model actually works

- **SOLO mode (default):** only speech diarized as you (`EARS_SELF_SPEAKER`) is ever transcribed, extracted, or written to disk. If someone else is talking near you, `redaction.py` drops their content before it reaches the fact extractor — the most it ever produces is a single non-identifying line like "you were in conversation with someone" for context.
- **ANNOUNCED_RECORDING mode:** you explicitly call `/consent/start_announced_recording` — meant for situations where you've told the people present that you're recording (e.g., a meeting you're running). Only then does other people's content get stored. Call `/consent/stop` the moment it's over; it's also the panic-button endpoint if you ever want capture off immediately.
- This split is enforced in one place (`redaction.py`) so it can't quietly get bypassed as you add features later.

## Setup on your PC (C:\era)

```bash
cd C:\era
# copy the ears/ folder in here
pip install -r ears\requirements.txt
```

Set environment variables (PowerShell example):
```powershell
$env:DEEPGRAM_API_KEY = "your-deepgram-key"
$env:ERA_ROOT = "C:\era"
```

Get a Deepgram key at https://console.deepgram.com — free tier covers a good amount of testing before you need to pay.

Run the backend:
```bash
python -m ears.daemon
```
This starts listening on `http://<your-pc-ip>:8787`. Find your PC's local IP with `ipconfig` (look for the IPv4 address on your Wi-Fi adapter) — the phone app needs this.

## Test without the phone first

```bash
python -m ears.capture.mic_stream
```
Talk into your PC mic for a bit, Ctrl+C, and check `Memory/<today>_episodes.jsonl` for new lines. This confirms diarization, the privacy gate, extraction, and writing all work before you touch Android at all.

## Identifying yourself each session

Deepgram's diarization returns speaker indices (0, 1, 2…) that reset each session — it doesn't know which one is "you" ahead of time. Simplest fix for now: start each session by saying a few sentences alone before anyone else is around, check which speaker index got assigned to that stretch, and set `EARS_SELF_SPEAKER` accordingly. A more robust version (voice-embedding enrollment) is a reasonable Phase 2 upgrade once diarization is proven out.

## Building the Android side

`ears_mobile_reference/` is a documented starting point, not a working app — I can't build or test Android code in this environment. Open Android Studio, create a new Kotlin project, drop these files in, and fill in the TODOs (mainly: wiring OkHttp's WebSocket client to Deepgram's streaming protocol). The foreground-service notification is Android's mandatory background-mic requirement, and it doubles as your consent indicator — there's no way to hide it, which is intentional here.

## Next steps

1. Get `mic_stream.py` working end-to-end on your PC.
2. Confirm episodes look right in your existing `Memory/*.jsonl` files and that your Ministers/PWM pick them up normally.
3. Build the Android foreground service against this backend.
4. Only then consider whether you ever want `ANNOUNCED_RECORDING` mode wired to an actual UI button — that one's worth sitting with for a bit rather than rushing.
