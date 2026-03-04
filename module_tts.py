import os
import re
import wave
import ctypes
import asyncio
from io import BytesIO
from piper.voice import PiperVoice
from modules.module_messageQue import queue_message

# --- 1. SILENCIADOR DE ERRORES ALSA ---
ERROR_HANDLER_FUNC = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p)
def py_error_handler(filename, line, function, err, fmt): pass
c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
try:
    asound = ctypes.cdll.LoadLibrary('libasound.so')
    asound.snd_lib_error_set_handler(c_error_handler)
except:
    pass

# --- 2. PRECARGA DEL MODELO EN RAM ---
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

# --- 3. SÍNTESIS SÍNCRONA (Para usar en hilos de fondo) ---
def synthesize_sync(chunk):
    """Genera el audio usando la CPU. Se ejecutará en un hilo separado para no bloquear."""
    wav_buffer = BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)  
        wav_file.setsampwidth(2)  
        wav_file.setframerate(voice.config.sample_rate)
        
        try:
            if hasattr(voice, "synthesize_wav"):
                voice.synthesize_wav(chunk, wav_file)
            elif hasattr(voice, "synthesize"):
                voice.synthesize(chunk, wav_file)
        except Exception as e:
            print(f"Error de síntesis: {e}")
            
    wav_buffer.seek(0)
    return wav_buffer

# --- 4. STREAMING ASÍNCRONO SIN CORTES ---
async def play_audio_chunks(text, model="piper", is_wake_word=False):
    if not voice: return

    # Trocear inteligentemente manteniendo los signos de puntuación
    chunks = re.findall(r'[^.!?\n]+[.!?\n]*', text)
    audio_queue = asyncio.Queue()

    # TAREA 1: El Productor (El Cerebro)
    async def producer():
        for chunk in chunks:
            clean_chunk = chunk.strip()
            if clean_chunk:
                # Usamos to_thread para que la CPU trabaje en la frase 2 mientras suena la 1
                wav_buffer = await asyncio.to_thread(synthesize_sync, clean_chunk)
                await audio_queue.put(wav_buffer)
        
        # Le decimos al consumidor que ya no hay más frases
        await audio_queue.put(None) 

    # TAREA 2: El Consumidor (La Boca)
    async def consumer():
        while True:
            wav_buffer = await audio_queue.get()
            if wav_buffer is None: # Si recibe None, termina
                break
            
            try:
                # Usamos create_subprocess_exec para reproducir sin congelar el programa
                proc = await asyncio.create_subprocess_exec(
                    "aplay", "-q",
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await proc.communicate(input=wav_buffer.read())
            except Exception as e:
                print(f"Error aplay: {e}")
            
            audio_queue.task_done()

    # Lanzamos las dos tareas a la vez
    await asyncio.gather(producer(), consumer())

# --- 5. COMPATIBILIDAD CON APP.PY ---
def update_tts_settings(*args, **kwargs): pass
def initialize_manager_tts(*args, **kwargs): pass
