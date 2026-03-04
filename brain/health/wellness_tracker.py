import sqlite3
import re
import logging
from datetime import datetime
from brain.infra.database import DB_PATH

logger = logging.getLogger(__name__)

def update_wellness_metric(metric: str, value):
    """Update a specific wellness metric for today in the SQLite database."""
    today = datetime.now().strftime("%Y-%m-%d")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Ensure today's row exists
    cursor.execute("INSERT OR IGNORE INTO wellness_log (date) VALUES (?)", (today,))
    
    # 2. Update the metric
    # Note: For water, sleep, and exercise, we ADD to the existing value
    if metric in ["water_glasses", "exercise_minutes", "sleep_hours"]:
        cursor.execute(f"UPDATE wellness_log SET {metric} = {metric} + ? WHERE date = ?", (value, today))
    else:
        # For diet_rating and mood, we overwrite
        cursor.execute(f"UPDATE wellness_log SET {metric} = ? WHERE date = ?", (value, today))
        
    conn.commit()
    conn.close()
    print(f"[Wellness] Logged {value} for {metric} today.")

def get_today_summary() -> dict:
    """Retrieve today's wellness data."""
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM wellness_log WHERE date = ?", (today,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    # wellness_log schema: date, water, exercise, sleep, diet, mood
    return {
        "water": row[1],
        "exercise": row[2],
        "sleep": row[3],
        "diet": row[4],
        "mood": row[5]
    }

def generate_health_report() -> str:
    """Generate a Hinglish health report based on today's logged data."""
    data = get_today_summary()
    if not data:
        return "Sir, aaj aapne abhi tak koi wellness data log nahi kiya hai. Aap pani intake ya exercise ke bare mein bata sakte hain."
        
    report = f"Sir, aaj aapne {data['water']} glasses pani piya hai, {data['exercise']} minutes exercise ki hai, aur "
    if data['sleep'] > 0:
        report += f"aapne {data['sleep']} hours ki neend li hai. "
    else:
        report += "sleep hours abhi log hona baaki hain. "
        
    # Mention Mood/Diet if notable
    if data['mood'] != 'neutral':
        report += f"Aapka mood aaj {data['mood']} raha, "
    
    if data['diet'] >= 4:
        report += "aur aapne kaafi healthy diet follow ki. "
    elif data['diet'] > 0 and data['diet'] <= 2:
        report += "lekin diet thodi unhealthy rahi sir. "

    # Add status assessment
    if data['water'] >= 8 and data['exercise'] >= 30:
        report += "Aapka routine aaj kaafi healthy aur balanced lag raha hai. Keep it up!"
    elif data['water'] < 4:
        report += "Lekin sir, hydration thoda kam hai. Aapko thoda aur pani peena chahiye."
    elif data['exercise'] == 0:
        report += "Thoda movement ya stretch karna aapki health ke liye acha rahega."
    else:
        report += "Aapka din normal hi ja raha hai sir."
        
    return report

def handle_wellness_query(text: str) -> str:
    """Detect numbers and metrics from user query and log them."""
    text_lower = text.lower()
    
    # 1. Check for report request
    if any(k in text_lower for k in ["report", "healthy", "how was my day", "health status", "kaisa raha"]):
        return generate_health_report()
    
    # 2. Try to extract numbers for logging
    # Matches patterns like "4 glasses of water", "30 minutes exercise", "7 hours sleep"
    extracted = False
    response_parts = []
    
    # Water
    water_match = re.search(r"(\d+)\s*(?:glasses?|cup|glass|bottle)?\s*(?:of|ki|ka)?\s*(?:water|pani)", text_lower)
    if water_match:
        val = int(water_match.group(1))
        update_wellness_metric("water_glasses", val)
        response_parts.append(f"{val} glasses water")
        extracted = True
        
    # Exercise
    ex_match = re.search(r"(\d+)\s*(?:minutes?|mins?|ghante)?\s*(?:of|ki|ka)?\s*(?:exercise|workout|gym|walking|walk)", text_lower)
    if ex_match:
        val = int(ex_match.group(1))
        update_wellness_metric("exercise_minutes", val)
        response_parts.append(f"{val} minutes exercise")
        extracted = True
        
    # Sleep
    sleep_match = re.search(r"(\d+)\s*(?:hours?|hrs?|ghante)?\s*(?:of|ki|ka)?\s*(?:sleep|soya|neend)", text_lower)
    if sleep_match:
        val = float(sleep_match.group(1))
        update_wellness_metric("sleep_hours", val)
        response_parts.append(f"{val} hours sleep")
        extracted = True

    # Diet (Simple keyword mapping)
    diet_keywords = {"healthy": 5, "good": 4, "balanced": 4, "okay": 3, "bad": 2, "junk": 1, "oily": 1}
    for k, v in diet_keywords.items():
        if k in text_lower or (k == "good" and "diet" in text_lower):
            update_wellness_metric("diet_rating", v)
            response_parts.append(f"healthy diet ({k})")
            extracted = True
            break

    # Mood (Simple keyword mapping)
    mood_keywords = ["happy", "great", "excellent", "sad", "tired", "low", "neutral", "okay", "good"]
    for m in mood_keywords:
        if m in text_lower and ("feeling" in text_lower or "mood" in text_lower or "am" in text_lower):
            update_wellness_metric("mood", m)
            response_parts.append(f"{m} mood")
            extracted = True
            break

    if extracted:
        items = " aur ".join(response_parts)
        return f"Got it sir. Maine aapka {items} record kar liya hai. Aaj ka routine achha chal raha hai."
        
    return "Sir, kya aap apni health ke bare mein kuch log karna chahte hain? Jaise water intake ya exercise?"
