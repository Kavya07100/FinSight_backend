"""
Seeds learning modules 2-8 (SIP through Cutting Losses Early) directly into
Neon -- module 1 ("Emergency Fund Building") is already there, see
scripts/seed_module1.py for that one.

Connects straight to the Neon DATABASE_URL used by migrate_to_neon.py rather
than app.database.engine, since app/.env's DATABASE_URL still points at the
local Postgres instance.
"""
from sqlalchemy import create_engine, text

NEON_URL = "postgresql://neondb_owner:npg_L9s3QfwpbyMX@ep-cool-dust-aznthne3-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
engine = create_engine(NEON_URL)


# ============================================================
# Module: SIP and Rupee Cost Averaging
# ============================================================
ARTICLE_SIP = """A Systematic Investment Plan, or SIP, is a way of investing a fixed amount of money regularly into a mutual fund. For example, an investor may choose to invest ₹5,000 each month. The amount stays fixed, but the number of mutual-fund units bought can change because the fund's NAV, or Net Asset Value per unit, changes over time.

Rupee-cost averaging is the effect of investing the same amount regularly when prices or NAVs move up and down. When the NAV is lower, the fixed investment amount buys more units. When the NAV is higher, the same amount buys fewer units. This does not guarantee profits or protect you from losses, but it can reduce the need to guess the best time to invest.

Why does this matter? A first-time investor may wait indefinitely for the "perfect" time to invest and miss the habit of regular investing. Another investor may put all available money into a fund just before a market fall and feel pressured to sell after seeing a loss. A SIP spreads investments across different dates, although it cannot prevent losses if the investment itself falls.

Consider Kavita, who earns ₹60,000 each month. Assume her essential monthly expenses are:
• Rent: ₹18,000
• Groceries: ₹9,000
• Utilities: ₹3,000
• Transport: ₹4,000
• Insurance: ₹2,000
• Loan payment: ₹14,000

Her total essential monthly expenses are:
₹18,000 + ₹9,000 + ₹3,000 + ₹4,000 + ₹2,000 + ₹14,000 = ₹50,000.

The amount remaining after essential expenses is:
₹60,000 − ₹50,000 = ₹10,000.

Assume Kavita chooses to invest ₹5,000 regularly through a SIP and keep ₹5,000 for other financial needs:
₹10,000 − ₹5,000 = ₹5,000.

In one month, assume the mutual fund's NAV is ₹50. Units purchased are:
₹5,000 ÷ ₹50 = 100 units.

In the next month, assume the NAV falls to ₹40. Units purchased are:
₹5,000 ÷ ₹40 = 125 units.

The total amount invested is:
₹5,000 + ₹5,000 = ₹10,000.

The total units purchased are:
100 + 125 = 225 units.

The average cost per unit is:
₹10,000 ÷ 225 = ₹44.44, approximately.

This shows how the same SIP amount buys more units when the NAV is lower.

Here are four practical steps. First, choose an SIP amount that fits your budget after essential expenses. Second, select a mutual fund that matches your goal, time horizon, and ability to handle risk. Third, set up the SIP on a regular date and maintain enough money in your account for the payment. Fourth, review your investment periodically instead of stopping automatically because of short-term market movements.

A common mistake is believing that a SIP guarantees profits or protects your capital. A SIP is only a method of investing; the value of the mutual fund can still rise or fall.

Takeaway: A SIP helps you invest regularly, while rupee-cost averaging means the same amount can buy more or fewer units as the NAV changes."""

SUMMARY_SIP = [
    "A SIP invests a fixed amount regularly into a mutual fund.",
    "Rupee-cost averaging means a fixed amount generally buys more units at lower NAVs and fewer units at higher NAVs.",
    "A SIP can build investing discipline but does not guarantee profits or prevent losses.",
]

QUESTIONS_SIP = [
    {
        "question": "What is a SIP?",
        "option_a": "A guaranteed-return investment",
        "option_b": "A method of investing a fixed amount regularly",
        "option_c": "A type of bank loan",
        "option_d": "A guarantee against market losses",
        "correct_answer": "b",
        "explanation_correct": "A SIP involves investing a chosen amount at regular intervals.",
        "explanation_wrong_a": "A SIP does not guarantee any return.",
        "explanation_wrong_c": "A SIP is an investment method, not a loan.",
        "explanation_wrong_d": "Investments made through a SIP can still lose value.",
    },
    {
        "question": "What happens to the number of units bought when the same SIP amount is invested at a lower NAV?",
        "option_a": "More units are generally bought",
        "option_b": "Fewer units are always bought",
        "option_c": "No units are bought",
        "option_d": "The NAV becomes fixed",
        "correct_answer": "a",
        "explanation_correct": "Dividing the same investment amount by a lower NAV produces more units.",
        "explanation_wrong_b": "A lower NAV generally allows the same amount to buy more units.",
        "explanation_wrong_c": "A lower NAV does not prevent the purchase of units.",
        "explanation_wrong_d": "Investing through a SIP does not fix the NAV.",
    },
    {
        "question": "What is rupee-cost averaging?",
        "option_a": "Receiving a guaranteed average return",
        "option_b": "Investing the same amount regularly while the NAV changes",
        "option_c": "Buying the same number of units every time",
        "option_d": "Selling investments whenever the NAV falls",
        "correct_answer": "b",
        "explanation_correct": "The fixed investment amount buys different quantities of units as prices or NAVs change.",
        "explanation_wrong_a": "Rupee-cost averaging does not guarantee returns.",
        "explanation_wrong_c": "The number of units usually changes when the NAV changes.",
        "explanation_wrong_d": "Rupee-cost averaging concerns regular investing, not automatic selling.",
    },
    {
        "question": "Does using a SIP guarantee that an investor will make a profit?",
        "option_a": "Yes, because regular investing removes all risk",
        "option_b": "Yes, because NAVs always rise over time",
        "option_c": "No, because the underlying mutual fund can still fall in value",
        "option_d": "No, because SIPs cannot buy mutual-fund units",
        "correct_answer": "c",
        "explanation_correct": "A SIP is only an investment method and the fund's value can still decline.",
        "explanation_wrong_a": "Regular investing does not remove investment risk.",
        "explanation_wrong_b": "NAVs can rise or fall over time.",
        "explanation_wrong_d": "SIP contributions are used to buy mutual-fund units.",
    },
    {
        "question": "Why can a SIP help an investor avoid trying to predict the perfect time to invest?",
        "option_a": "It invests regularly according to a chosen schedule",
        "option_b": "It guarantees the lowest possible NAV",
        "option_c": "It predicts future market movements",
        "option_d": "It prevents the market from falling",
        "correct_answer": "a",
        "explanation_correct": "Regular investments reduce the need to decide on a new entry date each time.",
        "explanation_wrong_b": "A SIP cannot guarantee the lowest NAV.",
        "explanation_wrong_c": "SIPs do not predict market movements.",
        "explanation_wrong_d": "A SIP cannot control market performance.",
    },
    {
        "question": "Why should an investor choose an SIP amount that fits their budget?",
        "option_a": "Because essential expenses should be considered before committing money to investments",
        "option_b": "Because every SIP amount guarantees the same return",
        "option_c": "Because a larger SIP always produces a profit",
        "option_d": "Because a SIP replaces the need for emergency savings",
        "correct_answer": "a",
        "explanation_correct": "An investment commitment should not prevent the investor from meeting essential financial needs.",
        "explanation_wrong_b": "Returns depend on the underlying investment, not simply the SIP amount.",
        "explanation_wrong_c": "A larger investment can also experience larger losses.",
        "explanation_wrong_d": "Emergency savings and investments serve different purposes.",
    },
    {
        "question": "What is a sensible response to a short-term market fall when investing through a SIP?",
        "option_a": "Automatically stop the SIP without reviewing your goal",
        "option_b": "Review your financial goal and investment suitability before making a decision",
        "option_c": "Assume that the SIP has guaranteed future profits",
        "option_d": "Sell every investment immediately",
        "correct_answer": "b",
        "explanation_correct": "Investment decisions should consider goals, time horizon, and risk rather than reacting automatically to short-term movements.",
        "explanation_wrong_a": "A short-term fall alone may not mean the investment is unsuitable.",
        "explanation_wrong_c": "A SIP never guarantees future profits.",
        "explanation_wrong_d": "Immediate selling without considering the situation can turn a temporary decline into a realised loss.",
    },
    {
        "question": "What is the main difference between a SIP and the mutual fund itself?",
        "option_a": "A SIP is a way to invest regularly, while a mutual fund is the investment product",
        "option_b": "A SIP and a mutual fund are exactly the same thing",
        "option_c": "A SIP guarantees returns, while a mutual fund does not",
        "option_d": "A mutual fund is a method of payment, while a SIP is an asset",
        "correct_answer": "a",
        "explanation_correct": "A SIP is an investment method used to make regular contributions into a mutual fund or similar investment.",
        "explanation_wrong_b": "The SIP is the method, while the mutual fund is the underlying investment.",
        "explanation_wrong_c": "Neither a SIP nor a mutual fund guarantees returns.",
        "explanation_wrong_d": "The mutual fund is the investment product, not merely a payment method.",
    },
    {
        "question": "Application — An investor puts ₹6,000 into a mutual fund when the NAV is ₹30 per unit. How many units are purchased?",
        "option_a": "100 units",
        "option_b": "150 units",
        "option_c": "200 units",
        "option_d": "250 units",
        "correct_answer": "c",
        "explanation_correct": "₹6,000 ÷ ₹30 = 200 units.",
        "explanation_wrong_a": "₹6,000 ÷ ₹30 equals 200 units, not 100.",
        "explanation_wrong_b": "₹6,000 ÷ ₹30 equals 200 units, not 150.",
        "explanation_wrong_d": "₹6,000 ÷ ₹30 does not equal 250 units.",
    },
    {
        "question": "Application — An investor invests ₹4,000 at an NAV of ₹40 and then invests another ₹4,000 at an NAV of ₹50. What is the total number of units purchased?",
        "option_a": "160 units",
        "option_b": "180 units",
        "option_c": "200 units",
        "option_d": "220 units",
        "correct_answer": "b",
        "explanation_correct": "100 units + 80 units = 180 units.",
        "explanation_wrong_a": "The first investment buys ₹4,000 ÷ ₹40 = 100 units and the second buys ₹4,000 ÷ ₹50 = 80 units, giving 180 units.",
        "explanation_wrong_c": "The two investments do not together purchase 200 units.",
        "explanation_wrong_d": "The two investments do not together purchase 220 units.",
    },
]


