"""Keyword engine verification — identifies any test failures."""
from keyword_engine import keyword_match

TESTS = [
    ("please open chrome for me",          "OPEN_APP",       "chrome"),
    ("can you play some music",             "PLAY_MUSIC",     ""),
    ("gana chalao",                         "PLAY_MUSIC",     ""),
    ("gaana bajao yaar",                    "PLAY_MUSIC",     ""),
    ("chrome kholo",                        "OPEN_APP",       "chrome"),
    ("bhai firefox chalao",                 "OPEN_APP",       "firefox"),
    ("search for python tutorials",         "SEARCH_WEB",     "python tutorials"),
    ("google machine learning",             "SEARCH_WEB",     "machine learning"),
    ("samay kya hai",                       "TIME_QUERY",     ""),
    ("what time is it",                     "TIME_QUERY",     ""),
    ("aaj ki date kya hai",                 "DATE_QUERY",     ""),
    ("mausam batao",                        "WEATHER",        ""),
    ("weather in delhi",                    "WEATHER",        ""),
    ("band karo chrome",                    "CLOSE_WINDOW",   ""),
    ("close this window",                   "CLOSE_WINDOW",   ""),
    ("volume up please",                    "SYSTEM_CONTROL", ""),
    ("take a screenshot",                   "SYSTEM_CONTROL", ""),
    ("remind me to call mom",               "NOTE_TASK",      ""),
    ("latest news sunao",                   "NEWS",           ""),
    ("open youtube",                        "OPEN_YOUTUBE",   "youtube"),
    ("play music on youtube",               "YOUTUBE_MUSIC",  ""),
    ("open chrome and search python",       "OPEN_APP",       "chrome"),
]

fails = []
for text, exp_intent, exp_entity in TESTS:
    r = keyword_match(text)
    if r is None:
        ok  = False
        got = "None"
    else:
        ok  = r["intent"] == exp_intent and exp_entity.lower() in r["entity"].lower()
        got = str(r["intent"]) + "/" + repr(r["entity"])
    if not ok:
        fails.append((text, "want " + exp_intent + "/" + repr(exp_entity) + " got " + got))

print()
if fails:
    print("FAILURES " + str(len(fails)) + "/" + str(len(TESTS)) + ":")
    for t, m in fails:
        print("  FAIL: " + repr(t))
        print("        " + m)
else:
    print("All " + str(len(TESTS)) + "/" + str(len(TESTS)) + " passed!")
