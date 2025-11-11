# This file holds the text templates we send to the models.
from textwrap import dedent

from config import JUDGE_LABEL, WRITER_LABEL


# This function writes the pep talk each debater gets.
def build_debater_system_prompt(model_name, base_system):
    guidance = dedent(
        f"""
        You are {model_name}, an OpenAI assistant participating in a structured debate with other models.
        You are cooperative but competitive: present the strongest case you can, yet concede if another model clearly outperforms your position.
        Always reply using valid JSON so downstream tooling can parse your answer.
        """
    ).strip()
    if base_system:
        guidance = f"{guidance}\n\nOperator context to honor:\n{base_system.strip()}"
    return guidance


# This function builds the first message for every debater.
def build_initial_debate_message(user_prompt):
    return dedent(
        f"""
        Round 1 Instructions:
        • Consider the user submission below and provide your best initial answer.
        • You must respond with JSON using the keys "stance", "content", and optional "notes".
        • For Round 1 set "stance" to "stand". Reserve concessions for later rounds.
        • Keep "content" concise (<= 250 words) and directly address the submission.

        User submission:
        {user_prompt.strip()}
        """
    ).strip()


# This function sums up the debate so far for the next round.
def build_round_update_message(round_number, state_summary):
    return dedent(
        f"""
        Round {round_number} Update:
        • Latest positions (JSON digest):
        {state_summary}
        • Parse the JSON to understand each participant's stance, key points, and concessions.
        • You may reinforce your stance or concede if another model's case is stronger.
        • To concede, set "stance" to "concede:<Model Name>" referencing the model you believe should win.
        • If you remain in the debate, keep "stance" as "stand" and refine your argument (<= 200 words).
        • Always respond with JSON keys "stance", "content", and optional "notes".
        """
    ).strip()


# This function tells the models what the judge decided.
def build_consensus_prompt(judge_conclusion, judge_reasoning):
    return dedent(
        f"""
        The judge has delivered the final verdict.
        Conclusion: {judge_conclusion}
        Reasoning: {judge_reasoning}

        Reply with JSON using keys "agreement" ("agree" or "disagree") and optional "comment" (<= 40 words).
        """
    ).strip()


# This function sets the judge's mindset before reading anything.
def build_judge_system_prompt(base_system):
    instructions = dedent(
        """
        You are {judge_label}, an impartial arbiter who reviews debate transcripts and delivers the final answer for the user.
        Your responsibilities:
        1. Verify whether the apparent winning model's claims are factual and well-reasoned.
        2. If no single winner exists, synthesize the best possible answer yourself.
        3. Always explain your reasoning succinctly.
        Respond with strict JSON so tooling can parse your verdict.
        """
    ).strip().format(judge_label=JUDGE_LABEL)
    if base_system:
        instructions = f"{instructions}\n\nOperator context to honor:\n{base_system.strip()}"
    return instructions


# This function lays out what the judge should review and report.
def build_judge_request(user_prompt, winner, transcript_text, final_positions):
    winner_text = winner if winner else "None"
    return dedent(
        f"""
        Review the following debate and deliver the final verdict.

        User submission:
        {user_prompt.strip()}

        Debate transcript:
        {transcript_text}

        Latest positions:
        {final_positions}

        Apparent winner after the debate rounds: {winner_text}

        Respond in JSON with keys:
        - "verdict": "approved" (winner confirmed), "rejected" (winner incorrect, provide correction), or "no_winner" (you produce the answer).
        - "conclusion": Your final answer for the user.
        - "reasoning": Brief fact-checking summary (<= 120 words).
        - "winner": Name of the winning model you validated or corrected (null if none).
        """
    ).strip()


# This function frames the judge's final speaking role.
def build_final_answer_system_prompt(base_system):
    instructions = dedent(
        f"""
        You are {WRITER_LABEL}, finalizing the response for the end user.
        Provide one clear, direct answer derived from the validated verdict.
        Do not mention the debate process or the word "verdict".
        Respond in plain Markdown without surrounding JSON or metadata.
        """
    ).strip()
    if base_system:
        instructions = f"{instructions}\n\nOperator context to honor:\n{base_system.strip()}"
    return instructions


# This function collects the judge's notes to craft the final answer.
def build_final_answer_request(user_prompt, verdict_summary, judge_conclusion, winner_label, winner_statement):
    decisive_source = ""
    if winner_statement:
        decisive_source = dedent(
            f"""
            Winning model ({winner_label}) statement:
            {winner_statement}
            """
        ).strip()
    else:
        decisive_source = dedent(
            f"""
            Judge conclusion:
            {judge_conclusion}
            """
        ).strip()

    return dedent(
        f"""
        Craft the final answer for the user.

        User prompt:
        {user_prompt.strip()}

        Verified verdict summary:
        {verdict_summary.strip()}

        {decisive_source}

        Requirements:
        • Deliver only the direct answer the user needs.
        • Exclude debate logistics, model names, or vote tallies.
        • Keep the response coherent and, if useful, formatted in Markdown.
        """
    ).strip()
