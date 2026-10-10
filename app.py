from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pathlib import Path
import math, random, struct, wave, uuid, subprocess, json
from vocals import synthesize_vocal
from neural_provider import generate_with_acestep
import os

BASE = Path(__file__).resolve().parent
OUT = BASE / "generated"
OUT.mkdir(exist_ok=True)
MAX_REFERENCE_BYTES = 30 * 1024 * 1024
ALLOWED_REFERENCE_EXTENSIONS = {".mp4", ".mov", ".m4v", ".mp3", ".wav", ".m4a", ".aac", ".ogg", ".webm", ".flac"}
app = FastAPI(title="Own Song Engine", version="0.1.0")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")

class AISongRequest(BaseModel):
    title: str = Field(default="My AI Song", max_length=80)
    language: str = Field(default="Telugu", pattern="^(Telugu|English|Telugu-English)$")
    genre: str = Field(default="Playful", pattern="^(Playful|Folk|Pop|Cinematic|Lullaby)$")
    duration_seconds: int = Field(default=15, ge=10, le=60)
    bpm: int = Field(default=110, ge=60, le=180)
    lyrics: str = Field(default="", min_length=1, max_length=800)
    reference_id: str = Field(default="", max_length=64)

class SongRequest(BaseModel):
    title: str = Field(default="My First Song", max_length=80)
    language: str = Field(default="Telugu", pattern="^(Telugu|English|Telugu-English)$")
    genre: str = Field(default="Playful", pattern="^(Playful|Folk|Pop|Cinematic|Lullaby)$")
    duration_seconds: int = Field(default=15, ge=5, le=60)
    bpm: int = Field(default=110, ge=60, le=180)
    seed: int = Field(default=7, ge=0, le=999999)
    lyrics: str = Field(default="", max_length=800)
    voice: str = Field(default="Female", pattern="^(Male|Female|Child)$")

def envelope(t, duration):
    return min(1.0, t / 0.015) * min(1.0, max(0.0, (duration - t) / 0.06))

def tone(freq, t, kind="sine"):
    if freq <= 0: return 0.0
    if kind == "pluck":
        return (math.sin(2*math.pi*freq*t) + 0.22*math.sin(4*math.pi*freq*t)) * math.exp(-4.0*t)
    if kind == "warm":
        return 0.72*math.sin(2*math.pi*freq*t) + 0.2*math.sin(2*math.pi*freq*2*t) + 0.08*math.sin(2*math.pi*freq*3*t)
    return math.sin(2*math.pi*freq*t)

