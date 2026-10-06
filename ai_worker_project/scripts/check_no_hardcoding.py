import os
import sys

def main():
    agent_dir = os.path.join(os.path.dirname(__file__), "..", "agent")
    tools_dir = os.path.join(os.path.dirname(__file__), "..", "tools")
    
    banned_strings = [
        "http://localhost",
        "localhost:80",
        "qwen2.5:0.5b"
    ]
    
    found_issues = []
    
    for directory in [agent_dir, tools_dir]:
        for root, _, files in os.walk(directory):
            for file in files:
                if not file.endswith(".py"):
                    continue
                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    for string in banned_strings:
                        if string in content:
                            found_issues.append(f"{filepath} contains hardcoded string: {string}")
                            
    if found_issues:
        print("HARDCODING DETECTED:")
        for issue in found_issues:
            print(f" - {issue}")
        sys.exit(1)
    else:
        print("No hardcoding detected.")
        sys.exit(0)

if __name__ == "__main__":
    main()
