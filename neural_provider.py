"""Optional ACE-Step 1.5 remote inference adapter.

Set ACE_STEP_API_URL to the base URL of a self-hosted ACE-Step OpenRouter-compatible
server (the server exposing POST /v1/chat/completions). This module never calls a
provider unless that environment variable is configured.
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
            "Natural AI singing is not configured yet. Set ACE_STEP_API_URL to an "
            "ACE-Step 1.5 inference server URL. The current Render app has no GPU model server."
        )
    api_key = os.getenv("ACE_STEP_API_KEY", "").strip()
    lang = {"Telugu": "te", "English": "en", "Telugu-English": "te"}.get(language, "te")
    content = [
        {"type": "text", "text": (
            f"<prompt>{prompt}. Full song with clear, melodic human-like lead singing, "
            f"natural phrasing, intelligible {language} pronunciation, warm professional "
            f"mix, rhythmically aligned lyrics. Tempo {bpm} BPM.</prompt>\n"
            f"<lyrics>{lyrics}</lyrics>"
        )}
    ]
    if reference_path and reference_path.exists():
        raw = base64.b64encode(reference_path.read_bytes()).decode("ascii")
        content.append({
            "type": "input_audio",
            "input_audio": {"data": raw, "format": "wav"}
        })
        content[0]["text"] += (
            " Use the supplied audio as a melody/arrangement reference where supported; "
            "create a cover-like Telugu vocal replacement, not a verbatim copy of a recording."
        )
    payload = {
        "model": os.getenv("ACE_STEP_MODEL", "acestep/ACE-Step-v1.5"),
        "messages": [{"role": "user", "content": content}],
        "stream": False,
        "thinking": True,
        "use_format": False,
        "audio_config": {
            "duration": max(10, min(60, duration)),
            "bpm": bpm,
            "format": "mp3",
            "vocal_language": lang
        }
    }
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
