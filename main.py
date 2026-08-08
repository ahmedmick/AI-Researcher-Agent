from Gemini_web_search import start_gemini_agent
from Groq_web_search import start_groq_agent
from rich.console import Console

if __name__ == "__main__":
    console = Console()
    console.print("[bold]Welcome to AI Researcher Agent[/bold]\n")
    
    model_choice = input("\n- Enter '1' for Gemini Model\n- Enter '2' for Groq/OpenAI Model\nChoose your perfered AI Model: ")
    while model_choice != '1' and model_choice != '2':
        model_choice = input("\n- Enter '1' for Gemini Model\n- Enter '2' for Groq/OpenAI Model\nChoose your perfered AI Model: ")
        
    if model_choice == '1':
        start_gemini_agent()
    else:
        start_groq_agent()
