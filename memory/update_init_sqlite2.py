import sys
import os

def update_init_sqlite(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()

    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if 'def _init_sqlite(self) -> None:' in line:
            # We found the _init_sqlite method signature.
            # We will skip the signature line and then look for the line that starts the execute call.
            new_lines.append(line)
            i += 1
            # We will add the lines until we find the execute call.
            while i < len(lines):
                current_line = lines[i]
                new_lines.append(current_line)
                if 'self._sqlite_conn.execute(' in current_line:
                    # We have found the execute call. Now we will replace the SQL string and the parameters.
                    # We will skip the lines until we find the closing parenthesis of the execute call.
                    # We will build the new execute call.
                    # We will add the new SQL string and then the parameters.
                    # We will skip the old lines until we find the closing parenthesis.
                    # We will then add the new execute call.
                    # We will break out of the inner loop and continue.
                    # We will build the new execute call lines.
                    new_sql_lines = [
                        '            self._sqlite_conn.execute("""\n',
                        '                CREATE TABLE IF NOT EXISTS memory_entries (\n',
                        '                    id TEXT PRIMARY KEY,\n',
                        '                    key TEXT NOT NULL,\n',
                        '                    value TEXT NOT NULL,\n',
                        '                    memory_type TEXT DEFAULT \\'general\\',\n',
                        '                    scope TEXT DEFAULT \\'global\\',\n',
                        '                    namespace TEXT DEFAULT \\'\\',\n',
                        '                    tags TEXT DEFAULT \\'[]\\',\n',
                        '                    metadata TEXT DEFAULT \\'{}\\',\n',
                        '                    importance REAL DEFAULT 0.5,\n',
                        '                    created_at REAL NOT NULL,\n',
                        '                    updated_at REAL NOT NULL,\n',
                        '                    expires_at REAL,\n',
                        '                    source TEXT,  -- origin of the memory\n',
                        '                    summary TEXT,\n',
                        '                    source_type TEXT,\n',
                        '                    source_id TEXT,\n',
                        '                    owner_id TEXT,\n',
                        '                    agent_id TEXT,\n',
                        '                    session_id TEXT,\n',
                        '                    project_id TEXT,\n',
                        '                    mission_id TEXT,\n',
                        '                    task_id TEXT,\n',
                        '                    sensitivity REAL,\n',
                        '                    embedding_id TEXT,\n',
                        '                    status TEXT DEFAULT \\'active\\',\n',
                        '                    provenance_source TEXT DEFAULT \\'system\\'\n',
                        '                )\n',
                        '            """)\n',
                    ]
                    # We will skip the old lines until we find the closing parenthesis of the execute call.
                    # We assume the old execute call ends with a line that contains ');' (the end of the parameters and the closing of the execute call).
                    # We will skip lines until we find a line that contains '');' (the closing of the execute call).
                    # We will then add the new SQL lines.
                    # We will skip the old lines.
                    while i < len(lines):
                        if ');' in lines[i]:
                            i += 1  # skip the line with '");'
                            break
                        i += 1
                    # Now we are at the line after the old execute call.
                    # We will add the new SQL lines.
                    new_lines.extend(new_sql_lines)
                    # We will not add the old lines that we skipped.
                    # We will continue to add the rest of the lines.
                    continue
                i += 1
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
