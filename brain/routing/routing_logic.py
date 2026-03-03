import pkgutil
import importlib
import commands
import os
from brain.infra.web_search import search_web

COMMAND_REGISTRY = {}

def load_commands():
    """Dynamically register all command modules exposing a run() function."""
    for finder, name, ispkg in pkgutil.walk_packages(commands.__path__, commands.__name__ + "."):
        try:
            module = importlib.import_module(name)
            if hasattr(module, "run"):
                cmd_key = name.split(".")[-1].replace("command_", "").lower()
                COMMAND_REGISTRY[cmd_key] = module.run
        except Exception as e:
            print(f"[Routing] Failed to load {name}: {e}")

# Initial load
load_commands()
print(f"[Routing] System ready with {len(COMMAND_REGISTRY)} modules.")

def execute_action(plan: dict, original_text: str) -> str:
    """
    Executes an action (command, web_search, or direct answer) based on the plan.
    """
    action = (plan.get("action") or "answer").lower()
    target = (plan.get("target") or original_text).lower()
    
    try:
        if action == "command":
            # Match target or original text to registry keys
            for key in COMMAND_REGISTRY:
                if key in target or key in original_text.lower():
                    print(f"[Routing] Triggering module: {key}")
                    return COMMAND_REGISTRY[key](original_text)
            
            # Fallback to web search if it looks like a command but we lack the module
            print(f"[Routing] No local module for '{target}'. Falling back to web.")
            return search_web(target)

        elif action == "web_search":
            return search_web(target)

        elif action == "answer":
            return plan.get("target") or "I'm here to help!"

    except Exception as e:
        print(f"[Routing] Execution error: {e}")
        return f"I ran into a problem while trying to help: {str(e)}"

    return "I'm not exactly sure how to process that request."
