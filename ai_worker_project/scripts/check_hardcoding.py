import os
import sys

def check_hardcoding():
    target_dirs = ["agent", "tools"]
    forbidden = ["globex", "acme", "5000", "expense", "invoice", "vendor"]
    
    # We will exclude the test environment files, but they are not in agent/tools anyway.
    failed = False
    
    for d in target_dirs:
        for root, _, files in os.walk(d):
            for file in files:
                if not file.endswith(".py"): continue
                path = os.path.join(root, file)
                
                with open(path, "r", encoding="utf-8") as f:
                    for i, line in enumerate(f):
                        lower_line = line.lower()
                        for term in forbidden:
                            if term in lower_line:
                                print(f"Hardcoding found: {term} in {path}:{i+1} -> {line.strip()}")
                                failed = True
                                
    if failed:
        sys.exit(1)
    else:
        print("No hardcoding found.")
        sys.exit(0)

if __name__ == "__main__":
    check_hardcoding()
