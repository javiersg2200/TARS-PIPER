import os
import re
import wave
import ctypes
import asyncio
import subprocess
from io import BytesIO
from piper.voice import PiperVoice
from modules.module_messageQue import queue_message

# --- 1. SILENCIADOR DE ERRORES ALSA ---
# Magia oscura de Linux para que la terminal no se llene de advertencias de audio inútiles.
ERROR_HANDLER_FUNC = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p)
def py_error_handler(filename, line, function, err, fmt): pass
c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
try:
    asound = ctypes.cdll.LoadLibrary('libasound.so')
    asound.snd_lib_error_set_handler(c_error_handler)
except:
    pass

# --- 2. PRECARGA DEL MODELO EN RAM ---
# Esto elimina el retraso de 7 segundos cargando a 'Dave' directamente en la memoria.
MODEL_PATH = "/home/javiersg/TARS-AI/src/assets/voices/es_ES-davefx-medium.onnx"
voice = None

print("🧠 Cargando cuerdas vocales en la RAM. Un momento...")
try:
    if os.path.exists(MODEL_PATH):
        voice = PiperVoice.load(MODEL_PATH)
        print("✅ Voz de Dave cargada y lista para la misión.")
    else:
        print(f"❌ ERROR: No se encuentra el archivo de voz en {MODEL_PATH}")
except Exception as e:
    print(f"❌ Error crítico cargando el motor Piper: {e}")

# --- 3. MOTOR DE SÍNTESIS ---
async def synthesize(chunk):
    """Convierte un fragmento de texto en un archivo WAV temporal en la memoria RAM."""
    wav_buffer = BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(voice.config.sample_rate)
        
        try:
            if hasattr(voice, "synthesize_wav"):
                voice.synthesize_wav(chunk, wav_file)
            elif hasattr(voice, "synthesize"):
                voice.synthesize(chunk, wav_file)
        except Exception as e:
            queue_message(f"Error de síntesis interna: {e}")
            
    wav_buffer.seek(0)
    return wav_buffer

# --- 4. FUNCIÓN PRINCIPAL DE REPRODUCCIÓN (STREAMING) ---
async def play_audio_chunks(text, model="piper", is_wake_word=False):
    """
    Trocea el texto y lo reproduce al instante. 
    Llamada por module_main.py cuando el cerebro (LLM) tiene una respuesta.
    """
    if not voice:
        queue_message("ERROR: El sistema vocal está desconectado.")
        return

    # Trocear el texto por signos de puntuación (. ! ?) para no ahogar el procesador
    chunks = re.split(r'(?<=[.!?])\s+', text)

    for chunk in chunks:
        clean_chunk = chunk.strip()
        if not clean_chunk: 
            continue
            
        # 1. Sintetizar la frase en la RAM
        wav_buffer = await synthesize(clean_chunk)
        
        # 2. Reproducir canalizando el audio directamente al altavoz (aplay)
        try:
            proceso = subprocess.Popen(
                ["aplay", "-q"], 
                stdin=subprocess.PIPE, 
                stderr=subprocess.DEVNULL
            )
            # Volcamos los bytes de RAM directamente a la tarjeta de sonido
            proceso.communicate(input=wav_buffer.read())
        except Exception as e:
            queue_message(f"Error de hardware reproduciendo audio: {e}")

# --- 5. COMPATIBILIDAD CON APP.PY ---
# Estas funciones evitan que el programa principal colapse buscando configuraciones antiguas.
def update_tts_settings(*args, **kwargs):
    queue_message("SYSTEM: Configuración de voz redirigida a Piper local.")
    pass

def initialize_manager_tts(*args, **kwargs):
    queue_message("SYSTEM: TTS Manager local inicializado.")
    pass
