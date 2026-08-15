import os
from dotenv import load_dotenv
from tavily import TavilyClient
from trafilatura import extract
import requests

load_dotenv()

tavily_client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))

all_sources = []  # Global list to store all sources across multiple web_search calls

def web_search(query:str, max_results: int = 5, **kwargs) -> str:
    """Search the web and return a compact string of results for the LLM."""

    response = tavily_client.search(
        query=query,
        search_depth="basic",  # "advanced" costs more credits, gives deeper results
        max_results=max_results,
    )

    formatted = []
    for r in response["results"]:
        if not r['url'].startswith(("http://", "https://")):
            continue  # Skip results without valid URLs

        idx = len(all_sources) + 1  # Calculate the index based on the global list

        all_sources.append((idx, r["title"], r["url"]))  # Store the source in the global list

        formatted.append(
            f"{idx}. Title: {r['title']}\nURL: {r['url']}\nContent: {r['content']}\n"
        )
    return "\n\n".join(formatted)

def fetch_page(url: str, **kwargs) -> str:
    """Fetch the content of a web page given its URL."""
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (research-agent/1.0)"}, # Set a user-agent to avoid being blocked
            timeout=10,  # Set a timeout to avoid hanging indefinitely
        )
    except requests.RequestException as e:
        raise Exception(f"Failed to fetch page: {url}. Error: {str(e)}")

    content = extract(response.text)
    if not content:
        raise Exception(f"Failed to extract content from page: {url}")

    # Truncate to avoid blowing up the model's context window
    max_chars = 8000
    if len(content) > max_chars:
        content = content[:max_chars] + "\n\n[content truncated]"
        
    return content
