
import json
import logging
import re
import threading
from typing import List, Dict, Any
import ollama

from core.state.runtime_state import state
from brain.knowledge.engine import get_answer, _OLLAMA_MODEL

logger = logging.getLogger(__name__)

class TaskAgent:
    """
    Autonomous Task Agent: Breaks complex queries into steps and executes them.
    Limited to 5 steps to prevent infinite loops.
    """
    def __init__(self):
        self.max_steps = 5

    def generate_plan(self, query: str) -> List[Dict[str, Any]]:
        """Ask LLM to break the query into a JSON plan."""
        system_prompt = """
        You are a task planning agent for JARVIS.
        Break the user query into a sequence of maximum 5 actionable steps.
        Supported actions: "web_search", "info_lookup", "comparison", "summarization".
        Return ONLY a JSON list of objects with "step" (int) and "description" (string).
        Example: [{"step": 1, "description": "Search for best laptops under 1 lakh"}, {"step": 2, "description": "Compare top 3 models"}]
        """
        
        prompt = f"User Query: {query}\nGenerate a step-by-step plan in JSON format."
        
        try:
            response = ollama.chat(model=_OLLAMA_MODEL, messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': prompt},
            ])
            content = response.get('message', {}).get('content', '').strip()
            
            # Extract JSON from potential marks
            json_match = re.search(r"\[.*\]", content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return []
        except Exception as e:
            logger.error(f"Planning error: {e}")
            return []

    def execute_plan(self, query: str, callback=None) -> str:
        """Execute the generated plan sequentially."""
        if state.is_stop_requested(): return ""

        # 1. Generate Plan
        if callback: callback("Planning steps for your request, sir...")
        plan = self.generate_plan(query)
        if not plan:
            return get_answer(query) # Fallback to normal answer

        results = []
        for i, step in enumerate(plan[:self.max_steps]):
            if state.is_stop_requested(): break
            
            desc = step.get("description", "")
            if callback: callback(f"Step {i+1}: {desc}")
            
            # Execute step using knowledge engine
            # We pass the full history/context by appending previous results
            context = "\n".join(results[-2:]) # Last two steps for context
            step_result = get_answer(desc, history=f"Previous Context: {context}")
            results.append(f"Step {i+1} Result: {step_result}")

        # 2. Final Synthesis
        if state.is_stop_requested(): return ""
        if callback: callback("Synthesizing final recommendation, sir...")
        
        final_prompt = f"Query: {query}\nResults from steps:\n" + "\n".join(results)
        return get_answer(final_prompt, history="You are synthesizing a multi-step task result.")

task_agent = TaskAgent()