def make_song(path: Path, req: SongRequest):
    rng = random.Random(req.seed); sr = 22050; beat = 60.0 / req.bpm
    total = req.duration_seconds; frames = int(sr * total); audio = [0.0] * frames
    scales = {"Playful":[0,2,4,7,9,12,14],"Folk":[0,2,3,7,9,12,14],"Pop":[0,2,4,7,9,12,14],"Cinematic":[0,2,4,5,7,9,12],"Lullaby":[0,2,4,7,9,12,14]}
    scale = scales[req.genre]; root = 57 if req.genre == "Lullaby" else 60
    chords = [[0,2,4],[5,7,9],[3,5,7],[0,2,4]]; bar_len = beat * 4
    def add(start, dur, freq, amp, kind):
        begin=max(0,int(start*sr)); end=min(frames,int((start+dur)*sr))
        for i in range(begin,end):
            t=i/sr-start; audio[i] += amp*tone(freq,t,kind)*envelope(t,dur)
    for bar in range(math.ceil(total/bar_len)):
        start=bar*bar_len; chord=chords[bar%len(chords)]; bar_dur=min(bar_len,total-start)
        for deg in chord:
            midi=root+deg; freq=440*(2**((midi-69)/12)); add(start,bar_dur,freq,0.075,"warm")
        bass=440*(2**((root-12+chord[0]-69)/12))
        for b in range(4):
            t0=start+b*beat
            if t0<total: add(t0,min(beat*0.8,total-t0),bass,0.16,"pluck")
        for step in range(8):
            t0=start+step*beat/2
            if t0>=total or rng.random()<(0.12 if req.genre=="Lullaby" else 0.08): continue
            midi=root+12+rng.choice(scale)+(12 if rng.random()<0.18 else 0)
            freq=440*(2**((midi-69)/12)); dur=min(beat*rng.choice([0.28,0.42,0.7]),total-t0)
            add(t0,dur,freq,0.13,"pluck")
        for b in range(4):
            t0=start+b*beat
            if t0>=total: continue
            dur=min(0.12 if b in (0,2) else 0.035,total-t0)
            begin=int(t0*sr); end=min(frames,int((t0+dur)*sr))
            for i in range(begin,end):
                t=i/sr-t0
                if b in (0,2):
                    f=95-45*min(1,t/max(dur,0.001)); audio[i]+=0.17*math.sin(2*math.pi*f*t)*math.exp(-22*t)
                else: audio[i]+=(rng.random()*2-1)*0.025*math.exp(-90*t)
    vocal_info = synthesize_vocal(audio, sr, total, req.bpm, req.lyrics, req.language, req.voice, req.seed)
    peak=max(max(abs(x) for x in audio),1e-9); factor=0.88/peak
    with wave.open(str(path),"wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        chunk=bytearray()
        for x in audio: chunk.extend(struct.pack("<h",int(max(-1,min(1,x*factor))*32767)))
        wf.writeframes(chunk)
    return vocal_info

@app.get("/",response_class=HTMLResponse)
def home(): return (BASE/"static"/"index.html").read_text(encoding="utf-8")

@app.get("/health")
def health():
    return {"status":"ok","engine":"own-song-engine","version":"0.3.0","neural_provider_configured":bool(os.getenv("ACE_STEP_API_URL")),"capabilities":["procedural instrumental composition","experimental formant-based vocal synthesis","optional ACE-Step neural song generation when configured"]}

@app.post("/api/reference")
async def upload_reference(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_REFERENCE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Upload an audio/video file: MP4, MOV, MP3, WAV, M4A, AAC, OGG, WEBM or FLAC.")
    data = await file.read(MAX_REFERENCE_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(data) > MAX_REFERENCE_BYTES:
        raise HTTPException(status_code=413, detail="Maximum upload size is 30 MB.")
    source_id = uuid.uuid4().hex
    source_path = OUT / f"{source_id}{suffix}"
    audio_path = OUT / f"{source_id}_reference.wav"
    source_path.write_bytes(data)
    try:
        proc = subprocess.run(
            ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
             "-i", str(source_path), "-vn", "-ac", "1", "-ar", "22050",
             "-t", "180", "-c:a", "pcm_s16le", str(audio_path)],
            capture_output=True, text=True, timeout=90
        )
        if proc.returncode != 0 or not audio_path.exists() or audio_path.stat().st_size < 44:
            raise HTTPException(status_code=400, detail="Could not extract audio. Please try a file containing an audio track.")
        with wave.open(str(audio_path), "rb") as wf:
            duration = round(wf.getnframes() / wf.getframerate(), 2)
        return {
            "reference_id": source_id,
            "filename": Path(file.filename or "reference").name,
            "duration_seconds": duration,
            "audio_url": f"/audio-reference/{source_id}",
            "status": "uploaded_audio_extracted",
            "message": "Reference audio extracted successfully. This build can preview the reference; automatic melody matching and Telugu vocal replacement are not yet connected to generation."
        }
    except HTTPException:
        raise
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Audio extraction timed out. Try a shorter file.")
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Audio conversion is unavailable on the server.")
    finally:
        try: source_path.unlink(missing_ok=True)
        except Exception: pass

@app.get("/audio-reference/{reference_id}")
def reference_audio(reference_id: str):
    if not reference_id.isalnum():
        raise HTTPException(status_code=404, detail="Reference audio not found")
    path = OUT / f"{reference_id}_reference.wav"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Reference audio not found")
    return FileResponse(path, media_type="audio/wav", filename="reference-audio.wav")

@app.post("/api/generate-ai")
def generate_ai(req: AISongRequest):
    """Generate a neural song through an optional ACE-Step 1.5 server."""
    ref_path = None
    if req.reference_id:
        if not req.reference_id.isalnum():
            raise HTTPException(status_code=400, detail="Invalid reference ID.")
        candidate = OUT / f"{req.reference_id}_reference.wav"
        if not candidate.exists():
            raise HTTPException(status_code=404, detail="Reference audio expired or not found. Upload it again.")
        ref_path = candidate
    prompt = {
        "Playful": "Playful, catchy, bright family-friendly pop with lively percussion and memorable hook",
        "Folk": "Contemporary Telugu folk-pop, rhythmic hand percussion, acoustic strings and lively groove",
        "Pop": "Polished contemporary pop, strong chorus, punchy drums, melodic bass and bright synths",
        "Cinematic": "Cinematic Indian pop, emotional build, rich orchestration and dramatic percussion",
        "Lullaby": "Gentle soothing lullaby, soft piano, warm strings and delicate percussion"
    }[req.genre]
    mp3_path = OUT / f"{uuid.uuid4().hex}.mp3"
    wav_path = OUT / f"{mp3_path.stem}.wav"
    try:
        mp3_data = generate_with_acestep(
            prompt=prompt, lyrics=req.lyrics, language=req.language,
            duration=req.duration_seconds, bpm=req.bpm, reference_path=ref_path
        )
        mp3_path.write_bytes(mp3_data)
        proc = subprocess.run(
            ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
             "-i", str(mp3_path), "-ac", "1", "-ar", "22050", "-c:a", "pcm_s16le", str(wav_path)],
            capture_output=True, text=True, timeout=90
        )
        if proc.returncode != 0 or not wav_path.exists() or wav_path.stat().st_size < 44:
            raise RuntimeError("Could not convert AI-generated audio to WAV.")
    except Exception as exc:
        mp3_path.unlink(missing_ok=True)
        wav_path.unlink(missing_ok=True)
        msg = str(exc)
        code = 503 if "not configured" in msg.lower() else 502
        raise HTTPException(status_code=code, detail=msg)
    finally:
        mp3_path.unlink(missing_ok=True)
    return {
        "title": req.title, "language": req.language, "genre": req.genre,
        "duration_seconds": req.duration_seconds, "format": "WAV",
        "engine": "ACE-Step 1.5 neural generation", "lyrics_supplied": True,
        "note": "Neural song generated through your configured ACE-Step server. Telugu pronunciation and melody adherence should be checked by listening.",
        "audio_url": f"/audio/{wav_path.name}"
    }

@app.post("/api/generate")
def generate(req: SongRequest):
    filename=f"{uuid.uuid4().hex}.wav"; target=OUT/filename
    try: vocal_info = make_song(target,req)
    except Exception as exc: raise HTTPException(status_code=500,detail=f"Audio generation failed: {exc}")
    return {"title":req.title,"language":req.language,"genre":req.genre,"duration_seconds":req.duration_seconds,"format":"WAV","voice":req.voice if req.lyrics.strip() else None,"lyrics_supplied":bool(req.lyrics.strip()),"vocal_syllables":vocal_info["syllables"],"note":"Original procedural music. If lyrics were supplied, vocals use experimental formant synthesis; pronunciation and naturalness are not human-quality yet.","audio_url":f"/audio/{filename}"}

@app.get("/audio/{filename}")
def audio(filename:str):
    if Path(filename).name!=filename or not filename.endswith(".wav"): raise HTTPException(status_code=404,detail="Audio not found")
    path=OUT/filename
    if not path.exists(): raise HTTPException(status_code=404,detail="Audio not found")
    return FileResponse(path,media_type="audio/wav",filename=filename)
