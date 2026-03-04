#!/usr/bin/env python3
import os
import re
import asyncio
import random
import subprocess
from modules.module_config import load_config
from modules.module_messageQue import queue_message
from modules.module_llm import process_completion
from modules.module_tts import play_audio_chunks
import modules.tars_status as status 

CONFIG = load_config()

# === DICCIONARIO DE MAPEO CONTEXTUAL ===
# Mapea el texto exacto que enviará OpenAI con tus archivos MP3 locales
MAPPING_MULETILLAS = {
    "Mmm...": "m_01.mp3",
    "A ver...": "m_02.mp3",
    "Déjame pensar...": "m_03.mp3",
    "Vamos a ver...": "m_04.mp3",
    "La verdad es que...": "m_05.mp3",
    "Bueno...": "m_06.mp3",
    "Pues...": "m_07.mp3",
    "Mira...": "m_08.mp3",
    "O sea...": "m_09.mp3",
    "Ehhh...": "m_10.mp3",
    "Un segundo...": "m_11.mp3",
    "Francamente...": "m_12.mp3",
    "Interesante...": "m_13.mp3",
    "Si te soy sincero...": "m_14.mp3",
    "Curiosamente...": "m_15.mp3"
}

# Variables Globales
ui_manager = None
stt_manager = None

def initialize_managers(mem_mgr, char_mgr, stt_mgr, ui_mgr, shutdown_evt, batt_mod):
    global ui_manager, stt_manager
    ui_manager = ui_mgr
    stt_manager = stt_mgr
    queue_message("SYSTEM: Managers initialized (Contextual Mode).")

def reproducir_muletilla_por_nombre(texto_muletilla):
    """Busca y reproduce el archivo MP3 que coincide con el texto enviado por el LLM."""
    archivo_mp3 = MAPPING_MULETILLAS.get(texto_muletilla)
    if not archivo_mp3:
        return

    ruta_completa = os.path.join("/home/javiersg/TARS-AI/src/assets/muletillas", archivo_mp3)
    
    if os.path.exists(ruta_completa):
        try:
            # Reproducción en segundo plano para no bloquear el inicio del TTS real
            subprocess.Popen(
                ["mpg123", "-q", ruta_completa],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            queue_message(f"Error hardware muletilla: {e}")

def wake_word_callback(wake_response="¿Sí?"):
    """Respuesta inmediata al detectar 'TARS'"""
    if status.is_speaking: return
    
    if ui_manager:
        ui_manager.deactivate_screensaver()
        ui_manager.update_data("TARS", wake_response, "TARS")
    
    status.is_speaking = True
    try:
        asyncio.run(play_audio_chunks(wake_response, "edge", True))
    finally:
        status.is_speaking = False

def utterance_callback(message):
    """
    Procesado Contextual: 
    1. Envía a OpenAI -> 2. Recibe muletilla + respuesta -> 3. Suena muletilla local -> 4. Habla respuesta.
    """
    if not message or status.is_speaking:
        return

    user_text = str(message)
    if ui_manager:
        ui_manager.update_data("USER", user_text, "USER")
    
    queue_message(f"USER: {user_text}")

    # 1. COMANDO DE APAGADO
    cmd = user_text.lower()
    if "apágate" in cmd and "tars" in cmd:
        asyncio.run(play_audio_chunks("Entendido. Cerrando sistemas.", "edge"))
        os.system("sudo shutdown -h now")
        return

    try:
        # Bloqueamos el micrófono
        status.is_speaking = True
        
        # 2. GENERAR RESPUESTA (Aquí se produce la pequeña espera de red)
        respuesta_gen = process_completion(user_text)
        full_reply = "".join(list(respuesta_gen))
        
        # Limpieza de etiquetas de pensamiento internas si las hubiera
        full_reply = re.sub(r"<think>.*?</think>", "", full_reply, flags=re.DOTALL).strip()

        # 3. EXTRACCIÓN Y REPRODUCCIÓN DE MULETILLA
        # Buscamos patrones tipo [Mmm...] al inicio de la respuesta
        match = re.search(r"^\[(.*?)\]", full_reply)
        if match:
            muletilla_texto = match.group(1) # Extrae el texto dentro de los corchetes
            # Limpiamos el texto principal para el TTS real
            full_reply = full_reply.replace(f"[{muletilla_texto}]", "").strip()
            
            # Lanzamos el audio pregrabado de Alonso
            reproducir_muletilla_por_nombre(f"{muletilla_texto}]" if not muletilla_texto.endswith(']') else muletilla_texto)
            # Nota: El re.search puede devolver "Mmm..." sin el corchete de cierre según el patrón
            # Por seguridad, el mapeo usa la cadena exacta: "Mmm..."
            reproducir_muletilla_por_nombre(muletilla_texto)

        # 4. MOSTRAR Y HABLAR RESPUESTA REAL
        if ui_manager:
            ui_manager.update_data("TARS", full_reply, "TARS")
        
        # Usamos Edge TTS (Alonso) para la respuesta larga
        asyncio.run(play_audio_chunks(full_reply, "edge"))

    except Exception as e:
        queue_message(f"Error en flujo: {e}")
    finally:
        # Abrimos el micrófono para la siguiente interacción
        status.is_speaking = False

def post_utterance_callback():
    pass
