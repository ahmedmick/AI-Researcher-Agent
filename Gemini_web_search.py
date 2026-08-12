import os
from dotenv import load_dotenv
from google import genai
from tools import web_search, fetch_page, all_sources
import json
import re
import time
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from arabic_parser import ArabicParser

def print_sources_table(all_sources, final, is_cited, console):
    cited_sources = [
        (i, title, url) for i, title, url in all_sources if is_cited(i, final)
    ]

    if not cited_sources:
        return  # nothing to show

    table = Table(
        title="Sources",
        show_lines=True,
        title_style="bold magenta",
    )
    table.add_column("#", style="bold cyan", justify="center")
    table.add_column("Title", header_style="red", style="white", justify="center")
    table.add_column("URL", header_style="red", justify="center")

    for i, title, url in cited_sources:
        table.add_row(f"[{i}]", title, f"[blue underline]{url}[/blue underline]")

    console.print("\n")
    console.print(table)


def is_cited(source_num: int, text: str) -> bool:
    # Matches [1], [1, 2], [1,2], [2, 1], etc. — source_num appearing
    # as a whole number inside any bracketed citation group
    pattern = r"\[(?:\d+,\s*)*" + str(source_num) + r"(?:,\s*\d+)*\]"
    """
    Breaking that pattern down:
    - \[ and \] : literal brackets
    - (?:\d+,\s*)* : zero or more "number, " groups before your target number (handles [1, 2] 
                      when checking for 2)
    - str(source_num) : your specific number
    - (?:,\s*\d+)* : zero or more ", number" groups after your target number (handles [1, 2] 
                     when checking for 1)"""

    return bool(re.search(pattern, text))

def start_gemini_agent():
    load_dotenv()
    console = Console()
    parser = ArabicParser()

    client = genai.Client(api_key=os.environ.get("Gemini_API_KEY"))
    
    tools_schema = [
        {
            "type": "function",
            "name": "web_search",
            "description": "Search the web for information",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "The maximum number of results to return",
                    },
                },
                "required": ["query"],
            },
        },
        {
            "type": "function",
            "name": "fetch_page",
            "description": "Fetch the content of a web page given its URL",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL of the web page to fetch",
                    },
                },
                "required": ["url"],
            },
        },
    ]

    available_functions = {"web_search": web_search, "fetch_page": fetch_page}

    system_instruction=(
        "You are a research assistant. Use web_search to find current information "
        "before answering.\n\n"
        "Citation rules:\n"
        "- Each search result you receive is numbered, e.g. [1], [2], [3].\n"
        "- When you state a fact from a source, cite it inline using that exact number, e.g. 'Fast inference reduces cost [2].'\n"
        "- Do NOT invent your own citation format.\n"
        "- Only cite sources that were actually returned by web_search. Never fabricate a URL."
    )

    while True:
        user_query = input("\nAsk a question (or type 'exit' to quit): ")
        if user_query.strip().lower() == 'exit':
            break

        all_sources.clear()  # Clear the global list of sources before starting a new session

        previous_id = None  # Initialize previous_id to None

        # Set a maximum number of iterations to prevent infinite loops
        max_iterations = 10
        iteration = 0

        previous_id = None  # Initialize previous_id to None
        is_completed = False
        failed = False

        while iteration < max_iterations:
            iteration += 1

            for attempt in range(5):
                try:
                    response = client.interactions.create(
                        model=os.environ.get("MODEL"),
                        input=user_query,
                        system_instruction=system_instruction,
                        tools=tools_schema,
                        previous_interaction_id=previous_id,
                    )

                    function_results = []
                    for step in response.steps:
                        if step.type == "function_call":
                            result = available_functions[step.name](**step.arguments)
                            preview = str(result)[:200] + ("..." if len(str(result)) > 200 else "")
                            console.print(f"[dim]→ Calling {step.name}({step.arguments})\nResult:\n{preview}[/dim]")
                            function_results.append({
                                "type": "function_result",
                                "name": step.name,
                                "call_id": step.id,
                                "result": [{"type": "text", "text": json.dumps(result)}]
                            })

                    if not function_results:
                        is_completed = True
                        break  # Exit the loop if there are no function calls

                    previous_id = response.id  # Update previous_id for the next iteration
                    user_query = function_results # Update user_query with the function results for the next iteration

                    break  # Exit the retry loop if successful        

                except Exception as e:
                    wait = 2**attempt  # exponential backoff: 1s, 2s, 4s, 8s, 16s
                    if "429" in str(e) or "quota" in str(e).lower():
                        console.print(
                            f"[yellow][Rate limited, waiting {wait}s before retry...][/yellow]"
                        )
                        time.sleep(wait)  # Exponential backoff before retrying
                    else:
                        raise

            else:
                # Only runs if all 5 attempts failed (no break was hit)
                final = "Sorry, the request failed after multiple retries."
                failed = True
                break

            if is_completed:
                break # Exit the loop if there are no function calls

        # After the loop, you can get the final response from the model
        if not failed and is_completed:
            final = response.output_text # Get the final output text from the last response
        elif not failed and not is_completed:
            final = (
                "I wasn't able to complete full research within the allowed search limit." + 
                "Here's what I found so far:\n\n" +
                response.output_text
            )

        console.print("\n[bold green]FINAL RESPONSE[/bold green]\n")

        if parser.contains_arabic(final):
            parser.render_arabic_markdown(final, console)
        else:
            console.print(Markdown(final))

        print_sources_table(all_sources, final, is_cited, console)
