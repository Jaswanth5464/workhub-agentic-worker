import json
import os

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "company_memory.json")

def load_rules():
    if not os.path.exists(MEMORY_FILE):
        return []
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_rule(rule: str):
    rules = load_rules()
    if rule not in rules:
        rules.append(rule)
        with open(MEMORY_FILE, "w") as f:
            json.dump(rules, f, indent=4)
    return True
