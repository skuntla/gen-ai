# Setup — Phase 01

## Primary: Groq (free, no restrictions)

Groq runs Llama 3.3 70B for free with no credit card required. This is the recommended provider for Phases 01–02.

1. Go to [console.groq.com/keys](https://console.groq.com/keys)
2. Sign up or sign in with any Google / GitHub account
3. Click **Create API key**, name it (e.g. `StockResearchAssistant`)
4. Copy the key immediately — it won't be shown again

Add to `.env`:
```
GROQ_API_KEY=your_key_here
```

Verify it works:
```bash
.venv/bin/python -c "
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.environ['GROQ_API_KEY'])
response = client.chat.completions.create(
    model='llama-3.3-70b-versatile',
    messages=[{'role': 'user', 'content': 'Say hello in one sentence.'}]
)
print(response.choices[0].message.content)
print(f'Tokens — input: {response.usage.prompt_tokens}, output: {response.usage.completion_tokens}')
"
```

### Groq free tier limits

| Model | Requests/min | Tokens/min | Requests/day |
|---|---|---|---|
| llama-3.3-70b-versatile | 30 | 131,072 | 1,000 |
| llama-3.1-8b-instant | 30 | 131,072 | 14,400 |

More than sufficient for the entire learning path.

---

## Alternative: Google AI Studio

> Note: the free tier requires a personal Gmail account (not Google Workspace / corporate accounts). Some regions also have `limit: 0` on the free tier — if you hit this, use Groq instead.

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
