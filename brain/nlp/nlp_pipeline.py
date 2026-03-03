"""
nlp_pipeline.py  –  Production NLP Pipeline Orchestrator for Jarvis
====================================================================
Replaces the ad-hoc chain in main.py with a clean, 6-stage pipeline
that mirrors how Alexa / Google Assistant process speech.

Stage 1: Normalize      – wake words, fillers, phonetic fixes, dedup
Stage 2: Translate      – Hinglish/Hindi → English (translator.py)
Stage 3: Resolve Entities – fuzzy whitelist matching (entity_resolver.py)
Stage 4: Detect Intent  – keyword engine + intent engine (keyword_engine.py)
Stage 5: Plan           – multi-step split, context resolution (command_planner.py)
Stage 6: Validate       – reject hallucinated entities before execution

Public API
----------
    from nlp_pipeline import NLPPipeline

    pipe = NLPPipeline(speak_fn=rm.speak)
    result = pipe.process(raw_text, lang)
    # result: PipelineResult → .handled (bool), .intent_result (dict), .steps (list)
"""

from __future__ import annotations
import re
import time
from dataclasses import dataclass, field
from typing import Optional, Callable

# ── Core & Brain helpers ─────────────────────────────────
from brain.nlp.normalizer import normalize
from core.infra.translator import translate_to_english
from brain.nlp.transliterator import transliterate_devanagari, has_devanagari
from brain.nlp.entity_resolver import resolve_entity
from brain.nlp.keyword_engine import keyword_match, normalise_intent
from brain.reasoning.reasoning_engine import interpret_command

# ── Context + planning ───────────────────────────────────
from brain.memory.context_memory import ContextMemory, ctx_mem
from brain.reasoning.command_planner import CommandPlanner, plan, parse_step, execute_step, Step

_pipeline_instance: Optional["NLPPipeline"] = None

def get_pipeline(speak_fn: Callable[[str], None]) -> "NLPPipeline":
    """
    Returns a singleton instance of the NLPPipeline.
    """
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = NLPPipeline(speak_fn=speak_fn)
    return _pipeline_instance

def process_text(text: str) -> dict:
    """
    Simplified wrapper for the brain.brain orchestrator.
    """
    # Initialize with default speak function (print) if not already done
    pipe = get_pipeline(speak_fn=print)
    result = pipe.process(text)
    # Return as dict for detect_intent consumption
    return {
        "text": result.clean_text,
        "handled": result.handled,
        "intent_result": result.intent_result,
        "steps": result.steps,
        "raw": result.raw_text
    }

# ─────────────────────────────────────────────────────────────────────────────
# Result container
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PipelineResult:
    """Returned by NLPPipeline.process(). Tells main.py exactly what to do."""

    # Was the utterance fully handled by the pipeline (multi-step or context)?
    handled: bool = False

    # The resolved intent dict  {intent, entity, confidence, raw, ...}
    # None if unrecognised or already handled by multi-step planner.
    intent_result: Optional[dict] = None

    # Ordered steps (for multi-step commands, else single-item or empty)
    steps: list[Step] = field(default_factory=list)

    # Cleaned / normalised text passed all the way through the pipeline
    clean_text: str = ""

    # LLM Reasoning outputs
    needs_clarification: bool = False
    clarification_question: str = ""
    reasoning: str = ""

    # Pipeline diagnostics
    raw_text: str = ""
    stage_reached: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline
# ─────────────────────────────────────────────────────────────────────────────

