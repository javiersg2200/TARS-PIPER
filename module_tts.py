import asyncio
import edge_tts
from modules.module_messageQue import queue_message

# La voz neuronal elegida (Masculina, España, tono serio)
VOICE = "es-ES-AlvaroNeural"

async def play_audio_chunks(text, model="edge", is_wake_word=False):
    """
    Se conecta a Microsoft Edge TTS y canaliza el audio directamente al altavoz
    en formato streaming. Latencia casi cero.
    """
    if not text:
        return

    try:
        # Iniciamos el reproductor mpg123 esperando datos de entrada en streaming ("-")
        proc = await asyncio.create_subprocess_exec(
            "mpg123", "-q", "-",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )

        # Conectamos con el servidor neuronal
        communicate = edge_tts.Communicate(text, VOICE)
        
        # Recibimos el audio pedacito a pedacito y lo inyectamos al altavoz
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                proc.stdin.write(chunk["data"])
                await proc.stdin.drain()
                
        # Cerramos la transmisión cuando termina la frase
        proc.stdin.close()
        await proc.wait()
        
    except Exception as e:
        queue_message(f"❌ Error de comunicación con Edge TTS: {e}")

# --- COMPATIBILIDAD CON APP.PY ---
# Mantenemos las funciones vacías para que el núcleo del programa no colapse
def update_tts_settings(*args, **kwargs): 
    pass

def initialize_manager_tts(*args, **kwargs): 
    pass
