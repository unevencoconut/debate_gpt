# This file makes the AI talk to OpenAI for us.
import openai

from config import MODEL_PARAMETERS


class Colors:
    GREEN = "\033[92m"
    WHITE = "\033[97m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    AQAU = "\033[36m"
    RESET = "\033[0m"


# This function asks OpenAI for a reply.
def generate_chat_response(messages, model_overrides=None):
    """Generates a chat response using the OpenAI API."""
    try:
        request_parameters = dict(MODEL_PARAMETERS)
        if isinstance(model_overrides, dict):
            request_parameters.update(model_overrides)
        elif isinstance(model_overrides, str):
            request_parameters["model"] = model_overrides
        completion = openai.chat.completions.create(**request_parameters, messages=messages)
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating chat response: {e}")
        return ""