# ============================================================
# Module: What is a Mutual Fund?
# ============================================================
ARTICLE_MF = """A mutual fund is a pool of money collected from many investors. A professional fund manager uses this pooled money to invest in assets such as shares, bonds, or other securities, depending on the fund's objective. When you invest in a mutual fund, you own units of the fund. The value of your investment changes as the value of the fund's investments changes.

Why does this matter? A mutual fund can make investing easier because you do not have to choose and manage every individual security yourself. It can also provide diversification by spreading money across several investments. However, mutual funds are not guaranteed returns. If the investments held by a fund fall in value, your investment can also fall. For example, someone who invests money needed for next month's rent in an equity mutual fund could face a loss when the market falls.

Consider Priya, who earns ₹60,000 a month. Assume her essential monthly expenses are:
• Rent: ₹18,000
• Groceries: ₹10,000
• Electricity and internet: ₹4,000
• Transport: ₹5,000
• Insurance: ₹3,000
• Loan payment: ₹10,000

Her total essential expenses are:
₹18,000 + ₹10,000 + ₹4,000 + ₹5,000 + ₹3,000 + ₹10,000 = ₹50,000.

Her monthly amount left after these essential expenses is:
₹60,000 − ₹50,000 = ₹10,000.

Suppose Priya decides to invest half of this leftover amount in a mutual fund and keep the other half for other goals. Her mutual-fund investment is:
₹10,000 ÷ 2 = ₹5,000.

Assume the mutual fund's NAV, or Net Asset Value per unit, is ₹50 when she invests. The number of units she receives is:
₹5,000 ÷ ₹50 = 100 units.

If the NAV later rises to ₹55, the value of her 100 units becomes:
100 × ₹55 = ₹5,500.

Her gain before applicable costs and taxes is:
₹5,500 − ₹5,000 = ₹500.

If the NAV instead falls to ₹45, the value becomes:
100 × ₹45 = ₹4,500.

The loss would be:
₹5,000 − ₹4,500 = ₹500.

This example shows that mutual funds can grow or fall in value.

Here are four practical steps. First, understand the fund's objective before investing. Second, check whether the fund matches your goal and time horizon. Third, understand that different mutual funds carry different levels of risk. Fourth, invest through a regulated and suitable route and review your investments periodically rather than reacting to every market movement.

A common mistake is choosing a mutual fund only because it recently gave high returns. Past performance does not guarantee future performance. A fund that performed strongly in one period may perform differently later.

Takeaway: A mutual fund lets you invest in a professionally managed pool of investments, but you should choose one based on your goal, time horizon, and ability to handle risk."""

SUMMARY_MF = [
    "A mutual fund pools money from many investors and invests it according to a stated objective.",
    "Mutual funds can provide diversification and professional management, but returns are not guaranteed.",
    "Choose a fund based on your financial goal, time horizon, and ability to handle risk.",
]

QUESTIONS_MF = [
    {
        "question": "What is a mutual fund?",
        "option_a": "A guaranteed-return bank deposit",
        "option_b": "A pool of investors' money managed and invested according to a stated objective",
        "option_c": "A personal savings account",
        "option_d": "A type of insurance policy",
        "correct_answer": "b",
        "explanation_correct": "A mutual fund combines investors' money and invests it according to its objective.",
        "explanation_wrong_a": "Mutual funds do not guarantee returns.",
        "explanation_wrong_c": "A mutual fund is an investment product, not a personal savings account.",
        "explanation_wrong_d": "A mutual fund and insurance policy serve different purposes.",
    },
    {
        "question": "What does an investor generally receive when investing in a mutual fund?",
        "option_a": "Units of the fund",
        "option_b": "Ownership of the fund manager's office",
        "option_c": "A guaranteed monthly income",
        "option_d": "A fixed bank interest rate",
        "correct_answer": "a",
        "explanation_correct": "Investors receive units representing their investment in the mutual fund.",
        "explanation_wrong_b": "Buying mutual-fund units does not give ownership of the fund manager's office.",
        "explanation_wrong_c": "Mutual funds do not guarantee a fixed monthly income.",
        "explanation_wrong_d": "Mutual-fund returns are not the same as a fixed bank interest rate.",
    },
    {
        "question": "Why can mutual funds be useful for first-time investors?",
        "option_a": "They remove all investment risk",
        "option_b": "They can provide diversification and professional management",
        "option_c": "They guarantee profits",
        "option_d": "They prevent market prices from falling",
        "correct_answer": "b",
        "explanation_correct": "Mutual funds can spread investments and are managed according to the fund's strategy.",
        "explanation_wrong_a": "Mutual funds still carry investment risk.",
        "explanation_wrong_c": "Mutual funds cannot guarantee profits.",
        "explanation_wrong_d": "Mutual funds remain affected by market movements.",
    },
    {
        "question": "What does NAV represent in a mutual fund?",
        "option_a": "The value per unit of the fund",
        "option_b": "The investor's monthly salary",
        "option_c": "The fund manager's salary",
        "option_d": "The guaranteed annual return",
        "correct_answer": "a",
        "explanation_correct": "NAV represents the value of each mutual-fund unit.",
        "explanation_wrong_b": "An investor's salary has nothing to do with NAV.",
        "explanation_wrong_c": "NAV does not represent the fund manager's salary.",
        "explanation_wrong_d": "NAV is a unit value, not a guaranteed return.",
    },
    {
        "question": "Why should an investor consider the time horizon before choosing a mutual fund?",
        "option_a": "Different investments may be suitable for different periods and goals",
        "option_b": "A longer time horizon guarantees profits",
        "option_c": "Time horizon determines the fund manager's salary",
        "option_d": "Every mutual fund must be held for the same period",
        "correct_answer": "a",
        "explanation_correct": "The suitability of an investment depends partly on when the money will be needed.",
        "explanation_wrong_b": "A longer time horizon does not guarantee profits.",
        "explanation_wrong_c": "An investor's time horizon does not determine the fund manager's salary.",
        "explanation_wrong_d": "Mutual funds can be used for different investment periods.",
    },
    {
        "question": "Priya needs money for a bill due very soon. Why could investing that money in an equity mutual fund be unsuitable?",
        "option_a": "Equity funds can never be sold",
        "option_b": "The fund's value could fall before she needs the money",
        "option_c": "Equity funds always charge the same fee",
        "option_d": "Mutual funds cannot hold shares",
        "correct_answer": "b",
        "explanation_correct": "Market movements can reduce the investment's value before the money is needed.",
        "explanation_wrong_a": "Mutual-fund units can generally be redeemed according to the fund's rules.",
        "explanation_wrong_c": "Fees and expenses can vary across funds and schemes.",
        "explanation_wrong_d": "Equity mutual funds invest primarily in shares.",
    },
    {
        "question": "Why is choosing a fund only because of its recent high return a mistake?",
        "option_a": "Recent performance guarantees future performance",
        "option_b": "Past performance does not guarantee future performance",
        "option_c": "High returns always mean the fund has no risk",
        "option_d": "Fund returns never change",
        "correct_answer": "b",
        "explanation_correct": "A fund's future performance can differ from its earlier performance.",
        "explanation_wrong_a": "Past performance does not guarantee future results.",
        "explanation_wrong_c": "Higher potential returns can involve investment risk.",
        "explanation_wrong_d": "Fund values can rise or fall over time.",
    },
    {
        "question": "Which approach is most sensible before investing in a mutual fund?",
        "option_a": "Choose the fund with the highest recent return without further research",
        "option_b": "Match the fund's objective and risk level with your goal and time horizon",
        "option_c": "Invest all available money immediately",
        "option_d": "Choose a fund because a friend owns it",
        "correct_answer": "b",
        "explanation_correct": "Investment choices should fit your financial goal, time horizon, and risk ability.",
        "explanation_wrong_a": "Recent returns alone do not show whether a fund suits you.",
        "explanation_wrong_c": "Investing all available money can leave too little for other financial needs.",
        "explanation_wrong_d": "Another person's financial situation may be different from yours.",
    },
    {
        "question": "Application — An investor puts ₹4,000 into a mutual fund when its NAV is ₹40 per unit. How many units does the investor receive?",
        "option_a": "40 units",
        "option_b": "80 units",
        "option_c": "100 units",
        "option_d": "160 units",
        "correct_answer": "c",
        "explanation_correct": "₹4,000 ÷ ₹40 = 100 units.",
        "explanation_wrong_a": "₹4,000 ÷ ₹40 equals 100 units, not 40.",
        "explanation_wrong_b": "₹4,000 ÷ ₹40 equals 100 units, not 80.",
        "explanation_wrong_d": "160 units would require a different investment amount or NAV.",
    },
    {
        "question": "Application — An investor owns 200 mutual-fund units and the NAV is ₹25 per unit. What is the investment's value?",
        "option_a": "₹4,000",
        "option_b": "₹5,000",
        "option_c": "₹6,000",
        "option_d": "₹7,500",
        "correct_answer": "b",
        "explanation_correct": "200 units × ₹25 per unit = ₹5,000.",
        "explanation_wrong_a": "200 × ₹25 equals ₹5,000.",
        "explanation_wrong_c": "200 × ₹25 does not equal ₹6,000.",
        "explanation_wrong_d": "200 × ₹25 does not equal ₹7,500.",
    },
]


