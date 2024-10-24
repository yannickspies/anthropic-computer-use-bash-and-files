# Anthropic Computer Use -> Text Editor
> Let Claude 3.5 Sonnet NEW edit your files for you.

## Quick Start
- `uv run main "write a detailed 3 use case document for llms to a 'llm_use_cases.md' markdown file. then break that file into three going into details about the use cases."`
  - This will create a file at `./repo/llm_use_cases.md` with the 3 use cases.
  - Then it will break that file into three going into details about the use cases.

## Very cool command sequence
- `uv run main "write a detailed 3 use case document for llms to a 'llm_use_cases.md' markdown file. then break that file into three going into details about the use cases."`
- `uv run main "update the llm_use_cases.md file to add a fourth use case for data analysis and insights."`
- `uv run main "read the llm_use_cases.md file and update it to contain a mermaid diagram of the use cases."`
- `uv run main "update llm_use_cases.md: simplify the mermaid chart and make it lr."`

## Resources
- https://docs.anthropic.com/en/docs/build-with-claude/computer-use#bash-tool