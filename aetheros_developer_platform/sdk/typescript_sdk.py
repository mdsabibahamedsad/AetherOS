"""
TypeScript SDK for AetherOS
===========================

TypeScript SDK with full type definitions and async support.

Usage::

    from aetheros_developer_platform.sdk import SDKFactory
    sdk = SDKFactory.create("typescript")
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

# TypeScript SDK templates
PLUGIN_TEMPLATE = '''/**
 * {plugin_name}
 * =============
 *
 * {description}
 *
 * @author {author}
 * @version {version}
 */

import {{ PluginAPI, ToolAPI, EventAPI, ExtensionContext }} from '@aetheros/sdk';

export function register(ctx: ExtensionContext): void {{
    console.log('Registering plugin: {plugin_name}');

    // Register tools
    ctx.tools.registerTool({{
        name: '{tool_name}',
        description: '{tool_description}',
        parameters: {{}},
        handler: handle{class_name},
    }});

    // Register event handlers
    ctx.events.on('session:start', (event) => {{
        console.log('Session started:', event.data);
    }});
}}

async function handle{class_name}(args: Record<string, unknown>): Promise<string> {{
    return JSON.stringify({{ success: true, data: 'Hello from {plugin_name}' }});
}}
'''

AGENT_TEMPLATE = '''/**
 * {agent_name} Agent
 * ==================
 *
 * {description}
 *
 * @author {author}
 * @version {version}
 */

import {{ AgentAPI, ExtensionContext }} from '@aetheros/sdk';

interface AgentResult {{
    status: string;
    agent: string;
    task: string;
    output: string;
}}

export class {class_name}Agent {{
    private ctx: ExtensionContext;
    public readonly name: string;

    constructor(ctx: ExtensionContext) {{
        this.ctx = ctx;
        this.name = '{agent_name}';
    }}

    async execute(task: string, context?: Record<string, unknown>): Promise<AgentResult> {{
        console.log(`Executing agent ${{this.name}}: ${{task}}`);

        return {{
            status: 'success',
            agent: this.name,
            task,
            output: 'Agent execution completed',
        }};
    }}
}}

export function register(ctx: ExtensionContext): void {{
    const agent = new {class_name}Agent(ctx);
    ctx.registerAgent(agent.name, agent);
}}
'''

MCP_TEMPLATE = '''/**
 * {server_name} MCP Server
 * ========================
 *
 * {description}
 *
 * @author {author}
 * @version {version}
 */

import {{ MCPServer, Tool, Resource }} from '@aetheros/sdk';

export class {class_name}MCPServer implements MCPServer {{
    public readonly name: string;
    private tools: Tool[] = [];
    private resources: Resource[] = [];

    constructor() {{
        this.name = '{server_name}';
    }}

    listTools(): Tool[] {{
        return this.tools;
    }}

    callTool(name: string, args: Record<string, unknown>): unknown {{
        return {{ result: `Tool ${{name}} executed` }};
    }}

    listResources(): Resource[] {{
        return this.resources;
    }}

    readResource(uri: string): unknown {{
        return {{ uri, content: 'Resource content' }};
    }}
}}

export function register(ctx): void {{
    const server = new {class_name}MCPServer();
    ctx.registerMCP(server.name, server);
}}
'''

WORKFLOW_TEMPLATE = '''/**
 * {workflow_name} Workflow
 * ========================
 *
 * {description}
 *
 * @author {author}
 * @version {version}
 */

import {{ WorkflowNode, WorkflowEdge, ExtensionContext }} from '@aetheros/sdk';

export class {class_name}Workflow {{
    private ctx: ExtensionContext;
    public readonly name: string;
    private nodes: WorkflowNode[] = [];
    private edges: WorkflowEdge[] = [];

    constructor(ctx: ExtensionContext) {{
        this.ctx = ctx;
        this.name = '{workflow_name}';
    }}

    define(): void {{
        this.addNode('start', 'trigger', {{}});
        this.addNode('process', 'action', {{ action: 'process_data' }});
        this.addNode('end', 'output', {{}});

        this.addEdge('start', 'process');
        this.addEdge('process', 'end');
    }}

    addNode(id: string, type: string, config: Record<string, unknown>): void {{
        this.nodes.push({{ id, type, config }});
    }}

    addEdge(source: string, target: string): void {{
        this.edges.push({{ source, target }});
    }}

    async execute(inputData: Record<string, unknown>): Promise<Record<string, unknown>> {{
        console.log(`Executing workflow: ${{this.name}}`);
        return {{ status: 'completed', output: inputData }};
    }}
}}

export function register(ctx: ExtensionContext): void {{
    const workflow = new {class_name}Workflow(ctx);
    workflow.define();
    ctx.registerWorkflow(workflow.name, workflow);
}}
'''

THEME_TEMPLATE = '''/**
 * {theme_name} Theme
 * ==================
 *
 * {description}
 *
 * @author {author}
 * @version {version}
 */

import {{ ThemeConfig }} from '@aetheros/sdk';

export const themeConfig: ThemeConfig = {{
    name: '{theme_name}',
    description: '{description}',
    author: '{author}',
    version: '{version}',
    colors: {{
        primary: '#007ACC',
        secondary: '#1E1E1E',
        background: '#FFFFFF',
        surface: '#F5F5F5',
        text: '#000000',
        textSecondary: '#666666',
        border: '#E0E0E0',
        success: '#4CAF50',
        warning: '#FF9800',
        error: '#F44336',
    }},
    fonts: {{
        primary: 'Inter, sans-serif',
        mono: 'JetBrains Mono, monospace',
    }},
    spacing: {{
        unit: 4,
        radius: 8,
    }},
    animations: {{
        duration: '0.2s',
        easing: 'ease-in-out',
    }},
}};

export function register(ctx): void {{
    ctx.registerTheme(themeConfig.name, themeConfig);
}}
'''


class TypeScriptSDK(BaseSDK):
    """TypeScript SDK for AetherOS extensions."""

    @property
    def language(self) -> SDKLanguage:
        return SDKLanguage.TYPESCRIPT

    def init_project(self, name: str, directory: Optional[Path] = None) -> SDKProject:
        """Initialize a new TypeScript extension project."""
        if directory is None:
            directory = Path.cwd() / name
        directory.mkdir(parents=True, exist_ok=True)

        # Create project structure
        (directory / "src").mkdir(exist_ok=True)
        (directory / "tests").mkdir(exist_ok=True)

        # Create package.json
        package_json = self._generate_package_json(name)
        (directory / "package.json").write_text(
            json.dumps(package_json, indent=2), encoding="utf-8"
        )

        # Create tsconfig.json
        tsconfig = self._generate_tsconfig()
        (directory / "tsconfig.json").write_text(
            json.dumps(tsconfig, indent=2), encoding="utf-8"
        )

        # Create src/index.ts
        index_content = f'''/**
 * {name}
 * =============
 *
 * AetherOS extension.
 */

import {{ ExtensionContext }} from '@aetheros/sdk';

export function register(ctx: ExtensionContext): void {{
    console.log('Plugin {name} registered');
}}
'''
        (directory / "src" / "index.ts").write_text(index_content, encoding="utf-8")

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
        """Build the TypeScript extension project."""
        try:
            import subprocess
            result = subprocess.run(
                ["npm", "run", "build"],
                cwd=str(project.directory),
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except Exception as exc:
            logger.error("Build failed: %s", exc)
            return False

    def test_project(self, project: SDKProject) -> Dict[str, Any]:
        """Run tests for the TypeScript extension project."""
        try:
            import subprocess
            result = subprocess.run(
                ["npm", "test"],
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
        """Package the TypeScript extension for distribution."""
        try:
            import subprocess
            result = subprocess.run(
                ["npm", "pack"],
                cwd=str(project.directory),
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                packages = list(project.directory.glob("*.tgz"))
                if packages:
                    return packages[0]
            return None
        except Exception as exc:
            logger.error("Package failed: %s", exc)
            return None

    def get_template(self, plugin_type: str) -> str:
        """Get a TypeScript code template for a specific plugin type."""
        templates = {
            "tool_plugin": PLUGIN_TEMPLATE,
            "ai_agent": AGENT_TEMPLATE,
            "mcp_server": MCP_TEMPLATE,
            "workflow_plugin": WORKFLOW_TEMPLATE,
            "theme": THEME_TEMPLATE,
        }
        return templates.get(plugin_type, PLUGIN_TEMPLATE)

    def _generate_package_json(self, name: str) -> Dict[str, Any]:
        """Generate package.json content."""
        return {
            "name": f"@aetheros/{name}",
            "version": "0.1.0",
            "description": "AetherOS extension",
            "main": "dist/index.js",
            "types": "dist/index.d.ts",
            "scripts": {
                "build": "tsc",
                "test": "jest",
                "lint": "eslint src/",
            },
            "dependencies": {
                "@aetheros/sdk": "^1.0.0",
            },
            "devDependencies": {
                "typescript": "^5.0.0",
                "@types/node": "^20.0.0",
                "jest": "^29.0.0",
                "@types/jest": "^29.0.0",
                "ts-jest": "^29.0.0",
            },
        }

    def _generate_tsconfig(self) -> Dict[str, Any]:
        """Generate tsconfig.json content."""
        return {
            "compilerOptions": {
                "target": "ES2020",
                "module": "commonjs",
                "lib": ["ES2020"],
                "outDir": "./dist",
                "rootDir": "./src",
                "strict": True,
                "esModuleInterop": True,
                "skipLibCheck": True,
                "forceConsistentCasingInFileNames": True,
                "declaration": True,
                "declarationMap": True,
                "sourceMap": True,
            },
            "include": ["src/**/*"],
            "exclude": ["node_modules", "dist", "tests"],
        }