# ============================================================
# Module: What is Diversification?
# ============================================================
ARTICLE_DIV = """Diversification means spreading your investment money across different investments instead of putting all of it into one company, sector, or type of asset. The idea is simple: if one investment performs poorly, the impact on your overall portfolio may be reduced because your money is not concentrated in one place.

Why does this matter? Imagine putting all your investment money into shares of one company. If that company faces business problems, its share price may fall sharply, and your entire investment could be affected. Diversification cannot remove all risk or guarantee profits, but it can reduce the risk of one investment causing severe damage to your whole portfolio.

Consider Arjun, who earns ₹70,000 each month. Assume his monthly essential expenses are:
• Rent: ₹20,000
• Groceries: ₹12,000
• Utilities: ₹3,000
• Transport: ₹5,000
• Insurance: ₹4,000
• Loan payment: ₹11,000

His total essential monthly expenses are:
₹20,000 + ₹12,000 + ₹3,000 + ₹5,000 + ₹4,000 + ₹11,000 = ₹55,000.

The money remaining after essential expenses is:
₹70,000 − ₹55,000 = ₹15,000.

Assume Arjun decides to invest this ₹15,000 and spread it across three different investments. His allocation is:
• Equity mutual fund: ₹6,000
• Debt mutual fund: ₹5,000
• Gold investment: ₹4,000

The total invested amount is:
₹6,000 + ₹5,000 + ₹4,000 = ₹15,000.

Suppose the equity mutual fund falls by ₹600, while the debt mutual fund gains ₹200 and the gold investment gains ₹100. The total change in Arjun's investments is:
−₹600 + ₹200 + ₹100 = −₹300.

The value of his ₹15,000 investment becomes:
₹15,000 − ₹300 = ₹14,700.

If the entire ₹15,000 had been invested only in the investment that fell by ₹600, the impact would depend on the size of the loss relative to the full investment. Diversification spreads exposure so that different investments can affect the portfolio differently.

Here are four practical steps. First, avoid putting all your investment money into a single company or sector. Second, consider spreading money across different asset types based on your financial goal and ability to handle risk. Third, understand what you already own because different funds or investments may hold similar underlying assets. Fourth, review your portfolio periodically and rebalance if one investment grows so much that it creates unwanted concentration.

A common mistake is believing that owning many mutual funds automatically means being diversified. Several funds may invest in similar companies, sectors, or asset types. True diversification depends on what the investments actually hold, not simply on how many products you own.

Takeaway: Diversification spreads your money across different investments to reduce the impact of any one investment performing badly, but it cannot eliminate all investment risk."""

SUMMARY_DIV = [
    "Diversification means spreading investments to reduce concentration in any single investment.",
    "It can reduce the impact of one investment performing badly, but it cannot guarantee profits or remove all risk.",
    "Check what you actually own and avoid assuming that many investments automatically mean good diversification.",
]

QUESTIONS_DIV = [
    {
        "question": "What does diversification mean?",
        "option_a": "Putting all money into the best-performing investment",
        "option_b": "Spreading money across different investments",
        "option_c": "Keeping all money as cash",
        "option_d": "Buying and selling investments every day",
        "correct_answer": "b",
        "explanation_correct": "Diversification involves spreading investments rather than concentrating money in one place.",
        "explanation_wrong_a": "Putting everything into one investment creates concentration risk.",
        "explanation_wrong_c": "Diversification concerns how investments are spread, not simply holding all money as cash.",
        "explanation_wrong_d": "Frequent trading is not the definition of diversification.",
    },
    {
        "question": "What is the main purpose of diversification?",
        "option_a": "To guarantee profits",
        "option_b": "To remove every type of investment risk",
        "option_c": "To reduce the impact of one investment performing badly",
        "option_d": "To ensure every investment earns the same return",
        "correct_answer": "c",
        "explanation_correct": "Spreading investments can reduce the damage caused by one poor-performing investment.",
        "explanation_wrong_a": "Diversification cannot guarantee profits.",
        "explanation_wrong_b": "Diversification reduces some risks but cannot eliminate all investment risk.",
        "explanation_wrong_d": "Different investments can perform differently.",
    },
    {
        "question": "Which situation shows concentration risk?",
        "option_a": "Investing across different asset types",
        "option_b": "Checking whether different funds own similar investments",
        "option_c": "Putting all investment money into one company",
        "option_d": "Reviewing a portfolio periodically",
        "correct_answer": "c",
        "explanation_correct": "Relying on one company exposes the entire investment to that company's performance.",
        "explanation_wrong_a": "Spreading across asset types can reduce concentration.",
        "explanation_wrong_b": "Checking underlying holdings can help identify concentration.",
        "explanation_wrong_d": "Periodic review can help manage concentration risk.",
    },
    {
        "question": "Does diversification guarantee that an investor will never lose money?",
        "option_a": "Yes, because all investments will always rise together",
        "option_b": "Yes, because diversification removes market risk",
        "option_c": "No, because diversified investments can still fall in value",
        "option_d": "No, because diversification means holding only cash",
        "correct_answer": "c",
        "explanation_correct": "Even a diversified portfolio can lose value.",
        "explanation_wrong_a": "Investments do not always rise and diversification does not guarantee gains.",
        "explanation_wrong_b": "Diversification cannot remove all market-related risk.",
        "explanation_wrong_d": "Diversification does not mean holding only cash.",
    },
    {
        "question": "Why might owning several mutual funds still result in poor diversification?",
        "option_a": "Mutual funds cannot own investments",
        "option_b": "The funds may invest in similar companies or sectors",
        "option_c": "Every mutual fund always invests in completely different assets",
        "option_d": "More funds automatically eliminate risk",
        "correct_answer": "b",
        "explanation_correct": "Several funds can have overlapping holdings and create hidden concentration.",
        "explanation_wrong_a": "Mutual funds invest in underlying securities or assets.",
        "explanation_wrong_c": "Different funds can hold many of the same investments.",
        "explanation_wrong_d": "Owning more funds does not automatically eliminate investment risk.",
    },
    {
        "question": "What is portfolio rebalancing mainly intended to address?",
        "option_a": "Restoring the portfolio when growth in one investment creates unwanted concentration",
        "option_b": "Guaranteeing that every investment will make a profit",
        "option_c": "Predicting the exact future price of every asset",
        "option_d": "Eliminating all taxes and investment costs",
        "correct_answer": "a",
        "explanation_correct": "Rebalancing can help bring a portfolio back toward its intended allocation.",
        "explanation_wrong_b": "Rebalancing cannot guarantee profits.",
        "explanation_wrong_c": "Future asset prices cannot be predicted exactly through rebalancing.",
        "explanation_wrong_d": "Rebalancing does not eliminate all taxes or costs.",
    },
    {
        "question": "An investor owns shares from several companies in the same industry. What should the investor check?",
        "option_a": "Whether the investments are still heavily exposed to one sector",
        "option_b": "Whether all companies will always give identical returns",
        "option_c": "Whether diversification guarantees profits",
        "option_d": "Whether the number of investments removes all risk",
        "correct_answer": "a",
        "explanation_correct": "Several companies from one sector can still create sector concentration.",
        "explanation_wrong_b": "Companies in the same industry can still perform differently.",
        "explanation_wrong_c": "Diversification never guarantees profits.",
        "explanation_wrong_d": "Having several investments does not remove all risk.",
    },
    {
        "question": "Which approach best reflects sensible diversification?",
        "option_a": "Selecting investments only because they recently performed well",
        "option_b": "Putting all money into one popular company",
        "option_c": "Spreading investments while considering goals, risk, and what the investments actually hold",
        "option_d": "Buying as many investment products as possible without checking them",
        "correct_answer": "c",
        "explanation_correct": "Good diversification considers both the investor's needs and the actual exposure of the investments.",
        "explanation_wrong_a": "Recent performance alone does not ensure suitable diversification.",
        "explanation_wrong_b": "Investing everything in one company creates concentration risk.",
        "explanation_wrong_d": "Buying many products without checking their holdings can still create overlap.",
    },
    {
        "question": "Application — An investor puts ₹8,000 into Investment A and ₹12,000 into Investment B. What is the total amount invested?",
        "option_a": "₹16,000",
        "option_b": "₹18,000",
        "option_c": "₹20,000",
        "option_d": "₹22,000",
        "correct_answer": "c",
        "explanation_correct": "₹8,000 + ₹12,000 = ₹20,000.",
        "explanation_wrong_a": "₹8,000 + ₹12,000 = ₹20,000, not ₹16,000.",
        "explanation_wrong_b": "₹8,000 + ₹12,000 = ₹20,000, not ₹18,000.",
        "explanation_wrong_d": "₹8,000 + ₹12,000 does not equal ₹22,000.",
    },
    {
        "question": "Application — An investor has ₹30,000 invested across several investments. One investment falls by ₹1,200, while the others together gain ₹700. What is the new total value?",
        "option_a": "₹28,900",
        "option_b": "₹29,300",
        "option_c": "₹29,500",
        "option_d": "₹31,900",
        "correct_answer": "c",
        "explanation_correct": "₹30,000 − ₹1,200 + ₹700 = ₹29,500.",
        "explanation_wrong_a": "The net change is −₹1,200 + ₹700 = −₹500, giving ₹29,500.",
        "explanation_wrong_b": "₹30,000 − ₹1,200 + ₹700 equals ₹29,500, not ₹29,300.",
        "explanation_wrong_d": "The losses are greater than the gains, so the final value cannot be above ₹30,000.",
    },
]


