# Jarvis — Modular AI Voice Assistant

![Python](https://img.shields.io/badge/Python-3.11-blue)
![AI Assistant](https://img.shields.io/badge/Project-AI%20Voice%20Assistant-purple)
![Architecture](https://img.shields.io/badge/Architecture-Modular-green)
![Status](https://img.shields.io/badge/Status-Active-success)

Jarvis is a **modular AI-powered voice assistant built with Python**.  
It supports voice interaction, intelligent reasoning, system automation, health assistance, and autonomous AI agents.

The project is designed using a **layered architecture** to keep the system scalable, maintainable, and easy to extend.

---

# Features

## Voice Interaction
- Hindi + English voice commands
- Real-time speech recognition
- Natural voice responses using pyttsx3
- Wake word activation (Jarvis / Hey Jarvis)
- Stop interrupt system

---

## AI Reasoning System
Jarvis contains a modular reasoning system.

Capabilities include:

- Intent detection engine
- Conversation memory
- Self-learning intent correction
- Hybrid knowledge engine (Wikipedia + AI)

Example:

User:  
Who is Elon Musk  

Jarvis:  
Elon Musk is the CEO of Tesla and SpaceX.

User:  
Where was he born  

Jarvis understands that **he = Elon Musk**.

---

## Autonomous AI Agents

Jarvis includes intelligent agents capable of performing multi-step tasks.

Examples:

- Research and comparison agent
- Browser automation agent
- Multi-step task planning

Example command:


Jarvis find the best laptop under 1 lakh


Jarvis will:

1. Search laptops  
2. Compare specifications  
3. Recommend the best option

---

## Personal Assistant Capabilities

Jarvis works as a **daily productivity assistant**.

Capabilities:

- Long-term memory of user information
- Task & reminder manager
- Personal productivity assistant
- Reminder notifications

Example commands:


Jarvis remind me to drink water at 10 PM
Jarvis list my tasks
Jarvis my name is Pawan


---

## Health & Wellness Assistant

Jarvis can provide basic health guidance and wellness tracking.

Supported topics include:

- Fever
- Dengue
- Malaria
- Thyroid
- Goitre
- Cold and Flu
- Diet suggestions
- Hydration tracking
- Exercise monitoring
- Sleep tracking

Example:


Jarvis what should I eat during dengue


---

## Computer Vision (Screen Understanding)

Jarvis can analyze your computer screen.

Capabilities:

- OCR text extraction
- Detect active applications
- Read visible screen content

Example commands:


Jarvis read my screen
Jarvis what is on my screen


---

## System Automation

Jarvis can control system operations.

Examples:


open notepad
open chrome
shutdown computer
take screenshot
search google


---

# Architecture

Jarvis follows a **modular layered architecture**.


UI Layer
↓
Core Layer
↓
Brain Layer
↓
Commands Layer


### UI Layer
Handles user interface and visual interaction.

### Core Layer
Manages runtime services such as audio, state management, and responses.

### Brain Layer
Responsible for reasoning, planning, AI modules, memory systems, and decision making.

### Commands Layer
Executes operating system commands and automation tasks.

---

# Project Structure

Voice_Assistant
│
├── brain/                     # AI reasoning layer
│   ├── agent/                 # autonomous task agents
│   │   ├── task_agent.py
│   │   └── browser_agent.py
│   │
│   ├── memory/                # conversation & long-term memory
│   │   ├── conversation_memory.py
│   │   └── long_term_memory.py
│   │
│   ├── learning/              # self-learning intent system
│   │   └── intent_learning.py
│   │
│   ├── productivity/          # reminders & task manager
│   │   └── task_manager.py
│   │
│   ├── health/                # wellness tracker
│   │   └── wellness_tracker.py
│   │
│   ├── knowledge/             # knowledge engines
│   │   ├── engine.py
│   │   └── nutrition.py
│   │
│   ├── vision/                # screen understanding
│   │   └── screen_analyzer.py
│   │
│   ├── infra/                 # database & infrastructure
│   │   └── database.py
│   │
│   ├── orchestrator.py
│   ├── intents.py
│   └── capabilities.py
│
├── core/                      # runtime & system services
│   ├── audio/
│   │   ├── voice_control.py
│   │   └── voice_engine.py
│   │
│   ├── runtime/
│   │   └── response_manager.py
│   │
│   ├── state/
│   │   └── runtime_state.py
│   │
│   └── wake/
│
├── commands/                  # OS command execution
│   └── system/
│       └── command_system.py
│
├── ui/                        # Jarvis visual interface
│   └── visual_ui.py
│
├── config/                    # configuration files
│
├── legacy/                    # previous experimental modules
│
├── main.py                    # application entry point
├── requirements.txt
├── cleanup.py
└── README.md

---

# Installation

## Clone the repository

git clone https://github.com/mishraji018/Voice_assistant_anti.git

cd Voice_Assistant


---

## Create virtual environment


python -m venv venv


Activate environment

Windows:


venv\Scripts\activate


---

## Install dependencies


pip install -r requirements.txt


---

## Run Jarvis


python main.py


---

# Example Commands

You can interact with Jarvis using commands like:


Jarvis what is the weather today
Jarvis open notepad
Jarvis search python tutorials
Jarvis read my screen
Jarvis remind me to drink water
Jarvis what should I eat during fever


---

# Version

Current Release: **v2.0 — Jarvis AI Assistant**

---

# Author

Pawan Mishra

GitHub  
https://github.com/mishraji018

---

# License

MIT License
