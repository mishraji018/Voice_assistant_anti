import pkgutil
import importlib
import os
import sys

# Ensure root is in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

for root, dirs, files in os.walk(root_dir):
    if "__pycache__" in root or ".git" in root or ".gemini" in root:
        continue
    for f in files:
        if f.endswith(".py") and f != "check_imports.py":
            rel_path = os.path.relpath(os.path.join(root, f), root_dir)
            mod = rel_path.replace("\\", ".").replace("/", ".").replace(".py", "")
            mod = mod.lstrip(".")
            if mod == "main": continue # main.py is special
            try:
                importlib.import_module(mod)
            except Exception as e:
                print(f"ERROR in {mod} → {e}")