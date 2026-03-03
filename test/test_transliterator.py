# -*- coding: utf-8 -*-
"""Quick integration test for transliterator.py + translator.py"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from transliterator import transliterate_devanagari, has_devanagari

tests = [
    ("jarvis youtube \u0916\u094b\u0932\u094b",          "kholo"),
    ("\u0938\u094d\u091f\u0949\u0930\u094d\u092e",                   "storm"),
    ("\u092e\u094c\u0938\u092e \u092c\u0924\u093e\u0913",            "weather batao"),
    ("\u0917\u093e\u0928\u093e \u092c\u091c\u093e\u0913",            "gaana bajao"),
    ("open chrome aur \u0917\u093e\u0928\u093e \u092c\u091c\u093e\u0913", "gaana bajao"),
    ("pure english text",     "pure english text"),   # passthrough
    ("\u0916\u094b\u0932\u094b \u092f\u0942\u091f\u094d\u092f\u0942\u092c",      "kholo youtube"),
]

print("=== transliterator.py self-test ===")
passed = 0
for inp, expected in tests:
    result = transliterate_devanagari(inp)
    ok = expected.lower() in result.lower()
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}]  in:  {repr(inp)}")
    print(f"         out: {repr(result)}")
    print(f"         exp: {repr(expected)}")
    print()
    if ok:
        passed += 1

print(f"Result: {passed}/{len(tests)} passed")
print()

# Also test translator pipeline
print("=== translator.py integration test ===")
from core.infra.translator import translate_to_english

trans_tests = [
    ("\u0938\u094d\u091f\u0949\u0930\u094d\u092e",               "hi",  "storm"),          # unknown proper noun in Devanagari
    ("\u0916\u094b\u0932\u094b",               "hi",  "open"),           # common command
    ("youtube kholo",   "en",  "open youtube"),    # Hinglish passthrough
    ("gaana bajao",     "en",  "play"),            # Hinglish verb
    ("chrome kholo",    "en",  "open"),           # 'chrome open' or 'open chrome' — both contain 'open'
]

trans_passed = 0
for inp, lang, expected in trans_tests:
    result = translate_to_english(inp, lang)
    ok = expected.lower() in result.lower()
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}]  in={repr(inp)}  lang={lang!r}")
    print(f"         out={repr(result)}")
    print(f"         exp contains: {repr(expected)}")
    print()
    if ok:
        trans_passed += 1

print(f"Result: {trans_passed}/{len(trans_tests)} passed")
print()
all_ok = (passed == len(tests)) and (trans_passed == len(trans_tests))
sys.exit(0 if all_ok else 1)
