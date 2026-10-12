"""
C# SDK for AetherOS
===================

C# SDK for .NET ecosystem integration.

Usage::

    from aetheros_developer_platform.sdk import SDKFactory
    sdk = SDKFactory.create("csharp")
    project = sdk.init_project("my-plugin")
    sdk.build_project(project)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_developer_platform.sdk import (
    BaseSDK,
    SDKConfig,
    SDKLanguage,
    SDKProject,
)

logger = logging.getLogger(__name__)

# C# SDK templates
PLUGIN_TEMPLATE = '''// {plugin_name}
// =============
//
// {description}
//
// Author: {author}
// Version: {version}

using AetherOS.SDK;
using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Threading.Tasks;

namespace {namespace}
{{
    /// <summary>
    /// AetherOS Plugin
    /// </summary>
    public class Plugin : IPlugin
    {{
        private readonly ExtensionContext _ctx;
        private readonly string _name = "{plugin_name}";

        /// <summary>
        /// Plugin name
        /// </summary>
        public string Name => _name;

        /// <summary>
        /// Create a new plugin instance
        /// </summary>
        /// <param name="ctx">Extension context</param>
        public Plugin(ExtensionContext ctx)
        {{
            _ctx = ctx;
        }}

        /// <summary>
        /// Register the plugin with AetherOS
        /// </summary>
        public void Register()
        {{
            Console.WriteLine($"Registering plugin: {_name}");

            // Register tools
            _ctx.Tools.RegisterTool(new Tool
            {{
                Name = "{tool_name}",
                Description = "{tool_description}",
                Parameters = new Dictionary<string, object>(),
                Handler = HandleTool,
            }});

            // Register event handlers
            _ctx.Events.On("session:start", (event) =>
            {{
                Console.WriteLine($"Session started: {event.Data}");
            }});
        }}

        private string HandleTool(Dictionary<string, object> args)
        {{
            return JsonSerializer.Serialize(new
            {{
                Success = true,
                Data = $"Hello from {_name}"
            }});
        }}
    }}
}}
'''

AGENT_TEMPLATE = '''// {agent_name} Agent
// ==================
//
// {description}
//
// Author: {author}
// Version: {version}

using AetherOS.SDK;
using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Threading.Tasks;

namespace {namespace}
{{
    /// <summary>
    /// Agent execution result
    /// </summary>
    public class AgentResult
    {{
        public string Status {{ get; set; }}
        public string Agent {{ get; set; }}
        public string Task {{ get; set; }}
        public string Output {{ get; set; }}
    }}

    /// <summary>
    /// AI Agent
    /// </summary>
    public class Agent : IAgent
    {{
        private readonly ExtensionContext _ctx;
        private readonly string _name = "{agent_name}";

        /// <summary>
        /// Agent name
        /// </summary>
        public string Name => _name;

        /// <summary>
        /// Create a new agent instance
        /// </summary>
        /// <param name="ctx">Extension context</param>
        public Agent(ExtensionContext ctx)
        {{
            _ctx = ctx;
        }}

        /// <summary>
        /// Execute the agent task
        /// </summary>
        /// <param name="task">Task description</param>
        /// <param name="context">Optional context data</param>
        /// <returns>Execution result</returns>
        public async Task<AgentResult> ExecuteAsync(string task, Dictionary<string, object> context = null)
        {{
            Console.WriteLine($"Executing agent {_name}: {task}");

            return new AgentResult
            {{
                Status = "success",
                Agent = _name,
                Task = task,
                Output = "Agent execution completed"
            }};
        }}
    }}

    /// <summary>
    /// Plugin entry point
    /// </summary>
    public static class PluginEntry
    {{
        public static void Register(ExtensionContext ctx)
        {{
            var agent = new Agent(ctx);
            ctx.RegisterAgent(agent.Name, agent);
        }}
    }}
}}
'''

MCP_TEMPLATE = '''// {server_name} MCP Server
// ========================
//
// {description}
//
// Author: {author}
// Version: {version}

using AetherOS.SDK;
using System;
using System.Collections.Generic;
using System.Text.Json;

namespace {namespace}
{{
    /// <summary>
    /// MCP Tool definition
    /// </summary>
    public class MCPServer : IMCPServer
    {{
        private readonly string _name = "{server_name}";
        private readonly List<MCPTool> _tools = new();
        private readonly List<MCPResource> _resources = new();

        /// <summary>
        /// Server name
        /// </summary>
        public string Name => _name;

        /// <summary>
        /// List available tools
        /// </summary>
        public IReadOnlyList<MCPTool> ListTools() => _tools.AsReadOnly();

        /// <summary>
        /// Call a tool by name
        /// </summary>
        public object CallTool(string name, Dictionary<string, object> args)
        {{
            return new
            {{
                Result = $"Tool {name} executed"
            }};
        }}

        /// <summary>
        /// List available resources
        /// </summary>
        public IReadOnlyList<MCPResource> ListResources() => _resources.AsReadOnly();

        /// <summary>
        /// Read a resource by URI
        /// </summary>
        public object ReadResource(string uri)
        {{
            return new
            {{
                Uri = uri,
                Content = "Resource content"
            }};
        }}
    }}

    /// <summary>
    /// Plugin entry point
    /// </summary>
    public static class PluginEntry
    {{
        public static void Register(ExtensionContext ctx)
        {{
            var server = new MCPServer();
            ctx.RegisterMCP(server.Name, server);
        }}
    }}
}}
'''

WORKFLOW_TEMPLATE = '''// {workflow_name} Workflow
// ========================
//
// {description}
//
// Author: {author}
// Version: {version}

using AetherOS.SDK;
using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Threading.Tasks;

namespace {namespace}
{{
    /// <summary>
    /// Workflow node
    /// </summary>
    public class WorkflowNode
    {{
        public string Id {{ get; set; }}
        public string Type {{ get; set; }}
        public Dictionary<string, object> Config {{ get; set; }}
    }}

    /// <summary>
    /// Workflow edge
    /// </summary>
    public class WorkflowEdge
    {{
        public string Source {{ get; set; }}
        public string Target {{ get; set; }}
    }}

    /// <summary>
    /// Workflow
    /// </summary>
    public class Workflow : IWorkflow
    {{
        private readonly ExtensionContext _ctx;
        private readonly string _name = "{workflow_name}";
        private readonly List<WorkflowNode> _nodes = new();
        private readonly List<WorkflowEdge> _edges = new();

        /// <summary>
        /// Workflow name
        /// </summary>
        public string Name => _name;

        /// <summary>
        /// Create a new workflow
        /// </summary>
        /// <param name="ctx">Extension context</param>
        public Workflow(ExtensionContext ctx)
        {{
            _ctx = ctx;
        }}

        /// <summary>
        /// Define the workflow structure
        /// </summary>
        public void Define()
        {{
            AddNode("start", "trigger", new Dictionary<string, object>());
            AddNode("process", "action", new Dictionary<string, object> {{ ["action"] = "process_data" }});
            AddNode("end", "output", new Dictionary<string, object>());

            AddEdge("start", "process");
            AddEdge("process", "end");
        }}

        private void AddNode(string id, string type, Dictionary<string, object> config)
        {{
            _nodes.Add(new WorkflowNode {{ Id = id, Type = type, Config = config }});
        }}

        private void AddEdge(string source, string target)
        {{
            _edges.Add(new WorkflowEdge {{ Source = source, Target = target }});
        }}

        /// <summary>
        /// Execute the workflow
        /// </summary>
        public async Task<Dictionary<string, object>> ExecuteAsync(Dictionary<string, object> inputData)
        {{
            Console.WriteLine($"Executing workflow: {_name}");
            return new Dictionary<string, object>
            {{
                ["status"] = "completed",
                ["output"] = inputData
            }};
        }}
    }}

    /// <summary>
    /// Plugin entry point
    /// </summary>
    public static class PluginEntry
    {{
        public static void Register(ExtensionContext ctx)
        {{
            var workflow = new Workflow(ctx);
            workflow.Define();
            ctx.RegisterWorkflow(workflow.Name, workflow);
        }}
    }}
}}
'''

THEME_TEMPLATE = '''// {theme_name} Theme
// ==================
//
// {description}
//
// Author: {author}
// Version: {version}

using AetherOS.SDK;
using System;
using System.Collections.Generic;

namespace {namespace}
{{
    /// <summary>
    /// Theme configuration
    /// </summary>
    public class ThemeConfig
    {{
        public string Name {{ get; set; }}
        public string Description {{ get; set; }}
        public string Author {{ get; set; }}
        public string Version {{ get; set; }}
        public Dictionary<string, string> Colors {{ get; set; }}
        public Dictionary<string, string> Fonts {{ get; set; }}
        public Dictionary<string, int> Spacing {{ get; set; }}
        public Dictionary<string, string> Animations {{ get; set; }}
    }}

    /// <summary>
    /// Plugin entry point
    /// </summary>
    public static class PluginEntry
    {{
        public static void Register(ExtensionContext ctx)
        {{
            var config = new ThemeConfig
            {{
                Name = "{theme_name}",
                Description = "{description}",
                Author = "{author}",
                Version = "{version}",
                Colors = new Dictionary<string, string>
                {{
                    ["primary"] = "#007ACC",
                    ["secondary"] = "#1E1E1E",
                    ["background"] = "#FFFFFF",
                    ["surface"] = "#F5F5F5",
                    ["text"] = "#000000",
                    ["textSecondary"] = "#666666",
                    ["border"] = "#E0E0E0",
                    ["success"] = "#4CAF50",
                    ["warning"] = "#FF9800",
                    ["error"] = "#F44336"
                }},
                Fonts = new Dictionary<string, string>
                {{
                    ["primary"] = "Inter, sans-serif",
                    ["mono"] = "JetBrains Mono, monospace"
                }},
                Spacing = new Dictionary<string, int>
                {{
                    ["unit"] = 4,
                    ["radius"] = 8
                }},
                Animations = new Dictionary<string, string>
                {{
                    ["duration"] = "0.2s",
                    ["easing"] = "ease-in-out"
                }}
            }};

            ctx.RegisterTheme(config.Name, config);
        }}
    }}
}}
'''


class CSharpSDK(BaseSDK):
    """C# SDK for AetherOS extensions."""

    @property
    def language(self) -> SDKLanguage:
        return SDKLanguage.CSHARP

    def init_project(self, name: str, directory: Optional[Path] = None) -> SDKProject:
        """Initialize a new C# extension project."""
        if directory is None:
            directory = Path.cwd() / name
        directory.mkdir(parents=True, exist_ok=True)

        # Create project structure
        (directory / "src").mkdir(exist_ok=True)
        (directory / "tests").mkdir(exist_ok=True)

        # Create .csproj file
        csproj = self._generate_csproj(name)
        (directory / f"{name}.csproj").write_text(csproj, encoding="utf-8")

        # Create Program.cs
        program_content = f'''using System;
using AetherOS.SDK;

namespace {name}
{{
    class Program
    {{
        static void Main(string[] args)
        {{
            Console.WriteLine("AetherOS Extension: {name}");
        }}
    }}
}}
'''
        (directory / "src" / "Program.cs").write_text(program_content, encoding="utf-8")

        # Create manifest
        manifest = {
            "name": name,
            "version": "0.1.0",
            "description": "",
            "author": "",
            "sdk_version": self._config.sdk_version,
            "aetheros_version": self._config.aetheros_version,
            "permissions": [],
            "dependencies": [],
        }
        (directory / "manifest.yaml").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

        return SDKProject(
            name=name,
            language=self.language,
            directory=directory,
            manifest=manifest,
        )

    def build_project(self, project: SDKProject) -> bool:
        """Build the C# extension project."""
        try:
            import subprocess
            result = subprocess.run(
                ["dotnet", "build"],
                cwd=str(project.directory),
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except Exception as exc:
            logger.error("Build failed: %s", exc)
            return False

    def test_project(self, project: SDKProject) -> Dict[str, Any]:
        """Run tests for the C# extension project."""
        try:
            import subprocess
            result = subprocess.run(
                ["dotnet", "test"],
                cwd=str(project.directory),
                capture_output=True,
                text=True,
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr,
            }
        except Exception as exc:
            return {"success": False, "output": "", "errors": str(exc)}

    def package_project(self, project: SDKProject) -> Optional[Path]:
        """Package the C# extension for distribution."""
        try:
            import subprocess
            result = subprocess.run(
                ["dotnet", "publish", "-c", "Release"],
                cwd=str(project.directory),
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                publish_dir = project.directory / "bin" / "Release" / "net8.0" / "publish"
                if publish_dir.exists():
                    dlls = list(publish_dir.glob("*.dll"))
                    if dlls:
                        return dlls[0]
            return None
        except Exception as exc:
            logger.error("Package failed: %s", exc)
            return None

    def get_template(self, plugin_type: str) -> str:
        """Get a C# code template for a specific plugin type."""
        templates = {
            "tool_plugin": PLUGIN_TEMPLATE,
            "ai_agent": AGENT_TEMPLATE,
            "mcp_server": MCP_TEMPLATE,
            "workflow_plugin": WORKFLOW_TEMPLATE,
            "theme": THEME_TEMPLATE,
        }
        return templates.get(plugin_type, PLUGIN_TEMPLATE)

    def _generate_csproj(self, name: str) -> str:
        """Generate .csproj content."""
        return f'''<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <RootNamespace>{name}</RootNamespace>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="AetherOS.SDK" Version="1.0.0" />
  </ItemGroup>

</Project>
'''
