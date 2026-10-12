import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { La as Button, P as Switch, ao as require_jsx_runtime, k as Label, oo as require_react } from "./index-B_yd1pEX.js";
import { o as SettingSection } from "./primitives-BsyJey4v.js";
//#region src/app/settings/developer-settings.tsx
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
function DeveloperSettings() {
	const [devMode, setDevMode] = (0, import_react.useState)(false);
	const [logLevel, setLogLevel] = (0, import_react.useState)("info");
	const [reactQueryDev, setReactQueryDev] = (0, import_react.useState)(false);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "space-y-6",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SettingSection, {
				description: "Enable developer features and tools",
				title: "Developer Mode",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center justify-between",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "Developer Mode" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-xs text-(--ui-text-tertiary)",
						children: "Enable developer tools and debug features"
					})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
						checked: devMode,
						onCheckedChange: setDevMode
					})]
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SettingSection, {
				description: "Control log verbosity",
				title: "Logging",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "space-y-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "Log Level" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "flex gap-2",
						children: [
							"debug",
							"info",
							"warn",
							"error"
						].map((level) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							className: "text-xs capitalize",
							onClick: () => setLogLevel(level),
							size: "sm",
							variant: logLevel === level ? "default" : "outline",
							children: level
						}, level))
					})]
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SettingSection, {
				description: "Developer diagnostics tools",
				title: "Diagnostics",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center justify-between",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "React Query Devtools" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-xs text-(--ui-text-tertiary)",
						children: "Show React Query devtools panel"
					})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
						checked: reactQueryDev,
						onCheckedChange: setReactQueryDev
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex gap-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						className: "text-xs",
						onClick: () => window.location.reload(),
						size: "sm",
						variant: "outline",
						children: "Reload Renderer"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						className: "text-xs",
						onClick: () => window.aetherosDesktop?.revealLogs?.()?.catch(() => void 0),
						size: "sm",
						variant: "outline",
						children: "Reveal Logs"
					})]
				})]
			})
		]
	});
}
//#endregion
export { DeveloperSettings };
