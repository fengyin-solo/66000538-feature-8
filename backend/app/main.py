import asyncio, math, random, time, json, threading
from collections import defaultdict, deque
from typing import List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np

app = FastAPI(title="Digital Twin Factory Monitor")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DEVICE_TYPES = ["CNC", "RobotArm", "Conveyor", "AGV", "InjectionMolding", "QCStation"]
STATUSES = ["RUNNING", "IDLE", "FAULT", "OFFLINE"]
ACTIVE_CLIENTS: list[WebSocket] = []
SIMULATOR_RUNNING = True

# 账号与角色：viewer 为只读账号，任何写操作在服务端都会被拒绝
ACCOUNTS = {
    "admin": {"name": "管理员", "role": "admin"},
    "operator": {"name": "操作员", "role": "operator"},
    "viewer": {"name": "访客", "role": "viewer"},
}
WRITE_ROLES = {"admin", "operator"}
DEFAULT_ACCOUNT = "viewer"  # 未携带账号时按只读处理（受控默认）

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
    def __init__(self):
        self.rules = [
            {"name": "高温告警", "field": "temperature", "threshold": 48, "op": "gt"},
            {"name": "振动超标", "field": "vibration", "threshold": 2.0, "op": "gt"},
            {"name": "压力异常", "field": "pressure", "threshold": 1.5, "op": "gt"},
        ]
        self.windows = defaultdict(lambda: deque(maxlen=10))
        self.lock = threading.Lock()

    def snapshot(self):
        with self.lock:
            return [dict(r) for r in self.rules]

    def update_thresholds(self, updates: dict):
        # 整体替换规则列表，模拟线程读到的始终是完整一致的旧版或新版
        with self.lock:
            new_rules = [dict(r) for r in self.rules]
            for r in new_rules:
                if r["name"] in updates:
                    r["threshold"] = float(updates[r["name"]])
            self.rules = new_rules

    def check(self, dev: DeviceState):
        triggers = []
        for rule in self.snapshot():
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


class RuleUpdate(BaseModel):
    name: str
    threshold: float


class ConfigUpdate(BaseModel):
    rules: List[RuleUpdate]


def resolve_account(x_account: Optional[str]) -> Optional[str]:
    """返回有效账号 id；未携带或未知账号返回 None（视为越权）。"""
    if x_account and x_account in ACCOUNTS:
        return x_account
    return None


@app.get("/api/accounts")
def get_accounts():
    return {"accounts": [
        {"id": aid, "name": a["name"], "role": a["role"], "can_write": a["role"] in WRITE_ROLES}
        for aid, a in ACCOUNTS.items()
    ]}


@app.get("/api/session")
def get_session(account: str = DEFAULT_ACCOUNT):
    acct = ACCOUNTS.get(account)
    if not acct:
        raise HTTPException(status_code=404, detail="未知账号")
    return {"account": account, "name": acct["name"], "role": acct["role"],
            "can_write": acct["role"] in WRITE_ROLES}


@app.get("/api/config")
def get_config():
    return {"rules": rules_engine.snapshot()}


@app.put("/api/config")
def update_config(cfg: ConfigUpdate, x_account: Optional[str] = Header(None)):
    # 越权防护：只读/未知账号一律拒绝，且不改动任何数据
    account = resolve_account(x_account)
    if account is None or ACCOUNTS[account]["role"] not in WRITE_ROLES:
        raise HTTPException(status_code=403,
                            detail="当前账号为只读权限，参数修改已被服务端拒绝，数据未被更改")
    # 先整体校验，全部通过后才落库，避免部分修改
    known = {r["name"] for r in rules_engine.snapshot()}
    for item in cfg.rules:
        if item.name not in known:
            raise HTTPException(status_code=400, detail=f"未知规则: {item.name}")
        if not (0 < item.threshold <= 200):
            raise HTTPException(status_code=400, detail=f"阈值超出允许范围(0,200]: {item.name}")
    rules_engine.update_thresholds({r.name: r.threshold for r in cfg.rules})
    return get_config()


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