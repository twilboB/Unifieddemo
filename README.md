# Data Spine — Post-Campaign Intelligence

Streamlit app connecting to BigQuery for live media reporting, PCA decks,
weekly meeting briefs, and natural-language Q&A.

**Data source:** `res-apac-dev-skynet-au.resodigital_MelbUnified.all_clients_unified`
**LLM:** Gemini on Vertex AI (uses your gcloud login — no API key needed)

---

## Prerequisites (one-time)

1. **Python 3.10+** — https://www.python.org/downloads/
   (On Windows, tick *“Add Python to PATH”* in the installer.)
2. **Google Cloud CLI** — https://cloud.google.com/sdk/docs/install
3. **Log in for data + LLM access:**
   ```
   gcloud auth application-default login
   gcloud config set project res-apac-dev-skynet-au
   ```
   This stores credentials the app reads automatically
   (`%APPDATA%\gcloud\` on Windows, `~/.config/gcloud/` on macOS/Linux).

---

## Run

### Windows (PowerShell or Command Prompt)
```bat
cd path\to\unified-demo
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m streamlit run app.py
```

### macOS / Linux
```bash
cd path/to/unified-demo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The app opens at **http://localhost:8501**.

---

## Modes
- **Dashboard** — spend, taxonomy, and platform performance
- **Benchmarks** — client vs portfolio efficiency
- **Weekly Meet** — per-channel + per-campaign WIP brief with WoW and next-week actions
- **Ask a Question** — natural-language Q&A over the live data
- **Build PCA** — full post-campaign deck (PPTX + Excel)
- **Slide Generator** — quick slides from a prompt

> `OMD Template.pptx` must stay in the same folder as `app.py` — the
> PCA and Slide Generator use it as the branded template.