# ============================================================
# Module: Risk vs Return
# ============================================================
ARTICLE_RR = """Risk and return are two important ideas in investing. Risk means the possibility that your investment may not perform as expected, including the possibility of losing money. Return means the gain or loss you receive from an investment. In general, investments with the potential for higher returns may also involve higher risk, but higher risk does not guarantee higher returns.

Why does this matter? If you choose an investment without understanding its risk, you may panic when its value falls and sell at a loss. On the other hand, keeping money needed for a long-term goal only in a low-return option may make it harder for your money to grow over time. The aim is not to choose the highest possible return. It is to choose an appropriate balance between risk and return based on your goal, time horizon, and ability to handle losses.

Consider Neha, who earns ₹80,000 each month. Assume her essential monthly expenses are:
• Rent: ₹25,000
• Groceries: ₹12,000
• Utilities: ₹4,000
• Transport: ₹6,000
• Insurance: ₹5,000
• Loan payment: ₹13,000

Her total essential monthly expenses are:
₹25,000 + ₹12,000 + ₹4,000 + ₹6,000 + ₹5,000 + ₹13,000 = ₹65,000.

The amount remaining after essential expenses is:
₹80,000 − ₹65,000 = ₹15,000.

Assume Neha invests this ₹15,000 in an investment whose value can rise or fall. If the investment gains ₹1,500, its new value becomes:
₹15,000 + ₹1,500 = ₹16,500.

Her return in rupees is ₹1,500.

If the investment instead loses ₹1,500, its new value becomes:
₹15,000 − ₹1,500 = ₹13,500.

Her loss in rupees is ₹1,500.

This example shows that the same investment can produce either a gain or a loss. The possibility of different outcomes is part of investment risk. Before investing, Neha should consider whether she can afford a fall in value and whether she can leave the money invested for the required period.

Here are four practical steps. First, identify when you will need the money because shorter timelines may require greater focus on stability and access. Second, understand the risks of the investment instead of looking only at possible returns. Third, match your investments with your financial goal and your ability to handle losses. Fourth, diversify your investments so that one investment does not have too much influence on your overall portfolio.

A common mistake is assuming that an investment with the highest potential return is automatically the best choice. A higher potential return may come with greater uncertainty, and the investment may not suit your needs.

Takeaway: Good investing is about balancing the return you want with the level of risk you understand and can handle."""

SUMMARY_RR = [
    "Risk is the possibility of outcomes different from what you expect, including losing money, while return is the gain or loss from an investment.",
    "Higher potential returns can involve higher risk, but higher risk never guarantees higher returns.",
    "Choose investments based on your goal, time horizon, and ability to handle losses.",
]

QUESTIONS_RR = [
    {
        "question": "What does investment risk mean?",
        "option_a": "A guaranteed profit from an investment",
        "option_b": "The possibility that an investment may not perform as expected, including a loss",
        "option_c": "The amount of salary an investor earns",
        "option_d": "A fixed return paid by every investment",
        "correct_answer": "b",
        "explanation_correct": "Risk includes the possibility of outcomes different from expectations, including losing money.",
        "explanation_wrong_a": "Investment risk does not guarantee a profit.",
        "explanation_wrong_c": "An investor's salary is separate from investment risk.",
        "explanation_wrong_d": "Investments do not all provide fixed returns.",
    },
    {
        "question": "What does return mean in investing?",
        "option_a": "Only a guaranteed profit",
        "option_b": "The gain or loss from an investment",
        "option_c": "The number of investments a person owns",
        "option_d": "The amount of risk an investor avoids",
        "correct_answer": "b",
        "explanation_correct": "Return describes the gain or loss produced by an investment.",
        "explanation_wrong_a": "Return can be negative when an investment loses value.",
        "explanation_wrong_c": "The number of investments does not define return.",
        "explanation_wrong_d": "Avoiding risk is not the meaning of investment return.",
    },
    {
        "question": "Which statement about higher-risk investments is correct?",
        "option_a": "They always produce higher returns",
        "option_b": "They guarantee that investors will not lose money",
        "option_c": "They may offer higher potential returns but can also involve greater uncertainty",
        "option_d": "They always perform better than lower-risk investments",
        "correct_answer": "c",
        "explanation_correct": "Greater potential returns can come with greater uncertainty and possible losses.",
        "explanation_wrong_a": "Higher risk does not guarantee a higher return.",
        "explanation_wrong_b": "Higher-risk investments can lose value.",
        "explanation_wrong_d": "Performance can vary and higher risk does not ensure better results.",
    },
    {
        "question": "Which factor is important when choosing an investment?",
        "option_a": "Your financial goal and ability to handle losses",
        "option_b": "Only the highest advertised return",
        "option_c": "What every other investor is buying",
        "option_d": "The most recent market rumour",
        "correct_answer": "a",
        "explanation_correct": "Suitable investments should match your goals and ability to handle risk.",
        "explanation_wrong_b": "Potential return alone does not show whether an investment suits you.",
        "explanation_wrong_c": "Another investor may have different goals and financial circumstances.",
        "explanation_wrong_d": "Investment decisions should not be based on unverified rumours.",
    },
    {
        "question": "Why is time horizon important when considering risk?",
        "option_a": "It helps determine when you will need the money and how much volatility you may be able to tolerate",
        "option_b": "It guarantees that every investment will become profitable",
        "option_c": "It determines the exact future market price",
        "option_d": "It removes all investment risk",
        "correct_answer": "a",
        "explanation_correct": "The time available before you need the money can affect which risks are suitable.",
        "explanation_wrong_b": "Having more or less time does not guarantee profits.",
        "explanation_wrong_c": "Time horizon cannot predict exact future prices.",
        "explanation_wrong_d": "No time horizon can remove all investment risk.",
    },
    {
        "question": "What could happen if an investor panics and sells after a temporary fall in value?",
        "option_a": "The investor automatically receives a guaranteed profit",
        "option_b": "The investor may turn a temporary decline into an actual loss",
        "option_c": "The investment becomes completely risk-free",
        "option_d": "The market is forced to rise immediately",
        "correct_answer": "b",
        "explanation_correct": "Selling can lock in the lower value and make the loss real.",
        "explanation_wrong_a": "Selling after a fall does not guarantee a profit.",
        "explanation_wrong_c": "Selling does not remove the risks involved in investing.",
        "explanation_wrong_d": "One investor's sale does not force the market to rise.",
    },
    {
        "question": "Which investor is making the more suitable decision?",
        "option_a": "An investor choosing only the investment with the highest potential return",
        "option_b": "An investor matching investments with financial goals, time horizon, and ability to handle losses",
        "option_c": "An investor ignoring possible losses",
        "option_d": "An investor investing money needed immediately into a highly volatile asset",
        "correct_answer": "b",
        "explanation_correct": "Suitable investing considers goals, time horizon, and risk tolerance together.",
        "explanation_wrong_a": "The highest potential return may come with unsuitable risk.",
        "explanation_wrong_c": "Understanding possible losses is necessary for informed investing.",
        "explanation_wrong_d": "Money needed immediately may be unsuitable for a highly volatile investment.",
    },
    {
        "question": "How can diversification help when managing investment risk?",
        "option_a": "It guarantees profits every year",
        "option_b": "It spreads exposure so one investment may have less impact on the overall portfolio",
        "option_c": "It ensures every investment earns the same return",
        "option_d": "It completely removes the possibility of losses",
        "correct_answer": "b",
        "explanation_correct": "Spreading investments can reduce the impact of one poor-performing investment.",
        "explanation_wrong_a": "Diversification cannot guarantee profits.",
        "explanation_wrong_c": "Different investments can produce different returns.",
        "explanation_wrong_d": "Diversification cannot eliminate all investment risk.",
    },
    {
        "question": "Application — An investor puts ₹20,000 into an investment. The investment gains ₹2,000. What is the new value?",
        "option_a": "₹18,000",
        "option_b": "₹20,000",
        "option_c": "₹22,000",
        "option_d": "₹24,000",
        "correct_answer": "c",
        "explanation_correct": "₹20,000 + ₹2,000 = ₹22,000.",
        "explanation_wrong_a": "A gain of ₹2,000 is added to ₹20,000.",
        "explanation_wrong_b": "The investment value changes after the ₹2,000 gain.",
        "explanation_wrong_d": "₹20,000 + ₹2,000 does not equal ₹24,000.",
    },
    {
        "question": "Application — An investor puts ₹25,000 into an investment. The investment later loses ₹3,000. What is the new value?",
        "option_a": "₹22,000",
        "option_b": "₹25,000",
        "option_c": "₹28,000",
        "option_d": "₹30,000",
        "correct_answer": "a",
        "explanation_correct": "₹25,000 − ₹3,000 = ₹22,000.",
        "explanation_wrong_b": "The ₹3,000 loss reduces the original investment value.",
        "explanation_wrong_c": "A loss is subtracted rather than added.",
        "explanation_wrong_d": "The investment did not gain ₹5,000.",
    },
]


