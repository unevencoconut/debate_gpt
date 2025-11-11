# The Council (Debate GPT)
This CLI assistant routes every user prompt through a structured, multi-model debate before producing a final answer. It keeps a complete record of the interaction while only surfacing the final conclusion in the terminal.

## Local Setup
1. Clone the repository and move into it: `git clone <repo-url> && cd the_council`.
2. Create and activate a virtual environment:
   - macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`
   - Windows (PowerShell): `py -3 -m venv .venv; .\.venv\Scripts\Activate.ps1`
3. Install dependencies with `pip install -r requirements.txt`.
4. Copy `.env.example` to `.env` and supply your OpenAI credentials (`OPENAI_API_KEY`) plus any model parameter overrides you want. The app uses `python-dotenv`, so the `.env` file is loaded automatically on startup.
5. Run the CLI with `python3 main.py`.

## Running the CLI
- Start the tool with `python3 main.py`.
- On startup the CLI looks for a `SYSTEM.md` file; if it exists and contains text, that content becomes the shared system prompt for every role. If the file is missing or blank, the debate runs with no additional system guidance.
- Subsequent prompts are entered at `User:`. The app maintains in-memory history and mirrors the conversation to `TRANSCRIPT.md` after each turn.
- While a debate is running the console prints concise status updates (round, model, stance, verdict progress) so you can track the workflow without digging into the transcript.

## Conversation Flow
```mermaid
flowchart TD
    U[User Prompt]
    SP[SYSTEM.md (optional)]
    subgraph Round 1
        D1[GPT-5 Debater]
        D2[GPT-4o Debater]
        D3[GPT-4.1 Debater]
    end
    subgraph Follow-up Rounds
        Digest[JSON Digest of latest stances]
        D1R[GPT-5 Updates/Stands or Concedes]
        D2R[GPT-4o Updates/Stands or Concedes]
        D3R[GPT-4.1 Updates/Stands or Concedes]
    end
    subgraph Verdict Stage
        J[The Judge (o3)]
        Consensus[Debater Consensus Votes]
    end
    subgraph Final Answer
        W[The Writer (o3)]
    end

    U -->|User submission| Round 1
    SP -->|System prompt| Round 1
    Round 1 --> Digest
    Digest --> Follow-up Rounds
    Follow-up Rounds -->|Transcript + Final Positions| J
    J -->|Verdict JSON| Consensus
    J -->|Verdict Summary| W
    Consensus --> W
    W -->|Final answer| Console[(Console Output)]
    W --> Transcript[(TRANSCRIPT.md + Saved Logs)]
```
1. **Debate Round 1** – Three debater roles (labels `GPT-5`, `GPT-4o`, `GPT-41`) receive identical instructions and reply in JSON containing `stance`, `content`, and optional `notes`. They begin with `stance: "stand"`.
2. **Follow-up Rounds** – Up to two additional rounds run while more than one debater remains active. Each participant receives a JSON digest of every model's latest stance/content, can refine their answer, or concede using `stance: "concede:<opponent>"`. Invalid JSON responses trigger a single retry before the turn is recorded.
3. **Judge Review** – The judge role (model `o3` by default) reads the formatted transcript, the final positions, and the perceived winner. It returns JSON detailing the verdict (`approved`, `rejected`, or `no_winner`), reasoning, conclusion, and winner label.
4. **Consensus Check** – Every debater receives the judge’s conclusion and responds with JSON indicating agreement or dissent (`agreement`, optional `comment`). These votes are tracked for later display.
5. **Final Answer Synthesis** – A separate writer role (model `o3` by default) crafts the user-facing response using the judge’s validated verdict and the winning debater’s statement when available.
6. **Output & Persistence** – The console shows the writer’s final answer (or the verdict, if no final answer is available). A richly formatted transcript—including system prompt, verdict details, vote counts, and every debate turn—is appended to the assistant’s message history and written to `TRANSCRIPT.md`. Conversation snapshots can be saved to `conversations/<id>.md` and `conversations_data/<id>.py`.

## Models & Configuration
- Debater labels map to OpenAI models: `GPT-5 → gpt-5`, `GPT-4o → gpt-4o`, `GPT-41 → gpt-4.1`.
- The judge (`The Judge`) and writer (`The Writer`) roles default to the `o3` model but can be changed in `config.py`.
- Default request parameters come from environment variables (`MODEL_NAME`, `MODEL_TEMPERATURE`, `MODEL_TOP_P`, `MODEL_FREQUENCY_PENALTY`, `MODEL_PRESENCE_PENALTY`). Values defined in `.env` or the shell are applied at runtime.

## Interactive Shortcuts
- `q` – Quit and clear `TRANSCRIPT.md`.
- `s` – Save the conversation history to `conversations/<id>.md`.
- `d` – Export the conversation as Python data to `conversations_data/<id>.py`.
- `a` – Perform both `s` and `d`.
- `c` – Clear numbered conversation files in `conversations/` and `conversations_data/`.
- `i` – Load the next user prompt from `USER_INPUT.txt`.
- `h` – Load a previous conversation by ID (populates history and rewrites `TRANSCRIPT.md`).

All shortcuts run before the debate workflow. The conversation ID increments automatically to avoid overwriting saved sessions.
