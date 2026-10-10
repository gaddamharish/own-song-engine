"""Optional ACE-Step 1.5 inference adapter.

Configure ACE_STEP_API_URL with a reachable self-hosted ACE-Step OpenRouter-compatible
server. No external service is contacted unless an endpoint is explicitly configured.
"""
import base64
import json
import os
import urllib.request
import urllib.error
from pathlib import Path

def generate_with_acestep(*, prompt: str, lyrics: str, language: str, duration: int,
                          bpm: int, reference_path: Path | None = None) -> bytes:
    base_url = os.getenv("ACE_STEP_API_URL", "").strip().rstrip("/")
    if not base_url:
        raise RuntimeError(
            "Natural AI singing is not configured. A reachable ACE-Step 1.5 inference "
            "server is required; this lightweight Render app does not host the model."
        )
    api_key = os.getenv("ACE_STEP_API_KEY", "").strip()
    lang = {"Telugu": "te", "English": "en", "Telugu-English": "te"}.get(language, "te")
    content = [{"type": "text", "text": (
        f"<prompt>{prompt}. Natural melodic lead singing, clear diction, expressive "
        f"phrasing, polished mix, tempo {bpm} BPM. Sing the supplied lyrics in {language}.</prompt>"
    )}]
    payload = {
        "model": os.getenv("ACE_STEP_MODEL", "acemusic/acestep-v15-turbo"),
        "messages": [{"role": "user", "content": content}],
        "lyrics": lyrics,
        "stream": False,
        "thinking": True,
        "use_format": False,
        "audio_config": {
            "duration": max(10, min(60, duration)),
            "bpm": bpm,
            "format": "mp3",
            "vocal_language": lang,
            "instrumental": False
        }
    }
    if reference_path and reference_path.exists():
        raw = base64.b64encode(reference_path.read_bytes()).decode("ascii")
        content.append({
            "type": "input_audio",
            "input_audio": {"data": raw, "format": "wav"}
        })
        payload["task_type"] = "cover"
        payload["audio_cover_strength"] = 0.75
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = "Bearer " + api_key
    req = urllib.request.Request(
        base_url + "/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"ACE-Step server returned HTTP {exc.code}: {detail}") from exc
    choices = result.get("choices") or []
    if not choices:
        raise RuntimeError("ACE-Step server returned no music result.")
    audio_items = (choices[0].get("message") or {}).get("audio") or []
    if not audio_items:
        raise RuntimeError("ACE-Step response contained no audio. Check server model/API mode.")
    audio_url = (audio_items[0].get("audio_url") or {}).get("url", "")
    if not audio_url.startswith("data:audio/") or "," not in audio_url:
        raise RuntimeError("ACE-Step returned an unsupported audio URL format.")
    return base64.b64decode(audio_url.split(",", 1)[1])
