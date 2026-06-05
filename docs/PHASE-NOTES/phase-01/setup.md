# Setup — Phase 01

## Get a Google AI Studio API key

1. Open a browser and go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Sign in with a **personal Gmail account** (not a Google Workspace / corporate / school account — those have admin restrictions on API key creation)
3. Click **Create API key**
4. Name it something recognisable (e.g. `StockResearchAssistant`)
5. Leave "Choose an imported project" as-is — no Google Cloud project needed for the free tier
6. Click **Create key** and copy the key immediately

> If you see "You do not have permission to create a key in this project", you are signed into a Workspace account. Switch to a personal Gmail.

---

## Add the key to your project

```bash
cp .env.example .env
```

Open `.env` and add:

```
GOOGLE_API_KEY=your_key_here
```

Never commit `.env` — it is already in `.gitignore`.

---

## Verify the key works

```bash
python -c "
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.environ['GOOGLE_API_KEY'])
model = genai.GenerativeModel('gemini-2.0-flash')
response = model.generate_content('Say hello in one sentence.')
print(response.text)
"
```

Expected output: any one-sentence greeting. If you see an authentication error, double-check the key was copied correctly into `.env`.

---

## Free tier limits (as of 2026)

| Model | Requests/day | Requests/minute |
|---|---|---|
| Gemini 2.0 Flash | 1,500 | 15 |
| Gemini 1.5 Flash | 1,500 | 15 |

More than sufficient for the entire Phase 01 and 02 work.
