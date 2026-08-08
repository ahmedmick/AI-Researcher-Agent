from Gemini_web_search import start_gemini_agent
from Groq_web_search import start_groq_agent
from rich.console import Console

if __name__ == "__main__":
    console = Console()
    console.print("[bold]Welcome to AI Researcher Agent[/bold]")

    model_choice = input(
        "\n- Enter '1' for Gemini Model\n"
        "- Enter '2' for Groq/OpenAI Model(in progress)\n"
        "Choose your perfered AI Model: "
    )
    if model_choice == '2':
        console.print(
            f"\n[red][Groq/OpenAI Model is still in progress please choose another model.][/red]"
        )
        
    while model_choice != '1':
        model_choice = input(
            "\n- Enter '1' for Gemini Model\n"
            "- Enter '2' for Groq/OpenAI Model(in progress)\n"
            "Choose your perfered AI Model: "
        )
        if model_choice == '2':
            console.print(
                f"\n[red][Groq/OpenAI Model is still in progress please choose another model.][/red]"
            )

    if model_choice == '1':
        start_gemini_agent()
    elif model_choice == '2':
        # start_groq_agent()
        pass