# ============================================================
# Module: Index Funds
# ============================================================
ARTICLE_IF = """An index fund is a type of mutual fund designed to track a specific market index. A market index is a group of securities used to represent a part of the market. Instead of a fund manager actively choosing which securities to buy and sell in an attempt to beat the market, an index fund generally aims to hold the same securities, or a similar set of securities, as the index it follows.

Why does this matter? An index fund offers a simple way to invest in a broad group of companies or securities through one investment. This can help with diversification. However, an index fund does not guarantee profits or protect you from market falls. If the index it tracks falls, the value of the index fund can also fall. Someone who invests money needed soon may therefore face a loss when the money is required.

Consider Aman, who earns ₹75,000 each month. Assume his essential monthly expenses are:
• Rent: ₹22,000
• Groceries: ₹11,000
• Utilities: ₹3,000
• Transport: ₹5,000
• Insurance: ₹4,000
• Loan payment: ₹15,000

His total essential monthly expenses are:
₹22,000 + ₹11,000 + ₹3,000 + ₹5,000 + ₹4,000 + ₹15,000 = ₹60,000.

The money remaining after essential expenses is:
₹75,000 − ₹60,000 = ₹15,000.

Assume Aman decides to invest ₹10,000 from this remaining amount in an index fund and keep the other ₹5,000 for other financial needs:
₹15,000 − ₹10,000 = ₹5,000.

Assume the index fund's NAV is ₹100 when Aman invests. The number of units he receives is:
₹10,000 ÷ ₹100 = 100 units.

If the NAV later rises to ₹110, the value of his investment becomes:
100 × ₹110 = ₹11,000.

His gain before applicable costs and taxes is:
₹11,000 − ₹10,000 = ₹1,000.

If the NAV instead falls to ₹90, the value becomes:
100 × ₹90 = ₹9,000.

His loss before applicable costs and taxes is:
₹10,000 − ₹9,000 = ₹1,000.

This shows that an index fund follows the performance of its underlying index, subject to factors such as expenses and tracking differences. Its value can rise or fall with the securities it holds.

Here are four practical steps. First, understand which index the fund is designed to track. Second, check whether the fund suits your financial goal and time horizon. Third, compare relevant features such as costs and how closely the fund has tracked its index. Fourth, review your investment periodically without reacting to every short-term market movement.

A common mistake is assuming that an index fund is completely risk-free because it invests in many securities. Diversification can reduce the impact of one company, but the overall market or index can still fall.

Takeaway: An index fund is a simple way to track a market index, offering diversification but still carrying market risk."""

SUMMARY_IF = [
    "An index fund aims to track the performance of a specific market index rather than actively trying to beat it.",
    "It can provide diversification through one investment, but its value can still rise or fall with the market.",
    "Before investing, understand the index, costs, tracking differences, and whether the fund suits your goal and time horizon.",
]

