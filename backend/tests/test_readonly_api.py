"""只读模式与越权防护的接口测试。

验证点：
1. 配置查询对所有账号开放（受控视图数据一致）；
2. 只读账号/未携带账号/未知账号的写请求一律 403，且配置数据不被改动；
3. 非法参数（未知规则、阈值越界）400，且配置数据不被改动；
4. 可写账号（admin/operator）可正常修改并生效。
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def get_thresholds():
    resp = client.get("/api/config")
    assert resp.status_code == 200
    return {r["name"]: r["threshold"] for r in resp.json()["rules"]}


def test_config_is_public_and_consistent():
    rules = client.get("/api/config").json()["rules"]
    assert len(rules) == 3
    names = {r["name"] for r in rules}
    assert names == {"高温告警", "振动超标", "压力异常"}


def test_accounts_and_session():
    accounts = {a["id"]: a for a in client.get("/api/accounts").json()["accounts"]}
    assert accounts["viewer"]["can_write"] is False
    assert accounts["admin"]["can_write"] is True
    assert accounts["operator"]["can_write"] is True

    assert client.get("/api/session", params={"account": "viewer"}).json()["can_write"] is False
    assert client.get("/api/session", params={"account": "admin"}).json()["can_write"] is True
    assert client.get("/api/session", params={"account": "nobody"}).status_code == 404


def test_readonly_account_cannot_modify():
    before = get_thresholds()
    resp = client.put("/api/config",
                      json={"rules": [{"name": "高温告警", "threshold": 99}]},
                      headers={"X-Account": "viewer"})
    assert resp.status_code == 403
    assert "只读" in resp.json()["detail"]
    assert get_thresholds() == before  # 越权操作不得改动数据


def test_missing_or_unknown_account_cannot_modify():
    before = get_thresholds()
    r1 = client.put("/api/config", json={"rules": [{"name": "高温告警", "threshold": 99}]})
    r2 = client.put("/api/config",
                    json={"rules": [{"name": "高温告警", "threshold": 99}]},
                    headers={"X-Account": "hacker"})
    assert r1.status_code == 403
    assert r2.status_code == 403
    assert get_thresholds() == before


def test_invalid_payload_rejected_without_side_effect():
    before = get_thresholds()
    r1 = client.put("/api/config",
                    json={"rules": [{"name": "不存在的规则", "threshold": 10}]},
                    headers={"X-Account": "admin"})
    r2 = client.put("/api/config",
                    json={"rules": [{"name": "高温告警", "threshold": -5}]},
                    headers={"X-Account": "admin"})
    assert r1.status_code == 400
    assert r2.status_code == 400
    assert get_thresholds() == before


def test_writable_accounts_can_modify():
    before = get_thresholds()
    try:
        resp = client.put("/api/config",
                          json={"rules": [{"name": "高温告警", "threshold": 52},
                                          {"name": "振动超标", "threshold": 2.5}]},
                          headers={"X-Account": "admin"})
        assert resp.status_code == 200
        after = get_thresholds()
        assert after["高温告警"] == 52
        assert after["振动超标"] == 2.5
        assert after["压力异常"] == before["压力异常"]  # 未提交的项保持不变

        resp = client.put("/api/config",
                          json={"rules": [{"name": "压力异常", "threshold": 1.8}]},
                          headers={"X-Account": "operator"})
        assert resp.status_code == 200
        assert get_thresholds()["压力异常"] == 1.8
    finally:
        # 恢复初始阈值，避免污染其他测试
        client.put("/api/config",
                   json={"rules": [{"name": k, "threshold": v} for k, v in before.items()]},
                   headers={"X-Account": "admin"})
        assert get_thresholds() == before
