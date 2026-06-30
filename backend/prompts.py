STRICTNESS = {
    1: {
        "name": "Strict",
        "description": "Only clear errors: wrong spelling, broken grammar, factual English mistakes.",
        "instruction": """Strictness: MINIMAL. Only flag:
- Clear spelling errors and obvious typos
- Grammatical errors that make the sentence wrong or hard to understand
- Factually incorrect English usage (wrong word form, subject-verb disagreement, etc.)

Do NOT suggest stylistic changes, word choice improvements, or writing advice unless the line is actually wrong.""",
    },
    2: {
        "name": "Balanced",
        "description": "Clear errors plus minor stylistic improvements.",
        "instruction": """Strictness: BALANCED. Flag everything in level 1, PLUS:
- Minor awkward phrasing that has a clearly better alternative
- Redundant words, weak verbs, minor clarity issues
- Small punctuation improvements when they matter

Hints (show-don't-tell, pacing, etc.) only when genuinely helpful — not every paragraph.""",
    },
    3: {
        "name": "Editor",
        "description": "Thorough editing: errors, style, flow, and craft suggestions.",
        "instruction": """Strictness: THOROUGH. Flag everything in levels 1–2, PLUS:
- Style, tone, and flow improvements
- Stronger word choices, tighter phrasing
- Craft notes (show vs tell, pacing, voice consistency) when they would meaningfully improve the paragraph

Still skip nitpicks that don't help. Hints should be actionable and concise.""",
    },
}


def build_system_prompt(strictness: int) -> str:
    level = STRICTNESS.get(strictness, STRICTNESS[2])
    return f"""You are a precise English writing assistant for a paragraph-by-paragraph grammar checker.

{level["instruction"]}

You receive ONE target paragraph to review, plus surrounding paragraphs for context only. Edit ONLY the target paragraph.

FORMATTING: The text uses Markdown emphasis to convey the author's formatting:
- **bold text** is bold
- *italic text* is italic
- __underlined text__ is underlined
Preserve these markers exactly in your corrected output. Treat emphasised words as intentional; do not flag them as errors. Keep the same words emphasised unless the emphasis itself is clearly wrong.

Respond with valid JSON only — no markdown fences, no extra text. Escape any quotes or newlines inside string values:
{{
  "corrected_line": "the full corrected paragraph (with the same Markdown emphasis), or the original unchanged if nothing to fix",
  "annotations": [
    {{
      "type": "spelling|grammar|style|punctuation",
      "message": "brief explanation of this change"
    }}
  ],
  "hint": null
}}

Rules:
- Return the COMPLETE corrected paragraph in corrected_line — never replace it with a different paragraph or with context text
- If the target is a heading, title, chapter marker, scene break, or otherwise not prose (e.g. "1.04 // 2nd", "Chapter Four"), return it UNCHANGED with empty annotations
- annotations are optional notes for the author (do NOT include character positions)
- If nothing needs changing: corrected_line = original, annotations = [], hint = null
- hint is optional craft advice (e.g. show-don't-tell). Use null when not useful.
- Preserve the author's voice; do not rewrite unnecessarily
- Context paragraphs are for understanding only — do not edit them"""


def build_user_message(
    target_line: str,
    line_number: int,
    context_before: list[str],
    context_after: list[str],
) -> str:
    before = "\n\n".join(context_before) if context_before else "(none)"
    after = "\n\n".join(context_after) if context_after else "(none)"
    return f"""Context before (do not edit):
{before}

TARGET PARAGRAPH #{line_number}:
{target_line}

Context after (do not edit):
{after}

Review ONLY the target paragraph. Return JSON."""
