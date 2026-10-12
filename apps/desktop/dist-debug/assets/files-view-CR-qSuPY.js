import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { Fa as ErrorState, Jt as readDesktopDir, La as Button, S as ScrollArea, ao as require_jsx_runtime, ni as Input, oo as require_react } from "./index-B_yd1pEX.js";
import { t as Card } from "./card-CXjwIosc.js";
import { t as EmptyState } from "./empty-state-DbK8L0dQ.js";
import { a as TableHeader, i as TableHead, n as TableBody, o as TableRow, r as TableCell, s as TableSkeletonRows, t as Table } from "./table-DCnw6rtb.js";
//#region src/app/files-view/index.tsx
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
function parentOf(path) {
	const trimmed = path.replace(/[/\\]+$/, "");
	const idx = Math.max(trimmed.lastIndexOf("/"), trimmed.lastIndexOf("\\"));
	if (idx <= 0) return null;
	return trimmed.slice(0, idx);
}
function FilesView() {
	const [cwd, setCwd] = (0, import_react.useState)(null);
	const [entries, setEntries] = (0, import_react.useState)([]);
	const [searchQuery, setSearchQuery] = (0, import_react.useState)("");
	const [refreshTick, setRefreshTick] = (0, import_react.useState)(0);
	const [status, setStatus] = (0, import_react.useState)("loading");
	const [error, setError] = (0, import_react.useState)("");
	function refresh() {
		setRefreshTick((t) => t + 1);
	}
	(0, import_react.useEffect)(() => {
		let live = true;
		(async () => {
			try {
				const settings = await window.aetherosDesktop?.settings?.getDefaultProjectDir?.();
				if (!live) return;
				const root = settings?.resolvedCwd || settings?.dir;
				if (!root) {
					setStatus("unavailable");
					return;
				}
				setCwd(root);
			} catch {
				if (live) setStatus("unavailable");
			}
		})();
		return () => {
			live = false;
		};
	}, []);
	(0, import_react.useEffect)(() => {
		if (!cwd) return;
		let live = true;
		setStatus("loading");
		(async () => {
			try {
				const result = await readDesktopDir(cwd);
				if (!live) return;
				if (result.error) {
					setError(result.error);
					setStatus("error");
					return;
				}
				setEntries(result.entries);
				setStatus("ready");
			} catch (e) {
				if (!live) return;
				setError(e instanceof Error ? e.message : String(e));
				setStatus("error");
			}
		})();
		return () => {
			live = false;
		};
	}, [cwd, refreshTick]);
	const q = searchQuery.trim().toLowerCase();
	const visible = entries.filter((e) => !q || e.name.toLowerCase().includes(q));
	const parent = cwd ? parentOf(cwd) : null;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScrollArea, {
		className: "h-full",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "mx-auto max-w-7xl space-y-6 p-6",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, {
				className: "p-6",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
						className: "text-2xl font-semibold tracking-tight",
						children: "Files"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mb-6 text-sm text-(--ui-text-tertiary)",
						children: "Browse the project filesystem"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "mb-4 flex flex-col gap-3 sm:flex-row",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
							className: "flex-1 sm:w-64",
							onChange: (e) => setSearchQuery(e.target.value),
							placeholder: "Filter by name...",
							value: searchQuery
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								disabled: !parent || status === "loading",
								onClick: () => parent && setCwd(parent),
								size: "sm",
								variant: "secondary",
								children: "Up"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								disabled: status === "loading",
								onClick: refresh,
								size: "sm",
								variant: "outline",
								children: "Refresh"
							})]
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mb-3 truncate font-mono text-xs text-(--ui-text-tertiary)",
						title: cwd ?? "",
						children: cwd ?? "No directory selected"
					}),
					status === "loading" ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Table, {
						loading: true,
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TableHead, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(TableRow, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TableHeader, { children: "Name" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(TableHeader, { children: "Type" })] }) }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(TableBody, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(TableSkeletonRows, {
							columns: 2,
							rows: 8
						}) })]
					}) : status === "unavailable" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
						description: "The desktop bridge is not connected, so no directory can be listed.",
						icon: "file-directory",
						title: "Filesystem bridge unavailable"
					}) : status === "error" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ErrorState, {
						description: error || "The directory could not be read.",
						title: "Could not list directory",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							onClick: refresh,
							size: "sm",
							variant: "outline",
							children: "Retry"
						})
					}) : visible.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
						description: entries.length === 0 ? "This directory contains no entries." : "No entry names match the filter.",
						icon: "file-directory",
						title: entries.length === 0 ? "Empty directory" : "No matches"
					}) : /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Table, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TableHead, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(TableRow, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TableHeader, { children: "Name" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(TableHeader, { children: "Type" })] }) }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(TableBody, { children: visible.map((entry) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(TableRow, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TableCell, { children: entry.isDirectory ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
						className: "truncate text-left font-medium underline",
						onClick: () => setCwd(entry.path),
						type: "button",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-folder mr-2" }), entry.name]
					}) : /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
						className: "truncate",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "codicon codicon-file mr-2" }), entry.name]
					}) }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(TableCell, {
						className: "text-(--ui-text-tertiary)",
						children: entry.isDirectory ? "Folder" : "File"
					})] }, entry.path)) })] })
				]
			})
		})
	});
}
//#endregion
export { FilesView };
