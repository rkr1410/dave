class ReadFileTool:
    name = "read-file"
    aliases = {"read_file"}

    def __init__(self, workspace):
        self.workspace = workspace

    def schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "Read a UTF-8 text file from a workspace-relative path.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Workspace-relative file path.",
                        },
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
            },
        }

    def run(self, path):
        target = self.workspace.resolve_path(path)
        if not target.exists():
            raise FileNotFoundError(f"path does not exist: {path}")
        if not target.is_file():
            raise IsADirectoryError(f"path is not a file: {path}")

        return {
            "path": str(target.relative_to(self.workspace.root)),
            "content": target.read_text(encoding="utf-8"),
        }
