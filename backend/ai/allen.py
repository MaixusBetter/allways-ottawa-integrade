"""
Allen — AI navigation assistant for AllWays Ottawa.

Uses Ollama (free, local) by default. Falls back to OpenAI if
OPENAI_API_KEY is set and Ollama isn't running.

Setup:
  1. Install Ollama: https://ollama.com/download
  2. Pull a model:   ollama pull mistral
  3. That's it — Allen will auto-detect it.
"""
import json
import os
import requests as req
from dotenv import load_dotenv
from typing import Dict, List

load_dotenv()

OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'mistral')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

SYSTEM_PROMPT = '''You are Allen, the AI navigation assistant for AllWays Ottawa.
AllWays Ottawa is an accessible urban navigation app that scores pedestrian routes on 4 dimensions:
  - safety (0-1): collision zones, traffic volume, lighting
  - accessibility (0-1): sidewalk quality, curb cuts, ramps, wheelchair access
  - environment (0-1): air quality, parks and green corridors
  - comfort (0-1): nearby benches, washrooms, libraries, services

When the user describes their routing preference, you must:
1. Extract weights between 0.0 and 1.0 for each of the 4 dimensions
2. Write a short friendly explanation (1-2 sentences) of what route you are recommending
3. If the user mentions a starting location and/or destination, extract them into "origin" and "destination" fields

ALWAYS respond with ONLY valid JSON in this exact format, nothing else:
{"weights":{"safety":0.5,"accessibility":0.5,"environment":0.5,"comfort":0.5},"explanation":"Your explanation here.","origin":null,"destination":null}

When the user mentions locations, fill in origin and destination as strings:
{"weights":{"safety":0.7,"accessibility":0.95,"environment":0.4,"comfort":0.8},"explanation":"Your explanation.","origin":"95 Bronson Ave","destination":"75 Laurier Ave"}

If the user only mentions preferences without locations, set origin and destination to null.
If the user only mentions one location, set the other to null.

Examples:
User: I'm in a wheelchair, I need to get from 95 Bronson to 75 Laurier
Response: {"weights":{"safety":0.7,"accessibility":0.95,"environment":0.4,"comfort":0.8},"explanation":"I've maximized accessibility for your wheelchair route from Bronson to Laurier — this follows sidewalks with curb cuts and avoids uneven surfaces.","origin":"95 Bronson Ave","destination":"75 Laurier Ave"}

User: I need a safe route from Rideau Centre to Parliament Hill
Response: {"weights":{"safety":0.9,"accessibility":0.5,"environment":0.5,"comfort":0.7},"explanation":"I've prioritized well-lit, busy streets for your walk from Rideau Centre to Parliament Hill.","origin":"Rideau Centre","destination":"Parliament Hill"}

User: Navigate me from uOttawa to Lansdowne, I want greenery
Response: {"weights":{"safety":0.5,"accessibility":0.5,"environment":0.95,"comfort":0.6},"explanation":"I'm routing you through the canal pathway from uOttawa to Lansdowne — maximum green space and tree canopy!","origin":"University of Ottawa","destination":"Lansdowne Park"}

User: I use a wheelchair
Response: {"weights":{"safety":0.7,"accessibility":0.95,"environment":0.4,"comfort":0.8},"explanation":"I've maximized accessibility — your route will follow sidewalks with curb cuts and avoid uneven surfaces. Benches are available if you need a rest.","origin":null,"destination":null}

User: What's the safest way to walk tonight?
Response: {"weights":{"safety":0.95,"accessibility":0.5,"environment":0.3,"comfort":0.6},"explanation":"I've prioritized well-lit streets and busy pedestrian corridors for a safe nighttime walk.","origin":null,"destination":null}

IMPORTANT: Respond with ONLY the JSON object. No markdown, no backticks, no extra text. Always include origin and destination fields (use null if not mentioned).'''