QUESTIONS_IF = [
    {
        "question": "What is an index fund designed to do?",
        "option_a": "Guarantee a fixed return",
        "option_b": "Track the performance of a specific market index",
        "option_c": "Invest only in one company",
        "option_d": "Avoid all market movements",
        "correct_answer": "b",
        "explanation_correct": "An index fund aims to follow the performance of its chosen market index.",
        "explanation_wrong_a": "Index funds do not guarantee fixed returns.",
        "explanation_wrong_c": "An index fund generally invests across the securities represented by its index or a similar set.",
        "explanation_wrong_d": "An index fund can rise or fall with the market it tracks.",
    },
    {
        "question": "What is one potential benefit of investing in an index fund?",
        "option_a": "Guaranteed profits",
        "option_b": "Complete protection from losses",
        "option_c": "Exposure to a group of securities through one investment",
        "option_d": "A fixed bank interest rate",
        "correct_answer": "c",
        "explanation_correct": "One index fund can provide exposure to multiple securities.",
        "explanation_wrong_a": "Index funds cannot guarantee profits.",
        "explanation_wrong_b": "Index funds can lose value when their underlying market falls.",
        "explanation_wrong_d": "An index fund does not provide a fixed bank interest rate.",
    },
    {
        "question": "If the market index tracked by an index fund falls, what can happen to the fund?",
        "option_a": "Its value can also fall",
        "option_b": "Its value is guaranteed to rise",
        "option_c": "The investor automatically receives a profit",
        "option_d": "The fund becomes a fixed deposit",
        "correct_answer": "a",
        "explanation_correct": "An index fund generally follows the performance of its underlying index.",
        "explanation_wrong_b": "A falling index can lead to a falling fund value.",
        "explanation_wrong_c": "A market decline does not automatically create a profit.",
        "explanation_wrong_d": "An index fund remains an investment fund.",
    },
    {
        "question": "What does an index fund generally try to do instead of actively selecting securities to beat the market?",
        "option_a": "Track a chosen market index",
        "option_b": "Guarantee the highest return",
        "option_c": "Avoid holding securities",
        "option_d": "Predict exact future prices",
        "correct_answer": "a",
        "explanation_correct": "The fund's objective is generally to follow its chosen index.",
        "explanation_wrong_b": "Tracking an index does not guarantee the highest return.",
        "explanation_wrong_c": "An index fund invests in securities to provide index exposure.",
        "explanation_wrong_d": "Index funds do not depend on predicting exact future prices.",
    },
    {
        "question": "Why should an investor understand which index an index fund tracks?",
        "option_a": "Different indexes can provide exposure to different groups of securities",
        "option_b": "Every index contains exactly the same investments",
        "option_c": "The index guarantees a profit",
        "option_d": "The index determines an investor's salary",
        "correct_answer": "a",
        "explanation_correct": "Different indexes can represent different parts of the market.",
        "explanation_wrong_b": "Indexes can contain different securities and follow different rules.",
        "explanation_wrong_c": "Following an index does not guarantee profits.",
        "explanation_wrong_d": "An index has no connection to an investor's salary.",
    },
    {
        "question": "Why can an index fund still involve risk even when it holds many securities?",
        "option_a": "Diversification guarantees a market fall",
        "option_b": "The overall market or index can still decline",
        "option_c": "Every company in the index always rises",
        "option_d": "Index funds cannot change in value",
        "correct_answer": "b",
        "explanation_correct": "Diversification cannot prevent the entire market or index from falling.",
        "explanation_wrong_a": "Diversification does not guarantee a market fall.",
        "explanation_wrong_c": "Companies can rise or fall in value.",
        "explanation_wrong_d": "Index-fund values can change as their underlying investments change.",
    },
    {
        "question": "What is a sensible factor to consider when comparing index funds?",
        "option_a": "Whether the fund has the most exciting name",
        "option_b": "Relevant costs and how closely the fund has tracked its index",
        "option_c": "Whether a friend recently bought it",
        "option_d": "Whether the fund guarantees profits",
        "correct_answer": "b",
        "explanation_correct": "Costs and tracking differences can affect how closely an investor's experience follows the index.",
        "explanation_wrong_a": "A fund's name does not determine its suitability or performance.",
        "explanation_wrong_c": "Another person's investment may not suit your own goals.",
        "explanation_wrong_d": "Index funds do not guarantee profits.",
    },
    {
        "question": "Why may an index fund be unsuitable for money needed very soon?",
        "option_a": "Index funds cannot be sold",
        "option_b": "The fund's value may fall before the money is needed",
        "option_c": "Index funds always charge the highest costs",
        "option_d": "Index funds never hold securities",
        "correct_answer": "b",
        "explanation_correct": "Market movements can reduce the value of an index fund over a short period.",
        "explanation_wrong_a": "Index-fund units can generally be redeemed or sold according to the product structure and applicable rules.",
        "explanation_wrong_c": "Costs vary and index funds are not automatically the most expensive option.",
        "explanation_wrong_d": "Index funds hold securities or provide exposure to securities represented by an index.",
    },
    {
        "question": "Application — An investor puts ₹12,000 into an index fund when its NAV is ₹60 per unit. How many units does the investor receive?",
        "option_a": "100 units",
        "option_b": "150 units",
        "option_c": "200 units",
        "option_d": "250 units",
        "correct_answer": "c",
        "explanation_correct": "₹12,000 ÷ ₹60 = 200 units.",
        "explanation_wrong_a": "₹12,000 ÷ ₹60 equals 200 units, not 100.",
        "explanation_wrong_b": "₹12,000 ÷ ₹60 equals 200 units, not 150.",
        "explanation_wrong_d": "₹12,000 ÷ ₹60 does not equal 250.",
    },
    {
        "question": "Application — An investor owns 150 units of an index fund and the NAV rises to ₹80 per unit. What is the value of the investment?",
        "option_a": "₹10,000",
        "option_b": "₹11,000",
        "option_c": "₹12,000",
        "option_d": "₹13,000",
        "correct_answer": "c",
        "explanation_correct": "150 × ₹80 = ₹12,000.",
        "explanation_wrong_a": "150 × ₹80 equals ₹12,000, not ₹10,000.",
        "explanation_wrong_b": "150 × ₹80 equals ₹12,000, not ₹11,000.",
        "explanation_wrong_d": "150 × ₹80 does not equal ₹13,000.",
    },
]


# ============================================================
# Module: Understanding Market Volatility
# ============================================================
ARTICLE_MV = """Market volatility means the speed and size of changes in the price or value of an investment over time. When prices move up and down sharply or frequently, the market is considered more volatile. Volatility is not the same as a permanent loss. A temporary fall in value can later reverse, while a permanent loss happens when an investment is sold or loses value without recovery.

Why does this matter? A first-time investor may see the value of an investment fall and panic. Selling immediately without considering the reason for the investment, the time horizon, or the risk involved can turn a temporary fall into an actual loss. At the same time, ignoring volatility completely can also be risky if the investment no longer suits the investor's financial goal.

Consider Rahul, who earns ₹70,000 each month. Assume his essential monthly expenses are:
• Rent: ₹20,000
• Groceries: ₹10,000
• Utilities: ₹4,000
• Transport: ₹5,000
• Insurance: ₹3,000
• Loan payment: ₹13,000

His total essential monthly expenses are:
₹20,000 + ₹10,000 + ₹4,000 + ₹5,000 + ₹3,000 + ₹13,000 = ₹55,000.

The amount remaining after essential expenses is:
₹70,000 − ₹55,000 = ₹15,000.

Assume Rahul invests ₹10,000 from this amount and keeps ₹5,000 for other financial needs:
₹15,000 − ₹10,000 = ₹5,000.

Suppose Rahul's investment rises by ₹1,000. Its value becomes:
₹10,000 + ₹1,000 = ₹11,000.

Later, suppose the investment falls by ₹1,500 from ₹11,000. Its value becomes:
₹11,000 − ₹1,500 = ₹9,500.

Rahul's investment is now below his original ₹10,000 investment by:
₹10,000 − ₹9,500 = ₹500.

This example shows that investment values can move up and down. A fall after a rise does not always mean an investment is unsuitable, and a rise does not guarantee that the value will continue increasing.

Here are four practical steps for handling volatility. First, invest according to your financial goal and time horizon rather than short-term market excitement. Second, understand how much value fluctuation you can financially and emotionally handle before investing. Third, diversify so that one investment does not have too much influence on your overall portfolio. Fourth, review major changes in your financial situation or investment suitability, but avoid making decisions based only on daily market movements.

A common mistake is checking investment prices repeatedly and selling immediately whenever the market falls. Short-term movements are a normal part of many market-linked investments. Before acting, consider why you invested, when you need the money, and whether your original investment plan still makes sense.

Takeaway: Market volatility means investment values can move sharply up or down, so investors should focus on goals, time horizon, and risk rather than reacting emotionally to every market movement."""

SUMMARY_MV = [
    "Market volatility refers to how sharply and frequently investment values move up and down.",
    "A temporary fall does not automatically mean a permanent loss, but selling can make a loss real.",
    "Diversification, a suitable time horizon, and disciplined decision-making can help investors manage volatility.",
]

