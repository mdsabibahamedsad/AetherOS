from __future__ import annotations
import json, logging, os, textwrap
from typing import Any

logger = logging.getLogger(__name__)

class ProjectGenerator:
    def __init__(self):
        self._templates = self._load_templates()

    def _load_templates(self) -> dict[str, dict[str, Any]]:
        return {
            "python-api": {"name": "Python API", "description": "A Python REST API with FastAPI", "files": {
                "README.md": "# {name}\n\n{description}\n", "requirements.txt": "fastapi\nuvicorn[standard]\npydantic\n", "main.py": "from fastapi import FastAPI\n\napp = FastAPI(title=\"{name}\")\n\n@app.get(\"/\")\nasync def root():\n    return {\"message\": \"Hello from {name}\"}\n\n@app.get(\"/health\")\nasync def health():\n    return {\"status\": \"ok\"}\n", ".gitignore": "__pycache__/\n*.pyc\n.env\nvenv/\n.venv/\ndist/\n*.egg-info/\n"}},
            "react-app": {"name": "React Application", "description": "A React single-page application", "files": {
                "README.md": "# {name}\n\n{description}\n", "package.json": "{{\"name\": \"{name}\", \"version\": \"1.0.0\", \"private\": true, \"scripts\": {{\"dev\": \"vite\", \"build\": \"vite build\", \"preview\": \"vite preview\", \"test\": \"vitest run\"}}, \"dependencies\": {{\"react\": \"^19.0.0\", \"react-dom\": \"^19.0.0\"}}, \"devDependencies\": {{\"@vitejs/plugin-react\": \"^4.0.0\", \"vite\": \"^6.0.0\", \"vitest\": \"^3.0.0\"}}}}", "vite.config.ts": "import {{ defineConfig }} from 'vite'\nimport react from '@vitejs/plugin-react'\n\nexport default defineConfig({{ plugins: [react()] }})\n", "index.html": "<!DOCTYPE html>\n<html lang=\"en\">\n<head><meta charset=\"UTF-8\"/><meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\"/><title>{name}</title></head>\n<body><div id=\"root\"></div><script type=\"module\" src=\"/src/main.tsx\"></script></body>\n</html>\n", "src/main.tsx": "import React from 'react'\nimport ReactDOM from 'react-dom/client'\nimport App from './App'\n\nReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>)\n", "src/App.tsx": "function App() {{\n  return <div><h1>{name}</h1><p>{description}</p></div>\n}}\n\nexport default App\n", ".gitignore": "node_modules/\ndist/\n.env\n.DS_Store\n"}},
            "rust-cli": {"name": "Rust CLI", "description": "A Rust command-line application", "files": {
                "README.md": "# {name}\n\n{description}\n", "Cargo.toml": "[package]\nname = \"{name_lower}\"\nversion = \"0.1.0\"\nedition = \"2021\"\n\n[dependencies]\nclap = {{ version = \"4\", features = [\"derive\"] }}\n", "src/main.rs": "use clap::Parser;\n\n#[derive(Parser)]\n#[command(name = \"{name}\")]\n#[command(about = \"{description}\")]\nstruct Cli {{\n    #[arg(short, long)]\n    name: Option<String>,\n}}\n\nfn main() {{\n    let cli = Cli::parse();\n    println!(\"Hello from {name}!\");\n}}\n", ".gitignore": "target/\n*.swp\n.DS_Store\n"}},
            "typescript-library": {"name": "TypeScript Library", "description": "A TypeScript library package", "files": {
                "README.md": "# {name}\n\n{description}\n", "package.json": "{{\"name\": \"{name_lower}\", \"version\": \"1.0.0\", \"main\": \"dist/index.js\", \"types\": \"dist/index.d.ts\", \"scripts\": {{\"build\": \"tsc\", \"test\": \"vitest run\", \"lint\": \"eslint src/\"}}, \"devDependencies\": {{\"typescript\": \"^5.7.0\", \"vitest\": \"^3.0.0\"}}}}", "tsconfig.json": "{{\"compilerOptions\": {{\"target\": \"ES2022\", \"module\": \"ESNext\", \"moduleResolution\": \"bundler\", \"declaration\": true, \"outDir\": \"dist\", \"strict\": true, \"esModuleInterop\": true}}, \"include\": [\"src\"]}}", "src/index.ts": "export function greet(name: string): string {{\n  return `Hello, ${{name}}!`;\n}}\n", ".gitignore": "node_modules/\ndist/\n.DS_Store\n"}},
            "flask-app": {"name": "Flask Application", "description": "A Python Flask web application", "files": {
                "README.md": "# {name}\n\n{description}\n", "requirements.txt": "flask\n", "app.py": "from flask import Flask\n\napp = Flask(__name__)\n\n@app.route('/')\ndef home():\n    return '<h1>{name}</h1><p>{description}</p>'\n\nif __name__ == '__main__':\n    app.run(debug=True)\n", ".gitignore": "__pycache__/\n*.pyc\n.env\nvenv/\n.venv/\n"}},
            "nextjs-app": {"name": "Next.js Application", "description": "A Next.js full-stack application", "files": {
                "README.md": "# {name}\n\n{description}\n", "package.json": "{{\"name\": \"{name_lower}\", \"version\": \"0.1.0\", \"private\": true, \"scripts\": {{\"dev\": \"next dev\", \"build\": \"next build\", \"start\": \"next start\", \"lint\": \"next lint\"}}, \"dependencies\": {{\"next\": \"^15.0.0\", \"react\": \"^19.0.0\", \"react-dom\": \"^19.0.0\"}}, \"devDependencies\": {{\"@types/node\": \"^22.0.0\", \"@types/react\": \"^19.0.0\", \"typescript\": \"^5.7.0\"}}}}", "tsconfig.json": "{{\"compilerOptions\": {{\"target\": \"ES2017\", \"lib\": [\"dom\", \"dom.iterable\", \"esnext\"], \"allowJs\": true, \"skipLibCheck\": true, \"strict\": true, \"noEmit\": true, \"esModuleInterop\": true, \"module\": \"esnext\", \"moduleResolution\": \"bundler\", \"resolveJsonModule\": true, \"isolatedModules\": true, \"jsx\": \"preserve\", \"incremental\": true, \"plugins\": [{{\"name\": \"next\"}}]}}, \"include\": [\"next-env.d.ts\", \"**/*.ts\", \"**/*.tsx\", \".next/types/**/*.ts\"], \"exclude\": [\"node_modules\"]}}", "app/layout.tsx": "import type {{ Metadata }} from 'next'\n\nexport const metadata: Metadata = {{\n  title: '{name}',\n  description: '{description}',\n}}\n\nexport default function RootLayout({{children}}: {{children: React.ReactNode}}) {{\n  return (\n    <html lang=\"en\">\n      <body>{{children}}</body>\n    </html>\n  )\n}}\n", "app/page.tsx": "export default function Home() {{\n  return <div><h1>{name}</h1><p>{description}</p></div>\n}}\n", ".gitignore": "node_modules/\n.next/\n.env\n.DS_Store\n"}},
            "html-site": {"name": "HTML Website", "description": "A simple HTML/CSS/JS website", "files": {
                "README.md": "# {name}\n\n{description}\n", "index.html": "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n  <meta charset=\"UTF-8\">\n  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n  <title>{name}</title>\n  <link rel=\"stylesheet\" href=\"styles.css\">\n</head>\n<body>\n  <h1>{name}</h1>\n  <p>{description}</p>\n  <script src=\"script.js\"></script>\n</body>\n</html>\n", "styles.css": "body {{\n  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;\n  max-width: 800px;\n  margin: 0 auto;\n  padding: 2rem;\n}}\nh1 {{ color: #333; }}\n", "script.js": "console.log('{name} loaded');\n"}},
        }

    def list_templates(self) -> list[dict[str, Any]]:
        return [{"id": tid, "name": t["name"], "description": t["description"]} for tid, t in self._templates.items()]

    def get_template(self, template_id: str) -> dict[str, Any] | None:
        return self._templates.get(template_id)

    def generate_project(self, template_id: str, name: str, dest_path: str, description: str = "", params: dict[str, Any] = None) -> str:
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"Unknown template: {template_id}")
        project_dir = os.path.join(dest_path, name)
        os.makedirs(project_dir, exist_ok=True)
        ctx = {"name": name, "name_lower": name.lower().replace(" ", "-").replace("_", "-"), "description": description or template["description"], **(params or {})}
        for file_path, content in template["files"].items():
            full_path = os.path.join(project_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            rendered = content.format(**ctx)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(rendered)
        logger.info("Generated project '%s' from template '%s' at %s", name, template_id, project_dir)
        return project_dir

    def analyze_request(self, request: str) -> dict[str, Any]:
        request_lower = request.lower()
        template_matches = {"python-api": ["python", "api", "rest", "fastapi", "backend"], "react-app": ["react", "frontend", "spa", "web app", "ui"], "rust-cli": ["rust", "cli", "command line", "terminal app"], "typescript-library": ["typescript", "library", "package", "module"], "flask-app": ["flask", "web app", "python web"], "nextjs-app": ["next", "nextjs", "full stack", "ssr"], "html-site": ["html", "website", "static", "landing page"]}
        scores = {}
        for tid, keywords in template_matches.items():
            scores[tid] = sum(1 for k in keywords if k in request_lower)
        best = max(scores, key=scores.get)
        return {"template": best if scores[best] > 0 else "python-api", "confidence": scores[best] / max(1, max(scores.values()))} if max(scores.values()) > 0 else {"template": "python-api", "confidence": 0.0}
