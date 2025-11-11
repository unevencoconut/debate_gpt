# This file gathers all the settings the app needs in one spot.
import os

from dotenv import load_dotenv


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

MODEL_NAME = os.getenv("MODEL_NAME")
MODEL_TEMPERATURE = int(os.getenv("MODEL_TEMPERATURE"))
MODEL_TOP_P = int(os.getenv("MODEL_TOP_P"))
MODEL_FREQUENCY_PENALTY = int(os.getenv("MODEL_FREQUENCY_PENALTY"))
MODEL_PRESENCE_PENALTY = int(os.getenv("MODEL_PRESENCE_PENALTY"))

MODEL_PARAMETERS = {
    "model": MODEL_NAME,
    "temperature": MODEL_TEMPERATURE,
    "top_p": MODEL_TOP_P,
    "frequency_penalty": MODEL_FREQUENCY_PENALTY,
    "presence_penalty": MODEL_PRESENCE_PENALTY,
}

DEBATE_MODELS = [
    {"label": "GPT-5", "model": "gpt-5"},
    {"label": "GPT-4o", "model": "gpt-4o"},
    {"label": "GPT-41", "model": "gpt-4.1"},
]

JUDGE_LABEL = "The Judge"
JUDGE_MODEL = "o3"
MAX_DEBATE_ROUNDS = 3
