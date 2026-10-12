import sys
import os

def update_init_sqlite(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()

    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith('def _init_sqlite(self) -> None:'):
            # We found the _init_sqlite method signature.
            # We will replace the entire method from this line until the line that is not indented more than the method.
            # First, we will capture the signature line and then we will skip the entire method body.
            # We will then insert our new _init_sqlite method.

            # Get the indent of the signature line.
            indent = len(line) - len(line.lstrip())
            # We will skip the signature line and then any line that is indented more than the method.
            # We will skip until we find a line that is not indented more than the method.
            i += 1  # skip the signature line
            while i < len(lines):
                if len(lines[i]) - len(lines[i].lstrip()) <= indent:
                    # We are at a line that is not indented more than the method.
                    break
                i += 1
            # Now i is at the line that is not indented more than the method (i.e., the line after the method).
            # We will not add the skipped lines to new_lines.
            # We will now add our new _init_sqlite method to new_lines.

            # Build the new _init_sqlite method.
            new_method_lines = []
            new_method_lines.append('    def _init_sqlite(self) -> None:\n')
            new_method_lines.append('        """Initialize SQLite backend."""\n')
            new_method_lines.append('        try:\n')
            new_method_lines.append('            import sqlite3\n')
            new_method_lines.append('            self._sqlite_conn = sqlite3.connect(self._db_path, check_same_thread=False)\n')
            new_method_lines.append('            self._sqlite_conn.execute("""\n')
            new_method_lines.append('                CREATE TABLE IF NOT EXISTS memory_entries (\n')
            new_method_lines.append('                    id TEXT PRIMARY KEY,\n')
            new_method_lines.append('                    key TEXT NOT NULL,\n')
            new_method_lines.append('                    value TEXT NOT NULL,\n')
            new_method_lines.append('                    memory_type TEXT DEFAULT \\'general\\',\n')
            new_method_lines.append('                    scope TEXT DEFAULT \\'global\\',\n')
            new_method_lines.append('                    namespace TEXT DEFAULT \\'\\',\n')
            new_method_lines.append('                    tags TEXT DEFAULT \\'[]\\',\n')
            new_method_lines.append('                    metadata TEXT DEFAULT \\'{}\\',\n')
            new_method_lines.append('                    importance REAL DEFAULT 0.5,\n')
            new_method_lines.append('                    created_at REAL NOT NULL,\n')
            new_method_lines.append('                    updated_at REAL NOT NULL,\n')
            new_method_lines.append('                    expires_at REAL,\n')
            new_method_lines.append('                    source TEXT,  -- origin of the memory\n')
            new_method_lines.append('                    summary TEXT,\n')
            new_method_lines.append('                    source_type TEXT,\n')
            new_method_lines.append('                    source_id TEXT,\n')
            new_method_lines.append('                    owner_id TEXT,\n')
            new_method_lines.append('                    agent_id TEXT,\n')
            new_method_lines.append('                    session_id TEXT,\n')
            new_method_lines.append('                    project_id TEXT,\n')
            new_method_lines.append('                    mission_id TEXT,\n')
            new_method_lines.append('                    task_id TEXT,\n')
            new_method_lines.append('                    sensitivity REAL,\n')
            new_method_lines.append('                    embedding_id TEXT,\n')
            new_method_lines.append('                    status TEXT DEFAULT \\'active\\',\n')
            new_method_lines.append('                    provenance_source TEXT DEFAULT \\'system\\'\n')
            new_method_lines.append('                )\n')
            new_method_lines.append('            """)\n')
            new_method_lines.append('            self._sqlite_conn.commit()\n')
            new_method_lines.append('            logger.info("MemoryStore: initialized SQLite at %s", self._db_path)\n')
            new_method_lines.append('        except Exception as exc:\n')
            new_method_lines.append('            logger.warning("MemoryStore: SQLite init failed: %s", exc)\n')
            new_method_lines.append('            self._sqlite_conn = None\n')

            new_lines.extend(new_method_lines)
            # We have already advanced i to the line after the method.
            # We will continue the loop and add the line at i (which is the line after the method) in the next iteration.
            continue
        new_lines.append(line)
        i += 1

    # Write the updated content back to the file
    with open(filepath, 'w') as f:
        f.writelines(new_lines)

    print(f"Updated _init_sqlite method in {filepath}")

if __name__ == '__main__':
    memory_store_path = r'D:\\hermes-agent-main\\aetheros\\memory\\memory_store.py'
    update_init_sqlite(memory_store_path)
