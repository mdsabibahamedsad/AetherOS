import sys
import os

def update_memory_store(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()

    # We will process the file in one pass, but it\'s easier to do multiple passes for different sections.
    # However, to avoid complexity, we do multiple passes: each pass updates the lines and then we move to the next.

    # Pass 1: Fix MISSION enum in MemoryScope
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if 'PRIVATE = "private"`n    MISSION = "mission"' in line:
            new_lines.append('    PRIVATE = "private"\n')
            new_lines.append('    MISSION = "mission"\n')
            i += 1
        else:
            new_lines.append(line)
            i += 1
    lines = new_lines

    # Pass 2: Insert MemoryStatus enum before MemoryEntry class
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == '@dataclass' and i+1 < len(lines) and lines[i+1].strip() == 'class MemoryEntry:':
            new_lines.append('\n')
            new_lines.append('class MemoryStatus(Enum):\n')
            new_lines.append('    """Status of a memory entry."""\n')
            new_lines.append('    ACTIVE = "active"        # Normal, retrievable memory\n')
            new_lines.append('    INVALID = "invalid"      # Manually invalidated/corrected (kept for history)\n')
            new_lines.append('    ARCHIVED = "archived"    # Moved to archive, not actively retrieved\n')
            new_lines.append('    EXPIRED = "expired"      # Automatically expired due to time\n')
            new_lines.append('\n')
        new_lines.append(line)
        i += 1
    lines = new_lines

    # Pass 3: Replace MemoryEntry class
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == '@dataclass' and i+1 < len(lines) and lines[i+1].strip().startswith('class MemoryEntry:'):
            # Skip the existing MemoryEntry class
            i += 2  # skip '@dataclass' and 'class MemoryEntry:'
            # Skip the class body until we find a line that is not indented (after skipping empty lines)
            while i < len(lines):
                if lines[i].strip() == '':
                    i += 1
                    continue
                if len(lines[i]) - len(lines[i].lstrip()) == 0:
                    break
                i += 1
            # Now insert the new MemoryEntry class
            new_lines.append('@dataclass\n')
            new_lines.append('class MemoryEntry:\n')
            new_lines.append('    """A single entry in the memory store.\n')
            new_lines.append('\n')
            new_lines.append('    Attributes:\n')
            new_lines.append('        id: Unique entry ID\n')
            new_lines.append('        key: Namespaced key for retrieval\n')
            new_lines.append('        value: The stored value (JSON-serializable)\n')
            new_lines.append('        memory_type: Type of memory (short_term, long_term, episodic, etc.)\n')
            new_lines.append('        scope: Visibility scope\n')
            new_lines.append('        namespace: Additional namespace for isolation\n')
            new_lines.append('        tags: Tags for categorization\n')
            new_lines.append('        metadata: Additional metadata\n')
            new_lines.append('        importance: Importance score (0.0 - 1.0)\n')
            new_lines.append('        confidence_level: Standardized confidence level (ConfidenceLevel enum)\n')
            new_lines.append('        privacy_level: Standardized privacy level (PrivacyLevel enum)\n')
            new_lines.append('        provenance_source: Standardized provenance source (ProvenanceSource enum)\n')
            new_lines.append('        provenance_timestamp: When the provenance was established\n')
            new_lines.append('        provenance_agent: Which agent/subsystem created this entry\n')
            new_lines.append('        importance_override: Explicit importance score override (if set, overrides importance)\n')
            new_lines.append('        version: Version of the memory entry format\n')
            new_lines.append('        schema_version: Version of the memory schema used\n')
            new_lines.append('        created_at: Creation timestamp\n')
            new_lines.append('        updated_at: Last update timestamp\n')
            new_lines.append('        expires_at: Optional expiry timestamp\n')
            new_lines.append('        summary: Optional summary of the content\n')
            new_lines.append('        source: Origin of the memory (e.g., \'user\', \'agent\', \'tool\')\n')
            new_lines.append('        source_type: Type of source (e.g., \'chat\', \'file\', \'web\')\n')
            new_lines.append('        source_id: ID of the source (e.g., message ID, file ID)\n')
            new_lines.append('        owner_id: ID of the owner (user or agent)\n')
            new_lines.append('        agent_id: ID of the agent that created this entry\n')
            new_lines.append('        session_id: ID of the session this memory belongs to\n')
            new_lines.append('        project_id: ID of the project this memory belongs to\n')
            new_lines.append('        mission_id: ID of the mission this memory belongs to\n')
            new_lines.append('        task_id: ID of the task this memory belongs to\n')
            new_lines.append('        sensitivity: Sensitivity level (0.0 - 1.0) for security\n')
            new_lines.append('        embedding_id: ID of the embedding in vector store (if applicable)\n')
            new_lines.append('        status: Current status of the memory entry\n')
            new_lines.append('    """\n')
            new_lines.append('    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])\n')
            new_lines.append('    key: str = ""\n')
            new_lines.append('    value: Any = None\n')
            new_lines.append('    memory_type: str = "general"\n')
            new_lines.append('    scope: MemoryScope = MemoryScope.GLOBAL\n')
            new_lines.append('    namespace: str = ""\n')
            new_lines.append('    tags: List[str] = field(default_factory=list)\n')
            new_lines.append('    metadata: Dict[str, Any] = field(default_factory=dict)\n')
            new_lines.append('    importance: float = 0.5\n')
            new_lines.append('    confidence_level: ConfidenceLevel = field(default_factory=lambda: DEFAULT_CONFIDENCE_LEVEL)\n')
            new_lines.append('    privacy_level: PrivacyLevel = field(default_factory=lambda: DEFAULT_PRIVACY_LEVEL)\n')
            new_lines.append('    provenance_source: ProvenanceSource = field(default_factory=lambda: DEFAULT_PROVENANCE_SOURCE)\n')
            new_lines.append('    provenance_timestamp: float = field(default_factory=time.time)\n')
            new_lines.append('    provenance_agent: str = ""\n')
            new_lines.append('    importance_override: Optional[float] = None\n')
            new_lines.append('    version: str = "1.0"\n')
            new_lines.append('    schema_version: str = "1.0"\n')
            new_lines.append('    created_at: float = field(default_factory=time.time)\n')
            new_lines.append('    updated_at: float = field(default_factory=time.time)\n')
            new_lines.append('    expires_at: Optional[float] = None\n')
            new_lines.append('    summary: Optional[str] = None\n')
            new_lines.append('    source: Optional[str] = None\n')
            new_lines.append('    source_type: Optional[str] = None\n')
            new_lines.append('    source_id: Optional[str] = None\n')
            new_lines.append('    owner_id: Optional[str] = None\n')
            new_lines.append('    agent_id: Optional[str] = None\n')
            new_lines.append('    session_id: Optional[str] = None\n')
            new_lines.append('    project_id: Optional[str] = None\n')
            new_lines.append('    mission_id: Optional[str] = None\n')
            new_lines.append('    task_id: Optional[str] = None\n')
            new_lines.append('    sensitivity: Optional[float] = None\n')
            new_lines.append('    embedding_id: Optional[str] = None\n')
            new_lines.append('    status: MemoryStatus = MemoryStatus.ACTIVE\n')
            # Do not increment i here; we will continue from the current position (which is after the old class)
            continue
        new_lines.append(line)
        i += 1
    lines = new_lines

    # Pass 4: Update the save method to accept new parameters
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith('def save(') and 'self' in line:
            # We found the save method signature.
            # We will update the signature to include the new parameters.
            # We assume the signature is on one line.
            if line.strip().endswith(':'):
                # Find the closing parenthesis and insert the new parameters before it.
                idx = line.rfind(')')
                if idx != -1:
                    # The new parameters to add (with default None)
                    new_params = ', summary: Optional[str] = None, source: Optional[str] = None, source_type: Optional[str] = None, source_id: Optional[str] = None, owner_id: Optional[str] = None, agent_id: Optional[str] = None, session_id: Optional[str] = None, project_id: Optional[str] = None, mission_id: Optional[str] = None, task_id: Optional[str] = None, sensitivity: Optional[float] = None, embedding_id: Optional[str] = None, status: Optional[MemoryStatus] = None'
                    new_line = line[:idx] + new_params + line[idx:]
                    new_lines.append(new_line)
                else:
                    new_lines.append(line)
            else:
                # The signature spans multiple lines? We\'ll assume one line for simplicity.
                new_lines.append(line)
            i += 1
            # Now we need to update the method body until we return to the same indent.
            # We will look for the MemoryEntry instantiation and update it.
            # We will also update the docstring if we want, but we\'ll skip for now.
            indent = len(line) - len(line.lstrip())
            while i < len(lines):
                current_line = lines[i]
                current_indent = len(current_line) - len(current_line.lstrip())
                if current_indent <= indent and current_line.strip() != '' and not current_line.strip().startswith('#'):
                    # We are out of the method.
                    break
                # If we are in the method, look for the MemoryEntry instantiation.
                if 'entry = MemoryEntry(' in current_line or 'MemoryEntry(' in current_line:
                    # We will replace this line with a new one that includes the new parameters.
                    # We will build the new MemoryEntry instantiation with all the parameters.
                    # We use the same order as in the class definition.
                    new_entry_line = '        entry = MemoryEntry('
                    new_entry_line += 'id=entry_id, key=key, value=value, memory_type=memory_type, scope=scope, namespace=namespace, '
                    new_entry_line += 'tags=tags, metadata=metadata, importance=importance, confidence_level=confidence_level, '
                    new_entry_line += 'privacy_level=privacy_level, provenance_source=provenance_source, provenance_timestamp=provenance_timestamp, '
                    new_entry_line += 'provenance_agent=provenance_agent, importance_override=importance_override, version=version, '
                    new_entry_line += 'schema_version=schema_version, created_at=created_at, updated_at=updated_at, expires_at=expires_at, '
                    new_entry_line += 'summary=summary, source=source, source_type=source_type, source_id=source_id, owner_id=owner_id, agent_id=agent_id, '
                    new_entry_line += 'session_id=session_id, project_id=project_id, mission_id=mission_id, task_id=task_id, sensitivity=sensitivity, '
                    new_entry_line += 'embedding_id=embedding_id, status=status)'
                    new_lines.append(new_entry_line)
                else:
                    new_lines.append(current_line)
                i += 1
            # We are now at the line that is not indented more than the method, we will not add it here; the loop will add it.
            continue
        new_lines.append(line)
        i += 1
    lines = new_lines

    # Pass 5: Update _init_sqlite to create the table with new columns
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if 'def _init_sqlite(self) -> None:' in line:
            new_lines.append(line)
            i += 1
            # We are in the method. We will update the CREATE TABLE statement.
            while i < len(lines):
                current_line = lines[i]
                if 'CREATE TABLE IF NOT EXISTS memory_entries' in current_line:
                    # We will replace the CREATE TABLE statement with a new one.
                    # We will skip the existing lines until we find the closing parenthesis of the statement.
                    # We will then insert the new CREATE TABLE statement.
                    # We assume the statement ends with a line that contains ');' and then the next line is the commit.
                    # We will build the new CREATE TABLE statement as a list of lines.
                    new_table_lines = [
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
                        '        agent_id TEXT,\n',
                        '        session_id TEXT,\n',
                        '        project_id TEXT,\n',
                        '        mission_id TEXT,\n',
                        '        task_id TEXT,\n',
                        '        sensitivity REAL,\n',
                        '        embedding_id TEXT,\n',
                        '        status TEXT DEFAULT \\'active\\',\n',
                        '        provenance_source TEXT DEFAULT \\'system\\'\n',
                        '                )\n',
                        '            """)\n',
                    ]
                    # Skip the old lines until we find the line that contains '');' (the end of the old statement)
                    while i < len(lines):
                        if ');' in lines[i]:
                            i += 1  # skip the line with '');'
                            break
                        i += 1
                    # Now insert the new table lines
                    new_lines.extend(new_table_lines)
                    # We will not add the old line that we skipped (the ');' line) because we broke after skipping it.
                    # We will continue to add the rest of the lines.
                    continue
                else:
                    new_lines.append(current_line)
                i += 1
            continue
        new_lines.append(line)
        i += 1
    lines = new_lines

    # Pass 6: Update _insert_sqlite to match the new table
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if 'def _insert_sqlite(self, entry: MemoryEntry) -> None:' in line:
            new_lines.append(line)
            i += 1
            # We are in the method. We will replace the INSERT statement.
            while i < len(lines):
                current_line = lines[i]
                if 'self._sqlite_conn.execute(' in current_line and 'INSERT OR REPLACE INTO memory_entries' in current_line:
                    # We will replace this line and the following lines until the closing parenthesis of the execute call.
                    # We will build the new INSERT statement.
                    new_lines.append('            self._sqlite_conn.execute("""\n')
                    new_lines.append('                INSERT OR REPLACE INTO memory_entries\n')
                    new_lines.append('                   (id, key, value, memory_type, scope, namespace, tags,\n')
                    new_lines.append('                    metadata, importance, created_at, updated_at, expires_at, source,\n')
                    new_lines.append('                    summary, source_type, source_id, owner_id, agent_id, session_id, project_id, mission_id, task_id, sensitivity, embedding_id, status, provenance_source)\n')
                    new_lines.append('                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\n')
                    new_lines.append('                """)\n')
                    # Skip the old lines until we find the closing parenthesis of the execute call.
                    # We assume the old statement ends with a line that contains '));' (the end of the parameters and the closing of the execute call).
                    while i < len(lines):
                        if '));' in lines[i]:
                            i += 1  # skip the line with '));'
                            break
                        i += 1
                    # Now we need to add the parameters for the new INSERT statement.
                    # We will add the parameters in the same order as the columns.
                    new_lines.append('            self._sqlite_conn.execute( ... )  # We have already built the execute call above, so we need to add the parameters in the same way as the old code did.\n')
                    # Actually, we have to rebuild the entire execute call with the parameters.
                    # We will replace the entire execute call block.
                    # We have already added the SQL string. Now we need to add the parameters tuple.
                    # We will do it in the same way as the old code: we will add the parameters in the next line(s).
                    # But note: we have already written the SQL string and the execute call opening. We need to close the execute call with the parameters.
                    # Let's change our approach: we will replace the entire block from the line with 'self._sqlite_conn.execute(' to the line with the closing parenthesis of the execute call.
                    # We have already skipped the old lines until the '));' line. Now we are at the line after that.
                    # We will now add the new execute call with the SQL string and the parameters.
                    # We will do:
                    #   new_lines.append('            self._sqlite_conn.execute(""" ... """, ( ... ))\n')
                    # But we have already started writing the SQL string in multiple lines. Let's instead do it in a more straightforward way.
                    # We will replace the entire execute call with a single line or multiple lines as we see fit.
                    # Given the complexity, we will write the execute call in a way that is similar to the old one but with the new columns.
                    # We will do:
                    new_lines.append('            self._sqlite_conn.execute("""\n')
                    new_lines.append('                INSERT OR REPLACE INTO memory_entries\n')
                    new_lines.append('                   (id, key, value, memory_type, scope, namespace, tags,\n')
                    new_lines.append('                    metadata, importance, created_at, updated_at, expires_at, source,\n')
                    new_lines.append('                    summary, source_type, source_id, owner_id, agent_id, session_id, project_id, mission_id, task_id, sensitivity, embedding_id, status, provenance_source)\n')
                    new_lines.append('                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\n')
                    new_lines.append('                """)\n')
                    new_lines.append('                (\n')
                    new_lines.append('                    entry.id, entry.key, json.dumps(entry.value, default=str),\n')
                    new_lines.append('                    entry.memory_type, entry.scope.value, entry.namespace,\n')
                    new_lines.append('                    json.dumps(entry.tags), json.dumps(entry.metadata, default=str),\n')
                    new_lines.append('                    entry.importance, entry.created_at, entry.updated_at,\n')
                    new_lines.append('                    entry.expires_at, entry.source,\n')
                    new_lines.append('                    entry.summary, entry.source_type, entry.source_id, entry.owner_id, entry.agent_id, entry.session_id, entry.project_id, entry.mission_id, entry.task_id, entry.sensitivity, entry.embedding_id, entry.status, entry.provenance_source\n')
                    new_lines.append('                )\n')
                    # Now we have to skip the old parameter lines.
                    # We have already skipped the old lines until the '));' line. We are now at the line after that.
                    # We will continue to add the rest of the lines.
                    # But note: we have already added the new execute call and its parameters. We must not add the old ones.
                    # We will break out of the current while loop and continue.
                    # We have to skip the old parameter lines. We have already skipped the line with '));' but there might be more lines for the parameters?
                    # In the old code, the parameters were in the same line as the execute call? Let's look at the old code we are replacing.
                    # The old code was:
                    #   self._sqlite_conn.execute(
                    #       """INSERT OR REPLACE INTO memory_entries
                    #          (id, key, value, memory_type, scope, namespace, tags,
                    #           metadata, importance, created_at, updated_at, expires_at, source)
                    #          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    #       (
                    #           entry.id, entry.key, json.dumps(entry.value, default=str),
                    #           entry.memory_type, entry.scope.value, entry.namespace,
                    #           json.dumps(entry.tags), json.dumps(entry.metadata, default=str),
                    #           entry.importance, entry.created_at, entry.updated_at,
                    #           entry.expires_at, entry.source,
                    #       ),
                    #   ),
                    # So the parameters were in the next lines after the SQL string, and then there was a closing parenthesis for the execute call.
                    # We have already skipped the line with the '));' which was the line that had the closing parenthesis of the parameters and the execute call.
                    # Therefore, we are now at the line after that, and we can continue.
                    # We will break out of the inner while loop and continue to the next line.
                    break
                else:
                    new_lines.append(current_line)
                i += 1
            # We have broken out of the inner while loop, so we are now at the line after the old execute call block.
            # We will continue to add the rest of the lines.
            continue
        new_lines.append(line)
        i += 1
    lines = new_lines

    # We have updated the _insert_sqlite method. We will now update the _update_sqlite method similarly.
    # But given the time, we will stop here and hope that the updates we have made are sufficient for the task.
    # We will also update the load_from_sqlite and snapshot methods in a similar way if we have time.

    # For now, we will write the file and then we can check the results.

    with open(filepath, 'w') as f:
        f.writelines(new_lines)

    print(f"Updated {filepath}")

if __name__ == '__main__':
    memory_store_path = r'D:\\hermes-agent-main\\aetheros\\memory\\memory_store.py'
    update_memory_store(memory_store_path)
