import os
from dotenv import load_dotenv
from groq import Groq
from tools import web_search, all_sources
import json
import re


def is_cited(source_num: int, text: str) -> bool:
    # Matches [1], [1, 2], [1,2], [2, 1], etc. — source_num appearing
    # as a whole number inside any bracketed citation group
    pattern = r'\[(?:\d+,\s*)*' + str(source_num) + r'(?:,\s*\d+)*\]'
    """
    Breaking that pattern down:
    - \[ and \] : literal brackets
    - (?:\d+,\s*)* : zero or more "number, " groups before your target number (handles [1, 2] 
                      when checking for 2)
    - str(source_num) : your specific number
    - (?:,\s*\d+)* : zero or more ", number" groups after your target number (handles [1, 2] 
                     when checking for 1)"""

    return bool(re.search(pattern, text))

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

tools_schema = [
    {
        "type": "function",
        "function": {
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
                    }
                },
                "required": ["query"],
            },
        },
    }
]

available_functions = {"web_search": web_search}

messages = [
    {
        "role": "system",
        "content": (
            "You are a research assistant. Use web_search to find current information "
            "before answering.\n\n"
            "Citation rules:\n"
            "- Each search result you receive is numbered, e.g. [1], [2], [3].\n"
            "- When you state a fact from a source, cite it inline using that exact number, e.g. 'Fast inference reduces cost [2].'\n"
            "- Do NOT invent your own citation format.\n"
            "- Only cite sources that were actually returned by web_search. Never fabricate a URL."
        ),
    },
    {
        "role": "user",
        "content": os.environ.get("QUERY"),
    },
]

all_sources.clear()  # Clear the global list of sources before starting a new session

response = client.chat.completions.create(
    model=os.environ.get("MODEL"),
    messages=messages,
    tools=tools_schema,
)

messages.append(response.choices[0].message)

# Set a maximum number of iterations to prevent infinite loops
max_iterations = 10
iteration = 0

while response.choices[0].message.tool_calls and iteration < max_iterations:
    iteration += 1
    
    # Handle tool calls
    for tool_call in response.choices[0].message.tool_calls:
        # Get the function name and arguments from the tool call
        function_name = tool_call.function.name
        function_to_call = available_functions[function_name]
        function_args = json.loads(tool_call.function.arguments)

        print(f"[Agent is calling: {function_name}({function_args})]")

        function_to_call = available_functions[function_name]
        function_response = function_to_call(**function_args)

        # When you get the result back from actually running web_search(...),
        # you need to append a new message to your messages list
        # so the model can see it on the next call.
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": str(function_response),
            }
        )

    # After handling all tool calls, you can call the model again with the updated messages
    response = client.chat.completions.create(
        model=os.environ.get("MODEL"),
        messages=messages,
        tools=tools_schema,
    )

    # Append the new response to the messages list
    messages.append(response.choices[0].message)

# After the loop, you can get the final response from the model
final = response.choices[0].message.content

sources_section = "\n\nSources:\n" + "\n".join(
    f"[{i}] {title} - {url}"
    for i, title, url in all_sources
    if f"[{i}]" in final
)

print("FINAL RESPONSE:\n", final + sources_section)
