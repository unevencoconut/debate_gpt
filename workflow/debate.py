# This file runs the debate conversation from start to finish.
import json

from config import DEBATE_MODELS, JUDGE_LABEL, JUDGE_MODEL, MAX_DEBATE_ROUNDS, WRITER_MODEL
from services.openai_client import Colors, generate_chat_response
from workflow.prompts import (
    build_consensus_prompt,
    build_debater_system_prompt,
    build_final_answer_request,
    build_final_answer_system_prompt,
    build_initial_debate_message,
    build_judge_request,
    build_judge_system_prompt,
    build_round_update_message,
)


INVALID_DEBATER_RESPONSE_MESSAGE = (
    'The previous reply was not valid JSON. Respond again using only JSON with keys '
    '"stance", "content", and optional "notes".'
)

INVALID_CONSENSUS_RESPONSE_MESSAGE = (
    'The previous reply was not valid JSON. Respond again using only JSON with the keys '
    '"agreement" ("agree" or "disagree") and optional "comment".'
)


# This function removes code block wrappers from text.
def strip_code_fences(text):
    if text.startswith("```") and text.endswith("```"):
        inner = text.split("\n", 1)[1]
        return inner.rsplit("\n", 1)[0]
    return text


# This function tries to read any JSON hiding in the text.
def parse_json_response(text):
    candidate = strip_code_fences(text.strip())
    try:
        return json.loads(candidate, strict=False)
    except json.JSONDecodeError:
        try:
            start = candidate.find("{")
            end = candidate.rfind("}")
            if start != -1 and end != -1:
                return json.loads(candidate[start : end + 1], strict=False)
        except json.JSONDecodeError:
            pass
    return {}


# This function tidies up what a debater just said.
def normalize_debater_reply(raw_text):
    parsed = parse_json_response(raw_text)
    parsed_is_dict = isinstance(parsed, dict)
    stance_value = (parsed.get("stance") if parsed_is_dict else None) or "stand"
    stance = stance_value.lower() if isinstance(stance_value, str) else "stand"
    content = (parsed.get("content") if parsed_is_dict else raw_text)
    if not isinstance(content, str):
        content = str(content)
    notes = parsed.get("notes", "") if parsed_is_dict else ""
    if not isinstance(notes, str):
        notes = str(notes)

    is_valid = parsed_is_dict and "stance" in parsed and "content" in parsed

    conceded_to = None
    if stance.startswith("concede"):
        parts = stance.split(":", 1)
        if len(parts) == 2 and parts[1].strip():
            conceded_to = parts[1].strip()
        stance = "concede"
    elif stance not in {"stand"}:
        stance = "stand"

    return {
        "stance": stance,
        "content": content.strip(),
        "notes": notes.strip() if isinstance(notes, str) else "",
        "conceded_to": conceded_to,
        "raw": raw_text,
        "valid": is_valid,
    }


# This function sorts out the judge's answer.
def parse_judge_response(raw_text):
    parsed = parse_json_response(raw_text)
    verdict = parsed.get("verdict", "no_winner")
    conclusion = parsed.get("conclusion", raw_text)
    reasoning = parsed.get("reasoning", "")
    winner = parsed.get("winner")
    return {
        "verdict": verdict,
        "conclusion": conclusion.strip(),
        "reasoning": reasoning.strip(),
        "winner": winner,
        "raw": raw_text,
    }


# This function checks how each debater reacted to the verdict.
def normalize_consensus_reply(raw_text):
    parsed = parse_json_response(raw_text)
    parsed_is_dict = isinstance(parsed, dict)
    agreement_value = (parsed.get("agreement") if parsed_is_dict else None) or "agree"
    agreement = agreement_value.lower() if isinstance(agreement_value, str) else "agree"
    is_valid = parsed_is_dict and "agreement" in parsed
    if agreement not in {"agree", "disagree"}:
        agreement = "agree"
    comment = parsed.get("comment", "") if parsed_is_dict else ""
    if not isinstance(comment, str):
        comment = str(comment)
    return {
        "agreement": agreement,
        "comment": comment.strip() if isinstance(comment, str) else "",
        "raw": raw_text,
        "valid": is_valid,
    }


