# Own Song Engine — MVP 0.1

A small web app that generates original procedural instrumental music without paid music-generation APIs or pretrained model weights.

## Current capability
- Mobile-friendly web interface
- Code-generated melody, chord bed, bass and simple percussion
- WAV output
- Configurable style, duration, tempo and random seed
- Health endpoint at `/health`

## Important limitation
This is an instrumental synthesizer, **not a natural singing model**. It does not sing Telugu or English lyrics and does not yet provide male, female or child vocals. Building neural singing from scratch requires appropriately licensed training data, a training pipeline, compute time and listening tests.

## Run locally
Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000

## Deploy
This repository includes a Dockerfile and Render Blueprint configuration. Free hosting availability and sleep/storage limits depend on the host's current terms. Generated WAV files are temporary and may be lost on restart because this prototype has no persistent storage.

## Roadmap
1. Add a melody and arrangement editor.
2. Build a phoneme-aware Telugu and English lyrics pipeline.
3. Implement a from-scratch singing model and training code.
4. Acquire or record training data with proper permissions and consent.
5. Benchmark intelligibility, naturalness, pronunciation and generation speed.
6. Deploy neural inference only when it fits the selected host's memory and CPU limits.
