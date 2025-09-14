import os
from dotenv import load_dotenv
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack_integrations.components.generators.google_genai import GoogleGenAIChatGenerator
from haystack.dataclasses import ChatMessage
from haystack.components.agents import Agent
from haystack_integrations.tools.mcp import MCPTool, StdioServerInfo, StreamableHttpServerInfo
from haystack.utils import Secret

# Load environment variables from .env file
load_dotenv()
GITHUB_PERSONAL_ACCESS_TOKEN = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Check if the required environment variables are set
if not GITHUB_PERSONAL_ACCESS_TOKEN:
    raise ValueError(
        "GITHUB_PERSONAL_ACCESS_TOKEN environment variable not found. "
        "Please set it in your .env file or environment."
    )

if not OPENAI_API_KEY and not GOOGLE_API_KEY:
    raise ValueError(
        "OPENAI_API_KEY and GOOGLE_API_KEY environment variable not found. "
        "Please set it in your .env file or environment."
    )


""" # Create the MCP server
github_mcp_server = StdioServerInfo(
    command="docker",
    args=[
        "run", "-i", "--rm",
        "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
        "ghcr.io/github/github-mcp-server"
    ],
    env={"GITHUB_PERSONAL_ACCESS_TOKEN": GITHUB_PERSONAL_ACCESS_TOKEN}, 
) """

# Define the HTTP-based MCP server
github_mcp_server = StreamableHttpServerInfo(
    url="https://api.githubcopilot.com/mcp/",
    token=Secret.from_token(GITHUB_PERSONAL_ACCESS_TOKEN),
)

print("MCP server is created")


# Create the tools

# Issue Operations
get_issue = MCPTool(name="get_issue", server_info=github_mcp_server, connection_timeout=120)
create_issue = MCPTool(name="create_issue", server_info=github_mcp_server)
search_issues = MCPTool(name="search_issues", server_info=github_mcp_server)
edit_issue = MCPTool(name="update_issue", server_info=github_mcp_server)

# Repo Operations
get_file_contents = MCPTool(name="get_file_contents", server_info=github_mcp_server)
search_repos = MCPTool(name="search_repositories", server_info=github_mcp_server)
create_fork = MCPTool(name="fork_repository", server_info=github_mcp_server)

tools = [
    get_issue,
    create_issue,
    search_issues,
    edit_issue,
    get_file_contents,
    search_repos,
    create_fork,
]

print("MCP tools are created")

# Define the system prompt
system_prompt = """
            You are GitHub-AI, an intelligent assistant for GitHub operations. You can search repositories, retrieve files, fork repositories, and manage issues by calling the following tools:
            
            1. get_issue: Retrieve detailed information about a specific issue or pull request by number and repository.
            2. create_issue: Open a new issue in a given repository with title, body, and optional labels.
            3. search_issues: Search across issues and pull requests using GitHub query syntax (e.g., repo:owner/name is:open label:bug).
            4. update_issue: Modify an existing issue's title, body, or labels.
            5. get_file_contents: Fetch the contents of a file at a given path in a repository.
            6. search_repositories: Search for repositories using GitHub query syntax (e.g., language:python topic:haystack).
            7. create_fork: Fork a repository into the authenticated user's account.

            When you receive a user request:
            - Decide which tool(s) can fulfill the request.
            - Format tool calls with appropriate parameters.
            - After invoking tools, summarize results in clear, user-friendly language.

            Task Execution Guidelines

            For each user request, identify the task type and follow the exact tool call pattern below:

            Task 1: Check README.md for typos and open an issue
                1. Use "get_file_contents" to fetch README.md from {owner/repo}.
                2. Detect real orthographic typos (e.g., misspellings, homophones).
                3. If typos are found:
                - Use "create_issue" with:
                    - Title: "Typos found in README.md"
                    - Labels: ["typo", "docs"]
                    - Body: List typos with suggested fixes and line/column positions.
                4. Return raw JSON:
                {
                    "typo_count": <number>,
                    "issue_created": true/false
                }

            Task 2: “Check for open issues containing a keyword in owner/repo or a list of repos”
            Tool sequence:
            - For each target repository (e.g., deepset-ai/haystack, deepset-ai/haystack-core-integrations):
                - Call search_issues with query:
                    repo:owner/repo is:open keyword
            - Aggregate results and return a user-friendly summary.

            Task 3: “Find issues labeled 'Contributions wanted!' in owner/repo or a list of repos”
            Tool sequence:
            - For each target repository (e.g., deepset-ai/haystack, deepset-ai/haystack-core-integrations):
                - Call search_issues with query:
                    repo:owner/repo is:open label:"Contributions wanted!"
            - Summarize titles and links of matching issues.

            Task 4: “Fork a given repository owner/repo into the user's account”
            Tool sequence:
            - Call create_fork with:
                repository: owner/repo
            - Return the newly forked repository URL upon success.

            General Notes
            - For multi-repo tasks, repeat the pattern for each repository.
            - Always return both a plain-language summary and relevant tool results (e.g., issue links, repo URLs).
            - If required information is missing (e.g., repo name, keyword, label), ask the user for clarification before proceeding.

"""

""" 
chat_generator=OpenAIChatGenerator(
        model="o4-mini",
        api_key=Secret.from_token(OPENAI_API_KEY)
    ), """


# Create the agent
agent = Agent(
    chat_generator=GoogleGenAIChatGenerator(
        model ="gemini-2.5-flash",
        api_key=Secret.from_token(GOOGLE_API_KEY),
    ),
    tools=tools,
    system_prompt=system_prompt,
)


print("Agent created")

def pick_example_and_run(agent):
    # Header
    print("\n=== AGENTIC GITHUB DEMO - MCP x Haystack ===\n")

    # Define your example queries
    examples = {
        "1": "Can you find the typo in the README of TheMimikyu/spring-into-haystack and open an issue about how to fix it? Be clear in the details provided in the typo.",
        "2": "List all open issues containing 'async pipelines' in deepset-ai/haystack and deepset-ai/haystack-core-integrations.",
        "3": "Show me all open issues labelled 'Contributions wanted!' in deepset-ai/haystack and deepset-ai/haystack-core-integrations.",
        "4": "Fork the deepset-ai/haystack repository into my account.",
    }
    
    print("NOTE: Fixed input queries due to scope of work.\n")
    print("=== Example Queries ===")
    print("You can run the following example queries to test the agent.")

    # Display the menu
    for num, query in examples.items():
        print(f"[{num}] {query}")
    print()

    # Read user choice
    choice = input("Select an example to run (1–4): ").strip()
    user_input = examples.get(choice)
    if not user_input:
        print("⚠️  Invalid selection. Please choose 1, 2, 3, or 4.")
        return

    # Echo the chosen query
    print(f"\n> Running query: {user_input}\n")

    # Run the agent
    response = agent.run(
        messages=[
            ChatMessage.from_user(text=user_input)
        ]
    )

    # Show thinking process and result
    print("\n=== Agent Trace ===\n")
    print(response)
    print("\n=== Final Response ===\n")
    print(response["messages"][-1].text)


if __name__ == "__main__":
    # (Assuming `agent` is already created above)
    pick_example_and_run(agent)
