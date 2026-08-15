"""
scripts/learning_content.py

Generates learning module content (article + 10-question quiz) for the
FinSight financial literacy platform using Groq (llama-3.3-70b-versatile).

Content is written for Indian retail investors: simple language, Indian
examples (Reliance, HDFC Bank, Nifty 50, SIP, rupee amounts).

Run:
    D:\\finsight_venv\\Scripts\\python.exe -m scripts.learning_content

Output:
    Populates LEARNING_CONTENT (dict keyed by module name) and appends it,
    as a literal Python dict, to the bottom of this file so it can be
    imported directly (e.g. `from scripts.learning_content import LEARNING_CONTENT`)
    without needing to re-call Groq on every run.
"""

import json
import os
import re
import sys
import time

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_MODEL = "llama-3.3-70b-versatile"
PASS_THRESHOLD = 7  # out of 10

MODULES = [
    "Emergency Fund Building",
    "What is a Mutual Fund?",
    "What is Diversification?",
    "Risk vs Return",
    "Index Funds Explained",
    "SIP / Dollar-Cost Averaging",
    "Understanding Market Volatility",
    "When to Sell: Cutting Losses Early",
]

PROMPT_TEMPLATE = """You are creating financial education content for Indian retail investors.
Generate a JSON response with this exact structure for the module: {module_name}

{{
  "article": "full article text here (400-500 words)",
  "summary": ["key point 1", "key point 2", "key point 3"],
  "difficulty": "easy",
  "tags": ["tag1", "tag2", "tag3"],
  "quiz": [
    {{
      "question": "question text",
      "option_a": "first option",
      "option_b": "second option",
      "option_c": "third option",
      "option_d": "fourth option",
      "correct": "b",
      "explanation_correct": "Why b is correct",
      "explanation_wrong_a": "Why a is wrong",
      "explanation_wrong_c": "Why c is wrong",
      "explanation_wrong_d": "Why d is wrong"
    }},
    ... 10 questions total
  ]
}}

The article must be structured as (do not print these labels, just follow the flow):
- What is it? (1 paragraph, clear definition)
- Why does it matter? (1 paragraph, real consequence)
- Real Indian example (specific numbers, realistic scenario)
- How to apply it (3-4 practical steps)
- Common mistake to avoid (1 paragraph)
- Key takeaway (1 sentence summary)

The 10 quiz questions must be based DIRECTLY on the article content -- testing
comprehension, not tricks. Mix: 5 easy questions, 3 medium, 2 application-based.

Requirements:
- Use Indian examples with Rs (rupee) amounts -- e.g. Reliance, HDFC Bank, Nifty 50, SIP
- Article must cover: definition, importance, real example, practical steps, common mistake, key takeaway
- Questions must test understanding of the article content only
- Keep language simple -- target audience is first-time investors
- Return ONLY valid JSON, no other text"""


def extract_json(raw_text: str) -> dict:
    """
    Groq sometimes wraps JSON in markdown code fences or adds stray text
    around it. Strip fences first, then fall back to grabbing the outermost
    {...} block before parsing.
    """
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise ValueError("Could not locate a JSON object in the model response.")


def validate_module_content(data: dict) -> None:
    """
    Raises ValueError if the parsed content doesn't match the expected shape.
    Keeps bad/partial generations from silently entering LEARNING_CONTENT.
    """
    required_top_level = ["article", "summary", "difficulty", "tags", "quiz"]
    for key in required_top_level:
        if key not in data:
            raise ValueError(f"Missing top-level key: {key}")

    if not isinstance(data["quiz"], list) or len(data["quiz"]) != 10:
        raise ValueError(f"Expected 10 quiz questions, got {len(data.get('quiz', []))}")

    base_q_keys = [
        "question", "option_a", "option_b", "option_c", "option_d", "correct",
        "explanation_correct",
    ]
    for i, q in enumerate(data["quiz"]):
        for key in base_q_keys:
            if key not in q:
                raise ValueError(f"Quiz question {i + 1} missing key: {key}")
        if q["correct"] not in ("a", "b", "c", "d"):
            raise ValueError(f"Quiz question {i + 1} has invalid 'correct' value: {q['correct']!r}")

        # The three non-correct options each need a "why this is wrong" explanation.
        for opt in ("a", "b", "c", "d"):
            if opt == q["correct"]:
                continue
            key = f"explanation_wrong_{opt}"
            if key not in q:
                raise ValueError(f"Quiz question {i + 1} missing key: {key}")


