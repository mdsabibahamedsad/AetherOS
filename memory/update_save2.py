import sys
import os

def update_save_method(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()

    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith('def save(') and 'self' in line and 'key: str' in line:
            # We found the save method signature.
            # We will replace the entire method from this line until the line that is not indented more than the method.
            # First, we will capture the signature line and then we will skip the entire method body.
            # We will then insert our new save method.

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
            # We will now add our new save method to new_lines.

            # Build the new save method.
            new_method_lines = []
            # Signature
            new_method_lines.append('    def save(self, key: str, value: Any,\n')
            new_method_lines.append('             memory_type: str = "general",\n')
            new_method_lines.append('             scope: MemoryScope = MemoryScope.GLOBAL,\n')
            new_method_lines.append('             namespace: str = "",\n')
            new_method_lines.append('             tags: List[str] = None,\n')
            new_method_lines.append('             metadata: Dict[str, Any] = None,\n')
            new_method_lines.append('             importance: float = 0.5,\n')
            new_method_lines.append('             ttl: Optional[float] = None,\n')
            new_method_lines.append('             confidence_level: ConfidenceLevel = None,\n')
            new_method_lines.append('             privacy_level: PrivacyLevel = None,\n')
            new_method_lines.append('             provenance_source: ProvenanceSource = None,\n')
            new_method_lines.append('             provenance_agent: str = "",\n')
            new_method_lines.append('             importance_override: Optional[float] = None,\n')
            new_method_lines.append('             entry_id: str = None,\n')
            new_method_lines.append('             summary: Optional[str] = None,\n')
            new_method_lines.append('             source: Optional[str] = None,\n')
            new_method_lines.append('             source_type: Optional[str] = None,\n')
            new_method_lines.append('             source_id: Optional[str] = None,\n')
            new_method_lines.append('             owner_id: Optional[str] = None,\n')
            new_method_lines.append('             agent_id: Optional[str] = None,\n')
            new_method_lines.append('             session_id: Optional[str] = None,\n')
            new_method_lines.append('             project_id: Optional[str] = None,\n')
            new_method_lines.append('             mission_id: Optional[str] = None,\n')
            new_method_lines.append('             task_id: Optional[str] = None,\n')
            new_method_lines.append('             sensitivity: Optional[float] = None,\n')
            new_method_lines.append('             embedding_id: Optional[str] = None,\n')
            new_method_lines.append('             status: Optional[MemoryStatus] = None) -> MemoryEntry:\n')
            # Docstring
            new_method_lines.append('        """Save a memory entry.\n')
            new_method_lines.append('\n')
            new_method_lines.append('        If an entry with the same key, scope, and namespace already exists,\n')
            new_method_lines.append('        it will be updated. Otherwise a new entry is created.\n')
            new_method_lines.append('        """\n')
            # Create the entry with all fields
            new_method_lines.append('        entry = MemoryEntry(\n')
            new_method_lines.append('            id=entry_id or uuid.uuid4().hex[:16],\n')
            new_method_lines.append('            key=key,\n')
            new_method_lines.append('            value=value,\n')
            new_method_lines.append('            memory_type=memory_type,\n')
            new_method_lines.append('            scope=scope,\n')
            new_method_lines.append('            namespace=namespace,\n')
            new_method_lines.append('            tags=tags or [],\n')
            new_method_lines.append('            metadata=metadata or {},\n')
            new_method_lines.append('            importance=importance,\n')
            new_method_lines.append('            confidence_level=confidence_level or DEFAULT_CONFIDENCE_LEVEL,\n')
            new_method_lines.append('            privacy_level=privacy_level or DEFAULT_PRIVACY_LEVEL,\n')
            new_method_lines.append('            provenance_source=provenance_source or DEFAULT_PROVENANCE_SOURCE,\n')
            new_method_lines.append('            provenance_timestamp=time.time(),\n')
            new_method_lines.append('            provenance_agent=provenance_agent,\n')
            new_method_lines.append('            importance_override=importance_override,\n')
            new_method_lines.append('            version="1.0",\n')
            new_method_lines.append('            schema_version="1.0",\n')
            new_method_lines.append('            created_at=time.time(),\n')
            new_method_lines.append('            updated_at=time.time(),\n')
            new_method_lines.append('            expires_at=(time.time() + ttl) if ttl else None,\n')
            new_method_lines.append('            summary=summary,\n')
            new_method_lines.append('            source=source,\n')
            new_method_lines.append('            source_type=source_type,\n')
            new_method_lines.append('            source_id=source_id,\n')
            new_method_lines.append('            owner_id=owner_id,\n')
            new_method_lines.append('            agent_id=agent_id,\n')
            new_method_lines.append('            session_id=session_id,\n')
            new_method_lines.append('            project_id=project_id,\n')
            new_method_lines.append('            mission_id=mission_id,\n')
            new_method_lines.append('            task_id=task_id,\n')
            new_method_lines.append('            sensitivity=sensitivity,\n')
            new_method_lines.append('            embedding_id=embedding_id,\n')
            new_method_lines.append('            status=status or MemoryStatus.ACTIVE,\n')
            new_method_lines.append('        )\n')
            # Now the rest of the method: check for existing entry and save or update.
            new_method_lines.append('        with self._lock:\n')
            new_method_lines.append('            # Check for existing entry with same key + scope + namespace\n')
            new_method_lines.append('            existing_id = self._find_by_key_scope(key, scope, namespace)\n')
            new_method_lines.append('            if existing_id:\n')
            new_method_lines.append('                # Update existing entry\n')
            new_method_lines.append('                existing_entry = self._entries[existing_id]\n')
            new_method_lines.append('                # Update fields that are allowed to be updated\n')
            new_method_lines.append('                existing_entry.value = value\n')
            new_method_lines.append('                existing_entry.memory_type = memory_type\n')
            new_method_lines.append('                existing_entry.scope = scope\n')
            new_method_lines.append('                existing_entry.namespace = namespace\n')
            new_method_lines.append('                existing_entry.tags = tags or []\n')
            new_method_lines.append('                existing_entry.metadata = metadata or {}\n')
            new_method_lines.append('                existing_entry.importance = importance\n')
            new_method_lines.append('                existing_entry.confidence_level = confidence_level or DEFAULT_CONFIDENCE_LEVEL\n')
            new_method_lines.append('                existing_entry.privacy_level = privacy_level or DEFAULT_PRIVACY_LEVEL\n')
            new_method_lines.append('                existing_entry.provenance_source = provenance_source or DEFAULT_PROVENANCE_SOURCE\n')
            new_method_lines.append('                existing_entry.provenance_timestamp = time.time()\n')
            new_method_lines.append('                existing_entry.provenance_agent = provenance_agent\n')
            new_method_lines.append('                existing_entry.importance_override = importance_override\n')
            new_method_lines.append('                existing_entry.version = "1.0"\n')
            new_method_lines.append('                existing_entry.schema_version = "1.0"\n')
            new_method_lines.append('                existing_entry.updated_at = time.time()\n')
            new_method_lines.append('                # Note: id, key, created_at, etc. are not changed\n')
            new_method_lines.append('                entry = existing_entry\n')
            new_method_lines.append('            else:\n')
            new_method_lines.append('                # New entry: set creation time\n')
            new_method_lines.append('                entry.created_at = time.time()\n')
            new_method_lines.append('                entry.updated_at = time.time()\n')
            new_method_lines.append('                # Save to memory and indexes\n')
            new_method_lines.append('                self._entries[entry.id] = entry\n')
            new_method_lines.append('                self._add_to_indexes(entry)\n')
            new_method_lines.append('            # Save to SQLite if enabled\n')
            new_method_lines.append('            if self._sqlite_conn:\n')
            new_method_lines.append('                self._insert_sqlite(entry)\n')
            new_method_lines.append('        return entry\n')

            new_lines.extend(new_method_lines)
            # We have already advanced i to the line after the method.
            # We will continue the loop and add the line at i (which is the line after the method) in the next iteration.
            continue
        new_lines.append(line)
        i += 1

    # Write the updated content back to the file
    with open(filepath, 'w') as f:
        f.writelines(new_lines)

    print(f"Updated save method in {filepath}")

if __name__ == '__main__':
    memory_store_path = r'D:\\hermes-agent-main\\aetheros\\memory\\memory_store.py'
    update_save_method(memory_store_path)
