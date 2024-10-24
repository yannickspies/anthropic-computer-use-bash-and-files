import os
import anthropic
import argparse
import yaml
from datetime import datetime
import uuid
from typing import Dict, Any, List, Optional, Union
import traceback
import sys
import logging
from logging.handlers import RotatingFileHandler

EDITOR_FILE = os.path.join(os.getcwd(), "editor_dir", "file.txt")
SESSIONS_DIR = os.path.join(os.getcwd(), "sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)


class EditorSession:
    def __init__(self, session_id: Optional[str] = None):
        """Initialize editor session with optional existing session ID"""
        self.session_id = session_id or self._create_session_id()
        self.sessions_dir = os.path.join(os.getcwd(), "sessions")
        self.editor_dir = os.path.join(os.getcwd(), "editor_dir")
        self.client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.messages = []

        # Create both directories
        os.makedirs(self.sessions_dir, exist_ok=True)
        os.makedirs(self.editor_dir, exist_ok=True)
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Configure logging for the session"""
        log_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        log_file = os.path.join(self.sessions_dir, f"{self.session_id}.log")

        file_handler = RotatingFileHandler(
            log_file, maxBytes=1024 * 1024, backupCount=5
        )
        file_handler.setFormatter(log_formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)

        self.logger = logging.getLogger(self.session_id)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        self.logger.setLevel(logging.DEBUG)

    def _create_session_id(self) -> str:
        """Create a new session ID"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return f"{timestamp}-{uuid.uuid4().hex[:6]}"

    def log_to_session(self, data: Dict[str, Any], section: str) -> None:
        """Log data to session log file"""
        self.logger.info(f"{section}: {data}")

    def _get_editor_path(self, path: str) -> str:
        """Convert API path to local editor directory path"""
        # Strip any leading /repo/ from the path
        clean_path = path.replace("/repo/", "", 1)
        # Join with editor_dir
        full_path = os.path.join(self.editor_dir, clean_path)
        # Create the directory structure if it doesn't exist
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        return full_path

    def handle_text_editor_tool(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Handle text editor tool calls"""
        try:
            command = tool_call["command"]
            if not all(key in tool_call for key in ["command", "path"]):
                return {"error": "Missing required fields"}

            # Get path and ensure directory exists
            path = self._get_editor_path(tool_call["path"])

            handlers = {
                "view": self._handle_view,
                "create": self._handle_create,
                "str_replace": self._handle_str_replace,
                "insert": self._handle_insert,
            }

            handler = handlers.get(command)
            if not handler:
                return {"error": f"Unknown command {command}"}

            return handler(path, tool_call)

        except Exception as e:
            self.logger.error(f"Error in handle_text_editor_tool: {str(e)}")
            return {"error": str(e)}

    def _handle_view(self, path: str, _: Dict[str, Any]) -> Dict[str, Any]:
        """Handle view command"""
        editor_path = self._get_editor_path(path)
        if os.path.exists(editor_path):
            with open(editor_path, "r") as f:
                return {"content": f.read()}
        return {"error": f"File {editor_path} does not exist"}

    def _handle_create(self, path: str, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Handle create command"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(tool_call["file_text"])
        return {"content": f"File created at {path}"}

    def _handle_str_replace(
        self, path: str, tool_call: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle str_replace command"""
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

    def _handle_insert(self, path: str, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Handle insert command"""
        with open(path, "r") as f:
            lines = f.readlines()
        insert_line = tool_call["insert_line"]
        if insert_line > len(lines):
            return {"error": "insert_line beyond file length"}
        lines.insert(insert_line, tool_call["new_str"] + "\n")
        with open(path, "w") as f:
            f.writelines(lines)
        return {"content": "Content inserted successfully"}

    def process_tool_calls(
        self, tool_calls: List[anthropic.types.ContentBlock]
    ) -> List[Dict[str, Any]]:
        """Process tool calls and return results"""
        results = []

        for tool_call in tool_calls:
            if tool_call.type == "tool_use" and tool_call.name == "str_replace_editor":

                # Log the keys and first 20 characters of the values of the tool_call
                for key, value in tool_call.input.items():
                    truncated_value = str(value)[:20] + (
                        "..." if len(str(value)) > 20 else ""
                    )
                    self.logger.info(
                        f"Tool call key: {key}, Value (truncated): {truncated_value}"
                    )

                result = self.handle_text_editor_tool(tool_call.input)
                # Convert result to match expected tool result format
                tool_result_content = []
                is_error = False

                if result.get("error"):
                    is_error = True
                    tool_result_content = result["error"]
                else:
                    tool_result_content = [
                        {"type": "text", "text": result.get("content", "")}
                    ]

                results.append(
                    {
                        "tool_call_id": tool_call.id,
                        "output": {
                            "type": "tool_result",
                            "content": tool_result_content,
                            "tool_use_id": tool_call.id,
                            "is_error": is_error,
                        },
                    }
                )

        return results

    def process_edit(self, edit_prompt: str) -> None:
        """Main method to process editing prompts"""
        try:
            # Initial message with proper content structure
            api_message = {
                "role": "user",
                "content": [{"type": "text", "text": edit_prompt}],
            }
            self.messages = [api_message]

            self.logger.info(f"User input: {api_message}")

            while True:
                response = self.client.beta.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4096,
                    messages=self.messages,
                    tools=[
                        {"type": "text_editor_20241022", "name": "str_replace_editor"}
                    ],
                    betas=["computer-use-2024-10-22"],
                )

                self.logger.info(f"API response: {response.model_dump()}")

                # Convert response content to message params
                response_content = []
                for block in response.content:
                    if block.type == "text":
                        response_content.append({"type": "text", "text": block.text})
                    else:
                        response_content.append(block.model_dump())

                # Add assistant response to messages
                self.messages.append({"role": "assistant", "content": response_content})

                if response.stop_reason != "tool_use":
                    print(response.content[0].text)
                    break

                tool_results = self.process_tool_calls(response.content)

                # Add tool results as user message
                if tool_results:
                    self.messages.append(
                        {"role": "user", "content": [tool_results[0]["output"]]}
                    )

                    if tool_results[0]["output"]["is_error"]:
                        self.logger.error(
                            f"Error: {tool_results[0]['output']['content']}"
                        )
                        break

        except Exception as e:
            self.logger.error(f"Error in process_edit: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser()
    parser.add_argument("edit_prompt", help="The editing prompt for Claude")
    args = parser.parse_args()

    session = EditorSession()
    print(f"Session ID: {session.session_id}")
    session.process_edit(args.edit_prompt)


if __name__ == "__main__":
    main()
