# Minimal FastAPI service: health, upload song, run safe update (logged)
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import shutil, os, subprocess, psutil, datetime

app = FastAPI()
UPLOAD_DIR = "/home/kiosk/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Basic token guard (change token in production)
API_TOKEN = "changeme"

def auth_ok(token: str):
    return token == API_TOKEN

@app.get("/health")
def health():
    return {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "cpu_percent": psutil.cpu_percent(interval=0.2),
        "mem": psutil.virtual_memory()._asdict(),
        "disk": psutil.disk_usage("/")._asdict(),
        "uptime": subprocess.check_output(["uptime", "-p"]).decode().strip(),
    }

@app.post("/upload/song")
async def upload_song(file: UploadFile = File(...), token: str = ""):
    if not auth_ok(token):
        raise HTTPException(status_code=403, detail="forbidden")
    if not file.filename:
        raise HTTPException(400, "no filename")
    dest = os.path.join(UPLOAD_DIR, file.filename)
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"status": "ok", "path": dest}

@app.post("/update")
def do_update(token: str = ""):
    if not auth_ok(token):
        raise HTTPException(status_code=403, detail="forbidden")
    # Very conservative: just update package lists and list upgradable packages
    out = subprocess.check_output(["/usr/bin/apt", "update"]).decode()
    upgradable = subprocess.check_output(["/usr/bin/apt", "list", "--upgradable"]).decode()
    return {"updated": True, "apt_update_output": out, "upgradable": upgradable}

@app.post("/reboot")
def reboot(token: str = ""):
    if not auth_ok(token):
        raise HTTPException(status_code=403, detail="forbidden")
    subprocess.Popen(["/usr/bin/systemctl", "reboot"])
    return JSONResponse({"rebooting": True})
