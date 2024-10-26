# Anthropic Computer Use POC -> Bash and Text Tools
> Let Claude 3.5 Sonnet NEW operate your terminal andedit your files for you.
> Proof of concept

<img src="./images/computer_use.png" alt="anthropic-computer-use" style="max-width: 800px;">

## Setup
- `brew install uv` or [install another way](https://docs.astral.sh/uv/getting-started/installation/#pypi).
- `uv sync`
- `uv run main "hi please create a file called 'ping.txt' and write 'pong' in it."`

## Quick Start
- `uv run main "write a detailed 3 use case document for llms to a 'llm_use_cases.md' markdown file. then break that file into three going into details about the use cases."`
  - This will create a file at `./repo/llm_use_cases.md` with the 3 use cases.
  - Then it will break that file into three going into details about the use cases.

## Very cool command sequence
- `uv run main "write a detailed 3 use case document for llms to a 'llm_use_cases.md' markdown file. then break that file into three going into details about the use cases."`
- `uv run main "update the llm_use_cases.md file to add a fourth use case for data analysis and insights."`
- `uv run main "read the llm_use_cases.md file and update it to contain a mermaid diagram of the use cases."`
- `uv run main "update llm_use_cases.md: simplify the mermaid chart and make it lr."`

## Interesting notes
- Anthropics text editor tool is low key, very powerful. Most engineers will likely miss this.
- The text editor tool supports five commands (tools): `view, create, str_replace, insert, and undo_edit`.
- Upon consuming your prompt, it will generate and execute a series of these tools based on your prompt that you're code will run.
- The real innovation here to me is two fold.
  - First, this runs a SERIES ((`prompt chaining strikes again`)) of these tools based on your prompt.
  - Second, the tools execute very well, are context aware and follow instructions very well.

## Resources
- https://docs.anthropic.com/en/docs/build-with-claude/computer-use
- https://github.com/anthropics/anthropic-quickstarts/blob/main/computer-use-demo/computer_use_demo/loop.py