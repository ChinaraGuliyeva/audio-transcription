import logging
import os
import subprocess
import uuid
from pathlib import Path

import whisper
from fastapi import BackgroundTasks, FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI()

UPLOAD_DIR = "temp_audio"
os.makedirs(UPLOAD_DIR, exist_ok=True)

logger.info("Loading whisper model...")
model = whisper.load_model("base")
logger.info("Model is loaded")

tasks = {}

AUDIO_FILTERS = (
    "highpass=f=100,"
    "afftdn=nf=-25,"
    "loudnorm=I=-16:TP=-1.5:LRA=11,"
    "silenceremove=start_periods=1:start_duration=0.1:start_threshold=-45dB:detection=peak,"
    "areverse,"
    "silenceremove=start_periods=1:start_duration=0.1:start_threshold=-45dB:detection=peak,"
    "areverse"
)

# TO DO: Investigate this and refactor if possible
def preprocess_audio(input_path: str, output_path: str) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", input_path,
            "-af", AUDIO_FILTERS,
            "-ar", "16000", "-ac", "1",
            output_path,
        ],
        check=True,
        capture_output=True,
    )

# TO DO: Investigate this and refactor if possible
def run_whisper_task(task_id: str, file_path: str) -> None:
    tasks[task_id] = {"status": "processing", "result": None}
    clean_path = f"{file_path}.clean.wav"
    try:
        preprocess_audio(file_path, clean_path)
        result = model.transcribe(
            clean_path,
            temperature=0.1,
            condition_on_previous_text=False,
            no_speech_threshold=0.6,
            logprob_threshold=-1.0,
            compression_ratio_threshold=2.4,
        )
    except Exception:
        logger.exception("Transcription failed, task_id=%s", task_id)
        tasks[task_id] = {"status": "error", "error": "Transcription failed"}
    else:
        tasks[task_id] = {"status": "completed", "result": result["text"]}
    finally:
        Path(file_path).unlink(missing_ok=True)
        Path(clean_path).unlink(missing_ok=True)


@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/upload")
async def upload_and_start(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    task_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{task_id}_{file.filename}")

    with open(file_path, "wb") as buffer:
        while content := await file.read(1024 * 1024):
            buffer.write(content)

    background_tasks.add_task(run_whisper_task, task_id, file_path)

    return {"task_id": task_id, "message": "Processing is running in the background"}

@app.get("/status/{task_id}")
async def get_status(task_id: str):
    task = tasks.get(task_id)
    if not task:
        return JSONResponse(status_code=404, content={"message": "Task not found"})
    return task

app.mount("/", StaticFiles(directory="static", html=True), name="static")