"""Checks evaluate.py's rule enforcement. Expected per session: errors 3 (n=4 slow, n=6 "boom",
n=11 not a list), slow calls 1, rejected actions 8:
  n=0  12 actions                         -> 1 reject (the last 2 dropped)
  n=1  off-tick VANTA, qty 0, pull of an unknown ref, reused ref, 4-field post -> 5 rejects
  n=2  5 far-away AURIC bids              -> 1 reject (the 5th: 4 resting max)
  n=3  BRISA buy 61 (limit 60)            -> 1 reject
  n=11 returns a string                   -> discarded (an error)
Any failed assert raises, which shows up as an extra error.
"""
import time


class Strategy:
    def on_start(self, config):
        self.cfg = config
        assert config["products"]["VANTA"]["tick"] == 4 and config["max_actions"] == 10
        self.calls = 0

    def on_market(self, u):
        n = u["n"]
        self.calls += 1
        a = u["book"]["AURIC"]
        if n == 0:
            far = a["bid"][0][0] - 50
            return [("post", "AURIC", 1, far, 1)] + [("pull_all", "AURIC")] * 9 + [("post", "AURIC", 1, far, 2)] * 2
        if n == 1:
            assert [o[0] for o in u["open"]] == [1], u["open"]   # the pull_alls ran first, before the post
            vb = u["book"]["VANTA"]["bid"][0][0]
            return [("post", "VANTA", 1, vb - 2, 10), ("post", "AURIC", 0, a["bid"][0][0] - 50, 11),
                    ("pull", 999), ("post", "AURIC", 1, a["bid"][0][0] - 50, 1), ("post", "AURIC", 1, 5)]
        if n == 2:
            assert [o[0] for o in u["open"]] == [1], u["open"]
            far = a["bid"][0][0] - 60
            return [("post", "AURIC", 1, far - k, 20 + k) for k in range(4)]   # 1 + 4 = 5 resting -> 1 rejected
        if n == 3:
            assert len([o for o in u["open"] if o[1] == "AURIC"]) == 4, u["open"]
            return [("post", "BRISA", 61, u["book"]["BRISA"]["bid"][0][0] - 50, 30)]
        if n == 4:
            time.sleep(0.06)
            return [("take", "AURIC", 2, a["ask"][0][0], 40)]
        if n == 5:
            assert u["pos"]["AURIC"] == 0 and not u["fills"], (u["pos"], u["fills"])
            return []
        if n == 6:
            raise RuntimeError("boom")
        if n == 7:
            return [("take", "AURIC", 2, a["ask"][0][0], 900)]
        if n == 8:
            assert u["fills"] == [[900, "AURIC", 2, u["fills"][0][3], "taker"]], u["fills"]
            assert u["pos"]["AURIC"] == 2 and all(o[0] != 900 for o in u["open"])
            return [("pull_all", "AURIC")]
        if n == 9:
            assert not [o for o in u["open"] if o[1] == "AURIC"], u["open"]
            return [("take", "AURIC", -2, a["bid"][0][0], 901)]
        if n == 10:
            assert u["pos"]["AURIC"] == 0, u["pos"]
        if n == 11:
            return "not a list"
        return []
