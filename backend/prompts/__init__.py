from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

_PROMPTS_DIR = Path(__file__).parent

_env = Environment(
    loader=FileSystemLoader(_PROMPTS_DIR),
    autoescape=select_autoescape(enabled_extensions=()),
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)

_INSTRUCTION_FILES = {
    1: "instructions/strict.j2",
    2: "instructions/balanced.j2",
    3: "instructions/editor.j2",
}

STRICTNESS = {
    1: {
        "name": "Strict",
        "description": "Only clear errors: wrong spelling, broken grammar, missing words, factual English mistakes.",
        "instruction_template": _INSTRUCTION_FILES[1],
    },
    2: {
        "name": "Balanced",
        "description": "Clear errors plus minor stylistic improvements.",
        "instruction_template": _INSTRUCTION_FILES[2],
    },
    3: {
        "name": "Editor",
        "description": "Thorough editing: errors, style, flow, and craft suggestions.",
        "instruction_template": _INSTRUCTION_FILES[3],
    },
}


def _render_instruction(strictness: int) -> str:
    level = STRICTNESS.get(strictness, STRICTNESS[2])
    return _env.get_template(level["instruction_template"]).render().strip()


def build_system_prompt(strictness: int) -> str:
    instruction = _render_instruction(strictness)
    return _env.get_template("system.j2").render(instruction=instruction).strip()


def build_user_message(
    target_line: str,
    line_number: int,
    context_before: list[str],
    context_after: list[str],
) -> str:
    before = "\n\n".join(context_before) if context_before else "(none)"
    after = "\n\n".join(context_after) if context_after else "(none)"
    return _env.get_template("user.j2").render(
        target_line=target_line,
        line_number=line_number,
        context_before=before,
        context_after=after,
    ).strip()