# This function builds a plain text version of the debate.
def format_transcript(transcript):
    lines = []
    for entry in transcript:
        header = f"Round {entry['round']} — {entry['model']} ({entry['stance']})"
        if entry.get("conceded_to"):
            header += f" → conceded to {entry['conceded_to']}"
        lines.append(header)
        lines.append(entry["content"].strip())
        if entry.get("notes"):
            lines.append(f"Notes: {entry['notes'].strip()}")
        lines.append("")
    return "\n".join(lines).strip()


# This function makes a prettier version of the debate.
def format_transcript_display(transcript):
    sections = []
    for entry in transcript:
        round_label = entry.get("round", "")
        if isinstance(round_label, int):
            round_heading = f"ROUND {round_label}"
        else:
            round_heading = f"ROUND {str(round_label).upper()}"
        model_label = entry.get("model", "Unknown")
        stance = entry.get("stance", "")
        stance_display = stance.upper() if isinstance(stance, str) else ""
        if stance_display:
            header = f"### {round_heading} - {model_label} ({stance_display})"
        else:
            header = f"### {round_heading} - {model_label}"

        body_lines = []
        content = entry.get("content", "")
        if isinstance(content, str) and content.strip():
            body_lines.append(content.strip())
        notes = entry.get("notes")
        if isinstance(notes, str) and notes.strip():
            body_lines.append(f"**Notes:** {notes.strip()}")
        conceded_to = entry.get("conceded_to")
        if isinstance(conceded_to, str) and conceded_to.strip():
            body_lines.append(f"**Conceded to:** {conceded_to.strip()}")

        section_text = header if not body_lines else "\n".join([header, *body_lines])
        sections.append(section_text.strip())

    return "\n\n".join(sections).strip()


def build_round_digest(debate_state):
    """Create a JSON digest of the latest positions for all participants."""
    digest_entries = []
    for participant in DEBATE_MODELS:
        label = participant["label"]
        state = debate_state.get(label)
        if not state:
            continue
        latest = state.get("latest")
        if not latest:
            continue
        entry = {
            "model": label,
            "stance": latest.get("stance", "stand"),
            "content": latest.get("content", ""),
        }
        conceded_to = latest.get("conceded_to")
        if conceded_to:
            entry["conceded_to"] = conceded_to
        notes = latest.get("notes")
        if notes:
            entry["notes"] = notes
        digest_entries.append(entry)
    return json.dumps(digest_entries, ensure_ascii=False, indent=2)


def display_round_status(round_label, model_label, reply):
    """Print a concise update for the current model reply."""
    stance = reply.get("stance", "stand")
    stance_display = stance.upper()
    if stance == "concede":
        conceded_to = reply.get("conceded_to")
        if conceded_to:
            stance_display = f"CONCEDE → {conceded_to}"
    notes = reply.get("notes")
    if isinstance(notes, str) and notes.strip():
        cleaned_notes = " ".join(notes.strip().split())
        notes_display = f" | Notes: {cleaned_notes}"
    else:
        notes_display = ""
    print(f"{Colors.CYAN}Round {round_label} - {model_label} ({stance_display}){notes_display}{Colors.RESET}")


def request_debater_reply(history, model_id):
    """Fetch a debater reply, allowing a single retry if the JSON is invalid."""
    attempts = 0
    reply = None
    while attempts < 2:
        raw_response = generate_chat_response(history, model_id)
        reply = normalize_debater_reply(raw_response)
        history.append({"role": "assistant", "content": raw_response})
        if reply["valid"]:
            break
        attempts += 1
        if attempts < 2:
            history.append({"role": "user", "content": INVALID_DEBATER_RESPONSE_MESSAGE})
    return reply


def request_consensus_reply(history, model_id):
    """Fetch a consensus reply, allowing a single retry if the JSON is invalid."""
    attempts = 0
    reply = None
    while attempts < 2:
        raw_response = generate_chat_response(history, model_id)
        reply = normalize_consensus_reply(raw_response)
        history.append({"role": "assistant", "content": raw_response})
        if reply["valid"]:
            break
        attempts += 1
        if attempts < 2:
            history.append({"role": "user", "content": INVALID_CONSENSUS_RESPONSE_MESSAGE})
    return reply


