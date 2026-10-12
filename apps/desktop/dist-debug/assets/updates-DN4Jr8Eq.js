import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { Ia as Codicon, La as Button, Ya as useStore, ao as require_jsx_runtime, bn as stopUpdatePoller, gn as checkUpdates, hn as applyUpdates, mn as $updateStatus, oo as require_react, yn as startUpdatePoller } from "./index-B_yd1pEX.js";
import { i as PageTitle, n as PageHeader, r as PageShell, t as PageDescription } from "./page-shell-DlpGsnrD.js";
//#region src/app/updates/index.tsx
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
function UpdatesView() {
	const updateState = useStore($updateStatus);
	(0, import_react.useEffect)(() => {
		startUpdatePoller();
		return () => stopUpdatePoller();
	}, []);
	const isAvailable = updateState?.supported && (updateState?.behind ?? 0) > 0;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageShell, {
		header: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(PageHeader, {
			className: "w-full",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, { children: "Updates" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageDescription, { children: "Check for updates and manage update preferences" })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
				className: "text-xs",
				onClick: () => checkUpdates(),
				size: "sm",
				variant: "outline",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
					className: "mr-1",
					name: "refresh",
					size: "0.75rem"
				}), "Check for Updates"]
			})]
		}),
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "space-y-4",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "rounded-xl border border-(--ui-stroke-tertiary) p-4",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-3",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							className: "text-(--ui-text-tertiary)",
							name: isAvailable ? "cloud-download" : "check",
							size: "1.5rem"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
							className: "text-sm font-medium",
							children: isAvailable ? "Update Available" : "AetherOS is up to date"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-0.5 text-xs text-(--ui-text-tertiary)",
							children: isAvailable ? `${updateState?.behind ?? 0} commits behind ${updateState?.branch ?? "main"}` : `Running ${updateState?.currentBranch ?? "main"} (${(updateState?.currentSha ?? "unknown").slice(0, 8)})`
						})] }),
						isAvailable && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							className: "ml-auto",
							onClick: () => applyUpdates(),
							size: "sm",
							children: "Install Update"
						})
					]
				})
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "rounded-xl border border-(--ui-stroke-tertiary) p-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
						className: "text-sm font-medium",
						children: "Update Channel"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-1 text-xs text-(--ui-text-tertiary)",
						children: "Choose your update frequency. Stable releases are recommended for most users."
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "mt-3 flex gap-2",
						children: [
							"stable",
							"beta",
							"canary"
						].map((channel) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							className: "text-xs capitalize",
							onClick: () => window.aetherosDesktop?.updates?.setBranch?.(channel),
							size: "sm",
							variant: updateState?.branch === channel ? "default" : "outline",
							children: channel
						}, channel))
					})
				]
			})]
		})
	});
}
//#endregion
export { UpdatesView };
