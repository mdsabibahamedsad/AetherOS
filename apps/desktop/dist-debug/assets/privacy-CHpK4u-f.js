import "./chunk-DKxDMwdo.js";
import { P as Switch, Ya as useStore, ao as require_jsx_runtime, oo as require_react } from "./index-B_yd1pEX.js";
import { a as setClipboardPermission, c as setMicrophonePermission, d as setScreenPermission, f as setShowPrivacyIndicator, i as setCameraPermission, l as setOfflineMode, o as setEncryptedStorage, r as setAskBeforeUpload, s as setFilePermission, t as $privacy, u as setProcessingMode } from "./privacy-store-BVudYRSS.js";
require_react();
var import_jsx_runtime = require_jsx_runtime();
function PrivacySettingsPanel() {
	const state = useStore($privacy);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-col gap-5",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "text-lg font-semibold",
				children: "Privacy & Security"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-sm text-(--ui-text-tertiary)",
				children: "Control how AetherOS accesses your data and devices"
			})] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
				className: "flex flex-col gap-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
						className: "text-sm font-medium text-(--ui-text-secondary)",
						children: "Processing Mode"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "Processing Location"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)",
							children: "Where voice/image data is processed"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "flex gap-1 rounded-lg bg-(--ui-bg-tertiary) p-0.5",
							children: [
								"local",
								"hybrid",
								"cloud"
							].map((mode) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								className: `rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${state.processingMode === mode ? "bg-background text-foreground shadow-xs" : "text-(--ui-text-tertiary) hover:text-foreground"}`,
								onClick: () => setProcessingMode(mode),
								type: "button",
								children: mode.charAt(0).toUpperCase() + mode.slice(1)
							}, mode))
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "Ask Before Upload"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)}",
							children: "Confirm before sending data to cloud"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: state.askBeforeUpload,
							onCheckedChange: setAskBeforeUpload
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "Offline Mode"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)}",
							children: "Process everything locally"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: state.offlineMode,
							onCheckedChange: setOfflineMode
						})]
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
				className: "flex flex-col gap-4",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
					className: "text-sm font-medium text-(--ui-text-secondary)",
					children: "Permissions"
				}), [
					{
						key: "microphone",
						label: "Microphone",
						icon: "M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"
					},
					{
						key: "camera",
						label: "Camera",
						icon: "M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
					},
					{
						key: "screen",
						label: "Screen",
						icon: "M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
					},
					{
						key: "clipboard",
						label: "Clipboard",
						icon: "M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1"
					},
					{
						key: "files",
						label: "Files",
						icon: "M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h6a2 2 0 012 2v1"
					}
				].map((perm) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center justify-between",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("svg", {
							className: "size-4 text-(--ui-text-tertiary)",
							fill: "none",
							stroke: "currentColor",
							viewBox: "0 0 24 24",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
								d: perm.icon,
								strokeLinecap: "round",
								strokeLinejoin: "round",
								strokeWidth: 1.5
							})
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: perm.label
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)",
							children: state[perm.key].state === "granted" ? "Granted" : state[perm.key].state === "denied" ? "Denied" : state[perm.key].state === "ask" ? "Ask each time" : "Not determined"
						})] })]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						className: `rounded-md px-2 py-1 text-xs font-medium ${state[perm.key].state === "granted" ? "bg-green-500/10 text-green-500" : "bg-(--ui-bg-tertiary) text-(--ui-text-tertiary)"}`,
						onClick: () => {
							const p = state[perm.key];
							(perm.key === "microphone" ? setMicrophonePermission : perm.key === "camera" ? setCameraPermission : perm.key === "screen" ? setScreenPermission : perm.key === "clipboard" ? setClipboardPermission : setFilePermission)({
								state: p.state === "granted" ? "denied" : "granted",
								lastAccess: Date.now()
							});
						},
						type: "button",
						children: state[perm.key].state === "granted" ? "Revoke" : "Grant"
					})]
				}, perm.key))]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
				className: "flex flex-col gap-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
						className: "text-sm font-medium text-(--ui-text-secondary)",
						children: "Data Management"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "Encrypted Storage"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)}",
							children: "Encrypt locally stored data"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: state.encryptedStorage,
							onCheckedChange: setEncryptedStorage
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "Privacy Indicators"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)}",
							children: "Show mic/camera/screen indicators"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: state.showPrivacyIndicator,
							onCheckedChange: setShowPrivacyIndicator
						})]
					})
				]
			})
		]
	});
}
//#endregion
export { PrivacySettingsPanel };