# This function runs the entire debate cycle and bundles the results.
def run_debate_session(user_prompt, base_system):
    """Execute the multi-model debate workflow and return a structured result."""
    debate_state = {}
    transcript = []
    active_models = set()

    print(f"{Colors.GREEN}Commencing Debate!{Colors.RESET}")

    # Round 1 – initial answers
    for participant in DEBATE_MODELS:
        label = participant["label"]
        model_id = participant["model"]
        history = [
            {"role": "system", "content": build_debater_system_prompt(label, base_system)},
            {"role": "user", "content": build_initial_debate_message(user_prompt)},
        ]
        reply = request_debater_reply(history, model_id)

        debate_state[label] = {
            "model": model_id,
            "history": history,
            "latest": reply,
            "active": reply["stance"] != "concede",
        }

        if reply["stance"] != "concede":
            active_models.add(label)

        transcript.append(
            {
                "round": 1,
                "model": label,
                "stance": "stand" if reply["stance"] != "concede" else "concede",
                "content": reply["content"],
                "notes": reply.get("notes"),
                "conceded_to": reply.get("conceded_to"),
            }
        )

        display_round_status(1, label, reply)

    round_number = 2
    while len(active_models) > 1 and round_number <= MAX_DEBATE_ROUNDS:
        state_summary = build_round_digest(debate_state)

        for name in list(active_models):
            state = debate_state[name]
            state["history"].append({"role": "user", "content": build_round_update_message(round_number, state_summary)})
            reply = request_debater_reply(state["history"], state["model"])
            state["latest"] = reply

            if reply["stance"] == "concede":
                state["active"] = False
                active_models.discard(name)
            else:
                state["active"] = True

            transcript.append(
                {
                    "round": round_number,
                    "model": name,
                    "stance": reply["stance"],
                    "content": reply["content"],
                    "notes": reply.get("notes"),
                    "conceded_to": reply.get("conceded_to"),
                }
            )

            display_round_status(round_number, name, reply)

        round_number += 1

    winner = None
    if len(active_models) == 1:
        winner = next(iter(active_models))

    final_positions_lines = []
    for participant in DEBATE_MODELS:
        label = participant["label"]
        latest = debate_state[label]["latest"]
        if not latest:
            continue
        stance_display = latest["stance"]
        if stance_display == "concede" and latest.get("conceded_to"):
            stance_display = f"concede to {latest['conceded_to']}"
        final_positions_lines.append(f"- {label} ({stance_display}): {latest['content']}")
    final_positions_text = "\n".join(final_positions_lines)

    transcript_text_for_judge = format_transcript(transcript)

    judge_history = [
        {"role": "system", "content": build_judge_system_prompt(base_system)},
        {
            "role": "user",
            "content": build_judge_request(user_prompt, winner, transcript_text_for_judge, final_positions_text),
        },
    ]
    print(f"{Colors.MAGENTA}Judge reviewing debate...{Colors.RESET}")
    judge_raw = generate_chat_response(judge_history, JUDGE_MODEL)
    judge_history.append({"role": "assistant", "content": judge_raw})
    judge_result = parse_judge_response(judge_raw)
    judge_payload = parse_json_response(judge_raw)
    if judge_payload:
        for key in ("verdict", "winner", "reasoning", "conclusion"):
            value = judge_payload.get(key)
            if value is None:
                continue
            if isinstance(value, str):
                judge_result[key] = value
            else:
                judge_result[key] = value

    judge_conclusion_text = judge_result.get("conclusion", "")
    if isinstance(judge_conclusion_text, str):
        judge_conclusion_text = judge_conclusion_text.strip()
    else:
        judge_conclusion_text = str(judge_conclusion_text).strip()
    if not judge_conclusion_text:
        judge_conclusion_text = judge_result.get("raw", "").strip()
    parsed_conclusion = None
    if judge_conclusion_text and judge_conclusion_text.lstrip().startswith("{"):
        parsed_conclusion = parse_json_response(judge_conclusion_text)
        if isinstance(parsed_conclusion, dict) and parsed_conclusion:
            candidate = parsed_conclusion.get("conclusion")
            if isinstance(candidate, str) and candidate.strip():
                judge_conclusion_text = candidate.strip()
            for meta_key in ("reasoning", "verdict"):
                if meta_key in parsed_conclusion:
                    judge_result[meta_key] = parsed_conclusion.get(meta_key) or ""
            if "winner" in parsed_conclusion:
                judge_result["winner"] = parsed_conclusion.get("winner")
    if not judge_conclusion_text:
        judge_conclusion_text = "[No conclusion provided]"

    judge_result["conclusion"] = judge_conclusion_text

    transcript.append(
        {
            "round": JUDGE_LABEL,
            "model": JUDGE_LABEL,
            "stance": judge_result.get("verdict", "no_winner"),
            "content": judge_conclusion_text,
            "notes": judge_result.get("reasoning", ""),
            "conceded_to": judge_result.get("winner"),
        }
    )

    print(
        f"{Colors.MAGENTA}{JUDGE_LABEL} verdict ready ({judge_result.get('verdict', 'no_winner').upper()}){Colors.RESET}"
    )

    consensus_results = {}
    agree_count = 0
    disagree_count = 0
    for participant in DEBATE_MODELS:
        label = participant["label"]
        state = debate_state[label]
        consensus_prompt = build_consensus_prompt(judge_result["conclusion"], judge_result["reasoning"] or "")
        state["history"].append({"role": "user", "content": consensus_prompt})
        consensus = request_consensus_reply(state["history"], state["model"])
        consensus_results[label] = consensus
        if consensus["agreement"] == "agree":
            agree_count += 1
        else:
            disagree_count += 1

    verdict_lines = [f"{JUDGE_LABEL} Verdict ({judge_result['verdict']}):"]
    if judge_result.get("winner"):
        verdict_lines.append(f"Validated winner: {judge_result['winner']}")
    else:
        verdict_lines.append("Validated winner: None")
    verdict_lines.append(f"Judge final conclusion: {judge_conclusion_text}")
    if judge_result["reasoning"]:
        verdict_lines.append(f"Reasoning: {judge_result['reasoning']}")
    verdict_text = "\n".join(verdict_lines).strip()

    vote_lines = [f"Agreement: {agree_count} | Disagreement: {disagree_count}"]
    if consensus_results:
        vote_lines.append("Consensus votes:")
        for name, entry in consensus_results.items():
            vote = entry["agreement"].capitalize()
            comment = entry["comment"]
            if comment:
                vote_lines.append(f"- {name}: {vote} ({comment})")
            else:
                vote_lines.append(f"- {name}: {vote}")
    votes_text = "\n".join(vote_lines).strip()

    winner_label = judge_result.get("winner")
    canonical_winner = None
    winner_statement = None
    if isinstance(winner_label, str):
        for label_key in debate_state:
            if label_key.lower() == winner_label.lower():
                canonical_winner = label_key
                latest_entry = debate_state[label_key]["latest"]
                winner_statement = latest_entry.get("content", "").strip()
                break

    verdict_summary = verdict_text
    judge_conclusion_text = judge_result.get("conclusion", "")
    final_answer_history = [
        {"role": "system", "content": build_final_answer_system_prompt(base_system)},
        {
            "role": "user",
            "content": build_final_answer_request(
                user_prompt,
                verdict_summary,
                judge_conclusion_text,
                canonical_winner or (winner_label if isinstance(winner_label, str) else "None"),
                winner_statement,
            ),
        },
    ]
    final_answer_raw = generate_chat_response(final_answer_history, WRITER_MODEL)
    final_answer_history.append({"role": "assistant", "content": final_answer_raw})
    final_answer_candidate = final_answer_raw.strip()
    parsed_final_answer = parse_json_response(final_answer_candidate)
    if not parsed_final_answer and final_answer_candidate.startswith("```"):
        unfenced_candidate = strip_code_fences(final_answer_candidate).strip()
        if unfenced_candidate:
            parsed_final_answer = parse_json_response(unfenced_candidate)
            if parsed_final_answer:
                final_answer_candidate = unfenced_candidate
    if parsed_final_answer:
        for key in ("answer", "conclusion", "content", "final_answer"):
            value = parsed_final_answer.get(key)
            if isinstance(value, str) and value.strip():
                final_answer_candidate = value.strip()
                break
    if not final_answer_candidate:
        final_answer_candidate = judge_conclusion_text
    final_answer_text = final_answer_candidate.strip()

    formatted_transcript = format_transcript_display(transcript)
    final_transcript_text = format_transcript(transcript)

    return {
        "verdict": verdict_text,
        "votes": votes_text,
        "final_answer": final_answer_text,
        "winner": winner,
        "transcript": formatted_transcript,
        "raw_transcript": final_transcript_text,
        "judge": judge_result,
        "consensus": consensus_results,
    }
