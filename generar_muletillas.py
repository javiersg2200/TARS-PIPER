import os
import asyncio
import edge_tts

# Configuración táctica
VOICE = "es-US-AlonsoNeural"
OUTPUT_DIR = "/home/javiersg/TARS-AI/src/assets/muletillas"

# El arsenal de 15 respuestas humanas
MULETILLAS = [
    "Mmm...",
    "A ver...",
    "Déjame pensar...",
    "Vamos a ver...",
    "La verdad es que...",
    "Bueno...",
    "Pues...",
    "Mira...",
    "O sea...",
    "Ehhh...",
    "Un segundo...",
    "Francamente...",
    "Interesante...",
    "Si te soy sincero...",
    "Curiosamente..."
]

async def fabricar_audios():
    # 1. Asegurar que el búnker (carpeta) existe
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"📁 Directorio preparado: {OUTPUT_DIR}")

    # 2. Generar cada archivo de audio
    for i, texto in enumerate(MULETILLAS, start=1):
        nombre_archivo = f"m_{i:02d}.mp3"
        ruta_completa = os.path.join(OUTPUT_DIR, nombre_archivo)
        
        print(f"🎙️ Grabando en memoria [{nombre_archivo}]: '{texto}'")
        
        # Conexión con Microsoft y guardado directo en el disco
        comunicacion = edge_tts.Communicate(texto, VOICE)
        await comunicacion.save(ruta_completa)
        
    print("\n✅ Operación completada. TARS ya tiene su repertorio de imperfecciones humanas listo.")

if __name__ == "__main__":
    # Arrancamos el motor asíncrono
    asyncio.run(fabricar_audios())