class NLPPipeline:
    """
    6-stage NLP pipeline for Jarvis.

    Usage
    -----
        pipe = NLPPipeline(
            speak_fn     = rm.speak,
            speak_jarvis = lambda t: rm.speak(t, use_female=False),
            ctx          = ctx_mem,
        )

        result = pipe.process(raw_text, lang)

        if not result.handled and result.intent_result:
            intent = result.intent_result["intent"]
            entity = result.intent_result["entity"]
            # → run your existing execute(intent_result) here

    Design
    ------
    • Normalization happens before translation so phonetic errors are fixed
      before the translator sees the text.
    • Entity resolution runs AFTER intent detection, so the entity extracted
      by keyword_engine is fuzzily matched to a whitelisted canonical name.
    • Multi-step is checked before single-intent so compound commands work.
    • Context memory is updated at execution time by command_planner.
    """

    def __init__(
        self,
        speak_fn     : Callable[[str], None],
        speak_jarvis : Optional[Callable[[str], None]] = None,
        ctx          : Optional[ContextMemory] = None,
        step_delay   : float = 0.6,
    ):
        self._speak_f = speak_fn
        self._speak_j = speak_jarvis or speak_fn
        self._ctx     = ctx or ctx_mem
        self._planner = CommandPlanner(
            speak_female = speak_fn,
            speak_jarvis = speak_jarvis or speak_fn,
            step_delay   = step_delay,
            ctx          = self._ctx,
        )

    # ── Main entry point ──────────────────────────────────────────────────────

    def process(self, raw_text: str, lang: str = "en") -> PipelineResult:
        """
        Run all 6 stages on raw ASR output.

        Parameters
        ----------
        raw_text : transcript from speech_input.listen()
        lang     : "hi" or "en" (as returned by listen())

        Returns
        -------
        PipelineResult — see dataclass above.
        """
        result = PipelineResult(raw_text=raw_text)
        if not raw_text:
            return result

        # ── Stage 0: Transliterate ────────────────────────────────────────────
        # Convert any Devanagari Unicode to Roman BEFORE normalization.
        # This handles cases where speech_recognition returns "स्टॉर्म" etc.
        # Latin (Hinglish) words like "youtube" or "kholo" pass through unchanged.
        if has_devanagari(raw_text):
            raw_text = transliterate_devanagari(raw_text)
            result.raw_text = raw_text
            print(f"[Pipeline] Stage0 translit: '{result.raw_text}' (Devanagari removed)")

        # ── Stage 1: Normalize ────────────────────────────────────────────────
        # Phonetic fixes, filler removal, wake-word strip, dedup
        # Pass apply_hinglish=False here — translator handles verb mapping
        normalized = normalize(raw_text, apply_hinglish=False)
        result.stage_reached = "normalize"
        print(f"[Pipeline] Stage1 normalize: '{raw_text}' → '{normalized}'")

        # ── Stage 2: Translate ────────────────────────────────────────────────
        # Hindi/Hinglish → English  (translator.py handles Devanagari + HINDI_DICT)
        english = translate_to_english(normalized, lang)
        result.clean_text    = english
        result.stage_reached = "translate"
        print(f"[Pipeline] Stage2 translate: '{normalized}' → '{english}'")

        # ── Stage 4 & 5: LLM Reasoning ────────────────────────────────────────
        # This replaces the old Stage 4 (keyword_match) and Stage 5 (multi-step plan)
        # with a single high-intelligence reasoning pass.
        result.stage_reached = "reasoning"
        llm_resp = interpret_command(english)
        
        # Log reasoning results
        result.needs_clarification    = llm_resp.get("needs_clarification", False)
        result.clarification_question = llm_resp.get("clarification_question", "")
        result.reasoning              = llm_resp.get("reasoning", "")
        
        print(f"[Pipeline] Stage4 reasoning: intents={llm_resp.get('intent', [])} "
              f"conf={llm_resp.get('confidence', 0):.2f} "
              f"clarify={result.needs_clarification}")

        if result.needs_clarification:
            return result

        # ── Stage 5: Plan & Execute ──────────────────────────────────────────
        # Process the structured steps returned by the LLM
        steps_data = llm_resp.get("steps", [])
        if steps_data:
            result.stage_reached = "plan_llm"
            print(f"[Pipeline] LLM found {len(steps_data)} steps")
            
            # Map raw JSON steps to the pipeline's Step class
            multi_steps = []
            for s in steps_data:
                action = s.get("action", s.get("intent", "UNKNOWN"))
                target = s.get("target", s.get("entity", ""))
                multi_steps.append(Step(raw_segment="", intent=action, entity=target, meta={}))

            if len(multi_steps) >= 2:
                self._speak_f(f"Sure, I'll handle {len(multi_steps)} things for you.")

            for i, step in enumerate(multi_steps, 1):
                # Resolve entities (Stage 3) on each LLM-suggested step
                resolved_step = self._resolve_step_entity(step)
                multi_steps[i-1] = resolved_step # Update list with resolved version
                
                print(f"[Pipeline] Executing step {i}/{len(multi_steps)}: {resolved_step}")
                
                ok = execute_step(resolved_step, self._speak_f, self._speak_j, ctx=self._ctx)
                if not ok:
                    self._speak_j("Stopped — an error occurred in a step.")
                    break
                if i < len(multi_steps):
                    time.sleep(0.6)
            
            result.handled = True
            result.steps   = multi_steps
            return result

        # --- Fallback to single intent (backwards compat) ---
        # If the LLM returned intents but no specific steps, reconstruct one step.
        intents = llm_resp.get("intent", [])
        entities = llm_resp.get("entities", [])
        if intents:
            intent_result = {
                "intent": intents[0],
                "entity": entities[0] if entities else "",
                "confidence": llm_resp.get("confidence", 0.0),
                "raw": english,
                "_reasoning": result.reasoning
            }
            # Stage 3/6: Resolve & Validate
            intent_result = self._validate(intent_result, english)
            result.intent_result = intent_result
            return result

        return result

    # ── Private helpers ───────────────────────────────────────────────────────

    def _resolve_step_entity(self, step: Step) -> Step:
        """
        Apply entity resolution to a single Step.
        Returns a new Step with the canonical entity name if a match is found.
        """
        if not step.entity:
            return step
        resolved = resolve_entity(step.entity)
        if resolved and resolved["score"] >= 0.70:
            # Inject resolved URL into meta if not already present
            meta = dict(step.meta)
            new_intent = step.intent
            
            if resolved.get("url"):
                if not meta.get("url"):
                    meta["url"] = resolved["url"]
                # Upgrade OPEN_APP to OPEN_URL if it's a website
                if step.intent == "OPEN_APP":
                    new_intent = "OPEN_URL"

            return Step(
                raw_segment = step.raw_segment,
                intent      = new_intent,
                entity      = resolved["name"],
                meta        = meta,
            )
        return step

    def _validate(self, intent_result: dict, english_text: str) -> dict:
        """
        Stage 6: Reject or flag potentially hallucinated commands.

        Rules:
        • OPEN_APP with an empty or very short entity → flag as UNKNOWN
        • SEARCH_WEB with empty entity → fill with full cleaned text as query
        • Any intent with confidence 0 → UNKNOWN
        """
        intent = intent_result.get("intent", "UNKNOWN")
        entity = intent_result.get("entity", "")
        conf   = intent_result.get("confidence", 0.0)

        # Empty entity for app-open is not executable
        if intent in ("OPEN_APP",) and len(entity.strip()) < 2:
            print(f"[Pipeline] Stage6 validate: OPEN_APP entity too short '{entity}' → UNKNOWN")
            return {**intent_result, "intent": "UNKNOWN", "entity": ""}

        # Search with no query — use full text as fallback query
        if intent in ("SEARCH_WEB", "RESEARCH") and not entity.strip():
            fallback_query = re.sub(
                r"\b(search|google|find|dhundo)\b", "", english_text,
                flags=re.IGNORECASE,
            ).strip()
            print(f"[Pipeline] Stage6 validate: empty SEARCH entity → fallback '{fallback_query}'")
            return {**intent_result, "entity": fallback_query}

        # Zero confidence → UNKNOWN
        if conf == 0.0 and intent != "UNKNOWN":
            print(f"[Pipeline] Stage6 validate: zero-confidence {intent} → UNKNOWN")
            return {**intent_result, "intent": "UNKNOWN"}

        return intent_result


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton (import and use directly)
# ─────────────────────────────────────────────────────────────────────────────