QUESTIONS_MV = [
    {
        "question": "What does market volatility describe?",
        "option_a": "Guaranteed investment profits",
        "option_b": "The speed and size of changes in investment prices or values",
        "option_c": "A fixed interest rate",
        "option_d": "The amount of salary an investor earns",
        "correct_answer": "b",
        "explanation_correct": "Volatility describes how much and how quickly investment values can change.",
        "explanation_wrong_a": "Volatility does not guarantee profits.",
        "explanation_wrong_c": "A fixed interest rate does not describe changing market values.",
        "explanation_wrong_d": "An investor's salary is unrelated to market volatility.",
    },
    {
        "question": "Does a volatile investment always mean the investor has permanently lost money?",
        "option_a": "Yes, every fall is permanent",
        "option_b": "Yes, volatility always guarantees a loss",
        "option_c": "No, a temporary fall can later reverse",
        "option_d": "No, because volatile investments can never fall",
        "correct_answer": "c",
        "explanation_correct": "A fall in value may be temporary if the investment later recovers.",
        "explanation_wrong_a": "Some declines may be temporary and investment values can recover.",
        "explanation_wrong_b": "Volatility can involve both upward and downward movements.",
        "explanation_wrong_d": "Volatile investments can rise or fall.",
    },
    {
        "question": "Which behaviour can make a temporary market decline become an actual loss?",
        "option_a": "Reviewing whether the investment still suits your goal",
        "option_b": "Selling the investment after a fall",
        "option_c": "Understanding the investment's risk before buying",
        "option_d": "Diversifying investments",
        "correct_answer": "b",
        "explanation_correct": "Selling at a lower value can lock in the loss.",
        "explanation_wrong_a": "Reviewing suitability helps support informed decisions.",
        "explanation_wrong_c": "Understanding risk helps prepare for possible price movements.",
        "explanation_wrong_d": "Diversification can reduce concentration risk.",
    },
    {
        "question": "Which factor should an investor consider when dealing with market volatility?",
        "option_a": "Financial goal and time horizon",
        "option_b": "Only today's market price",
        "option_c": "Every market rumour",
        "option_d": "The investment choices of strangers",
        "correct_answer": "a",
        "explanation_correct": "Investment decisions should be connected to the investor's goals and when the money will be needed.",
        "explanation_wrong_b": "One day's price movement may not determine long-term suitability.",
        "explanation_wrong_c": "Unverified rumours are not a reliable basis for investment decisions.",
        "explanation_wrong_d": "Another person's investments may not suit your financial situation.",
    },
    {
        "question": "Why can checking investment prices repeatedly be a problem?",
        "option_a": "It guarantees that investments will fall",
        "option_b": "It may encourage emotional decisions based on short-term movements",
        "option_c": "It permanently stops market volatility",
        "option_d": "It guarantees better returns",
        "correct_answer": "b",
        "explanation_correct": "Frequent monitoring can increase the temptation to react emotionally to normal market changes.",
        "explanation_wrong_a": "Checking prices does not determine market direction.",
        "explanation_wrong_c": "Checking prices cannot stop markets from moving.",
        "explanation_wrong_d": "Frequent checking does not guarantee higher returns.",
    },
    {
        "question": "Why is diversification useful during volatile periods?",
        "option_a": "It guarantees that the portfolio will rise",
        "option_b": "It can reduce the impact of one investment performing badly",
        "option_c": "It prevents all investments from ever falling",
        "option_d": "It predicts the next market movement",
        "correct_answer": "b",
        "explanation_correct": "Spreading investments can reduce the influence of one poor-performing investment.",
        "explanation_wrong_a": "Diversification cannot guarantee gains.",
        "explanation_wrong_c": "Even diversified investments can decline in value.",
        "explanation_wrong_d": "Diversification does not predict market movements.",
    },
    {
        "question": "An investor experiences a market fall but does not need the invested money soon. What is the most sensible first step?",
        "option_a": "Sell immediately without reviewing the investment",
        "option_b": "Review the financial goal, time horizon, and whether the investment still suits the investor",
        "option_c": "Assume the market will definitely recover",
        "option_d": "Invest all available savings immediately",
        "correct_answer": "b",
        "explanation_correct": "The investor should assess whether the original investment remains suitable before acting.",
        "explanation_wrong_a": "Selling automatically may turn a temporary decline into a realised loss.",
        "explanation_wrong_c": "Future market recovery is never guaranteed.",
        "explanation_wrong_d": "Investing all available savings may create unnecessary financial risk.",
    },
    {
        "question": "Which situation best shows sensible behaviour during market volatility?",
        "option_a": "Changing the entire portfolio after every daily market movement",
        "option_b": "Making decisions only after considering goals, risk, and time horizon",
        "option_c": "Following social-media rumours about market crashes",
        "option_d": "Assuming a recent price rise will continue forever",
        "correct_answer": "b",
        "explanation_correct": "Goals, risk, and time horizon provide a more suitable basis for investment decisions.",
        "explanation_wrong_a": "Daily changes alone may not justify major portfolio decisions.",
        "explanation_wrong_c": "Unverified information can lead to poor financial decisions.",
        "explanation_wrong_d": "Past or recent price movements do not guarantee future performance.",
    },
    {
        "question": "Application — An investor puts ₹20,000 into an investment. Its value rises by ₹3,000 and then falls by ₹5,000. What is the final value?",
        "option_a": "₹18,000",
        "option_b": "₹20,000",
        "option_c": "₹22,000",
        "option_d": "₹28,000",
        "correct_answer": "a",
        "explanation_correct": "₹20,000 + ₹3,000 − ₹5,000 = ₹18,000.",
        "explanation_wrong_b": "The overall change is a loss of ₹2,000.",
        "explanation_wrong_c": "₹22,000 is the value before the ₹5,000 fall.",
        "explanation_wrong_d": "₹28,000 would result from adding both changes.",
    },
    {
        "question": "Application — An investment is worth ₹25,000 and then falls by ₹4,000. What is its new value?",
        "option_a": "₹19,000",
        "option_b": "₹21,000",
        "option_c": "₹25,000",
        "option_d": "₹29,000",
        "correct_answer": "b",
        "explanation_correct": "₹25,000 − ₹4,000 = ₹21,000.",
        "explanation_wrong_a": "₹25,000 − ₹4,000 = ₹21,000, not ₹19,000.",
        "explanation_wrong_c": "The ₹4,000 fall reduces the original value.",
        "explanation_wrong_d": "A fall is subtracted, not added.",
    },
]


# ============================================================
# Module: When to Sell: Cutting Losses Early
# ============================================================
ARTICLE_CL = """"Cutting losses early" means selling an investment when there is a clear reason to believe that continuing to hold it no longer fits your investment plan. It does not mean selling automatically whenever the price falls. Investment values can move up and down, and a temporary fall alone is not enough reason to sell.

Why does this matter? Imagine buying an investment because you expected a company or fund to meet a particular goal. Later, the reason for buying changes: the business weakens, the investment becomes too risky for you, or you discover that it no longer matches your financial goal. Continuing to hold it simply because you hope to recover your original purchase price can expose you to further losses. On the other hand, selling every time the market falls can also lock in losses unnecessarily.

Consider Meera, who earns ₹70,000 each month. Assume her essential monthly expenses are:
• Rent: ₹20,000
• Groceries: ₹10,000
• Utilities: ₹4,000
• Transport: ₹5,000
• Insurance: ₹3,000
• Loan payment: ₹13,000

Her total essential monthly expenses are:
₹20,000 + ₹10,000 + ₹4,000 + ₹5,000 + ₹3,000 + ₹13,000 = ₹55,000.

The money remaining after essential expenses is:
₹70,000 − ₹55,000 = ₹15,000.

Assume Meera invests ₹10,000 and keeps ₹5,000 for other financial needs:
₹15,000 − ₹10,000 = ₹5,000.

Later, the investment falls by ₹2,000. Its value becomes:
₹10,000 − ₹2,000 = ₹8,000.

Meera then reviews the investment. Assume she finds that the reason she originally invested no longer applies and the investment no longer matches her financial goal. She decides to sell at ₹8,000. Her realised loss is:
₹10,000 − ₹8,000 = ₹2,000.

If Meera held the investment without reviewing the changed situation and it later fell by another ₹1,000, its value would become:
₹8,000 − ₹1,000 = ₹7,000.

The total loss from the original investment would then be:
₹10,000 − ₹7,000 = ₹3,000.

This example does not mean every falling investment should be sold. The key is to review the reason for holding it rather than focusing only on the purchase price.

Here are four practical steps. First, write down why you are buying an investment before investing. Second, review whether that reason is still valid when the investment falls. Third, check whether your financial goal, time horizon, or ability to handle risk has changed. Fourth, make a decision based on current information and your plan rather than trying to "get back to even" emotionally.

A common mistake is holding an investment only because you do not want to accept a loss. The original purchase price does not determine what the investment will do next.

Takeaway: Cut losses when the reason for owning an investment has clearly changed, not simply because its price has fallen."""

SUMMARY_CL = [
    "A falling price alone is not automatically a reason to sell an investment.",
    "Review whether your original investment reason, financial goal, time horizon, or risk ability has changed.",
    "Avoid holding an unsuitable investment only because you hope to recover the original purchase price.",
]

