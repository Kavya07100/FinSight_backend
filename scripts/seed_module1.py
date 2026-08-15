import uuid
import sys
sys.path.insert(0, '.')
from app.database import engine
from sqlalchemy import text

ARTICLE = """An emergency fund is money kept aside for unexpected needs, such as losing your job, a sudden medical bill, urgent travel, or a major home repair. It is not meant for shopping, holidays, or regular monthly spending. The goal is to have enough easily available money so that an emergency does not force you to sell investments at the wrong time or borrow at high interest.

Why does it matter? Imagine you lose your income for a few months while your rent, food, electricity, and loan payments continue. Without savings, you may use a credit card or personal loan. Interest can make the original problem more expensive. You may also have to sell shares when the market is down, turning a temporary cash problem into a permanent investment loss.

Consider Rohan, who lives in Pune. He earns Rs.50,000 a month. His essential monthly expenses are: Rent Rs.15,000, Groceries Rs.8,000, Electricity and internet Rs.3,000, Transport Rs.4,000, Health and medicines Rs.2,000, Loan payment Rs.6,000.

His emergency-fund need for one month: Rs.15,000 + Rs.8,000 + Rs.3,000 + Rs.4,000 + Rs.2,000 + Rs.6,000 = Rs.38,000. For a six-month target: Rs.38,000 x 6 = Rs.2,28,000.

This does not mean every investor needs exactly Rs.2,28,000. The right amount depends on essential expenses, job stability, dependants, insurance, and other personal circumstances.

Steps to build your fund: First, calculate your essential monthly expenses, separating needs from wants. Second, choose a target based on how long you may need to manage without normal income. Third, automate a fixed amount from each salary into a separate savings or suitable liquid account. Fourth, review the fund when your rent, family responsibilities, income, or major expenses change.

A common mistake is investing the entire emergency fund in shares because they may offer higher returns. Shares can fall sharply and may not be available at a good price when you urgently need cash. Emergency money should prioritise safety and access over high returns.

Takeaway: Build an emergency fund around your essential expenses so unexpected events do not derail your daily life or long-term investments."""

SUMMARY = [
    "An emergency fund protects you from unexpected expenses and income loss.",
    "Calculate the fund using essential monthly expenses, not lifestyle spending.",
    "Keep emergency money safe and easily accessible rather than chasing high returns."
]

