# Own Song Engine: End-to-End Video, Voice and Song Pipeline
Research date: 2026-10-10

## Goal
Turn one prompt into a polished short video with consistent stylized 3D characters, Telugu and English dialogue, original Telugu and English singing, synchronized motion/audio, automated checks and an MP4 export.

## Production stages
1. **Intent compiler:** parse idea, audience, duration, aspect ratio, visual style, language per line, music mood, characters and ending into structured project data.
2. **Script and storyboard:** create a hook, setup, action, payoff; split into timed shots; write dialogue and lyrics; specify camera, lighting, gestures, sound cues and subtitle timings.
3. **Character/world bible:** save reusable character references, proportions, colour palette, accessories, facial expressions, movement style, voice profile and environment rules.
4. **Visual production:** either use prompt/reference-conditioned video generation (fast, but continuity and precise actions can vary) or Blender with rigged 3D assets (more controllable, but needs assets, rigging and render time).
5. **Speech:** use a dedicated Telugu TTS and English TTS path. TTS is spoken voice, not singing. Benchmark pronunciation, prosody, pauses and emotional delivery separately. AI4Bharat Indic-TTS is a Telugu research candidate: https://github.com/AI4Bharat/Indic-TTS
6. **Song generation:** use a lyric-conditioned music model that creates a vocal performance, melody, accompaniment and mix. ACE-Step 1.5 is a candidate; it documents lyrics, BPM, duration, vocal-language metadata and CPU inference. CPU is much slower than GPU, and language claims must be verified with actual Telugu samples. References: https://github.com/ace-step/ACE-Step-1.5 and https://ace-step.github.io/ACE-Step-1.5/en/INFERENCE
7. **Sound design/mix:** create separate dialogue, song, ambience and SFX tracks; align effects to visible events; normalize loudness, add fades, detect clipping/silence and mix with FFmpeg.
8. **Synchronization:** keep a master timeline for shots, dialogue, lyrics, beats, SFX and subtitles. Speech lip sync can use phoneme/viseme alignment. Singing lip sync is harder; prefer native audio-video generation or a dedicated animation stage if exact mouth movement matters.
9. **Quality gate:** check story payoff, character continuity, visual artifacts, Telugu/English intelligibility, whether vocals sound sung rather than robotic, clipping, silence, sync, duration, aspect ratio and license terms. Allow targeted regeneration of failed segments.
10. **Export:** mux video/audio/subtitles with FFmpeg, create mobile-ready MP4 and store the model/version, prompts and test report.

## Architecture for this project
Keep Render as a lightweight control plane for prompt editing, job state, uploads, configuration, progress and final assembly. Generation should be separate optional providers:
- visual provider: image/video generation or Blender render worker;
- speech provider: Telugu/English TTS;
- music provider: ACE-Step or another explicitly chosen model;
- alignment provider: subtitles, lyric timestamps and lip-sync cues;
- quality gate: technical checks and human listening review.

Each provider should report supported languages, formats, version, resource needs, license, latency and whether it calls an external service. Never silently route to a paid API.

## Cost and compute realities
- The web app can remain GPU-free; that does not make large-model inference free.
- Open-source weights avoid per-call API fees but still require CPU/RAM/disk and generation time.
- ACE-Step has CPU inference, but a small free Render web instance is not a sensible place to host its full model stack.
- Large video models such as Wan are also too heavy for the current lightweight Render instance.
- Free notebooks/spaces may sleep, queue jobs or impose limits; not a reliable production SLA.
- Grok app access is not the same as API access. The public xAI API lists video generation priced per output second. Do not automate the app or assume app access permits free API calls.
Official pricing/capability references: https://docs.x.ai/developers/models/grok-imagine-video, https://docs.x.ai/developers/models/grok-imagine-video-1.5, https://docs.x.ai/developers/pricing

## Benchmark pack
Test and keep outputs for:
1. 10-second Telugu children's song.
2. 10-second English children's song.
3. Emotional Telugu spoken line.
4. Emotional English spoken line.
5. 10-second 3D animal comedy with a clear payoff.
6. Dialogue scene with visible mouth movement.

For every output record exact prompt/model version, generation time, peak RAM/disk, file size, pronunciation/intelligibility ratings from a fluent speaker, vocal naturalness, melody adherence, visual consistency, motion coherence, sync and commercial license status. Use a 1–5 human rating. README claims do not substitute for listening tests.

## Recommended build order
1. Audit and correct the existing ACE-Step adapter against the official inference API; current OpenRouter-style payload has not been proven compatible.
2. Add a backend status screen that says whether a model is configured and reachable.
3. Benchmark music generation outside Render on a CPU machine with enough resources, without creating a paid service.
4. Benchmark Telugu and English speech separately.
5. Test video generation independently; do not bundle all heavy model dependencies into Render.
6. Build job orchestration, master timeline and FFmpeg assembly.
7. Add continuity and synchronization quality gates.
8. Only then automate the full prompt-to-MP4 process.

## Current status
The existing app is a lightweight procedural instrument/vocal prototype with an optional neural adapter. The adapter is not a model, and natural Telugu/English singing has not been validated. Keep Render lightweight until a real backend passes the benchmark.
