import os
import uuid
import whisper
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

UPLOAD_DIR = "temp_audio"
os.makedirs(UPLOAD_DIR, exist_ok=True)

model = whisper.load_model("base")

tasks = {}

def run_whisper_task(task_id: str, file_path: str):
    try:
        tasks[task_id] = {"status": "processing", "result": None}

        result = model.transcribe(file_path)

        tasks[task_id] = {"status": "completed", "result": result["text"]}

        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        tasks[task_id] = {"status": "error", "error": str(e)}

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