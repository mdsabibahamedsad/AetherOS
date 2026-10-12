import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { Ia as Codicon, La as Button, ao as require_jsx_runtime, oo as require_react } from "./index-B_yd1pEX.js";
import { i as PageTitle, n as PageHeader, r as PageShell, t as PageDescription } from "./page-shell-DlpGsnrD.js";
//#region src/app/logs-view/index.tsx
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
function LogsView() {
	const [logs, setLogs] = (0, import_react.useState)([]);
	const [loading, setLoading] = (0, import_react.useState)(true);
	const fetchLogs = async () => {
		setLoading(true);
		try {
			const recent = await window.aetherosDesktop?.getRecentLogs?.();
			if (recent?.lines) setLogs(recent.lines);
		} catch {}
		setLoading(false);
	};
	(0, import_react.useEffect)(() => {
		fetchLogs();
	}, []);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageShell, {
		header: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(PageHeader, {
			className: "w-full",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, { children: "Logs" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageDescription, { children: "Application and agent logs" })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
					className: "text-xs",
					onClick: () => window.aetherosDesktop?.revealLogs?.(),
					size: "sm",
					variant: "outline",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
						className: "mr-1",
						name: "folder-opened",
						size: "0.75rem"
					}), "Reveal in Finder"]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
					className: "text-xs",
					onClick: fetchLogs,
					size: "sm",
					variant: "outline",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
						className: "mr-1",
						name: "refresh",
						size: "0.75rem"
					}), "Refresh"]
				})]
			})]
		}),
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "space-y-1",
			children: loading ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "py-8 text-center text-xs text-(--ui-text-tertiary)",
				children: "Loading logs..."
			}) : logs.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "py-8 text-center text-xs text-(--ui-text-tertiary)",
				children: "No log entries"
			}) : logs.map((line, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "font-mono text-[0.625rem] leading-5 text-(--ui-text-tertiary)",
				children: line
			}, i))
		})
	});
}
//#endregion
export { LogsView };
