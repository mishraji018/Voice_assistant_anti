import customtkinter as ctk
import time
from core.config import config

class SetupWizardUI(ctk.CTk):
    def __init__(self, on_complete_callback):
        super().__init__()
        self.on_complete_callback = on_complete_callback
        
        # Window Setup
        self.title("J.A.R.V.I.S Setup")
        self.geometry("600x450")
        self.resizable(False, False)
        
        # Center the window
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        
        # J.A.R.V.I.S Theme (Dark Mode)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.configure(fg_color="#050a0f")
        
        # Main Container
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=40, pady=40)
        
        # Show Splash Screen first
        self.show_splash_screen()

    def clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def show_splash_screen(self):
        self.clear_container()
        
        title = ctk.CTkLabel(self.container, text="J.A.R.V.I.S", font=("Orbitron", 32, "bold"), text_color="#00e5ff")
        title.pack(pady=(40, 20))
        
        subtitle1 = ctk.CTkLabel(self.container, text="Welcome.", font=("Rajdhani", 18), text_color="#c8e8ff")
        subtitle1.pack(pady=5)
        
        subtitle2 = ctk.CTkLabel(self.container, text="Let's configure your assistant.", font=("Rajdhani", 16), text_color="#4a7a9b")
        subtitle2.pack(pady=5)
        
        btn_begin = ctk.CTkButton(self.container, text="[ Begin Setup ]", font=("Orbitron", 14, "bold"), 
                                  fg_color="transparent", border_width=2, border_color="#00e5ff", text_color="#00e5ff",
                                  hover_color="#006677", command=self.show_config_screen)
        btn_begin.pack(pady=(50, 20))

    def show_config_screen(self):
        self.clear_container()
        
        title = ctk.CTkLabel(self.container, text="API Configuration", font=("Orbitron", 24, "bold"), text_color="#00e5ff")
        title.pack(pady=(10, 20))
        
        # Groq API Key (Required)
        lbl_groq = ctk.CTkLabel(self.container, text="Groq API Key (Required)", font=("Rajdhani", 14), text_color="#c8e8ff")
        lbl_groq.pack(anchor="w")
        self.entry_groq = ctk.CTkEntry(self.container, width=500, placeholder_text="gsk_...", show="*")
        self.entry_groq.insert(0, config.get_secret("groq_api_key", ""))
        self.entry_groq.pack(pady=(0, 15))
        
        # Deepgram API Key (Required for Streaming STT)
        lbl_deepgram = ctk.CTkLabel(self.container, text="Deepgram API Key (Required for Streaming)", font=("Rajdhani", 14), text_color="#c8e8ff")
        lbl_deepgram.pack(anchor="w")
        self.entry_deepgram = ctk.CTkEntry(self.container, width=500, placeholder_text="Enter Deepgram key...", show="*")
        self.entry_deepgram.insert(0, config.get_secret("deepgram_api_key", ""))
        self.entry_deepgram.pack(pady=(0, 15))
        
        # OpenWeather API Key (Optional)
        lbl_weather = ctk.CTkLabel(self.container, text="OpenWeather API Key (Optional)", font=("Rajdhani", 14), text_color="#c8e8ff")
        lbl_weather.pack(anchor="w")
        self.entry_weather = ctk.CTkEntry(self.container, width=500, placeholder_text="Enter key to enable weather...", show="*")
        self.entry_weather.insert(0, config.get_secret("openweather_api_key", ""))
        self.entry_weather.pack(pady=(0, 15))
        
        # ElevenLabs API Key (Optional)
        lbl_eleven = ctk.CTkLabel(self.container, text="ElevenLabs API Key (Optional)", font=("Rajdhani", 14), text_color="#c8e8ff")
        lbl_eleven.pack(anchor="w")
        self.entry_eleven = ctk.CTkEntry(self.container, width=500, placeholder_text="Enter key to enable premium voices...", show="*")
        self.entry_eleven.insert(0, config.get_secret("elevenlabs_api_key", ""))
        self.entry_eleven.pack(pady=(0, 25))
        
        # Error Label
        self.error_label = ctk.CTkLabel(self.container, text="", font=("Rajdhani", 12), text_color="#ff4444")
        self.error_label.pack()
        
        # Save Button
        btn_save = ctk.CTkButton(self.container, text="Save Configuration", font=("Orbitron", 14, "bold"),
                                 fg_color="#00e5ff", text_color="#050a0f", hover_color="#00b3cc",
                                 command=self.save_and_continue)
        btn_save.pack()

    def save_and_continue(self):
        groq_key = self.entry_groq.get().strip()
        deepgram_key = self.entry_deepgram.get().strip()
        weather_key = self.entry_weather.get().strip()
        eleven_key = self.entry_eleven.get().strip()
        
        if not groq_key:
            self.error_label.configure(text="Error: Groq API Key is strictly required.", text_color="#ff4444")
            return
            
        self.error_label.configure(text="Validating key...", text_color="#ffab40")
        
        # Disable button during check
        self.btn_save = self.container.winfo_children()[-1]
        self.btn_save.configure(state="disabled")
        
        def validation_callback(is_valid, msg):
            self.btn_save.configure(state="normal")
            if is_valid:
                self.error_label.configure(text=f"🟢 {msg}", text_color="#00e5ff")
                # Save to ConfigManager
                config.set_secret("groq_api_key", groq_key)
                config.set_secret("deepgram_api_key", deepgram_key)
                config.set_secret("openweather_api_key", weather_key)
                config.set_secret("elevenlabs_api_key", eleven_key)
                # Ensure JSON gets a save call
                config.set("general", "wake_word", config.get("general", "wake_word", "jarvis"))
                self.after(500, self.show_completion_screen)
            else:
                self.error_label.configure(text=f"🔴 {msg}", text_color="#ff4444")
                # Allow user to proceed offline if they really want, but require a second click
                self.btn_save.configure(text="Save Anyway (Offline)", command=lambda: self._force_save(groq_key, deepgram_key, weather_key, eleven_key))
                
        config.validate_groq_async(groq_key, validation_callback)

    def _force_save(self, groq_key, deepgram_key, weather_key, eleven_key):
        config.set_secret("groq_api_key", groq_key)
        config.set_secret("deepgram_api_key", deepgram_key)
        config.set_secret("openweather_api_key", weather_key)
        config.set_secret("elevenlabs_api_key", eleven_key)
        config.set("general", "wake_word", config.get("general", "wake_word", "jarvis"))
        self.show_completion_screen()

    def show_completion_screen(self):
        self.clear_container()
        
        title = ctk.CTkLabel(self.container, text="Systems Online", font=("Orbitron", 32, "bold"), text_color="#00e5ff")
        title.pack(pady=(40, 20))
        
        subtitle1 = ctk.CTkLabel(self.container, text="Configuration Complete.", font=("Rajdhani", 18), text_color="#c8e8ff")
        subtitle1.pack(pady=5)
        
        subtitle2 = ctk.CTkLabel(self.container, text="Welcome aboard.", font=("Rajdhani", 16), text_color="#4a7a9b")
        subtitle2.pack(pady=5)
        
        btn_launch = ctk.CTkButton(self.container, text="[ Launch J.A.R.V.I.S ]", font=("Orbitron", 14, "bold"), 
                                  fg_color="transparent", border_width=2, border_color="#00e5ff", text_color="#00e5ff",
                                  hover_color="#006677", command=self.finish_setup)
        btn_launch.pack(pady=(50, 20))
        
    def finish_setup(self):
        self.destroy()
        if self.on_complete_callback:
            self.on_complete_callback()

def launch_setup_wizard():
    """Runs the setup wizard synchronously and blocks until complete."""
    completed = False
    
    def on_complete():
        nonlocal completed
        completed = True
        
    app = SetupWizardUI(on_complete_callback=on_complete)
    app.mainloop()
    return completed
