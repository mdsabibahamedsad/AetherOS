import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { La as Button, P as Switch, ao as require_jsx_runtime, k as Label, oo as require_react } from "./index-B_yd1pEX.js";
import { o as SettingSection } from "./primitives-BsyJey4v.js";
//#region src/app/settings/advanced-settings.tsx
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
function AdvancedSettings() {
	const [hardwareAccel, setHardwareAccel] = (0, import_react.useState)(true);
	const [autoUpdates, setAutoUpdates] = (0, import_react.useState)(true);
	const [telemetry, setTelemetry] = (0, import_react.useState)(false);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "space-y-6",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SettingSection, {
				description: "Performance and hardware settings",
				title: "Performance",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center justify-between",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "Hardware Acceleration" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-xs text-(--ui-text-tertiary)",
						children: "Use GPU for rendering when available"
					})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
						checked: hardwareAccel,
						onCheckedChange: setHardwareAccel
					})]
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SettingSection, {
				description: "Update preferences",
				title: "Updates",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center justify-between",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "Automatic Updates" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-xs text-(--ui-text-tertiary)",
						children: "Automatically download and install updates"
					})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
						checked: autoUpdates,
						onCheckedChange: setAutoUpdates
					})]
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SettingSection, {
				description: "Privacy and data collection",
				title: "Privacy",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center justify-between",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "Telemetry" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-xs text-(--ui-text-tertiary)",
						children: "Send anonymous usage data to improve AetherOS"
					})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
						checked: telemetry,
						onCheckedChange: setTelemetry
					})]
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SettingSection, {
				description: "Data management",
				title: "Data",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex gap-2",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							className: "text-xs",
							onClick: () => {},
							size: "sm",
							variant: "outline",
							children: "Clear Cache"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							className: "text-xs",
							onClick: () => {},
							size: "sm",
							variant: "outline",
							children: "Reset All Settings"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							className: "text-xs text-destructive",
							onClick: () => {},
							size: "sm",
							variant: "outline",
							children: "Factory Reset"
						})
					]
				})
			})
		]
	});
}
//#endregion
export { AdvancedSettings };
