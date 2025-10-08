# AI Environmental Report (OpenAQ)

Interactive, AI-native tool that fetches air-quality data from OpenAQ, computes KPIs, plots charts, and auto-writes a brief environmental assessment.

## Run (CLI)
```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt

python main.py  # uses config.example.yaml
