#####################################################################################
# Usage: python clean_chat_history_json.py <input_file.json> <output_file.json>
####################################################################################
import json
import re
import argparse

GAYNESS_RE = re.compile(r"I am (\d+)% gay")

def is_valid_gay_message(message):
    # Ensure message is via the HowGayBot and matches the gayness message pattern
    if message.get("via_bot") != "@HowGayBot":
        return False
    
    text = message.get("text", "")
    if isinstance(text, list):  # Text with formatting/entities
        text = "".join(t["text"] if isinstance(t, dict) else str(t) for t in text)

    return bool(GAYNESS_RE.search(text))

def clean_json(input_file, output_file):
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "messages" not in data:
        print("Invalid Telegram export file format.")
        return

    filtered_messages = [msg for msg in data["messages"] if is_valid_gay_message(msg)]

    cleaned_data = {
        "name": data.get("name", "Filtered Chat"),
        "messages": filtered_messages
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

    print(f"Cleaned JSON saved to: {output_file} ({len(filtered_messages)} messages kept)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean Telegram export JSON for HowGayBot messages.")
    parser.add_argument("input", help="Path to original Telegram export JSON")
    parser.add_argument("output", help="Path to save cleaned JSON")

    args = parser.parse_args()
    clean_json(args.input, args.output)
