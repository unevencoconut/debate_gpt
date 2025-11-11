# This file handles saving and loading the conversation logs.
import importlib
import os


# This function writes the chat history to a markdown file.
def save_conversation(conversation, conversation_id, directory="conversations"):
    """Saves the conversation to a markdown file."""
    file_name = f"{directory}/{conversation_id}.md"

    try:
        os.makedirs(directory, exist_ok=True)
        with open(file_name, "w", encoding="utf-8") as f:
            for message in conversation:
                f.write(f"{message['role']}: {message['content']}\n")
        print(f"Conversation saved to {file_name}")
    except IOError as e:
        print(f"Error saving conversation: {e}")


# This function copies the chat history into the transcript file.
def set_active_conversation(conversation, file_name="TRANSCRIPT.md"):
    """Saves the conversation to the transcript file."""
    try:
        with open(file_name, "w", encoding="utf-8") as f:
            for message in conversation:
                f.write(f"## {message['role']}:\n")
                f.write(f"{message['content']}\n\n")
        print(f"Active conversation saved to {file_name}")
    except IOError as e:
        print(f"Error saving conversation: {e}")


# This function wipes the transcript file clean.
def clear_active_conversation(file_name="TRANSCRIPT.md"):
    """Clears the active conversation file."""
    try:
        with open(file_name, "w", encoding="utf-8") as f:
            f.write("")
        print("Active conversation cleared")
    except IOError as e:
        print(f"Error clearing conversation: {e}")


# This function saves the chat history as importable data.
def save_conversation_data(conversation, conversation_id, directory="conversations_data"):
    """Saves the conversation history to a Python file."""
    file_name = f"{directory}/{conversation_id}.py"
    print(f"Saving conversation data to {file_name}")
    try:
        os.makedirs(directory, exist_ok=True)
        with open(file_name, "w") as f:
            f.write("history = [\n")
            for message in conversation:
                message_str = repr(message)
                f.write(f"{message_str},\n")
            f.write("]\n")
        print("Conversation data saved to conversation_data.py")
    except IOError as e:
        print(f"Error saving conversation data: {e}")


# This function saves both markdown and data copies at once.
def save_conversations_and_data(conversation, conversation_id):
    """Saves the conversation to a file and the conversation history to a Python file."""
    save_conversation(conversation, conversation_id)
    save_conversation_data(conversation, conversation_id)


# This function loads a past chat history by id.
def get_conversation_data(history_id):
    module = importlib.import_module(f"conversations_data.{history_id}")
    return module.history


# This function clears out numbered conversation logs.
def clear_conversations_and_data(directory="conversations", data_directory="conversations_data"):
    """Clears the conversation and conversation data files."""
    try:
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path) and file.rsplit(".", 1)[0].isdigit():
                os.unlink(file_path)
        print(f"Conversations cleared from {directory}")
    except IOError as e:
        print(f"Error clearing conversations: {e}")

    try:
        for file in os.listdir(data_directory):
            file_path = os.path.join(data_directory, file)
            if os.path.isfile(file_path) and file.rsplit(".", 1)[0].isdigit():
                os.unlink(file_path)
        print(f"Conversation data cleared from {data_directory}")
    except IOError as e:
        print(f"Error clearing conversation data: {e}")


# This function reads a canned user prompt from disk.
def get_user_input_from_file(file_name="USER_INPUT.txt"):
    """Gets the user input from a file."""
    if os.path.isfile(file_name):
        try:
            with open(file_name, "r", encoding="utf-8") as f:
                return f.read().strip()
        except IOError as e:
            print(f"Error reading file INPUT.md: {e}")
    return ""


# This function reads the shared system prompt if it exists.
def load_system_prompt(file_path="SYSTEM.md"):
    """Return the contents of the SYSTEM.md file, or an empty string if unavailable."""
    if os.path.isfile(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except IOError as e:
            print(f"Error reading {file_path}: {e}")
    return ""


# This function picks the next unused conversation id.
def find_next_conversation_id(current_id, directory="conversations"):
    """Finds the next available conversation id to avoid overwriting files."""
    file_name = f"{directory}/{current_id}.md"
    while os.path.isfile(file_name):
        current_id += 1
        file_name = f"{directory}/{current_id}.md"
    return current_id
