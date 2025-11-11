from services.openai_client import Colors
from storage.files import (
    clear_active_conversation,
    clear_conversations_and_data,
    find_next_conversation_id,
    get_conversation_data,
    get_user_input_from_file,
    load_system_prompt,
    save_conversation,
    save_conversation_data,
    save_conversations_and_data,
    set_active_conversation,
)
from workflow.debate import run_debate_session


CONVERSATION_ID = 0
CONVERSATION_HISTORY = []


if __name__ == "__main__":
    CONVERSATION_ID = find_next_conversation_id(CONVERSATION_ID)
    active_system_prompt = ""

    while True:
        if len(CONVERSATION_HISTORY) == 0:
            active_system_prompt = load_system_prompt() or ""
            CONVERSATION_HISTORY.append({"role": "system", "content": active_system_prompt})

        user_input = input("User:").strip()

        lower_input = user_input.lower()
        if lower_input == "q":
            clear_active_conversation()
            break
        elif lower_input == "s":
            save_conversation(CONVERSATION_HISTORY, CONVERSATION_ID)
            continue
        elif lower_input == "d":
            save_conversation_data(CONVERSATION_HISTORY, CONVERSATION_ID)
            continue
        elif lower_input == "a":
            save_conversations_and_data(CONVERSATION_HISTORY, CONVERSATION_ID)
            continue
        elif lower_input == "c":
            clear_conversations_and_data()
            continue
        elif lower_input == "i":
            user_input = get_user_input_from_file()
        elif lower_input == "h":
            previous_conversation_id = input("History Number:").strip()
            conversation_data = get_conversation_data(previous_conversation_id)
            CONVERSATION_HISTORY = conversation_data
            active_system_prompt = ""
            for message in CONVERSATION_HISTORY:
                if message.get("role") == "system":
                    active_system_prompt = message.get("content", "")
                    break
            set_active_conversation(CONVERSATION_HISTORY)
            continue

        if not user_input:
            print(f"{Colors.YELLOW}No prompt provided. Try again.{Colors.RESET}")
            continue

        try:
            debate_result = run_debate_session(user_input, active_system_prompt)
        except Exception as error:
            print(f"{Colors.RED}Debate error: {error}{Colors.RESET}")
            continue

        CONVERSATION_HISTORY.append({"role": "user", "content": user_input})

        system_section = active_system_prompt.strip() if active_system_prompt.strip() else "(none)"
        verdict_section = debate_result.get("verdict", "").strip() or "[No verdict provided]"
        final_answer_section = debate_result.get("final_answer", "").strip() or "[No final answer provided]"
        votes_section = debate_result.get("votes", "").strip() or "[No votes recorded]"
        transcript_section = debate_result.get("transcript", "").strip() or "[No transcript available]"

        assistant_sections = [
            "## SYSTEM",
            system_section,
            "",
            "## USER MESSAGE",
            user_input,
            "",
            "## VERDICT",
            verdict_section,
            "",
            "## FINAL ANSWER",
            final_answer_section,
            "",
            "## VOTES",
            votes_section,
            "",
            "## TRANSCRIPT",
            transcript_section,
        ]
        assistant_response = "\n".join(assistant_sections).strip()

        console_summary = final_answer_section or verdict_section
        print(f"{Colors.GREEN}Assistant:{Colors.RESET}", f"{Colors.GREEN}{console_summary}{Colors.RESET}")

        CONVERSATION_HISTORY.append({"role": "assistant", "content": assistant_response})

        set_active_conversation(CONVERSATION_HISTORY)
