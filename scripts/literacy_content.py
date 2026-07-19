"""
scripts/literacy_content.py

Starter educational content for the Learning Agent (RAG).
Each entry becomes one row in embedded_content once the embedding step
is wired up. Kept as a plain Python list for now for easy review.

Fields:
- id: stable identifier, used by Strategy Agent's config to reference
      specific modules (e.g. "diversification_basics"). Do not rename
      an id once it's been referenced in a strategy_config.json.
- difficulty: "beginner" | "intermediate" -- lets Strategy Agent sequence
      content instead of retrieving randomly.
- tags: used for filtered retrieval (e.g. Behavior Agent pulling
      "loss_aversion" content when a user panic-sells in simulation).
"""

LITERACY_CONTENT = [
    {
        "id": "diversification_basics",
        "title": "What is Diversification",
        "difficulty": "beginner",
        "tags": ["diversification", "risk", "basics"],
        "content": (
            "Diversification means spreading your money across different investments "
            "instead of putting it all into one stock or asset. The idea is simple: if "
            "one investment performs badly, others may perform well, softening the overall "
            "impact on your portfolio. A portfolio holding only one company's stock is "
            "fully exposed to that one company's risks -- a bad earnings report, a lawsuit, "
            "a product failure. Spreading investments across different companies, industries, "
            "and asset types (stocks, bonds, real estate) reduces this single-point-of-failure "
            "risk, though it does not eliminate risk entirely -- diversification protects "
            "against company-specific risk, not against the whole market falling."
        ),
    },
    {
        "id": "index_funds_explained",
        "title": "Index Funds Explained",
        "difficulty": "beginner",
        "tags": ["index_funds", "etf", "basics"],
        "content": (
            "An index fund is a type of investment that holds a small piece of every "
            "company in a market index (like the S&P 500), instead of trying to pick "
            "individual winning stocks. Because it automatically holds hundreds of "
            "companies at once, buying one index fund gives you instant diversification. "
            "Index funds are popular because they tend to have very low fees, and "
            "historically, most actively-managed funds (where a person tries to pick "
            "winning stocks) fail to beat simple index funds over long periods. This "
            "doesn't mean index funds always go up -- they rise and fall with the overall "
            "market -- but they remove the risk of a single bad stock pick."
        ),
    },
    {
        "id": "etf_vs_mutual_funds",
        "title": "ETFs vs Mutual Funds",
        "difficulty": "beginner",
        "tags": ["etf", "mutual_funds", "basics"],
        "content": (
            "ETFs (Exchange-Traded Funds) and mutual funds both let you buy a bundle of "
            "many investments at once, but they work differently. ETFs trade on a stock "
            "exchange throughout the day, just like a regular stock -- you can buy or sell "
            "at any point while markets are open, and prices move in real time. Mutual "
            "funds are priced only once per day, after markets close, and orders are "
            "processed at that single end-of-day price. ETFs generally have lower minimum "
            "investment amounts and lower fees than actively-managed mutual funds, which is "
            "part of why they've become more popular with everyday investors."
        ),
    },
    {
        "id": "risk_vs_return",
        "title": "Risk vs Return",
        "difficulty": "beginner",
        "tags": ["risk", "return", "basics"],
        "content": (
            "Risk and return are linked: investments with the potential for higher returns "
            "usually come with a higher chance of losing money too, and safer investments "
            "usually offer smaller returns. A savings account is very low risk, but it also "
            "grows your money very slowly. A single tech stock might double in value in a "
            "year, or it might drop by half. There's no investment that offers high returns "
            "with no risk -- when something claims to, it's usually a red flag. Building a "
            "portfolio is really about deciding how much risk you're comfortable taking, "
            "based on your goals and how long you can leave the money invested."
        ),
    },
    {
        "id": "understanding_volatility",
        "title": "Understanding Volatility",
        "difficulty": "beginner",
        "tags": ["volatility", "risk"],
        "content": (
            "Volatility describes how much and how quickly an investment's price moves up "
            "and down. A highly volatile stock might swing 5-10% in a single day; a low-"
            "volatility investment, like a government bond, barely moves day to day. "
            "Volatility isn't the same thing as an investment being 'bad' -- it just means "
            "the ride is bumpier. Someone investing for a goal 20 years away can usually "
            "tolerate more volatility, since there's time to recover from short-term drops. "
            "Someone who needs the money in 6 months generally cannot afford the same "
            "volatility, since a bad drop right before they need the cash could be "
            "permanent for their plans."
        ),
    },
    {
        "id": "what_is_drawdown",
        "title": "What is a Drawdown",
        "difficulty": "intermediate",
        "tags": ["drawdown", "risk", "behavior"],
        "content": (
            "A drawdown is the drop in value from a portfolio's highest point to its "
            "lowest point before it recovers. If a portfolio grows to $10,000 and then "
            "falls to $8,500 before climbing again, that's a 15% drawdown. Drawdowns are a "
            "normal part of investing -- even the overall stock market has experienced "
            "drawdowns of 30-50% during major downturns, and still recovered over time. "
            "What matters most is not whether a drawdown happens, but how an investor "
            "reacts to one -- selling in a panic during a drawdown locks in the loss, while "
            "staying invested gives the portfolio a chance to recover when prices rise "
            "again."
        ),
    },
    {
        "id": "dollar_cost_averaging",
        "title": "Dollar-Cost Averaging",
        "difficulty": "beginner",
        "tags": ["dca", "strategy", "basics"],
        "content": (
            "Dollar-cost averaging means investing a fixed amount of money at regular "
            "intervals (like $200 every month), regardless of whether prices are high or "
            "low that month, instead of investing one large lump sum all at once. This "
            "approach means you naturally buy more shares when prices are low and fewer "
            "shares when prices are high, which averages out your purchase price over "
            "time. Its biggest benefit isn't necessarily higher returns -- it's psychological: "
            "it removes the pressure of trying to guess the 'perfect' time to invest, which "
            "even professional investors struggle to do consistently."
        ),
    },
    {
        "id": "compound_interest",
        "title": "Compound Interest",
        "difficulty": "beginner",
        "tags": ["compounding", "basics"],
        "content": (
            "Compound interest is what happens when the returns your money earns start "
            "earning their own returns. If you invest $1,000 and it grows 10% in a year, "
            "you have $1,100. If it grows another 10% the next year, you don't just earn "
            "$100 again -- you earn 10% of $1,100, or $110, because last year's gains are "
            "now also invested. Over long periods, this effect compounds significantly -- "
            "it's the main reason financial advice so often emphasizes starting to invest "
            "early, since more years in the market means more cycles of compounding, even "
            "if the amount invested each year is small."
        ),
    },
    {
        "id": "asset_allocation",
        "title": "Asset Allocation",
        "difficulty": "intermediate",
        "tags": ["asset_allocation", "risk", "strategy"],
        "content": (
            "Asset allocation is the mix of different investment types in a portfolio -- "
            "commonly stocks, bonds, and cash. Stocks tend to offer higher long-term growth "
            "but with more volatility; bonds tend to be steadier but grow more slowly; cash "
            "is the safest but barely grows at all, and inflation can erode its value over "
            "time. A younger investor with a long time horizon might hold mostly stocks, "
            "since they have time to ride out volatility. Someone closer to needing the "
            "money might shift toward more bonds and cash, prioritizing stability over "
            "growth. There's no single 'correct' allocation -- it depends on goals, time "
            "horizon, and risk tolerance."
        ),
    },
    {
        "id": "rebalancing",
        "title": "Portfolio Rebalancing",
        "difficulty": "intermediate",
        "tags": ["rebalancing", "asset_allocation", "strategy"],
        "content": (
            "Rebalancing means periodically adjusting a portfolio back to its original "
            "target allocation. If someone starts with 70% stocks and 30% bonds, and "
            "stocks then grow faster than bonds over a year, the portfolio might drift to "
            "80% stocks and 20% bonds without any action being taken -- quietly making the "
            "portfolio riskier than originally intended. Rebalancing means selling some of "
            "the outperforming asset and buying more of the underperforming one to restore "
            "the original mix. It can feel counterintuitive -- selling what's doing well -- "
            "but the point isn't to chase returns, it's to keep the portfolio's risk level "
            "consistent with what was originally planned. A common approach is to rebalance "
            "on a fixed schedule, such as once a year."
        ),
    },
    {
        "id": "bonds_basics",
        "title": "Bonds Basics",
        "difficulty": "beginner",
        "tags": ["bonds", "basics"],
        "content": (
            "A bond is essentially a loan you give to a government or company, which pays "
            "you back over time with interest. Bonds are generally considered lower-risk "
            "than stocks, since bondholders are usually paid before stockholders if a "
            "company runs into trouble, and government bonds (especially from stable "
            "governments) are considered among the safest investments that still offer a "
            "return. Bond prices do still move -- they tend to fall when interest rates "
            "rise, since newly-issued bonds then offer better rates, making older, lower-"
            "rate bonds less attractive by comparison."
        ),
    },
    {
        "id": "bull_bear_markets",
        "title": "Bull Markets vs Bear Markets",
        "difficulty": "beginner",
        "tags": ["market_cycles", "basics"],
        "content": (
            "A bull market describes a sustained period where prices are generally rising "
            "and investor confidence is high. A bear market describes a sustained period "
            "(commonly defined as a drop of 20% or more from a recent high) where prices "
            "are generally falling and confidence is low. Markets naturally cycle between "
            "the two over time. New investors often only experience one type of market "
            "when they start, which can create a skewed sense of what's 'normal' -- someone "
            "who starts investing during a strong bull market may not be mentally prepared "
            "for their first real bear market, which is part of why understanding market "
            "cycles matters before investing real money."
        ),
    },
    {
        "id": "loss_aversion_panic_selling",
        "title": "Loss Aversion and Panic Selling",
        "difficulty": "intermediate",
        "tags": ["behavior", "loss_aversion", "psychology"],
        "content": (
            "Loss aversion is a well-documented pattern in behavioral finance: people tend "
            "to feel the pain of a loss roughly twice as strongly as the pleasure of an "
            "equivalent gain. In investing, this often shows up as panic selling -- selling "
            "an investment during a price drop purely out of emotional discomfort, even "
            "when the original reasons for investing haven't changed. Panic selling "
            "converts a temporary paper loss into a permanent, locked-in loss, and often "
            "means missing the recovery that follows. Recognizing this bias in yourself -- "
            "noticing the urge to sell is coming from fear rather than a change in the "
            "underlying investment's fundamentals -- is one of the most valuable skills in "
            "long-term investing."
        ),
    },
    {
        "id": "expense_ratios_fees",
        "title": "Expense Ratios and Fees",
        "difficulty": "beginner",
        "tags": ["fees", "expense_ratio", "index_funds"],
        "content": (
            "An expense ratio is the yearly fee a fund charges, shown as a percentage of "
            "your investment. A 0.03% expense ratio means $3 a year on a $10,000 "
            "investment; a 1.5% expense ratio means $150 a year on the same amount. That "
            "gap seems small year to year, but compounds over decades -- a higher-fee fund "
            "has to earn more just to match a lower-fee fund's actual return, since fees "
            "are deducted regardless of performance. This is a large part of why "
            "low-cost index funds are so often recommended: the fee difference between "
            "funds is one of the few things an investor can control with certainty, "
            "unlike future market returns."
        ),
    },
    {
        "id": "position_sizing",
        "title": "Position Sizing",
        "difficulty": "intermediate",
        "tags": ["position_sizing", "risk", "behavior"],
        "content": (
            "Position sizing is deciding how much of a portfolio to put into any single "
            "investment. Even a good investment idea can hurt a portfolio badly if too "
            "much money is put into it -- a stock that's genuinely a strong pick can still "
            "drop 40% for reasons no one predicted, and the damage from that drop depends "
            "entirely on how large a position it was. A common guideline is to avoid "
            "letting any single stock make up an outsized share of a portfolio, precisely "
            "so that being wrong about one investment doesn't derail the whole plan. "
            "Position sizing is a risk control, separate from and just as important as "
            "picking good investments in the first place."
        ),
    },
    {
        "id": "market_vs_limit_orders",
        "title": "Market Orders vs Limit Orders",
        "difficulty": "beginner",
        "tags": ["order_types", "mechanics", "basics"],
        "content": (
            "A market order buys or sells a stock immediately at whatever the current "
            "price is. It guarantees the trade happens right away but not the exact price "
            "you'll pay, which matters most for fast-moving or thinly-traded stocks. A "
            "limit order instead sets a specific price you're willing to buy or sell at -- "
            "the trade only happens if the market reaches that price, which could mean "
            "waiting, or the order never executing at all if the price is never reached. "
            "Market orders prioritize speed and certainty of execution; limit orders "
            "prioritize price control."
        ),
    },
    {
        "id": "pe_ratio_basics",
        "title": "What is a P/E Ratio",
        "difficulty": "intermediate",
        "tags": ["valuation", "pe_ratio", "fundamentals"],
        "content": (
            "The price-to-earnings (P/E) ratio compares a company's stock price to its "
            "earnings per share, giving a rough sense of how expensive a stock is relative "
            "to the profit it actually generates. A P/E of 20 means investors are paying "
            "$20 for every $1 of the company's annual earnings. A high P/E can mean a "
            "stock is overvalued, or it can mean investors expect strong future growth and "
            "are willing to pay more today for it -- the ratio alone doesn't say which. "
            "P/E ratios are most useful when compared against similar companies in the "
            "same industry, since 'normal' P/E levels vary a lot between sectors like "
            "technology versus utilities."
        ),
    },
]