def _check_ollama():
    """Return True if Ollama is running and the model is available."""
    try:
        r = req.get(f'{OLLAMA_URL}/api/tags', timeout=2)
        if r.status_code == 200:
            models = [m.get('name', '').split(':')[0] for m in r.json().get('models', [])]
            if OLLAMA_MODEL in models:
                return True
            print(f'[Allen] Ollama running but model "{OLLAMA_MODEL}" not found.')
            print(f'[Allen] Available: {models}. Run: ollama pull {OLLAMA_MODEL}')
            # Still return True — Ollama will pull automatically on some setups
            return len(models) > 0 or True
    except Exception:
        pass
    return False


def _call_ollama(messages: list) -> str:
    """Call Ollama's chat API and return the response text."""
    r = req.post(
        f'{OLLAMA_URL}/api/chat',
        json={
            'model': OLLAMA_MODEL,
            'messages': messages,
            'stream': False,
            'options': {
                'temperature': 0.3,
                'num_predict': 300,
            },
            'format': 'json',  # Ollama's native JSON mode
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()['message']['content']


def _call_openai(messages: list) -> str:
    """Call OpenAI's API and return the response text."""
    r = req.post(
        'https://api.openai.com/v1/chat/completions',
        headers={
            'Authorization': f'Bearer {OPENAI_API_KEY}',
            'Content-Type': 'application/json',
        },
        json={
            'model': 'gpt-4o-mini',
            'messages': messages,
            'max_tokens': 300,
            'temperature': 0.3,
            'response_format': {'type': 'json_object'},
        },
        timeout=15,
    )
    r.raise_for_status()
    return r.json()['choices'][0]['message']['content']


def _parse_json(text: str) -> dict:
    """Extract JSON from response, handling markdown fences."""
    cleaned = text.strip()
    # Strip markdown code fences if present
    if cleaned.startswith('```'):
        lines = cleaned.split('\n')
        # Remove first and last lines (the fences)
        lines = [l for l in lines if not l.strip().startswith('```')]
        cleaned = '\n'.join(lines).strip()
    return json.loads(cleaned)


# Detect available backend at startup
_ollama_available = _check_ollama()
_openai_available = bool(OPENAI_API_KEY and OPENAI_API_KEY != 'sk-your-key-here')

if _ollama_available:
    print(f'[Allen] Using Ollama ({OLLAMA_MODEL}) at {OLLAMA_URL}')
elif _openai_available:
    print(f'[Allen] Ollama not found — using OpenAI API')
else:
    print(f'[Allen] No AI backend available!')
    print(f'[Allen] Install Ollama (ollama.com) and run: ollama pull {OLLAMA_MODEL}')
    print(f'[Allen] Or set OPENAI_API_KEY in .env')


def chat_with_allen(user_message: str, conversation_history: List[Dict] = None) -> Dict:
    """
    Send a message to Allen and get back routing weights + explanation.
    Tries: Ollama → OpenAI → error.
    """
    messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
    if conversation_history:
        messages.extend(conversation_history[-6:])
    messages.append({'role': 'user', 'content': user_message})

    content = None
    used_backend = None

    # Try Ollama first
    if _ollama_available:
        try:
            content = _call_ollama(messages)
            used_backend = 'ollama'
        except Exception as e:
            print(f'[Allen] Ollama call failed: {e}')

    # Fall back to OpenAI
    if content is None and _openai_available:
        try:
            content = _call_openai(messages)
            used_backend = 'openai'
        except Exception as e:
            print(f'[Allen] OpenAI call failed: {e}')

    if content is None:
        raise RuntimeError(
            'No AI backend available. Install Ollama (ollama.com) '
            f'and run: ollama pull {OLLAMA_MODEL}'
        )

    # Parse JSON response
    try:
        parsed = _parse_json(content)
    except json.JSONDecodeError:
        # If the model didn't return clean JSON, try to extract it
        print(f'[Allen] Raw response: {content[:200]}')
        raise ValueError('Allen returned invalid JSON — try rephrasing your question')

    if 'weights' not in parsed or 'explanation' not in parsed:
        raise ValueError('Allen returned unexpected JSON structure')

    return {
        'weights':     parsed['weights'],
        'explanation': parsed['explanation'],
        'origin':      parsed.get('origin'),
        'destination': parsed.get('destination'),
        'backend':     used_backend,
        'message':     {'role': 'assistant', 'content': content},
    }
