from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import subprocess
import uuid
import json
import os
import re

app = FastAPI()
scheduler = BackgroundScheduler()
scheduler.start()

PULUMI_DIR = "./src"
DATA_FILE = "vm_data.json"

def load_vm_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {}

def save_vm_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

class CreateVMRequest(BaseModel):
    auto_delete_minutes: int = 0 

@app.post("/create-vm")
def create_vm(req: CreateVMRequest):
    vm_id = f"vm-{uuid.uuid4().hex[:8]}"

    try:
        result = subprocess.run(
            ["pulumi", "up", "--yes", "--stack", "dev"],
            cwd=PULUMI_DIR,
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Pulumi up failed: {e.stdout}")

    ip_match = re.search(r'public_ip:\s*"?(?P<ip>(?:\d{1,3}\.){3}\d{1,3})"?', result.stdout)
    print(result.stdout)
    if not ip_match:
        raise HTTPException(status_code=500, detail="Public IP not found in Pulumi output")

    public_ip = ip_match.group("ip")

    data = load_vm_data()
    data[vm_id] = {
        "created_at": datetime.utcnow().isoformat(),
        "public_ip": public_ip,
        "auto_delete": None
    }

    if req.auto_delete_minutes > 0:
        delete_time = datetime.utcnow() + timedelta(minutes=req.auto_delete_minutes)
        scheduler.add_job(delete_vm, 'date', run_date=delete_time, args=[vm_id])
        data[vm_id]["auto_delete"] = delete_time.isoformat()

    save_vm_data(data)
    return {"vm_id": vm_id, "status": "created", "public_ip": public_ip}

@app.delete("/delete-vm/{vm_id}")
def delete_vm(vm_id: str):
    try:
        result = subprocess.run(
            ["pulumi", "destroy", "--yes", "--stack", "dev"],
            cwd=PULUMI_DIR,
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Pulumi destroy failed: {e.stderr}")

    data = load_vm_data()
    data.pop(vm_id, None)
    save_vm_data(data)

    return {"vm_id": vm_id, "status": "deleted"}

@app.get("/vms")
def list_vms():
    return load_vm_data()
