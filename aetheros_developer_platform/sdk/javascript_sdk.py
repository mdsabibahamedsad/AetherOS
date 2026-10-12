"""
JavaScript SDK for AetherOS
===========================

JavaScript SDK supporting both CommonJS and ESM modules.

Usage::

    from aetheros_developer_platform.sdk import SDKFactory
    sdk = SDKFactory.create("javascript")
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

# JavaScript SDK templates
PLUGIN_TEMPLATE = '''/**
 * {plugin_name}
 * =============
 *
 * {description}
 *
 * @author {author}
 * @version {version}
 */

'use strict';

/**
 * Register the plugin with AetherOS.
 * @param {{object}} ctx - Extension context
 */
function register(ctx) {{
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

/**
 * Handle tool invocation.
 * @param {{object}} args - Tool arguments
 * @returns {{string}} JSON result
 */
async function handle{class_name}(args) {{
    return JSON.stringify({{ success: true, data: 'Hello from {plugin_name}' }});
}}

module.exports = {{ register }};
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

'use strict';

class {class_name}Agent {{
    /**
     * Create a new agent instance.
     * @param {{object}} ctx - Extension context
     */
    constructor(ctx) {{
        this.ctx = ctx;
        this.name = '{agent_name}';
    }}

    /**
     * Execute the agent task.
     * @param {{string}} task - Task description
     * @param {{object}} [context] - Optional context data
     * @returns {{Promise<object}} Execution result
     */
    async execute(task, context = null) {{
        console.log(`Executing agent ${{this.name}}: ${{task}}`);

        return {{
            status: 'success',
            agent: this.name,
            task,
            output: 'Agent execution completed',
        }};
    }}
}}

/**
 * Register the agent with AetherOS.
 * @param {{object}} ctx - Extension context
 */
function register(ctx) {{
    const agent = new {class_name}Agent(ctx);
    ctx.registerAgent(agent.name, agent);
}}

module.exports = {{ register, {class_name}Agent }};
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

'use strict';

class {class_name}MCPServer {{
    constructor() {{
        this.name = '{server_name}';
        this.tools = [];
        this.resources = [];
    }}

    listTools() {{
        return this.tools;
    }}

    callTool(name, args) {{
        return {{ result: `Tool ${{name}} executed` }};
    }}

    listResources() {{
        return this.resources;
    }}

    readResource(uri) {{
        return {{ uri, content: 'Resource content' }};
    }}
}}

/**
 * Register the MCP server with AetherOS.
 * @param {{object}} ctx - Extension context
 */
function register(ctx) {{
    const server = new {class_name}MCPServer();
    ctx.registerMCP(server.name, server);
}}

module.exports = {{ register, {class_name}MCPServer }};
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

'use strict';

class {class_name}Workflow {{
    constructor(ctx) {{
        this.ctx = ctx;
        this.name = '{workflow_name}';
        this.nodes = [];
        this.edges = [];
    }}

    define() {{
        this.addNode('start', 'trigger', {{}});
        this.addNode('process', 'action', {{ action: 'process_data' }});
        this.addNode('end', 'output', {{}});

        this.addEdge('start', 'process');
        this.addEdge('process', 'end');
    }}

    addNode(id, type, config) {{
        this.nodes.push({{ id, type, config }});
    }}

    addEdge(source, target) {{
        this.edges.push({{ source, target }});
    }}

    async execute(inputData) {{
        console.log(`Executing workflow: ${{this.name}}`);
        return {{ status: 'completed', output: inputData }};
    }}
}}

/**
 * Register the workflow with AetherOS.
 * @param {{object}} ctx - Extension context
 */
function register(ctx) {{
    const workflow = new {class_name}Workflow(ctx);
    workflow.define();
    ctx.registerWorkflow(workflow.name, workflow);
}}

module.exports = {{ register, {class_name}Workflow }};
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

'use strict';

const themeConfig = {{
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

/**
 * Register the theme with AetherOS.
 * @param {{object}} ctx - Extension context
 */
function register(ctx) {{
    ctx.registerTheme(themeConfig.name, themeConfig);
}}

module.exports = {{ register, themeConfig }};
'''


class JavaScriptSDK(BaseSDK):
    """JavaScript SDK for AetherOS extensions."""

    @property
    def language(self) -> SDKLanguage:
        return SDKLanguage.JAVASCRIPT

    def init_project(self, name: str, directory: Optional[Path] = None) -> SDKProject:
        """Initialize a new JavaScript extension project."""
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

        # Create src/index.js
        index_content = f'''/**
 * {name}
 * =============
 *
 * AetherOS extension.
 */

'use strict';

/**
 * Register the plugin with AetherOS.
 * @param {{object}} ctx - Extension context
 */
function register(ctx) {{
    console.log('Plugin {name} registered');
}}

module.exports = {{ register }};
'''
        (directory / "src" / "index.js").write_text(index_content, encoding="utf-8")

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
        """Build the JavaScript extension project."""
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
        """Run tests for the JavaScript extension project."""
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
        """Package the JavaScript extension for distribution."""
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
        """Get a JavaScript code template for a specific plugin type."""
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
            "main": "src/index.js",
            "scripts": {
                "build": "echo 'No build step needed'",
                "test": "jest",
                "lint": "eslint src/",
            },
            "dependencies": {
                "@aetheros/sdk": "^1.0.0",
            },
            "devDependencies": {
                "jest": "^29.0.0",
                "eslint": "^8.0.0",
            },
        }
