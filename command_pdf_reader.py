import PyPDF2
from voice_utils import speak

def read_pdf(file_path="example.pdf"):
    try:
        with open(file_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            pages = [page.extract_text() for page in reader.pages]
            text = " ".join(pages[:2])  # Reads first 2 pages
            speak(f"PDF content: {text[:500]}")  # Reads out up to 500 chars
    except Exception:
        speak("Failed to read the PDF file.")
