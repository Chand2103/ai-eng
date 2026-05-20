from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import os
from pathlib import Path
import shutil

from stt import STT
from llm import LLM
from tts import TTS

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Global model instances
models = {
    "stt": None,
    "llm": None,
    "tts": None
}

# Keep track of turn count for history management
turn_count = 0


@app.on_event("startup")
async def startup_event():
    """Load models when server starts"""
    try:
        print("Loading models...")
        
        models["stt"] = STT()
        models["llm"] = LLM()
        models["tts"] = TTS()
        
        print("All models loaded successfully!")
    except Exception as e:
        print(f"Error loading models: {str(e)}")
        raise


@app.post("/chat")
async def chat(audio_file: UploadFile = File(...)):
    """
    Process audio through STT -> LLM -> TTS pipeline
    
    Args:
        audio_file: Audio file (.wav, .mp3, etc.)
    
    Returns:
        JSON with transcription, AI response, and output audio file path
    """
    global turn_count
    
    try:
        turn_count += 1
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            content = await audio_file.read()
            tmp.write(content)
            tmp_audio_path = tmp.name
        
        try:
            # STT - Transcribe audio to text
            print(f"\n[Turn {turn_count} - STT]")
            text = models["stt"].transcribe(tmp_audio_path)
            
            if not text:
                raise HTTPException(
                    status_code=400,
                    detail="No speech detected in audio file"
                )
            
            print(f"Transcription: {text}")
            
            # LLM - Generate response
            print(f"\n[Turn {turn_count} - LLM]")
            use_history = turn_count > 1
            response = models["llm"].generate(text, use_history=use_history)
            print(f"AI Response: {response}")
            
            # TTS - Synthesize response to audio
            print(f"\n[Turn {turn_count} - TTS]")
            output_audio_path = f"output_{turn_count}.wav"
            models["tts"].synthesize(response, out_path=output_audio_path)
            
            print(f"\n[Turn {turn_count} complete]")
            
            # Return audio file directly
            return FileResponse(
                path=output_audio_path,
                media_type="audio/wav",
                filename=f"response_{turn_count}.wav"
            )
            
        finally:
            # Clean up temporary audio file
            if os.path.exists(tmp_audio_path):
                os.remove(tmp_audio_path)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing audio: {str(e)}"
        )


@app.get("/audio/{filename}")
async def get_audio(filename: str):
    """Download output audio file"""
    file_path = Path(filename)
    
    # Security check - only allow files in current directory
    if not file_path.exists() or file_path.is_absolute():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        media_type="audio/wav",
        filename=filename
    )


@app.get("/status")
async def status():
    """Check if models are loaded"""
    return {
        "models_loaded": all(models.values()),
        "stt_loaded": models["stt"] is not None,
        "llm_loaded": models["llm"] is not None,
        "tts_loaded": models["tts"] is not None,
        "turn_count": turn_count
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
