import logging
import os
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

def run_whisper_task(task_id: str, file_path: str) -> None:
    tasks[task_id] = {"status": "processing", "result": None}
    try:
        result = model.transcribe(file_path)
    except Exception:
        logger.exception("Transcription failed, task_id=%s", task_id)
        tasks[task_id] = {"status": "error", "error": "Transcription failed"}
    else:
        tasks[task_id] = {"status": "completed", "result": result["text"]}
    finally:
        Path(file_path).unlink(missing_ok=True)


@app.api_route("/health", methods=["GET", "HEAD"])
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