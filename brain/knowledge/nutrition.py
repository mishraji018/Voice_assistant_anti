
import re
import logging

logger = logging.getLogger(__name__)

# ── Knowledge Base ────────────────────────────────────────────────────────────

DISEASE_DATA = {
    "dengue": {
        "good": ["papaya", "papaya leaves juice", "kiwi", "coconut water", "pomegranate", "dalya", "khichdi"],
        "bad": ["oily food", "spicy food", "fried food", "caffeinated drinks", "non-veg"],
        "advice": "Dengue mein hydration sabse important hai sir. Fluids aur fruits jaise papaya aur coconut water kaafi faydemand hote hain."
    },
    "fever": {
        "good": ["soup", "broth", "citrus fruits", "vitamin c", "ginger tea", "oatmeal"],
        "bad": ["cold drinks", "heavy fatty food", "unprocessed sugar"],
        "advice": "Sir, fever ke waqt light food aur fluids lijiye. Warm vegetable soup ya ginger tea aapko relief degi."
    },
    "malaria": {
        "good": ["citrus fruits", "dal", "paneer", "eggs", "boiled vegetables", "rice water"],
        "bad": ["excessive fiber", "fried food", "thick cream", "spices"],
        "advice": "Sir, malaria mein protein aur vitamins zaroori hain. Eggs aur citrus fruits lijiye, par heavy masaledar khane se bachiye."
    },
    "thyroid": {
        "good": ["iodized salt", "brazil nuts", "eggs", "dairy products", "fish"],
        "bad": ["soy", "cruciferous vegetables", "cabbage", "cauliflower", "excessive gluten"],
        "advice": "Sir, thyroid control karne ke liye soy aur goitrogenic vegetables (jaise cabbage aur cauliflower) ko avoid karein. Iodized salt aur protein-rich diet achhi hoti hai."
    },
    "goitre": {
        "good": ["iodine rich food", "seaweed", "seafood", "eggs", "dairy"],
        "bad": ["cabbage", "cauliflower", "soy", "spinach", "mustard greens"],
        "advice": "Goitre ke liye iodine rich food sabse zaroori hai sir. Par raw cabbage aur spinach thoda kam kijiye, kyunki yeh iodine absorption mein rukawat dal sakte hain."
    },
    "cold": {
        "good": ["warm water", "honey", "ginger", "garlic", "chicken soup", "vitamic c"],
        "bad": ["cold water", "ice cream", "dark chocolate", "dairy"],
        "advice": "Zukam (cold) mein warm cheezein sabse behtar hain sir. Honey aur ginger ke saath warm water ya soup lene se gale ko kafi aram milega."
    },
    "flu": {
        "good": ["clear fluids", "juice", "herbal tea", "bananas", "rice", "toast"],
        "bad": ["alcohol", "fast food", "heavy snacks"],
        "advice": "Flu mein bahut sara rest aur fluids lijiye sir. Light diet jaise toast ya soup aapki energy recover karne mein madad karegi."
    }
}

DISEASES = list(DISEASE_DATA.keys())
FOOD_ITEMS = ["papaya", "kiwi", "banana", "apple", "orange", "eggs", "milk", "tea", "coffee", "rice", "bread", "chicken", "meat", "soy", "spinach", "cabbage", "cauliflower", "salt", "water"]

# ── Feature Logic ─────────────────────────────────────────────────────────────

def extract_entities(text: str):
    """Simple extraction of disease and food from text."""
    text_lower = text.lower()
    found_disease = None
    found_food = None

    for d in DISEASES:
        if d in text_lower:
            found_disease = d
            break
    
    for f in FOOD_ITEMS:
        if f in text_lower:
            found_food = f
            break
            
    return found_disease, found_food

def handle_nutrition_query(text: str) -> str:
    """Main handler for nutrition queries."""
    disease, food = extract_entities(text)
    disclaimer = "\n\nNote: This is general information sir. Please consult a doctor for proper medical advice."
    
    if not disease:
        return f"Sir, main abhi sirf common diseases ke bare mein nutrition advice de sakti hoon (like Dengue, Fever, ya Thyroid). Kya aap inme se kisi ke bare mein pooch rahe hain? {disclaimer}"

    data = DISEASE_DATA[disease]
    
    # Specific food check
    if food:
        if food in data["good"]:
            response = f"Yes sir, {disease} mein {food} khana bilkul safe aur beneficial hai. {data['advice']}"
        elif food in data["bad"]:
            response = f"Nahi sir, {disease} ke waqt {food} avoid karna behtar hai. {data['advice']}"
        else:
            response = f"Sir, {disease} ke liye {food} ke bare mein koi specific recommendation nahi hai, par general advice yeh hai: {data['advice']}"
    else:
        # General advice for the disease
        response = f"Sir, {disease} ke liye meri advice yeh hai: {data['advice']}"

    return response + disclaimer
