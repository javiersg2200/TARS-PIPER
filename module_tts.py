import os
import re
import wave
import ctypes
import asyncio
import subprocess
from io import BytesIO
from piper.voice import PiperVoice
from modules.module_messageQue import queue_message

# 1. Silenciador de errores ALSA (Magia de la comunidad para Linux)
ERROR_HANDLER_FUNC = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p)
def py_error_handler(filename, line, function, err, fmt): pass
c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
try:
    asound = ctypes.cdll.LoadLibrary('libasound.so')
    asound.snd_lib_error_set_handler(c_error_handler)
except:
    pass

# 2. PRECARGA DEL MODELO EN RAM (La clave de la velocidad)
MODEL_PATH = "/home/javiersg/TARS-AI/src/assets/voices/es_ES-davefx-medium.onnx"
voice = None

print("🧠 Cargando cuerdas vocales en la RAM. Un momento...")
try:
    voice = PiperVoice.load(MODEL_PATH)
    print("✅ Voz de Dave cargada y lista.")
except Exception as e:
    print(f"❌ Error crítico cargando Piper: {e}")

async def synthesize(chunk):
    """Convierte un fragmento de texto en un archivo WAV en la memoria RAM."""
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
            queue_message(f"Error de síntesis: {e}")
            
    wav_buffer.seek(0)
    return wav_buffer

async def play_audio_chunks(text, model="piper", is_wake_word=False):
    """
    Función principal llamada por module_main.py.
    Procesa el texto por frases y lo reproduce inmediatamente.
    """
    if not voice:
        queue_message("ERROR: El modelo de voz no está cargado.")
        return

    # Trocear el texto por signos de puntuación (. ! ?) para fluidez
    chunks = re.split(r'(?<=[.!?])\s+', text)

    for chunk in chunks:
        clean_chunk = chunk.strip()
        if not clean_chunk: 
            continue
            
        # 1. Sintetizar la frase en la RAM
        wav_buffer = await synthesize(clean_chunk)
        
        # 2. Reproducir inmediatamente canalizando el buffer a 'aplay'
        try:
            proceso = subprocess.Popen(
                ["aplay", "-q"], 
                stdin=subprocess.PIPE, 
                stderr=subprocess.DEVNULL
            )
            # Enviamos los bytes del audio directamente al altavoz
            proceso.communicate(input=wav_buffer.read())
        except Exception as e:
            queue_message(f"Error reproduciendo audio: {e}")
