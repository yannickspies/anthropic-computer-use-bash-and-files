import os
import anthropic
import argparse
import yaml
from datetime import datetime
import uuid
from typing import Dict, Any, List, Optional
import traceback
import sys

EDITOR_FILE = os.path.join(os.getcwd(), "editor_dir", "file.txt")
SESSIONS_DIR = os.path.join(os.getcwd(), "sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)


def handle_text_editor_tool(tool_call: Dict[str, Any]) -> Dict[str, Any]:
    """Handle text editor tool calls and return appropriate response"""
    command = tool_call["command"]
    # Remove /repo prefix and use the direct path to editor_dir
    path = tool_call["path"].replace("/repo/", "", 1)

    if command == "create":
        try:
            if os.path.exists(path):
                return {"error": f"File {path} already exists"}
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            # Write the file content
            with open(path, "w") as f:
                f.write(tool_call["file_text"])
            return {"content": f"File created at {path}"}
        except Exception as e:
            return {"error": str(e)}
            
    elif command == "view":
        try:
            if os.path.exists(path):
                with open(path, "r") as f:
                    content = f.read()
                return {"content": content}
            return {"error": f"File {path} does not exist"}
        except Exception as e:
            return {"error": str(e)}

    elif command == "create":
        try:
            if os.path.exists(path):
                return {"error": f"File {path} already exists"}
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(tool_call["file_text"])
            return {"content": f"File created at {path}"}
        except Exception as e:
            return {"error": str(e)}

    elif command == "str_replace":
        try:
            with open(path, "r") as f:
                content = f.read()
            if tool_call["old_str"] not in content:
                return {"error": "old_str not found in file"}
            new_content = content.replace(
                tool_call["old_str"], tool_call.get("new_str", "")
            )
            with open(path, "w") as f:
                f.write(new_content)
            return {"content": "File updated successfully"}
        except Exception as e:
            return {"error": str(e)}

    elif command == "insert":
        try:
            with open(path, "r") as f:
                lines = f.readlines()
            insert_line = tool_call["insert_line"]
            if insert_line > len(lines):
                return {"error": "insert_line beyond file length"}
            lines.insert(insert_line, tool_call["new_str"] + "\n")
            with open(path, "w") as f:
                f.writelines(lines)
            return {"content": "Content inserted successfully"}
        except Exception as e:
            return {"error": str(e)}

    return {"error": f"Unknown command {command}"}


def process_tool_calls(tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Process tool calls and return results"""
    results = []
    for tool_call in tool_calls:
        if tool_call["type"] == "tool_use" and tool_call["name"] == "str_replace_editor":
            result = handle_text_editor_tool(tool_call["input"])
            results.append({"tool_call_id": tool_call["id"], "output": result})
    return results


def create_session() -> str:
    """Create a new session with timestamp-based ID and return the session ID"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    session_id = f"{timestamp}-{uuid.uuid4().hex[:6]}"

    session_file = os.path.join(SESSIONS_DIR, f"{session_id}.yaml")
    session_data = {
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "messages": [],
        "tool_calls": [],
    }

    with open(session_file, "w") as f:
        yaml.safe_dump(session_data, f)

    return session_id


def log_to_session(session_id: str, data: Dict[str, Any], section: str):
    """Log data to the specified section of the session file"""
    session_file = os.path.join(SESSIONS_DIR, f"{session_id}.yaml")

    with open(session_file, "r") as f:
        session_data = yaml.safe_load(f)

    # Add timestamp to the data
    data["timestamp"] = datetime.now().isoformat()

    # Append to the specified section
    session_data[section].append(data)

    with open(session_file, "w") as f:
        yaml.safe_dump(session_data, f)


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument('edit_prompt', help='The editing prompt for Claude')
    args = parser.parse_args()

    # Initialize session
    session_id = create_session()
    print(f"Session ID: {session_id}")

    # Initialize the Anthropic client
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    # Create initial message with text editor tool
    api_message = {"role": "user", "content": args.edit_prompt}
    api_messages = [api_message]

    # Log initial message with metadata
    log_to_session(
        session_id,
        {
            **api_message,
            "timestamp": datetime.now().isoformat(),
            "type": "user_input"
        },
        "messages"
    )

    while True:
        try:
            response = client.beta.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                messages=api_messages,
                tools=[{"type": "text_editor_20241022", "name": "str_replace_editor"}],
                betas=["computer-use-2024-10-22"]
            )

            # Log API response
            log_to_session(
                session_id,
                {
                    "type": "api_response",
                    "timestamp": datetime.now().isoformat(),
                    "response": response.model_dump()
                },
                "messages"
            )

            # Extract content from response
            message_content = response.content[0] if response.content else None
            
            # Check for tool calls in the content array
            tool_calls = []
            for content in response.content:
                if hasattr(content, 'type') and content.type == 'tool_use':
                    tool_calls.append(content.model_dump())

            # Extract assistant message text
            assistant_text = next((c.text for c in response.content if hasattr(c, 'text')), "")

            # Log assistant message
            log_to_session(
                session_id,
                {
                    "role": "assistant",
                    "content": assistant_text,
                    "timestamp": datetime.now().isoformat(),
                    "type": "assistant_message"
                },
                "messages"
            )

            # If no tool calls, print response and exit
            if not tool_calls:
                print(assistant_text)
                break

            # Process tool calls
            for tool_call in tool_calls:
                # Log tool call request
                log_to_session(
                    session_id,
                    {
                        "type": "tool_call_request",
                        "timestamp": datetime.now().isoformat(),
                        "tool_call": tool_call
                    },
                    "tool_calls"
                )

            # Process tool calls and get results
            tool_results = process_tool_calls(tool_calls)

            # Log tool results
            for result in tool_results:
                log_to_session(
                    session_id,
                    {
                        "type": "tool_call_result",
                        "timestamp": datetime.now().isoformat(),
                        "result": result
                    },
                    "tool_calls"
                )

            # Add tool results message - note the different structure
            tool_results_message = {
                "role": "tool",
                "content": tool_results[0]["output"].get("content", "") if tool_results else "",
                "tool_call_id": tool_calls[0]["id"] if tool_calls else None
            }
            api_messages.append(tool_results_message)

            # Log tool results message
            log_to_session(
                session_id,
                {
                    **tool_results_message,
                    "timestamp": datetime.now().isoformat(),
                    "type": "tool_results_message"
                },
                "messages"
            )

        except Exception as e:
            # Log any errors
            log_to_session(
                session_id,
                {
                    "type": "error",
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc()
                },
                "messages"
            )
            print(f"Error: {str(e)}", file=sys.stderr)
            raise


if __name__ == "__main__":
    main()
