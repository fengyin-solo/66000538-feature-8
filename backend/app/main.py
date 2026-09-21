import asyncio, math, random, time, json, threading
from collections import defaultdict, deque
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import numpy as np

app = FastAPI(title="Digital Twin Factory Monitor")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DEVICE_TYPES = ["CNC", "RobotArm", "Conveyor", "AGV", "InjectionMolding", "QCStation"]
STATUSES = ["RUNNING", "IDLE", "FAULT", "OFFLINE"]
ACTIVE_CLIENTS: list[WebSocket] = []
SIMULATOR_RUNNING = True

class DeviceState:
    def __init__(self, did: int, dtype: str, x: float, y: float, z: float):
        self.id = did
        self.type = dtype
        self.status = "RUNNING"
        self.position = [x, y, z]
        self.temperature = random.uniform(35, 45)
        self.vibration = random.uniform(0.1, 1.5)
        self.pressure = random.uniform(0.8, 1.2)
        self.production_count = 0
        self.fault_count = 0
        self.uptime = 0.0
        self.cycle_time = random.uniform(2, 8)
        self.quality_rate = random.uniform(0.95, 0.995)

    def to_dict(self):
        return {
            "id": self.id, "type": self.type, "status": self.status,
            "position": self.position, "temperature": round(self.temperature, 2),
            "vibration": round(self.vibration, 3), "pressure": round(self.pressure, 2),
            "production_count": self.production_count, "fault_count": self.fault_count,
            "uptime": round(self.uptime, 2), "quality_rate": round(self.quality_rate, 3)
        }

devices = {i: DeviceState(i, random.choice(DEVICE_TYPES),
                          random.uniform(-5, 5), 0.5, random.uniform(-5, 5)) for i in range(1, 13)}

production_log = []
anomaly_log = []

class AnomalyRules:
    # 数值口径（单位）随规则一并下发，两种模式下页面图例/口径保持一致
    FIELD_UNITS = {"temperature": "°C", "vibration": "mm/s", "pressure": "MPa"}

    def __init__(self):
        self.rules = [
            {"name": "高温告警", "field": "temperature", "threshold": 48, "op": "gt"},
            {"name": "振动超标", "field": "vibration", "threshold": 2.0, "op": "gt"},
            {"name": "压力异常", "field": "pressure", "threshold": 1.5, "op": "gt"},
        ]
        self.windows = defaultdict(lambda: deque(maxlen=10))

    def describe(self):
        return [
            {
                "name": r["name"],
                "field": r["field"],
                "op": r["op"],
                "threshold": r["threshold"],
                "unit": self.FIELD_UNITS.get(r["field"], ""),
            }
            for r in self.rules
        ]

    def check(self, dev: DeviceState):
        triggers = []
        for rule in self.rules:
            val = getattr(dev, rule["field"])
            if (rule["op"] == "gt" and val > rule["threshold"]) or (rule["op"] == "lt" and val < rule["threshold"]):
                triggers.append({"device_id": dev.id, "rule": rule["name"],
                                 "value": round(val, 3), "threshold": rule["threshold"]})

        # sliding window trend
        key = f"{dev.id}_temp"
        self.windows[key].append(dev.temperature)
        if len(self.windows[key]) >= 8:
            vals = list(self.windows[key])
            if np.mean(vals[-4:]) - np.mean(vals[:4]) > 3:
                triggers.append({"device_id": dev.id, "rule": "温度趋势上升", "value": round(np.mean(vals[-4:]), 2), "threshold": ">3°C/周期"})

        if triggers:
            anomaly_log.append({"timestamp": time.time(), "triggers": triggers, "device_type": dev.type})
        return triggers

rules_engine = AnomalyRules()

