"""
Java SDK for AetherOS
=====================

Java SDK for JVM ecosystem integration.

Usage::

    from aetheros_developer_platform.sdk import SDKFactory
    sdk = SDKFactory.create("java")
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

# Java SDK templates
PLUGIN_TEMPLATE = '''/**
 * {plugin_name}
 * =============
 *
 * {description}
 *
 * @author {author}
 * @version {version}
 */

package {package_name};

import aetheros.sdk.ExtensionContext;
import aetheros.sdk.Tool;
import aetheros.sdk.Event;
import java.util.Map;
import java.util.HashMap;
import com.google.gson.Gson;

/**
 * AetherOS Plugin
 */
public class Plugin implements aetheros.sdk.Plugin {{
    private final ExtensionContext ctx;
    private final String name = "{plugin_name}";
    private final Gson gson = new Gson();

    /**
     * Create a new plugin instance
     * @param ctx Extension context
     */
    public Plugin(ExtensionContext ctx) {{
        this.ctx = ctx;
    }}

    @Override
    public String getName() {{
        return name;
    }}

    @Override
    public void register() {{
        System.out.println("Registering plugin: " + name);

        // Register tools
        ctx.getTools().registerTool(new Tool.Builder()
            .name("{tool_name}")
            .description("{tool_description}")
            .parameters(new HashMap<>())
            .handler(this::handleTool)
            .build());

        // Register event handlers
        ctx.getEvents().on("session:start", this::onSessionStart);
    }}

    private String handleTool(Map<String, Object> args) {{
        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("data", "Hello from " + name);
        return gson.toJson(result);
    }}

    private void onSessionStart(Event event) {{
        System.out.println("Session started: " + event.getData());
    }}
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

package {package_name};

import aetheros.sdk.ExtensionContext;
import aetheros.sdk.Agent;
import java.util.Map;
import java.util.HashMap;
import java.util.concurrent.CompletableFuture;
import com.google.gson.Gson;

/**
 * Agent execution result
 */
class AgentResult {{
    private final String status;
    private final String agent;
    private final String task;
    private final String output;

    AgentResult(String status, String agent, String task, String output) {{
        this.status = status;
        this.agent = agent;
        this.task = task;
        this.output = output;
    }}

    String getStatus() {{ return status; }}
    String getAgent() {{ return agent; }}
    String getTask() {{ return task; }}
    String getOutput() {{ return output; }}
}}

/**
 * AI Agent
 */
public class {class_name}Agent implements Agent {{
    private final ExtensionContext ctx;
    private final String name = "{agent_name}";
    private final Gson gson = new Gson();

    /**
     * Create a new agent instance
     * @param ctx Extension context
     */
    public {class_name}Agent(ExtensionContext ctx) {{
        this.ctx = ctx;
    }}

    @Override
    public String getName() {{
        return name;
    }}

    @Override
    public CompletableFuture<AgentResult> execute(String task, Map<String, Object> context) {{
        return CompletableFuture.supplyAsync(() -> {{
            System.out.println("Executing agent " + name + ": " + task);

            return new AgentResult(
                "success",
                name,
                task,
                "Agent execution completed"
            );
        }});
    }}
}}

/**
 * Plugin entry point
 */
class Plugin implements aetheros.sdk.Plugin {{
    private final ExtensionContext ctx;

    Plugin(ExtensionContext ctx) {{
        this.ctx = ctx;
    }}

    @Override
    public String getName() {{
        return "{agent_name}";
    }}

    @Override
    public void register() {{
        var agent = new {class_name}Agent(ctx);
        ctx.registerAgent(agent.getName(), agent);
    }}
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

package {package_name};

import aetheros.sdk.ExtensionContext;
import aetheros.sdk.MCPServer;
import aetheros.sdk.MCPTool;
import aetheros.sdk.MCPResource;
import java.util.List;
import java.util.ArrayList;
import java.util.Map;
import java.util.HashMap;
import com.google.gson.Gson;

/**
 * MCP Server
 */
public class {class_name}MCPServer implements MCPServer {{
    private final String name = "{server_name}";
    private final List<MCPTool> tools = new ArrayList<>();
    private final List<MCPResource> resources = new ArrayList<>();
    private final Gson gson = new Gson();

    @Override
    public String getName() {{
        return name;
    }}

    @Override
    public List<MCPTool> listTools() {{
        return tools;
    }}

    @Override
    public Object callTool(String name, Map<String, Object> args) {{
        Map<String, Object> result = new HashMap<>();
        result.put("result", "Tool " + name + " executed");
        return result;
    }}

    @Override
    public List<MCPResource> listResources() {{
        return resources;
    }}

    @Override
    public Object readResource(String uri) {{
        Map<String, Object> result = new HashMap<>();
        result.put("uri", uri);
        result.put("content", "Resource content");
        return result;
    }}
}}

/**
 * Plugin entry point
 */
class Plugin implements aetheros.sdk.Plugin {{
    private final ExtensionContext ctx;

    Plugin(ExtensionContext ctx) {{
        this.ctx = ctx;
    }}

    @Override
    public String getName() {{
        return "{server_name}";
    }}

    @Override
    public void register() {{
        var server = new {class_name}MCPServer();
        ctx.registerMCP(server.getName(), server);
    }}
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

package {package_name};

import aetheros.sdk.ExtensionContext;
import aetheros.sdk.Workflow;
import aetheros.sdk.WorkflowNode;
import aetheros.sdk.WorkflowEdge;
import java.util.List;
import java.util.ArrayList;
import java.util.Map;
import java.util.HashMap;
import java.util.concurrent.CompletableFuture;

/**
 * Workflow
 */
public class {class_name}Workflow implements Workflow {{
    private final ExtensionContext ctx;
    private final String name = "{workflow_name}";
    private final List<WorkflowNode> nodes = new ArrayList<>();
    private final List<WorkflowEdge> edges = new ArrayList<>();

    /**
     * Create a new workflow
     * @param ctx Extension context
     */
    public {class_name}Workflow(ExtensionContext ctx) {{
        this.ctx = ctx;
    }}

    @Override
    public String getName() {{
        return name;
    }}

    @Override
    public void define() {{
        addNode("start", "trigger", new HashMap<>());
        addNode("process", "action", Map.of("action", "process_data"));
        addNode("end", "output", new HashMap<>());

        addEdge("start", "process");
        addEdge("process", "end");
    }}

    private void addNode(String id, String type, Map<String, Object> config) {{
        nodes.add(new WorkflowNode(id, type, config));
    }}

    private void addEdge(String source, String target) {{
        edges.add(new WorkflowEdge(source, target));
    }}

    @Override
    public CompletableFuture<Map<String, Object>> execute(Map<String, Object> inputData) {{
        return CompletableFuture.supplyAsync(() -> {{
            System.out.println("Executing workflow: " + name);
            return Map.of(
                "status", "completed",
                "output", inputData
            );
        }});
    }}
}}

/**
 * Plugin entry point
 */
class Plugin implements aetheros.sdk.Plugin {{
    private final ExtensionContext ctx;

    Plugin(ExtensionContext ctx) {{
        this.ctx = ctx;
    }}

    @Override
    public String getName() {{
        return "{workflow_name}";
    }}

    @Override
    public void register() {{
        var workflow = new {class_name}Workflow(ctx);
        workflow.define();
        ctx.registerWorkflow(workflow.getName(), workflow);
    }}
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

package {package_name};

import aetheros.sdk.ExtensionContext;
import aetheros.sdk.ThemeConfig;
import java.util.Map;
import java.util.HashMap;

/**
 * Plugin entry point
 */
class Plugin implements aetheros.sdk.Plugin {{
    private final ExtensionContext ctx;

    Plugin(ExtensionContext ctx) {{
        this.ctx = ctx;
    }}

    @Override
    public String getName() {{
        return "{theme_name}";
    }}

    @Override
    public void register() {{
        ThemeConfig config = new ThemeConfig.Builder()
            .name("{theme_name}")
            .description("{description}")
            .author("{author}")
            .version("{version}")
            .colors(Map.of(
                "primary", "#007ACC",
                "secondary", "#1E1E1E",
                "background", "#FFFFFF",
                "surface", "#F5F5F5",
                "text", "#000000",
                "textSecondary", "#666666",
                "border", "#E0E0E0",
                "success", "#4CAF50",
                "warning", "#FF9800",
                "error", "#F44336"
            ))
            .fonts(Map.of(
                "primary", "Inter, sans-serif",
                "mono", "JetBrains Mono, monospace"
            ))
            .spacing(Map.of(
                "unit", 4,
                "radius", 8
            ))
            .animations(Map.of(
                "duration", "0.2s",
                "easing", "ease-in-out"
            ))
            .build();

        ctx.registerTheme(config.getName(), config);
    }}
}}
'''


class JavaSDK(BaseSDK):
    """Java SDK for AetherOS extensions."""

    @property
    def language(self) -> SDKLanguage:
        return SDKLanguage.JAVA

    def init_project(self, name: str, directory: Optional[Path] = None) -> SDKProject:
        """Initialize a new Java extension project."""
        if directory is None:
            directory = Path.cwd() / name
        directory.mkdir(parents=True, exist_ok=True)

        # Create project structure
        (directory / "src" / "main" / "java").mkdir(parents=True, exist_ok=True)
        (directory / "src" / "test" / "java").mkdir(parents=True, exist_ok=True)

        # Create pom.xml
        pom_xml = self._generate_pom_xml(name)
        (directory / "pom.xml").write_text(pom_xml, encoding="utf-8")

        # Create Main.java
        package_name = name.replace("-", "_")
        main_content = f'''package {package_name};

/**
 * AetherOS Extension: {name}
 */
public class Main {{
    public static void main(String[] args) {{
        System.out.println("AetherOS Extension: {name}");
    }}
}}
'''
        (directory / "src" / "main" / "java" / f"{package_name}" / "Main.java").write_text(
            main_content, encoding="utf-8"
        )

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
        """Build the Java extension project."""
        try:
            import subprocess
            result = subprocess.run(
                ["mvn", "compile"],
                cwd=str(project.directory),
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except Exception as exc:
            logger.error("Build failed: %s", exc)
            return False

    def test_project(self, project: SDKProject) -> Dict[str, Any]:
        """Run tests for the Java extension project."""
        try:
            import subprocess
            result = subprocess.run(
                ["mvn", "test"],
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
        """Package the Java extension for distribution."""
        try:
            import subprocess
            result = subprocess.run(
                ["mvn", "package"],
                cwd=str(project.directory),
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                target_dir = project.directory / "target"
                if target_dir.exists():
                    jars = list(target_dir.glob("*.jar"))
                    if jars:
                        return jars[0]
            return None
        except Exception as exc:
            logger.error("Package failed: %s", exc)
            return None

    def get_template(self, plugin_type: str) -> str:
        """Get a Java code template for a specific plugin type."""
        templates = {
            "tool_plugin": PLUGIN_TEMPLATE,
            "ai_agent": AGENT_TEMPLATE,
            "mcp_server": MCP_TEMPLATE,
            "workflow_plugin": WORKFLOW_TEMPLATE,
            "theme": THEME_TEMPLATE,
        }
        return templates.get(plugin_type, PLUGIN_TEMPLATE)

    def _generate_pom_xml(self, name: str) -> str:
        """Generate pom.xml content."""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>io.aetheros</groupId>
    <artifactId>{name}</artifactId>
    <version>0.1.0</version>
    <packaging>jar</packaging>

    <name>{name}</name>
    <description>AetherOS extension</description>

    <properties>
        <maven.compiler.source>17</maven.compiler.source>
        <maven.compiler.target>17</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    </properties>

    <dependencies>
        <dependency>
            <groupId>io.aetheros</groupId>
            <artifactId>aetheros-sdk</artifactId>
            <version>1.0.0</version>
        </dependency>
        <dependency>
            <groupId>com.google.code.gson</groupId>
            <artifactId>gson</artifactId>
            <version>2.10.1</version>
        </dependency>
    </dependencies>
</project>
'''