QUESTIONS = [
    {
        "question": "What is the main purpose of an emergency fund?",
        "option_a": "To maximise investment returns",
        "option_b": "To pay for unexpected financial needs",
        "option_c": "To fund regular shopping",
        "option_d": "To buy shares during every market fall",
        "correct_answer": "b",
        "explanation_correct": "An emergency fund provides accessible money for unexpected needs.",
        "explanation_wrong_a": "Maximising returns is not the main purpose of emergency savings.",
        "explanation_wrong_c": "Regular shopping is planned spending, not an emergency.",
        "explanation_wrong_d": "The fund should first protect financial stability rather than encourage market investing."
    },
    {
        "question": "Which expense should generally be included when calculating an emergency fund?",
        "option_a": "A planned holiday",
        "option_b": "Luxury shopping",
        "option_c": "Essential rent",
        "option_d": "A restaurant celebration",
        "correct_answer": "c",
        "explanation_correct": "Rent is a necessary expense that may continue during an emergency.",
        "explanation_wrong_a": "A planned holiday is not an essential emergency expense.",
        "explanation_wrong_b": "Luxury shopping is discretionary spending.",
        "explanation_wrong_d": "Celebrations are normally optional expenses."
    },
    {
        "question": "Why can selling shares during an emergency be risky?",
        "option_a": "Shares always lose all their value",
        "option_b": "Shares cannot ever be sold",
        "option_c": "You may have to sell when prices are low",
        "option_d": "Selling shares always creates a bank loan",
        "correct_answer": "c",
        "explanation_correct": "An urgent need may force you to sell during a market decline.",
        "explanation_wrong_a": "Shares do not always lose all their value.",
        "explanation_wrong_b": "Shares can generally be sold through the market.",
        "explanation_wrong_d": "Selling shares does not automatically create a bank loan."
    },
    {
        "question": "Which feature should an emergency fund prioritise?",
        "option_a": "Safety and easy access",
        "option_b": "Maximum possible market returns",
        "option_c": "High-risk investments",
        "option_d": "Frequent buying and selling",
        "correct_answer": "a",
        "explanation_correct": "Emergency money must be available when an unexpected need occurs.",
        "explanation_wrong_b": "High returns usually involve accepting more risk or less access.",
        "explanation_wrong_c": "High-risk investments may lose value when the money is needed.",
        "explanation_wrong_d": "Frequent trading is unnecessary for emergency savings."
    },
    {
        "question": "Why might someone with irregular income need a larger emergency cushion?",
        "option_a": "Their income may have longer gaps",
        "option_b": "They automatically spend more",
        "option_c": "Their investments cannot grow",
        "option_d": "They do not need insurance",
        "correct_answer": "a",
        "explanation_correct": "Irregular earnings can make it harder to predict when the next income will arrive.",
        "explanation_wrong_b": "Irregular income does not automatically mean higher spending.",
        "explanation_wrong_c": "Income patterns do not determine whether investments can grow.",
        "explanation_wrong_d": "Income irregularity does not remove the need for appropriate insurance."
    },
    {
        "question": "What should an investor do when rent or family responsibilities increase significantly?",
        "option_a": "Ignore the change",
        "option_b": "Review and potentially increase the emergency-fund target",
        "option_c": "Invest the existing fund in shares",
        "option_d": "Stop tracking essential expenses",
        "correct_answer": "b",
        "explanation_correct": "The emergency fund should reflect current essential financial commitments.",
        "explanation_wrong_a": "Higher essential costs can increase the amount needed during an emergency.",
        "explanation_wrong_c": "Moving emergency money into shares can reduce its safety and accessibility.",
        "explanation_wrong_d": "Tracking essential expenses is necessary for setting a sensible target."
    },
    {
        "question": "Why should emergency savings be kept separate from the investment portfolio?",
        "option_a": "To prevent all investment losses",
        "option_b": "To give emergency money a different purpose and reduce accidental spending or forced selling",
        "option_c": "To guarantee higher investment returns",
        "option_d": "To avoid having any savings account",
        "correct_answer": "b",
        "explanation_correct": "Emergency savings are for financial protection, while investments are for longer-term goals.",
        "explanation_wrong_a": "Separating accounts cannot prevent investment losses.",
        "explanation_wrong_c": "Separation does not guarantee investment returns.",
        "explanation_wrong_d": "An emergency fund still needs an appropriate safe and accessible place to hold the money."
    },
    {
        "question": "Which approach is most sensible when building an emergency fund?",
        "option_a": "Save only after all optional spending is completed",
        "option_b": "Automate a fixed saving amount and review the target when circumstances change",
        "option_c": "Put every rupee into shares",
        "option_d": "Borrow whenever an unexpected bill appears",
        "correct_answer": "b",
        "explanation_correct": "Automation encourages regular saving and reviews keep the target relevant.",
        "explanation_wrong_a": "Relying on leftover money can make consistent saving difficult.",
        "explanation_wrong_c": "Shares may fall in value when emergency cash is needed.",
        "explanation_wrong_d": "Borrowing can add interest and increase financial pressure."
    },
    {
        "question": "An investor has essential monthly expenses of Rs.12,000 for rent, Rs.7,000 for food, Rs.2,000 for utilities, and Rs.4,000 for transport. What is the one-month emergency-fund requirement?",
        "option_a": "Rs.21,000",
        "option_b": "Rs.23,000",
        "option_c": "Rs.25,000",
        "option_d": "Rs.27,000",
        "correct_answer": "c",
        "explanation_correct": "Rs.12,000 + Rs.7,000 + Rs.2,000 + Rs.4,000 = Rs.25,000.",
        "explanation_wrong_a": "This leaves out the Rs.4,000 transport expense.",
        "explanation_wrong_b": "The listed expenses add to Rs.25,000, not Rs.23,000.",
        "explanation_wrong_d": "The listed essential expenses total Rs.25,000, not Rs.27,000."
    },
    {
        "question": "An investor's essential monthly expenses total Rs.30,000. If the investor chooses a four-month emergency-fund target, what amount is needed?",
        "option_a": "Rs.90,000",
        "option_b": "Rs.1,00,000",
        "option_c": "Rs.1,20,000",
        "option_d": "Rs.1,50,000",
        "correct_answer": "c",
        "explanation_correct": "Rs.30,000 x 4 = Rs.1,20,000.",
        "explanation_wrong_a": "Rs.30,000 x 4 equals Rs.1,20,000, not Rs.90,000.",
        "explanation_wrong_b": "The calculation does not produce Rs.1,00,000.",
        "explanation_wrong_d": "Rs.1,50,000 would be more than the four-month calculation."
    }
]

def seed():
    with engine.begin() as conn:
        # Insert module
        conn.execute(text("""
            INSERT INTO learning_modules (module_name, article_content, article_summary, difficulty, tags)
            VALUES (:name, :content, :summary, :difficulty, :tags)
            ON CONFLICT (module_name) DO UPDATE SET
                article_content = EXCLUDED.article_content,
                article_summary = EXCLUDED.article_summary
        """), {
            "name": "Emergency Fund Building",
            "content": ARTICLE,
            "summary": SUMMARY,
            "difficulty": "easy",
            "tags": ["emergency fund", "savings", "financial planning", "basics"]
        })
        print("Module inserted")

        # Insert questions
        # Note: each question dict omits the explanation_wrong_* key for
        # whichever option is correct_answer (no "wrong" explanation needed
        # for the right option), so default the absent keys to None here.
        for q in QUESTIONS:
            params = {
                "module_name": "Emergency Fund Building",
                "explanation_wrong_a": None,
                "explanation_wrong_b": None,
                "explanation_wrong_c": None,
                "explanation_wrong_d": None,
                **q,
            }
            conn.execute(text("""
                INSERT INTO quiz_questions
                (module_name, question, option_a, option_b, option_c, option_d,
                 correct_answer, explanation_correct, explanation_wrong_a,
                 explanation_wrong_b, explanation_wrong_c, explanation_wrong_d)
                VALUES (:module_name, :question, :option_a, :option_b, :option_c, :option_d,
                        :correct_answer, :explanation_correct, :explanation_wrong_a,
                        :explanation_wrong_b, :explanation_wrong_c, :explanation_wrong_d)
            """), params)
        print(f"Inserted {len(QUESTIONS)} quiz questions")

        # Verify
        count = conn.execute(text(
            "SELECT COUNT(*) FROM quiz_questions WHERE module_name = 'Emergency Fund Building'"
        )).scalar()
        print(f"Verified: {count} questions in database")

if __name__ == "__main__":
    seed()
