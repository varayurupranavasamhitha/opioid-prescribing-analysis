"""
LLM executive-brief generator with automatic number checking.

What it does
1. Reads results/summary.json (all key numbers produced by the notebook).
2. Sends them to an LLM (Google Gemini) with a carefully designed prompt.
3. Checks EVERY number in the LLM's answer against the JSON, and flags any number
   that doesn't appear in the results (a possible hallucination).
4. Saves the brief and the verification report to results/.

Usage
    pip install google-genai
    set GEMINI_API_KEY=your_key          (Windows)   |   export GEMINI_API_KEY=your_key   (Mac/Linux)
    python src/llm_summary.py

    # No API key? Print the prompt, paste it into any chatbot, save the reply to a .txt file, then verify it:
    python src/llm_summary.py --print-prompt
    python src/llm_summary.py --verify-file my_reply.txt
"""
import argparse
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUMMARY = ROOT / "results" / "summary.json"

PROMPT_TEMPLATE = """You are a senior healthcare analytics consultant writing for the Tennessee Department of Health.

TASK
Write an executive brief (max 250 words) based ONLY on the analysis results in the JSON below.

AUDIENCE
A non-technical health department director. Avoid statistical jargon; when you mention a test result,
explain what it means in plain words.

STRUCTURE
1. One-sentence headline finding.
2. Three to five bullet points with the key insights, each with a number from the results.
3. A short recommendation paragraph.
4. One line on the main limitation.

RULES
- Use ONLY numbers that appear in the JSON. Do not calculate new numbers, estimate, or round differently.
- If something is not in the JSON, do not mention it.
- Responsiveness values in the optimization are assumptions, so describe optimization results as "expected".
- Statistical significance alone is not importance; use the effect sizes to judge what matters.

RESULTS (JSON)
{results}
"""


def build_prompt(summary: dict) -> str:
    return PROMPT_TEMPLATE.format(results=json.dumps(summary, indent=2))


def call_gemini(prompt: str, model: str) -> str:
    from google import genai  # pip install google-genai

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config={"temperature": 0.2},  # low temperature = more consistent, less "creative" with facts
    )
    return response.text


# ---------- verification: does every number in the brief exist in the results? ----------
def allowed_numbers(obj) -> set:
    """Every number in the JSON, plus common legitimate re-expressions (rounding, fraction -> percent)."""
    found = set()

    def add(x: float):
        for v in (x, x * 100):  # 0.201 may legitimately appear as 20.1%
            for d in (0, 1, 2, 3):
                found.add(round(v, d))

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(k)
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, bool):
            return
        elif isinstance(o, (int, float)):
            add(float(o))
        elif isinstance(o, str):
            for m in re.findall(r"-?\d+(?:\.\d+)?", o.replace(",", "")):
                add(float(m))

    walk(obj)
    return found


def verify(text: str, summary: dict) -> list:
    allowed = allowed_numbers(summary)
    issues = []
    # strip list markers like "1." at the start of a line so they aren't checked
    cleaned = re.sub(r"(?m)^\s*\d+\.\s", "", text)
    for raw in re.findall(r"-?\$?\d[\d,]*(?:\.\d+)?", cleaned):
        num = float(raw.replace(",", "").replace("$", ""))
        decimals = len(raw.split(".")[1]) if "." in raw else 0
        candidates = {round(num, decimals), abs(round(num, decimals))}
        if not any(c in allowed or -c in allowed for c in candidates):
            issues.append(raw)
    return sorted(set(issues), key=issues.index)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemini-2.5-flash",
                    help="Gemini model name (check Google AI Studio for current models)")
    ap.add_argument("--print-prompt", action="store_true", help="print the prompt and exit")
    ap.add_argument("--verify-file", help="verify a brief you got from any chatbot, saved as a text file")
    args = ap.parse_args()

    summary = json.loads(SUMMARY.read_text())
    prompt = build_prompt(summary)

    if args.print_prompt:
        print(prompt)
        return

    if args.verify_file:
        brief = Path(args.verify_file).read_text(encoding="utf-8")
    else:
        if "GEMINI_API_KEY" not in os.environ:
            raise SystemExit("Set GEMINI_API_KEY first, or use --print-prompt / --verify-file (see top of file).")
        brief = call_gemini(prompt, args.model)

    unverified = verify(brief, summary)
    print("=" * 70, "\nEXECUTIVE BRIEF\n" + "=" * 70)
    print(brief)
    print("=" * 70, "\nNUMBER CHECK\n" + "=" * 70)
    if unverified:
        print(f"WARNING: {len(unverified)} number(s) not found in the results. Check these by hand:")
        for n in unverified:
            print("  -", n)
    else:
        print("All numbers in the brief match the analysis results.")

    out = ROOT / "results"
    (out / "executive_brief.md").write_text(brief, encoding="utf-8")
    (out / "brief_number_check.json").write_text(json.dumps({"unverified_numbers": unverified}, indent=2))
    print(f"\nSaved to {out / 'executive_brief.md'}")


if __name__ == "__main__":
    main()
