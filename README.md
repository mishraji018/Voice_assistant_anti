# 🎙️ Voice Assistant with Anti-Spoof Security

An AI voice assistant built in Python with modular command routing,
background listening, and security protection against unauthorized voice commands.

## 🚀 Features
- Real-time voice recognition
- Modular command system
- Async background listening
- Anti-spoof authentication layer
- Logging system
- Config-driven behavior

## 🏗 Architecture
core → assistant brain  
commands → individual skills  
config → assistant settings  
logs → runtime history  

## ⚙️ Installation
pip install -r requirements.txt

## ▶️ Run
python main.py

## 🔮 Future Work
- Speaker verification via ML
- GUI interface
- Mobile integration



📁 1️⃣Project Structure Section

## 📂 Project Structure

Voice_assistant_anti/
├── main.py                # Entry point
├── cleanup.py             # Maintenance script
├── requirements.txt       # Python dependencies
│
├── brain/                 # Intelligence layer
│   ├── orchestrator.py    # Main logic router
│   ├── intents.py         # Intent detection
│   ├── learning.py        # Learning & correction system
│   ├── infra/             # Event bus + database
│   └── knowledge/         # AI + weather handlers
│
├── core/                  # System & hardware layer
│   ├── audio/             # Speech input/output
│   ├── monitor/           # Activity logging
│   ├── state/             # Runtime state
│   └── config/            # Configuration validation
│
├── commands/              # OS-level commands
│   └── system/            # Shutdown, hardware control, etc.
│
└── ui/                    # Visual interface


🔁 2️⃣Architecture Flow
## 🔄 Event Flow

Voice Capture  
→ Emit QUERY_RECEIVED  
→ Orchestrator  
→ Intent Detection  
→ Weather / OS / Knowledge Routing  
→ Emit SPEECH_REQUESTED  
→ UI Update + Text-to-Speech


⚙️ 3️⃣Setup Instructions
## ⚙️ Setup

1. Clone repository
2. Install dependencies:

   pip install -r requirements.txt

3. Create ni.env file:

   OPENWEATHER_API_KEY=your_key_here

4. Run:

   python main.py
