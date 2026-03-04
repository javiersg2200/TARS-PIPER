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

# Variables Globales
ui_manager = None
stt_manager = None

def initialize_managers(mem_mgr, char_mgr, stt_mgr, ui_mgr, shutdown_evt, batt_mod):
    global ui_manager, stt_manager
    ui_manager = ui_mgr
    stt_manager = stt_mgr
    queue_message("SYSTEM: Managers initialized (Solid Mode).")

def reproducir_muletilla_tactica():
    """Elige una muletilla al azar y la reproduce en segundo plano."""
    carpeta_muletillas = "/home/javiersg/TARS-AI/src/assets/muletillas"
    try:
        # 1. Escanear el arsenal de audios
        archivos = [f for f in os.listdir(carpeta_muletillas) if f.endswith('.mp3')]
        if not archivos:
            return
            
        # 2. Elegir munición al azar
        archivo_elegido = random.choice(archivos)
        ruta_completa = os.path.join(carpeta_muletillas, archivo_elegido)
        
        # 3. Disparar el audio en segundo plano (no bloquea el código)
        subprocess.Popen(
            ["mpg123", "-q", ruta_completa],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        queue_message(f"Error reproduciendo muletilla: {e}")

def wake_word_callback(wake_response="¿Sí?"):
    """Respuesta inmediata al detectar 'TARS'"""
    if status.is_speaking: return
    
    if ui_manager:
        ui_manager.deactivate_screensaver()
        ui_manager.update_data("TARS", wake_response, "TARS")
    
    status.is_speaking = True
    try:
        asyncio.run(play_audio_chunks(wake_response, "openai", True))
    finally:
        status.is_speaking = False

def utterance_callback(message):
    """
    Procesado en bloque: Escucha -> Procesa todo -> Habla todo.
    Evita entrecortes y asegura una entonación natural.
    """
    if not message or status.is_speaking:
        return

    user_text = str(message)
    if ui_manager:
        ui_manager.update_data("USER", user_text, "USER")
    
    queue_message(f"USER: {user_text}")

    # 1. COMANDO DE APAGADO (Apaga TARS y la Raspberry Pi)
    cmd = user_text.lower()
    if "apágate" in cmd and "tars" in cmd:
        asyncio.run(play_audio_chunks("Entendido. Cerrando sistemas.", "openai"))
        os.system("sudo shutdown -h now")
        return

    try:
        # Bloqueamos el micrófono para que TARS no se escuche a sí mismo
        status.is_speaking = True
        
        # --- MAGIA ACÚSTICA ---
        # Disparamos el audio de espera justo antes de que el cerebro trabaje
        reproducir_muletilla_tactica()
        # ----------------------
        
        # 2. GENERAR RESPUESTA COMPLETA (Sin streaming entre frases)
        # Esperamos a que el cerebro termine el párrafo
        respuesta_gen = process_completion(user_text)
        full_reply = "".join(list(respuesta_gen))
        
        # Limpieza de etiquetas de pensamiento
        full_reply = re.sub(r"<think>.*?</think>", "", full_reply, flags=re.DOTALL).strip()

        # 3. MOSTRAR Y HABLAR
        if ui_manager:
            ui_manager.update_data("TARS", full_reply, "TARS")
        
        # Enviamos el párrafo entero para máxima calidad de voz
        asyncio.run(play_audio_chunks(full_reply, "openai"))

    except Exception as e:
        queue_message(f"Error en flujo: {e}")
    finally:
        # Abrimos el oído de nuevo
        status.is_speaking = False

def post_utterance_callback():
    pass
