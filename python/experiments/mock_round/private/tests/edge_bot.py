import time
def trade(s, memory):
    seq = s["seq"]
    memory["n"] = memory.get("n", 0) + 1
    if seq == 5:
        time.sleep(0.15)
    if seq == 6:
        memory["bad"] = {1, 2}
    if seq == 7:
        raise RuntimeError("boom")
    if seq == 8:
        assert memory["n"] == 6, memory  # steps 5,6,7 discarded
        return [{"action": "new", "symbol": "LUMEN", "side": "BUY", "price": 99.73, "size": 1},
                {"action": "cancel", "id": "nope"},
                {"action": "new", "symbol": "CALDERA", "side": "BUY", "price": 1.0, "size": 16}]
    if seq == 9:
        b = s["books"]["OBERON"]["asks"][0]
        return [{"action": "new", "symbol": "OBERON", "side": "BUY", "price": b[0], "size": 2, "tif": "IOC", "id": "t1"}]
    if seq == 10:
        assert s["fills"] and s["fills"][0]["id"] == "t1", s["fills"]
        assert s["positions"]["OBERON"] == 2
    return []
