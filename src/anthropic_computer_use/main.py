import os
import anthropic

EDITOR_FILE = os.path.join(os.getcwd(), "editor_dir", "file.txt")


def main():
    # Initialize the Anthropic client
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    # Create a conversation
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[{"role": "user", "content": "Hello, Claude"}],
    )

    # Print the response
    print(message.content[0].text)


if __name__ == "__main__":
    main()
