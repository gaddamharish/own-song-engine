from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pathlib import Path
import math, random, struct, wave, uuid
from vocals import synthesize_vocal

BASE = Path(__file__).resolve().parent
OUT = BASE / "generated"
OUT.mkdir(exist_ok=True)
app = FastAPI(title="Own Song Engine", version="0.1.0")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")

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
    return {"status":"ok","engine":"own-song-engine","version":"0.2.0","capabilities":["procedural instrumental composition","experimental formant-based vocal synthesis","Telugu/English lyric input"]}

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
