import json

from tavily import TavilyClient

from app.config import get_settings


def main() -> None:
    client = TavilyClient(api_key=get_settings().require("tavily_api_key"))
    result = client.search(
        "latest trends in short-form creator marketing",
        search_depth="basic",
        max_results=1,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
