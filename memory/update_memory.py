import sys
import os

def update_memory_store(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()

    # Step 1: Fix the MISSION enum in MemoryScope
    # We'll look for the line that contains 'PRIVATE = "private"`n    MISSION = "mission"'
    # and replace it with two lines.
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if 'PRIVATE = "private"`n    MISSION = "mission"' in line:
            # Replace this line with two lines
            new_lines.append('    PRIVATE = "private"\n')
            new_lines.append('    MISSION = "mission"\n')
            i += 1
        else:
            new_lines.append(line)
            i += 1

    lines = new_lines

    # Step 2: Insert MemoryStatus enum before the MemoryEntry class
    # Find the line with '@dataclass' that is followed by 'class MemoryEntry:'
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == '@dataclass' and i+1 < len(lines) and lines[i+1].strip() == 'class MemoryEntry:':
            # Insert the MemoryStatus enum before this line
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

    # Step 3: Replace the MemoryEntry class
    # We'll find the '@dataclass' line for MemoryEntry and then replace everything until the next class or function.
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == '@dataclass' and i+1 < len(lines) and lines[i+1].strip().startswith('class MemoryEntry:'):
            # Skip the existing MemoryEntry class
            # We'll skip until we find a line that is not indented (or empty) and not part of the class.
            # First, skip the '@dataclass' and 'class MemoryEntry:' lines.
            i += 2  # now at the first line of the class body

            # Now skip the class body until we find a line that is not indented (i.e., starts with non-whitespace) and is not empty, but we have to be careful with empty lines in the class.
            # We'll skip empty lines and then check if the next non-empty line is indented.
            while i < len(lines):
                # Skip empty lines
                if lines[i].strip() == '':
                    i += 1
                    continue
                # If the line is not indented, we are out of the class.
                if len(lines[i]) - len(lines[i].lstrip()) == 0:
                    break
                # Otherwise, we are still in the class body.
                i += 1

            # Now we are at the line after the class body (or at the end of the file).
            # We will insert the new MemoryEntry class here.
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
            # Now we do not increment i here because we have already skipped the old class.
            # We will continue to add the rest of the lines from the original file.
            continue
        new_lines.append(line)
        i += 1

    # Write the updated content back to the file
    with open(filepath, 'w') as f:
        f.writelines(new_lines)

    print(f"Updated {filepath}")

if __name__ == '__main__':
    memory_store_path = r'D:\hermes-agent-main\aetheros\memory\memory_store.py'
    update_memory_store(memory_store_path)
