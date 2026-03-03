"""Quick verification test for command_planner.py + context_memory.py"""
from context_memory import ContextMemory
from commands.command_planner import plan, parse_step, CommandPlanner

def noop(m): pass

results = []

# T1: multi-step with same-sentence 'on that'
ctx1 = ContextMemory()
p1   = CommandPlanner(speak_female=noop, ctx=ctx1)
steps1 = p1.force_multi("open youtube and play a song on that")
results.append(("T1 step count", len(steps1) == 2))
if steps1:
    results.append(("T1 s1 intent OPEN_APP", steps1[0].intent == "OPEN_APP"))
    results.append(("T1 s2 intent PLAY/YOUTUBE", steps1[1].intent in ("PLAY_MUSIC","YOUTUBE_SEARCH")))

# T2: cross-turn context memory
ctx2 = ContextMemory()
ctx2.set_app("youtube")
resolved2 = ctx2.resolve_reference("play song on that")
step2 = parse_step(resolved2, ctx=ctx2)
results.append(("T2 resolved contains youtube", "youtube" in resolved2.lower()))
results.append(("T2 step is PLAY_MUSIC or YOUTUBE", step2 is not None and step2.intent in ("PLAY_MUSIC","YOUTUBE_SEARCH","OPEN_APP")))

# T3: try_context Hinglish
ctx3 = ContextMemory()
ctx3.set_app("youtube")
p3 = CommandPlanner(speak_female=noop, ctx=ctx3)
results.append(("T3 try_context returns True", p3.try_context("gana chalao wahan") == True))

# T4: entity extraction from 'search good python book'
steps4 = plan("search good python book")
results.append(("T4 step count", len(steps4) == 1))
results.append(("T4 entity", steps4[0].entity == "good python book" if steps4 else False))

# T5: Hinglish connector
steps5 = plan("youtube kholo aur gana sunao")
results.append(("T5 step count", len(steps5) == 2))

# T6: open firefox then search on it
ctx6 = ContextMemory()
p6   = CommandPlanner(speak_female=noop, ctx=ctx6)
steps6 = p6.force_multi("open firefox and search python docs on it")
results.append(("T6 step count", len(steps6) == 2))
if len(steps6) == 2:
    results.append(("T6 s2 intent SEARCH_WEB", steps6[1].intent == "SEARCH_WEB"))

# Print results
passed = sum(1 for _, ok in results if ok)
total  = len(results)
print(f"\nResults: {passed}/{total} passed\n")
for name, ok in results:
    icon = "OK " if ok else "FAIL"
    print(f"  [{icon}] {name}")
