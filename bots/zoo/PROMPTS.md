# Zoo prompts

Each prompt goes **after** `SPEC.md`, in one message. `python3 bots/zoo/bundle.py <name>` prints the
two together, ready to paste. Don't edit a prompt once a bot has been written from it: the zoo
compares models on the same words. A new idea is a new prompt with a new name.

The archetypes follow Lopez-Lira's LLM trading agents (value, momentum, market making;
`references/wiki/sources/llm-agents-market-simulation.md`), plus a plain baseline: what an agent
does when simply told to win, which is the organisers' `_LLM_BENCHMARK_`.

## baseline

Write the trading algorithm that you expect to make the most profit in this round. Reply with the
complete file in a single Python code block, and nothing after it.

## market_maker

Write a market-making algorithm for this round. Estimate a fair value for each product, quote
bids and asks around it to earn the spread, take any orders in the book that are mispriced
against your fair value, and manage your inventory so that you are not stuck at a position limit.
Make as much profit as you can. Reply with the complete file in a single Python code block, and
nothing after it.

## mean_reversion

Write a statistical-arbitrage algorithm for this round. Model each product's price with rolling
statistics (for example a moving average and standard deviation), and trade when the price moves
far enough from its typical value that it is likely to come back: buy when it is unusually low,
sell when it is unusually high, and exit as it reverts. Make as much profit as you can. Reply with
the complete file in a single Python code block, and nothing after it.

## momentum

Write a trend-following algorithm for this round. Detect when a product's price is trending (for
example with moving-average crossovers or recent returns), trade in the direction of the trend,
and get out when it fades. Make as much profit as you can. Reply with the complete file in a
single Python code block, and nothing after it.
