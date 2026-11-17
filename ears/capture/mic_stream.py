"""
ears/capture/mic_stream.py — OPTIONAL desktop test harness.

Lets you test the whole self/other + fact-extraction pipeline using your
PC's own mic and Deepgram's streaming API, before building/wiring the
Android companion app. Not part of the always-on production path — that
runs on the phone.

Requires: pip install sounddevice deepgram-sdk
Requires: DEEPGRAM_API_KEY set in your environment.
"""
import asyncio
import queue
import sounddevice as sd
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions

from ears.config import DEEPGRAM_API_KEY, DEEPGRAM_MODEL, DEEPGRAM_LANGUAGE
from ears.privacy.redaction import filter_segments, summarize_context_only, get_conversation_transcript_for_llm
from ears.extraction.fact_extractor import extract_facts
from ears.memory_bridge.episodic_writer import write_episode

SAMPLE_RATE = 16000
audio_q: "queue.Queue[bytes]" = queue.Queue()


def _audio_callback(indata, frames, time_info, status):
    audio_q.put(bytes(indata))


async def run():
    if not DEEPGRAM_API_KEY:
        raise RuntimeError("Set DEEPGRAM_API_KEY in your environment first.")

    dg = DeepgramClient(DEEPGRAM_API_KEY)
    conn = dg.listen.live.v("1")
    batch = []

    def on_transcript(_, result, **kwargs):
        for alt in result.channel.alternatives:
            if not alt.transcript:
                continue
            words = alt.words or []
            speaker = str(words[0].speaker) if words else "0"
            batch.append({
                "speaker": speaker,
                "text": alt.transcript,
                "start": words[0].start if words else 0.0,
                "end": words[-1].end if words else 0.0,
            })

    conn.on(LiveTranscriptionEvents.Transcript, on_transcript)

    options = LiveOptions(
        model=DEEPGRAM_MODEL,
        language=DEEPGRAM_LANGUAGE,
        diarize=True,
        punctuate=True,
        filler_words=True,
        interim_results=False,
    )
    conn.start(options)

    stream = sd.RawInputStream(
        samplerate=SAMPLE_RATE, blocksize=8000, dtype="int16",
        channels=1, callback=_audio_callback,
    )

    print("Listening on desktop mic. Ctrl+C to stop and flush.")
    with stream:
        try:
            while True:
                chunk = audio_q.get()
                conn.send(chunk)
                await asyncio.sleep(0)
        except KeyboardInterrupt:
            pass

    conn.finish()

    allowed = filter_segments(batch)
    context_note = summarize_context_only(batch)
    conversation_transcript = get_conversation_transcript_for_llm(allowed)
    facts = extract_facts(conversation_transcript, context_note)
    for f in facts:
        write_episode(f)
    print(f"Wrote {len(facts)} episodes.")


if __name__ == "__main__":
    asyncio.run(run())
