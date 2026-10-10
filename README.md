# Own Song Engine — Vocal Prototype 0.3

A lightweight procedural music generator with an experimental local vocal synthesizer plus an optional ACE-Step 1.5 neural-song adapter. The current Render service has no GPU model server configured; neural generation remains disabled until ACE_STEP_API_URL points to a reachable ACE-Step OpenRouter-compatible inference server.

## Current capabilities
- Mobile-friendly song studio
- Procedural chord bed, bass, lead melody and percussion
- Optional Telugu-script, English or mixed lyrics
- Experimental local synthesized vocal tones: Male, Female and Child profiles\n- Optional neural song generation through a separately hosted ACE-Step 1.5 server\n- Optional uploaded reference audio passed to the neural server
- Style, duration, tempo and deterministic variation seed controls
- WAV output and health endpoint at /health
- Docker/Render deployment

## Important quality boundary
This is a research prototype, **not a natural human-quality AI singer**. The vocal generator creates pitched harmonics shaped by approximate vowel formants and assigns lyric units to notes. It does not yet reliably pronounce complete words, model consonant transitions, sing expressive phonemes, or produce convincing child/female/male performances. Telugu syllabification is heuristic. The voice names refer only to synthesized pitch/formant presets, not recordings or real identities.

The user constraint is to develop the engine in-house without paid generation APIs or downloaded pretrained singing models. That constraint is respected. A natural neural singing model trained from scratch would require a substantial, properly licensed vocal dataset, a training pipeline, evaluation, and considerably more compute than a no-GPU free web service can provide. This code is a foundation and listening-test prototype, not a claim that the full natural-singing problem is solved.

## Run locally
Requires Python 3.11+.

~~~bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000
~~~

Open http://localhost:8000

## API
POST /api/generate accepts JSON fields:
- title: string
- language: Telugu, English or Telugu-English
- genre: Playful, Folk, Pop, Cinematic or Lullaby
- duration_seconds: 5–60
- bpm: 60–180
- seed: integer
- lyrics: optional string, up to 800 characters
- voice: Male, Female or Child

GET /health reports service health and implemented capabilities.

## Deployment and storage
The included Render Blueprint/Docker configuration can run on a free web-service tier when available. Free services may sleep, and generated audio is written to the container filesystem; files are not durable across restarts or redeploys. No persistent disk or external storage is configured.

## Next engineering milestones
1. Replace heuristic syllable splitting with Telugu akshara/phoneme segmentation and English grapheme-to-phoneme rules.
2. Add note editor, phrase timing, rests, pitch contour, harmony and instrument arrangement.
3. Improve source-filter synthesis with per-phoneme transitions, consonants, breath, vibrato and singer-specific controls.
4. Build an original training-data collection/consent workflow before attempting any from-scratch learned singing model.
5. Add objective and listening-based tests for pronunciation, pitch tracking, clipping, latency and intelligibility.


## Optional neural song mode (ACE-Step 1.5)

The studio now has a **Natural AI singing** mode and a backend endpoint at `POST /api/generate-ai`. This is an integration adapter, not a bundled model: Render's lightweight web container cannot host the model itself. To enable it, deploy an ACE-Step 1.5 server with its OpenRouter-compatible endpoint, then configure these Render environment variables:

- `ACE_STEP_API_URL`: base URL of your ACE-Step server (without `/v1/chat/completions`)
- `ACE_STEP_API_KEY`: optional bearer token if that server requires authentication
- `ACE_STEP_MODEL`: optional model identifier; defaults to `acestep/ACE-Step-v1.5`

The adapter sends lyrics, genre prompt, duration, tempo, language code, and—if uploaded—a reference WAV. It expects the ACE-Step OpenRouter-compatible response containing base64 audio. Do not set `ACE_STEP_API_URL` to an arbitrary website; it must be a server running the compatible API. The neural mode returns a clear setup error until configured. Telugu support and reference-melody fidelity must be tested on actual outputs; no model can be guaranteed to preserve an exact melody from a prompt alone.

Official project/API documentation:
- https://github.com/ace-step/ACE-Step-1.5
- https://github.com/ace-step/ACE-Step-1.5/blob/main/docs/en/Openrouter_API_DOC.md

This adapter does not itself provision or pay for GPU hosting. A hosted GPU endpoint may incur costs; verify its pricing before enabling it. The original local synthesizer remains available as a fallback.
