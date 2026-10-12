import { Ia as Codicon, La as Button, ao as require_jsx_runtime } from "./index-B_yd1pEX.js";
import { i as PageTitle, n as PageHeader, r as PageShell, t as PageDescription } from "./page-shell-DlpGsnrD.js";
//#region src/app/projects/index.tsx
var import_jsx_runtime = require_jsx_runtime();
function ProjectsView() {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageShell, {
		header: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(PageHeader, {
			className: "w-full",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, { children: "Projects" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageDescription, { children: "Manage your workspaces and projects" })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
				size: "sm",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
					className: "mr-1.5",
					name: "file-directory",
					size: "0.875rem"
				}), "Open Folder"]
			})]
		}),
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
			action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, { children: "Open Folder" }),
			description: "Open a folder to add it to your projects",
			icon: "project",
			title: "No projects yet"
		})
	});
}
function EmptyState({ icon, title, description, action }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-col items-center justify-center py-16 text-center",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
				className: "mb-3 text-(--ui-text-tertiary)",
				name: icon,
				size: "2rem"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
				className: "text-sm font-medium",
				children: title
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-1 text-xs text-(--ui-text-tertiary)",
				children: description
			}),
			action && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "mt-4",
				children: action
			})
		]
	});
}
//#endregion
export { EmptyState, ProjectsView };
