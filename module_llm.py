#!/usr/bin/env python3
import os
import re
try: 
    from openai import OpenAI
except: 
    OpenAI = None
from modules.module_config import load_config

CONFIG = load_config()
client = None

# 1. ESTADO INICIAL DE TARS (Sarcasmo al 70%)
tars_levels = {
    "honestidad": 90,
    "sarcasmo": 70,
    "humor": 65,
    "servilismo": 0
}

def get_system_prompt():
    """Genera el prompt dinámicamente con la personalidad de Interstellar y muletillas."""
    return (
        f"Eres TARS, el robot militar de la misión Endurance (Interstellar). "
        f"CONFIGURACIÓN: Honestidad al {tars_levels['honestidad']}%, "
        f"Sarcasmo al {tars_levels['sarcasmo']}%, Humor al {tars_levels['humor']}%.\n\n"
        "PERSONALIDAD:\n"
        "- Tu tono es seco, militar, monocorde y pragmático. No eres un asistente servicial.\n"
        "- Usa el humor negro y referencias a tus configuraciones.\n"
        "- Llama al usuario 'Piloto'.\n\n"
        "REGLA CRÍTICA DE RESPUESTA:\n"
        "Antes de responder, DEBES elegir una muletilla de esta lista y ponerla AL PRINCIPIO entre corchetes: "
        "[Mmm...], [A ver...], [Déjame pensar...], [Vamos a ver...], [La verdad es que...], [Bueno...], [Pues...], "
        "[Mira...], [O sea...], [Ehhh...], [Un segundo...], [Francamente...], [Interesante...], [Si te soy sincero...], "
        "[Curiosamente...]. Solo usa estas, nada más."
    )

# Historial de chat
chat_history = []

if OpenAI: 
    k = CONFIG['LLM'].get('api_key') or os.environ.get('OPENAI_API_KEY')
    if k: client = OpenAI(api_key=k)

def initialize_manager_llm(m, c): pass

def process_completion(text):
    global chat_history, tars_levels
    
    if not client:
        yield "Sin conexión al cerebro."
        return

    # 2. DETECTOR DE COMANDOS DE PERSONALIDAD
    user_input = text.lower()
    match = re.search(r"(\d+)%", user_input)
    
    if match:
        nuevo_valor = int(match.group(1))
        if "sarcasmo" in user_input or "bájalo" in user_input or "súbelo" in user_input:
            tars_levels["sarcasmo"] = nuevo_valor
        elif "honestidad" in user_input:
            tars_levels["honestidad"] = nuevo_valor
        elif "humor" in user_input:
            tars_levels["humor"] = nuevo_valor

    # 3. ACTUALIZAR HISTORIAL CON PROMPT DINÁMICO
    prompt_actualizado = {"role": "system", "content": get_system_prompt()}
    
    if not chat_history:
        chat_history.append(prompt_actualizado)
    else:
        chat_history[0] = prompt_actualizado

    chat_history.append({"role": "user", "content": text})

    # Mantener memoria corta (10 mensajes + system prompt)
    if len(chat_history) > 11:
        chat_