_pipeline_instance: Optional[NLPPipeline] = None


def get_pipeline(
    speak_fn     : Optional[Callable] = None,
    speak_jarvis : Optional[Callable] = None,
    ctx          : Optional[ContextMemory] = None,
) -> NLPPipeline:
    """
    Return the module-level NLPPipeline singleton.
    Creates it on first call (requires speak_fn).
    Returns existing instance on subsequent calls (args ignored).
    """
    global _pipeline_instance
    if _pipeline_instance is None:
        if speak_fn is None:
            raise RuntimeError("First call to get_pipeline() requires speak_fn.")
        _pipeline_instance = NLPPipeline(
            speak_fn=speak_fn, speak_jarvis=speak_jarvis, ctx=ctx
        )
    return _pipeline_instance


# ─────────────────────────────────────────────────────────────────────────────
# CLI demo
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    def _speak(msg):
        print(f"  [TTS] {msg}")

    pipe = NLPPipeline(speak_fn=_speak, speak_jarvis=_speak)

    TESTS = [
        ("hey jarvis youtub kholo yaar",              "en"),
        ("open crome and search python tutorials",    "en"),
        ("gaana chalao",                              "en"),
        ("microsft word khol do please",              "en"),
        ("watsapp kholo aur us par hello bolo",       "en"),
        ("search for machine learning",               "en"),
        ("time batao",                                "en"),
        ("open open chrome",                          "en"),
        ("umm uhh open youtube",                      "en"),
    ]

    print("\nNLP Pipeline Demo")
    print("=" * 70)
    for raw, lang in TESTS:
        print(f"\n{'─'*68}")
        print(f"  Input  : '{raw}'")
        result = pipe.process(raw, lang)
        print(f"  Clean  : '{result.clean_text}'")
        if result.handled:
            print(f"  Handled: multi-step ({len(result.steps)} steps)")
        elif result.intent_result:
            ir = result.intent_result
            print(f"  Intent : {ir['intent']} / '{ir.get('entity', '')}'"
                  f"  conf={ir.get('confidence', 0):.2f}")
        else:
            print("  Result : UNKNOWN / not handled")
