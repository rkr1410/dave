class ListFilesTool:
    name = "list-files"
    aliases = {"list_files"}

    def __init__(self, workspace):
        self.workspace = workspace

    def schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "List files and directories under a workspace-relative path.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Workspace-relative directory path. Use . for the workspace root.",
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
        if not target.is_dir():
            raise NotADirectoryError(f"path is not a directory: {path}")

        return {
            "path": str(target.relative_to(self.workspace.root)),
            "entries": [
                {
                    "name": child.name,
                    "path": str(child.relative_to(self.workspace.root)),
                    "type": "directory" if child.is_dir() else "file",
                }
                for child in sorted(target.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
            ],
        }
