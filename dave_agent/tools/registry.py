import json
from pathlib import Path

from .list_files import ListFilesTool
from .read_file import ReadFileTool


class Workspace:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def resolve_path(self, path):
        target = Path(path).expanduser()
        if not target.is_absolute():
            target = self.root / target

        resolved = target.resolve()
        if resolved != self.root and self.root not in resolved.parents:
            raise ValueError(f"path is outside workspace: {path}")
        return resolved


class ToolRegistry:
    available_tools = {
        ListFilesTool.name: ListFilesTool,
        ReadFileTool.name: ReadFileTool,
    }

    def __init__(self, workspace_root, tool_names):
        self.workspace = Workspace(workspace_root)
        self.tools = {}
        self.aliases = {}

        for name in tool_names:
            tool_class = self.available_tools[name]
            tool = tool_class(self.workspace)
            self.tools[tool.name] = tool
            self.aliases[tool.name] = tool.name
            for alias in tool.aliases:
                self.aliases[alias] = tool.name

    @classmethod
    def from_spec(cls, workspace_root, spec):
        names = [name.strip() for name in spec.split(",") if name.strip()]
        unknown = [name for name in names if name not in cls.available_tools]
        if unknown:
            raise ValueError(f"unknown tools: {', '.join(unknown)}")
        return cls(workspace_root, names)

    def schemas(self):
        return [tool.schema() for tool in self.tools.values()]

    def run_tool_call(self, tool_call):
        function = tool_call.get("function", {})
        name = function.get("name")
        tool_name = self.aliases.get(name)

        if tool_name is None:
            result = {"error": f"unknown tool: {name}"}
        else:
            try:
                arguments = self.parse_arguments(function.get("arguments") or "{}")
                result = self.tools[tool_name].run(**arguments)
            except Exception as error:
                result = {"error": str(error)}

        return {
            "role": "tool",
            "tool_call_id": tool_call["id"],
            "content": json.dumps(result, ensure_ascii=False),
        }

    def parse_arguments(self, raw_arguments):
        try:
            return json.loads(raw_arguments)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid JSON arguments: {error}") from error