def generate_module_content(client: Groq, module_name: str) -> dict:
    """
    Calls Groq for a single module, parses + validates the JSON response.
    Retries once on JSON parse / validation failure.
    """
    prompt = PROMPT_TEMPLATE.format(module_name=module_name)

    last_error = None
    for attempt in range(1, 3):  # 1 try + 1 retry
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            data = extract_json(raw)
            validate_module_content(data)

            data["module_name"] = module_name
            data["pass_threshold"] = PASS_THRESHOLD
            return data

        except Exception as e:
            last_error = e
            print(f"  Attempt {attempt} failed for '{module_name}': {e}")
            if attempt == 1:
                time.sleep(2)

    raise RuntimeError(f"Failed to generate valid content for '{module_name}' after retry: {last_error}")


def print_module_review(module_name: str, data: dict) -> None:
    """
    Prints the full article and the first 3 quiz questions for review.
    """
    print("\n" + "=" * 80)
    print(f"MODULE: {module_name}")
    print("=" * 80)

    print(f"\nDifficulty: {data.get('difficulty')}")
    print(f"Tags: {data.get('tags')}")

    print("\n--- ARTICLE ---\n")
    print(data.get("article", ""))
    word_count = len(data.get("article", "").split())
    print(f"\n[word count: {word_count}]")

    print("\n--- SUMMARY ---")
    for point in data.get("summary", []):
        print(f"  - {point}")

    print(f"\n--- QUIZ (showing first 3 of {len(data.get('quiz', []))}) ---")
    for i, q in enumerate(data.get("quiz", [])[:3], start=1):
        print(f"\nQ{i}. {q['question']}")
        print(f"  a) {q['option_a']}")
        print(f"  b) {q['option_b']}")
        print(f"  c) {q['option_c']}")
        print(f"  d) {q['option_d']}")
        print(f"  Correct: {q['correct']}")
        print(f"  Why correct: {q['explanation_correct']}")
        for opt in ("a", "b", "c", "d"):
            if opt == q["correct"]:
                continue
            key = f"explanation_wrong_{opt}"
            if key in q:
                print(f"  Why {opt} is wrong: {q[key]}")


def save_learning_content(content: dict, out_path: str) -> None:
    """
    Appends LEARNING_CONTENT as a literal Python dict to this file so it
    can be imported directly without re-calling Groq.
    """
    with open(out_path, "r", encoding="utf-8") as f:
        source = f.read()

    marker = "\n# --- GENERATED CONTENT BELOW (do not hand-edit; re-run script to regenerate) ---\n"
    if marker in source:
        source = source.split(marker)[0]

    generated_block = (
        marker
        + "LEARNING_CONTENT = "
        + json.dumps(content, indent=4, ensure_ascii=False)
        + "\n"
    )

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(source.rstrip() + "\n" + generated_block)


def run(modules_to_generate=None, review_first_only=False):
    """
    Main pipeline: loop through modules, call Groq, validate, collect results.

    review_first_only: if True, only generates module 1 and prints it for
    review, without touching the other 7 or writing to disk. Used for the
    quality check step before running the full batch.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY not set in environment/.env")
        sys.exit(1)

    client = Groq(api_key=api_key)

    modules = modules_to_generate or MODULES
    learning_content = {}

    for i, module_name in enumerate(modules, start=1):
        print(f"[{i}/{len(modules)}] Generating: {module_name}")
        try:
            data = generate_module_content(client, module_name)
        except RuntimeError as e:
            print(f"  SKIPPED (failed after retry): {e}")
            continue

        learning_content[module_name] = data
        print(f"  OK -- {len(data['article'].split())} words, {len(data['quiz'])} questions")

        if review_first_only:
            break

    if not review_first_only:
        save_learning_content(learning_content, __file__)
        print(f"\nSaved {len(learning_content)} modules to {__file__}")
    else:
        review_dump_path = os.path.join(
            os.path.dirname(__file__), "..", "_module1_review.json"
        )
        with open(review_dump_path, "w", encoding="utf-8") as f:
            json.dump(learning_content, f, indent=2, ensure_ascii=False)
        print(f"\n(Full JSON, all 10 questions, dumped to {review_dump_path} for review)")

    # Review output: first article + first 3 questions of first module
    if learning_content:
        first_module_name = next(iter(learning_content))
        print_module_review(first_module_name, learning_content[first_module_name])

    return learning_content


if __name__ == "__main__":
    # Review mode: generate only Module 1 for quality review before running
    # the full 8-module batch. Change to run(MODULES) to generate all 8.
    run(modules_to_generate=[MODULES[0]], review_first_only=True)