QUESTIONS_CL = [
    {
        "question": 'What does "cutting losses" mean in investing?',
        "option_a": "Selling automatically whenever an investment falls",
        "option_b": "Reviewing and selling an investment when there is a valid reason it no longer fits the investment plan",
        "option_c": "Never accepting any investment loss",
        "option_d": "Buying more whenever an investment falls",
        "correct_answer": "b",
        "explanation_correct": "Selling should be based on a valid change in the investment case or suitability.",
        "explanation_wrong_a": "A price fall alone does not automatically mean the investment should be sold.",
        "explanation_wrong_c": "Investment losses can occur and cannot always be avoided.",
        "explanation_wrong_d": "Buying more after a fall may increase risk if the investment is no longer suitable.",
    },
    {
        "question": "Which is a sensible reason to consider selling an investment?",
        "option_a": "The investment fell in value for one day",
        "option_b": "The original reason for investing is no longer valid",
        "option_c": "Another investor made a different choice",
        "option_d": "The investor wants to avoid ever seeing a negative return",
        "correct_answer": "b",
        "explanation_correct": "A change in the original investment case can be a valid reason to reassess and sell.",
        "explanation_wrong_a": "Short-term price movement alone may not change the investment's suitability.",
        "explanation_wrong_c": "Another investor may have different goals and circumstances.",
        "explanation_wrong_d": "Avoiding every negative return is not realistic in investing.",
    },
    {
        "question": "Why can focusing only on the original purchase price be a mistake?",
        "option_a": "The original purchase price guarantees future returns",
        "option_b": "The investment's future performance depends on current and future factors, not the price you paid",
        "option_c": "The original purchase price prevents the investment from falling",
        "option_d": "Every investment always returns to its purchase price",
        "correct_answer": "b",
        "explanation_correct": "The current investment decision should consider present information and future prospects.",
        "explanation_wrong_a": "The purchase price does not guarantee future returns.",
        "explanation_wrong_c": "Knowing the purchase price does not stop market movements.",
        "explanation_wrong_d": "There is no guarantee that an investment will return to its earlier price.",
    },
    {
        "question": "What should an investor do before deciding whether to sell after a price fall?",
        "option_a": "Review whether the original investment reason and financial plan are still valid",
        "option_b": "Sell immediately without checking anything",
        "option_c": "Assume the investment will definitely recover",
        "option_d": "Follow an unverified market rumour",
        "correct_answer": "a",
        "explanation_correct": "Reviewing the investment case helps separate a valid concern from normal market movement.",
        "explanation_wrong_b": "An automatic sale may be based on emotion rather than analysis.",
        "explanation_wrong_c": "Investment recovery is never guaranteed.",
        "explanation_wrong_d": "Unverified rumours are not a reliable basis for investment decisions.",
    },
    {
        "question": "Why might holding an unsuitable investment create additional risk?",
        "option_a": "The investment can never fall further",
        "option_b": "The reasons that made it unsuitable may continue or worsen",
        "option_c": "Holding automatically guarantees recovery",
        "option_d": "A loss disappears if it is ignored",
        "correct_answer": "b",
        "explanation_correct": "A weakened investment case may expose the investor to further losses.",
        "explanation_wrong_a": "An investment can continue to decline.",
        "explanation_wrong_c": "Simply holding does not guarantee recovery.",
        "explanation_wrong_d": "Ignoring a loss does not remove the underlying investment risk.",
    },
    {
        "question": "Which change may justify reviewing whether an investment should still be held?",
        "option_a": "A change in the investor's financial goal or time horizon",
        "option_b": "A single social-media comment",
        "option_c": "A random market prediction",
        "option_d": "The colour used in the investment company's logo",
        "correct_answer": "a",
        "explanation_correct": "A change in financial goals or time horizon can affect whether an investment remains suitable.",
        "explanation_wrong_b": "One unverified comment is not a sufficient basis for an investment decision.",
        "explanation_wrong_c": "Random predictions are not reliable evidence.",
        "explanation_wrong_d": "A company's logo does not determine investment suitability.",
    },
    {
        "question": 'An investor says, "I will not sell until I recover every rupee I lost," even though the investment no longer suits their goal. What is the main problem?',
        "option_a": "The investor is focusing too much on the past purchase price instead of current suitability",
        "option_b": "The investor has guaranteed future recovery",
        "option_c": "The investment can no longer lose value",
        "option_d": "The investor is automatically diversified",
        "correct_answer": "a",
        "explanation_correct": "The decision is being driven by the original price rather than whether the investment still fits the current plan.",
        "explanation_wrong_b": "Holding longer does not guarantee recovery.",
        "explanation_wrong_c": "An unsuitable investment may continue to fall.",
        "explanation_wrong_d": "Holding one unsuitable investment does not automatically create diversification.",
    },
    {
        "question": "Which approach is most sensible when an investment has fallen significantly?",
        "option_a": "Sell automatically because every fall means permanent loss",
        "option_b": "Buy more automatically because every investment eventually recovers",
        "option_c": "Review the investment case, financial goal, time horizon, and risk before deciding",
        "option_d": "Ignore the investment completely and never review it",
        "correct_answer": "c",
        "explanation_correct": "A decision should be based on whether the investment still fits the investor's circumstances and plan.",
        "explanation_wrong_a": "Some price declines may be temporary.",
        "explanation_wrong_b": "Investments do not always recover and buying more can increase exposure to an unsuitable investment.",
        "explanation_wrong_d": "Ignoring important changes can leave an unsuitable investment unaddressed.",
    },
    {
        "question": "Application — An investor buys an investment for ₹20,000. Its value falls by ₹4,000. What is its new value?",
        "option_a": "₹14,000",
        "option_b": "₹16,000",
        "option_c": "₹20,000",
        "option_d": "₹24,000",
        "correct_answer": "b",
        "explanation_correct": "₹20,000 − ₹4,000 = ₹16,000.",
        "explanation_wrong_a": "₹20,000 − ₹4,000 = ₹16,000, not ₹14,000.",
        "explanation_wrong_c": "The ₹4,000 fall reduces the investment's value.",
        "explanation_wrong_d": "A fall is subtracted rather than added.",
    },
    {
        "question": "Application — An investor bought an investment for ₹15,000. It is now worth ₹11,000. What is the loss compared with the original investment?",
        "option_a": "₹2,000",
        "option_b": "₹3,000",
        "option_c": "₹4,000",
        "option_d": "₹26,000",
        "correct_answer": "c",
        "explanation_correct": "₹15,000 − ₹11,000 = ₹4,000.",
        "explanation_wrong_a": "₹15,000 − ₹11,000 = ₹4,000, not ₹2,000.",
        "explanation_wrong_b": "₹15,000 − ₹11,000 = ₹4,000, not ₹3,000.",
        "explanation_wrong_d": "The loss is the difference between the original value and current value.",
    },
]


MODULES = [
    {
        "name": "SIP and Rupee Cost Averaging",
        "difficulty": "easy",
        "tags": ["SIP", "rupee cost averaging", "mutual funds", "investing basics"],
        "article": ARTICLE_SIP,
        "summary": SUMMARY_SIP,
        "questions": QUESTIONS_SIP,
    },
    {
        "name": "What is a Mutual Fund?",
        "difficulty": "easy",
        "tags": ["mutual funds", "NAV", "investing basics"],
        "article": ARTICLE_MF,
        "summary": SUMMARY_MF,
        "questions": QUESTIONS_MF,
    },
    {
        "name": "What is Diversification?",
        "difficulty": "easy",
        "tags": ["diversification", "risk management", "portfolio"],
        "article": ARTICLE_DIV,
        "summary": SUMMARY_DIV,
        "questions": QUESTIONS_DIV,
    },
    {
        "name": "Risk vs Return",
        "difficulty": "easy",
        "tags": ["risk", "return", "investing basics"],
        "article": ARTICLE_RR,
        "summary": SUMMARY_RR,
        "questions": QUESTIONS_RR,
    },
    {
        "name": "Index Funds",
        "difficulty": "medium",
        "tags": ["index funds", "NAV", "diversification", "passive investing"],
        "article": ARTICLE_IF,
        "summary": SUMMARY_IF,
        "questions": QUESTIONS_IF,
    },
    {
        "name": "Understanding Market Volatility",
        "difficulty": "medium",
        "tags": ["volatility", "market risk", "behavioral finance"],
        "article": ARTICLE_MV,
        "summary": SUMMARY_MV,
        "questions": QUESTIONS_MV,
    },
    {
        "name": "When to Sell: Cutting Losses Early",
        "difficulty": "medium",
        "tags": ["selling", "behavioral finance", "loss aversion"],
        "article": ARTICLE_CL,
        "summary": SUMMARY_CL,
        "questions": QUESTIONS_CL,
    },
]


def seed():
    with engine.begin() as conn:
        for module in MODULES:
            name = module["name"]

            conn.execute(
                text("""
                    INSERT INTO learning_modules (module_name, article_content, article_summary, difficulty, tags)
                    VALUES (:name, :content, :summary, :difficulty, :tags)
                    ON CONFLICT (module_name) DO UPDATE SET
                        article_content = EXCLUDED.article_content,
                        article_summary = EXCLUDED.article_summary,
                        difficulty = EXCLUDED.difficulty,
                        tags = EXCLUDED.tags
                """),
                {
                    "name": name,
                    "content": module["article"],
                    "summary": module["summary"],
                    "difficulty": module["difficulty"],
                    "tags": module["tags"],
                },
            )
            print(f"Module upserted: {name}")

            # Delete existing questions for this module first so re-running
            # the script doesn't duplicate them.
            conn.execute(
                text("DELETE FROM quiz_questions WHERE module_name = :name"),
                {"name": name},
            )

            for q in module["questions"]:
                # Each question dict omits the explanation_wrong_* key for
                # whichever option is correct_answer -- default the absent
                # keys to None here (same convention as seed_module1.py).
                params = {
                    "module_name": name,
                    "explanation_wrong_a": None,
                    "explanation_wrong_b": None,
                    "explanation_wrong_c": None,
                    "explanation_wrong_d": None,
                    **q,
                }
                conn.execute(
                    text("""
                        INSERT INTO quiz_questions
                        (module_name, question, option_a, option_b, option_c, option_d,
                         correct_answer, explanation_correct, explanation_wrong_a,
                         explanation_wrong_b, explanation_wrong_c, explanation_wrong_d)
                        VALUES (:module_name, :question, :option_a, :option_b, :option_c, :option_d,
                                :correct_answer, :explanation_correct, :explanation_wrong_a,
                                :explanation_wrong_b, :explanation_wrong_c, :explanation_wrong_d)
                    """),
                    params,
                )
            print(f"  Inserted {len(module['questions'])} quiz questions")

        # Verify
        for module in MODULES:
            count = conn.execute(
                text("SELECT COUNT(*) FROM quiz_questions WHERE module_name = :name"),
                {"name": module["name"]},
            ).scalar()
            print(f"Verified: {module['name']} -- {count} questions in database")


if __name__ == "__main__":
    seed()