def simulate():
    while SIMULATOR_RUNNING:
        for dev in devices.values():
            drift = 0.1 * math.sin(time.time() * 0.5 + dev.id)
            noise = random.gauss(0, 0.3)
            dev.temperature = max(25, min(65, dev.temperature + drift + noise))

            v_drift = 0.02 * math.sin(time.time() * 0.3 + dev.id * 0.7)
            dev.vibration = max(0, min(3, dev.vibration + v_drift + random.gauss(0, 0.05)))

            dev.pressure = max(0.5, min(2, dev.pressure + random.gauss(0, 0.02)))

            if random.random() < 0.015:
                dev.status = "FAULT"
                dev.fault_count += 1
            elif random.random() < 0.03 and dev.status == "FAULT":
                dev.status = "RUNNING"

            if dev.status == "RUNNING":
                if random.random() < 0.4:
                    dev.production_count += 1
                dev.uptime += 1

            triggers = rules_engine.check(dev)
            if triggers and dev.status != "FAULT" and random.random() < 0.3:
                dev.status = "FAULT"

        production_log.append({"timestamp": time.time(), "count": sum(d.production_count for d in devices.values())})

        try:
            payload = {
                "devices": [d.to_dict() for d in devices.values()],
                "production": sum(d.production_count for d in devices.values()),
                "anomalies": anomaly_log[-5:] if anomaly_log else [],
                "oee": calculate_oee()
            }
            msg = json.dumps(payload)
        except:
            continue

        dead = []
        for ws in ACTIVE_CLIENTS:
            try:
                asyncio.run_coroutine_threadsafe(ws.send_text(msg), asyncio.get_event_loop())
            except:
                dead.append(ws)
        for ws in dead:
            if ws in ACTIVE_CLIENTS:
                ACTIVE_CLIENTS.remove(ws)

        time.sleep(1)


def calculate_oee():
    oee_list = []
    for dev in devices.values():
        if dev.uptime == 0:
            continue
        availability = min(1.0, dev.uptime / max(1, dev.uptime + dev.fault_count))
        performance = min(1.0, dev.production_count / max(1, dev.uptime / 2))
        quality = dev.quality_rate
        oee = round(availability * performance * quality * 100, 1)
        oee_list.append({"id": dev.id, "type": dev.type, "oee": oee,
                         "availability": round(availability * 100, 1),
                         "performance": round(performance * 100, 1),
                         "quality": round(quality * 100, 1)})
    return oee_list


class OEEAnalysis(BaseModel):
    availability: float
    performance: float
    quality: float


@app.on_event("startup")
async def startup():
    t = threading.Thread(target=simulate, daemon=True)
    t.start()


@app.get("/api/devices")
def get_devices():
    return {"devices": [d.to_dict() for d in devices.values()], "anomalies": anomaly_log[-10:]}


@app.get("/api/oee")
def get_oee():
    return {"oee": calculate_oee()}


@app.get("/api/production")
def get_production():
    return {"log": production_log[-60:]}


@app.get("/api/rules")
def get_rules():
    """当前生效的异常检测阈值参数（只读获取，任何账号可见）。"""
    return {"rules": rules_engine.describe()}


class RuleThreshold(BaseModel):
    field: str
    threshold: float


def enforce_writable(request: Request):
    """
    大屏只读模式为受控视图：写操作必须显式携带 X-View-Mode: interactive。
    缺失或为 readonly 一律拒绝，确保前端绕过（越权）也无法改动数据。
    """
    mode = request.headers.get("x-view-mode", "")
    if mode != "interactive":
        return JSONResponse(
            status_code=403,
            content={
                "detail": "当前处于大屏只读展示模式，参数修改与保存已被禁用；退出只读模式后方可操作。"
            },
        )
    return None


@app.put("/api/rules")
async def update_rules(payload: list[RuleThreshold], request: Request):
    denied = enforce_writable(request)
    if denied is not None:
        return denied

    fields = {r["field"] for r in rules_engine.describe()}
    incoming = {item.field: item.threshold for item in payload}
    unknown = set(incoming) - fields
    if unknown:
        return JSONResponse(
            status_code=422,
            content={"detail": f"存在未知的参数字段: {sorted(unknown)}"},
        )

    for rule in rules_engine.rules:
        if rule["field"] in incoming:
            rule["threshold"] = incoming[rule["field"]]
    return {"rules": rules_engine.describe()}


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    ACTIVE_CLIENTS.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in ACTIVE_CLIENTS:
            ACTIVE_CLIENTS.remove(websocket)


@app.on_event("shutdown")
async def shutdown():
    global SIMULATOR_RUNNING
    SIMULATOR_RUNNING = False