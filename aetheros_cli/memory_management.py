"""Memory management CLI commands for pending memory writes.

Provides commands to review, approve, reject, and manage pending memory writes
through the write approval system.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_constants import get_aetheros_home
from tools.write_approval import (
    list_pending,
    get_pending,
    discard_pending,
    pending_count,
)
from tools.memory_tool import apply_memory_pending, memory_tool
from tools.registry import tool_error


def handle_memory_management_command(args) -> None:
    """Handle memory management subcommands: pending, approve, reject, approval."""
    sub = getattr(args, "memory_command", None)
    
    if sub == "pending":
        _handle_pending(args)
    elif sub == "approve":
        _handle_approve(args)
    elif sub == "reject":
        _handle_reject(args)
    elif sub == "approval":
        _handle_approval_toggle(args)
    else:
        print("\n  Unknown memory management command. Use: pending, approve, reject, approval\n")


def _handle_pending(args) -> None:
    """List pending memory writes."""
    try:
        pending_list = list_pending("memory")
        
        if not pending_list:
            print("\n  No pending memory writes.\n")
            return
        
        print(f"\n  Pending memory writes ({len(pending_list)}):\n")
        
        for i, record in enumerate(pending_list, 1):
            action = record.get("action", "unknown")
            target = record.get("target", "memory")
            summary = record.get("summary", "No summary")
            created_at = record.get("created_at", 0)
            origin = record.get("origin", "unknown")
            
            # Format timestamp
            if created_at:
                time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at))
            else:
                time_str = "unknown"
            
            print(f"  [{i}] ID: {record.get('id', 'unknown')}")
            print(f"      Action: {action} ({target})")
            print(f"      Summary: {summary}")
            print(f"      Time: {time_str} ({origin})")
            print()
            
    except Exception as e:
        print(f"\n  Error listing pending memory writes: {e}\n")


def _handle_approve(args) -> None:
    """Approve a pending memory write."""
    pending_id = getattr(args, "pending_id", None)
    
    if not pending_id:
        print("\n  Error: Pending ID required for approve command.\n")
        print("  Usage: aetheros memory approve <pending_id>\n")
        return
    
    try:
        # Get the pending record
        record = get_pending("memory", pending_id)
        if not record:
            print(f"\n  Error: No pending memory write found with ID '{pending_id}'\n")
            return
        
        # Show what we're about to approve
        action = record.get("action", "unknown")
        target = record.get("target", "memory")
        summary = record.get("summary", "No summary")
        
        print(f"\n  Approving memory write:")
        print(f"  ID: {pending_id}")
        print(f"  Action: {action} ({target})")
        print(f"  Summary: {summary}")
        
        # Get the store for replaying the write
        from agent.agent_runtime_helpers import invoke_tool
        # We need to get the agent's memory store - this is tricky in a CLI context
        # For now, we'll use a direct approach
        
        # Replay the write using the memory tool directly
        payload = record.get("payload", {})
        action = payload.get("action", "")
        target = payload.get("target", "memory")
        content = payload.get("content", "")
        old_text = payload.get("old_text", "")
        
        # Call the memory tool directly to replay the write
        result = memory_tool(
            action=action,
            target=target,
            content=content,
            old_text=old_text,
            scope="default",  # Use default scope for approved writes
            store=None  # Let the memory tool get the store from context
        )
        
        result_dict = json.loads(result)
        
        if result_dict.get("success"):
            # If successful, discard the pending record
            if discard_pending("memory", pending_id):
                print(f"  ��� � � ✓ Memory write approved and applied.")
            else:
                print(f"  ��� � � ✓ Memory write applied but failed to remove pending record.")
        else:
            print(f"  ��� � � ✗ Failed to apply memory write: {result_dict.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"\n  Error approving memory write: {e}\n")


def _handle_reject(args) -> None:
    """Reject a pending memory write."""
    pending_id = getattr(args, "pending_id", None)
    
    if not pending_id:
        print("\n  Error: Pending ID required for reject command.\n")
        print("  Usage: aetheros memory reject <pending_id>\n")
        return
    
    try:
        # Get the pending record to show what we're rejecting
        record = get_pending("memory", pending_id)
        if not record:
            print(f"\n  Error: No pending memory write found with ID '{pending_id}'\n")
            return
        
        # Show what we're about to reject
        action = record.get("action", "unknown")
        target = record.get("target", "memory")
        summary = record.get("summary", "No summary")
        
        print(f"\n  Rejecting memory write:")
        print(f"  ID: {pending_id}")
        print(f"  Action: {action} ({target})")
        print(f"  Summary: {summary}")
        
        # Confirm the rejection
        try:
            answer = input("\n  Are you sure you want to reject this memory write? (y/N): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  Cancelled.\n")
            return
        
        if answer == "y" or answer == "yes":
            # Discard the pending record
            if discard_pending("memory", pending_id):
                print(f"  ��� ��� � � � ✓ Memory write rejected and removed from pending queue.")
            else:
                print(f"  ��� ��� � � � ✗ Failed to remove pending record.")
        else:
            print(f"  ��� ��� � � Cancelled.")
            
    except Exception as e:
        print(f"\n  ��� ��� � � Error rejecting memory write: {e}\n")


def _handle_approval_toggle(args) -> None:
    """Toggle the memory write approval gate."""
    try:
        from aetheros_cli.config import load_config, save_config
        
        config = load_config()
        if not isinstance(config.get("memory"), dict):
            config["memory"] = {}
        
        current_setting = config.get("memory", {}).get("write_approval", False)
        new_setting = not current_setting
        
        if "memory" not in config:
            config["memory"] = {}
        config["memory"]["write_approval"] = new_setting
        
        save_config(config)
        
        status = "ON" if new_setting else "OFF"
        print(f"\n  Memory write approval gate is now {status}.")
        print(f"  When ON, memory writes require approval before being applied.")
        print(f"  When OFF, memory writes are applied immediately (default behavior).\n")
        
    except Exception as e:
        print(f"\n  ��� ��� � � Error toggling approval gate: {e}\n")