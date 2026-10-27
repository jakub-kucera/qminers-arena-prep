"""Our template trading inside an ABIDES market: the market's agents see its orders and react.

Run by export.py under ABIDES's Python (never imported by the repo's code or tests). Once a second
from the open it asks the exchange for the book's top three levels a side and runs the template's
own STRATEGY and EXECUTION on it: trade_product on the book, the position and the fills since the
last call, then execute. Without `resting` every order of ours is cancelled each second before the
new ones go out, as the per-tick engine expires them; with it, execute keeps the quotes that haven't
moved, as the template does where orders rest. ABIDES has no immediate-or-cancel order, so a take's
unfilled part waits for the next second's cancel. ABIDES doesn't enforce the position limit; the
template stays within PARAMS' limit on its own.

The template file is loaded by path with a stub `datamodel` (STRATEGY and EXECUTION don't use it), and
`overrides` sets dotted paths in it as arena.backtest's --set does (e.g. {"PARAMS.ABM.lin_rho3": 3}).
"""

import importlib.util
import sys
import types

from abides_core.utils import str_to_ns
from abides_markets.agents import TradingAgent
from abides_markets.messages.query import QuerySpreadResponseMsg
from abides_markets.orders import Side

SECOND = str_to_ns("1s")


def load_template(path, overrides):
    stub = types.ModuleType("datamodel")
    for name in ("Cancel", "Order", "OrderDepth", "TradingState", "Observation", "Trade", "Listing", "ProsperityEncoder", "Symbol"):
        setattr(stub, name, type(name, (), {}))
    sys.modules.setdefault("datamodel", stub)
    spec = importlib.util.spec_from_file_location("abides_template", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for dotted, value in (overrides or {}).items():
        names = dotted.split(".")
        target = getattr(module, names[0])
        for name in names[1:-1]:
            target = target.setdefault(name, {})
        target[names[-1]] = value
    return module


class TemplateAgent(TradingAgent):
    def __init__(self, id, symbol, template, product="ABM", resting=False, starting_cash=10_000_000, random_state=None):
        super().__init__(id, "TEMPLATE_AGENT", "TemplateAgent", random_state, starting_cash, log_orders=False)
        self.symbol, self.template, self.product, self.resting = symbol, template, product, resting
        self.p = {**template.DEFAULTS, **template.PARAMS[product]} if template is not None else None
        self.memory, self.fills, self.last_mid, self.calls, self.filled = {}, [], None, 0, 0
        self.state = "AWAITING_WAKEUP"

    def wakeup(self, current_time):
        can_trade = super().wakeup(current_time)
        if self.template is None:
            return  # an idle agent: the same market (latency draws) as with a bot, for the replay
        if not can_trade:
            return  # TradingAgent wakes it at the open, get_wake_frequency after it, once it knows the hours
        self.get_current_spread(self.symbol, depth=3)
        self.state = "AWAITING_SPREAD"

    def receive_message(self, current_time, sender_id, message):
        super().receive_message(current_time, sender_id, message)
        if self.state == "AWAITING_SPREAD" and isinstance(message, QuerySpreadResponseMsg):
            self.trade(current_time)
            self.state = "AWAITING_WAKEUP"
            if not self.mkt_closed:
                self.set_wakeup(current_time + SECOND)

    def get_wake_frequency(self):
        return SECOND

    def order_executed(self, order):
        super().order_executed(order)
        quantity = order.quantity if order.side.is_bid() else -order.quantity
        self.fills.append((order.fill_price, quantity))
        self.filled += abs(quantity)

    def trade(self, current_time):
        t = self.template
        bids = [[int(p), int(v)] for p, v in self.known_bids.get(self.symbol, [])]
        asks = [[int(p), int(v)] for p, v in self.known_asks.get(self.symbol, [])]
        if bids and asks:
            self.last_mid = (bids[0][0] + asks[0][0]) / 2
        book = t.Book(bids, asks)
        market = t.Market({self.product: book}, {}, {self.product: self.fills}, self.calls * 100)
        position = self.holdings.get(self.symbol, 0)
        plan = t.trade_product(self.product, book, position, self.p, self.memory, market)
        self.fills, self.calls = [], self.calls + 1
        if not self.resting:
            self.cancel_all_orders()
            resting = []
        else:
            resting = [(order.order_id, order.limit_price, order.quantity if order.side.is_bid() else -order.quantity)
                       for order in self.orders.values()]
        cancels, orders = t.execute(plan, resting)
        for order_id in cancels:
            if order_id in self.orders:
                self.cancel_order(self.orders[order_id])
        for price, quantity, _ioc in orders:
            self.place_limit_order(self.symbol, abs(quantity), Side.BID if quantity > 0 else Side.ASK, int(price))

    def result(self):
        position = self.holdings.get(self.symbol, 0)
        cash = self.holdings["CASH"] - self.starting_cash
        return {"pnl": cash + position * (self.last_mid or 0), "position": position, "filled": self.filled, "calls": self.calls}
