import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { La as Button, P as Switch, Qa as atom, Xa as init_nanostores, Ya as useStore, ao as require_jsx_runtime, oo as require_react } from "./index-B_yd1pEX.js";
import { n as requestPermission, t as $privacy } from "./privacy-store-BVudYRSS.js";
//#region src/store/screen-understanding.ts
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
init_nanostores();
var $screenUnderstanding = /* @__PURE__ */ atom({
	captureMode: "region",
	status: "idle",
	lastCapture: null,
	captureHistory: [],
	ocrEnabled: true,
	autoAnalyze: true,
	selectedWindow: null,
	availableWindows: [],
	regionSelection: null,
	askBeforeCapture: true,
	showOverlay: false,
	overlayPosition: {
		x: 16,
		y: 16
	}
});
var patch = (u) => $screenUnderstanding.set({
	...$screenUnderstanding.get(),
	...u
});
function setCaptureMode(m) {
	patch({ captureMode: m });
}
function setCaptureStatus(s) {
	patch({ status: s });
}
function setLastCapture(c) {
	patch({ lastCapture: c });
}
function addCaptureToHistory(c) {
	patch({ captureHistory: [c, ...$screenUnderstanding.get().captureHistory].slice(0, 50) });
}
function setOcrEnabled(e) {
	patch({ ocrEnabled: e });
}
function setAutoAnalyze(a) {
	patch({ autoAnalyze: a });
}
function setAskBeforeCapture(a) {
	patch({ askBeforeCapture: a });
}
function setScreenOverlayVisible(v) {
	patch({ showOverlay: v });
}
//#endregion
//#region src/app/screen-understanding/screen-capture-panel.tsx
var import_jsx_runtime = require_jsx_runtime();
var CAPTURE_MODES = [
	{
		value: "fullscreen",
		label: "Full Screen",
		icon: "M4 4h16v16H4z"
	},
	{
		value: "window",
		label: "Window",
		icon: "M3 5h14v12H3z"
	},
	{
		value: "region",
		label: "Region",
		icon: "M5 5h6v6H5z"
	},
	{
		value: "browser-tab",
		label: "Browser Tab",
		icon: "M7 3h10v14H7z"
	}
];
function ScreenCapturePanel() {
	const state = useStore($screenUnderstanding);
	const privacy = useStore($privacy);
	const [capturing, setCapturing] = (0, import_react.useState)(false);
	const handleCapture = (0, import_react.useCallback)(async () => {
		if (privacy.requireConsentForScreen && privacy.screen.state !== "granted") {
			if (!await requestPermission("screen")) return;
		}
		setCapturing(true);
		setCaptureStatus("capturing");
		try {
			const stream = await navigator.mediaDevices.getDisplayMedia({ video: { displaySurface: state.captureMode === "window" ? "window" : state.captureMode === "browser-tab" ? "browser" : "monitor" } });
			const track = stream.getVideoTracks()[0];
			const bitmap = await new ImageCapture(track).grabFrame();
			const canvas = document.createElement("canvas");
			canvas.width = bitmap.width;
			canvas.height = bitmap.height;
			const ctx = canvas.getContext("2d");
			if (!ctx) {
				stream.getTracks().forEach((t) => t.stop());
				return;
			}
			ctx.drawImage(bitmap, 0, 0);
			const dataUrl = canvas.toDataURL("image/png");
			stream.getTracks().forEach((t) => t.stop());
			const result = {
				dataUrl,
				mode: state.captureMode,
				timestamp: Date.now(),
				windowTitle: track.label || void 0
			};
			setLastCapture(result);
			addCaptureToHistory(result);
			setCaptureStatus("done");
			setScreenOverlayVisible(true);
		} catch {
			setCaptureStatus("error");
		} finally {
			setCapturing(false);
		}
	}, [state.captureMode, privacy]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-col gap-5",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "text-lg font-semibold",
				children: "Screen Understanding"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-sm text-(--ui-text-tertiary)",
				children: "Capture and analyze screen content with AI"
			})] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
				className: "flex flex-col gap-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
						className: "text-sm font-medium text-(--ui-text-secondary)",
						children: "Capture"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "flex gap-2",
						children: CAPTURE_MODES.map((mode) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
							className: `flex flex-1 flex-col items-center gap-1.5 rounded-lg border p-3 transition-colors ${state.captureMode === mode.value ? "border-primary bg-primary/10 text-primary" : "border-(--ui-stroke-tertiary) text-(--ui-text-secondary) hover:border-(--ui-stroke-secondary)"}`,
							onClick: () => setCaptureMode(mode.value),
							type: "button",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("svg", {
								className: "size-5",
								fill: "none",
								stroke: "currentColor",
								viewBox: `0 0 24 24`,
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
									d: mode.icon,
									strokeLinecap: "round",
									strokeLinejoin: "round",
									strokeWidth: 1.5
								})
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "text-xs font-medium",
								children: mode.label
							})]
						}, mode.value))
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							disabled: capturing,
							onClick: handleCapture,
							children: capturing ? "Capturing..." : "Capture Screen"
						}), privacy.screen.state !== "granted" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "text-xs text-(--ui-text-tertiary)",
							children: "Screen permission required"
						})]
					})
				]
			}),
			state.lastCapture && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
				className: "flex flex-col gap-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
						className: "text-sm font-medium text-(--ui-text-secondary)",
						children: "Last Capture"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "overflow-hidden rounded-lg border border-(--ui-stroke-tertiary)",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("img", {
							alt: "Screen capture",
							className: "max-h-64 w-full object-contain",
							src: state.lastCapture.dataUrl
						})
					}),
					state.lastCapture.windowTitle && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
						className: "text-xs text-(--ui-text-tertiary)",
						children: ["Window: ", state.lastCapture.windowTitle]
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
				className: "flex flex-col gap-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
						className: "text-sm font-medium text-(--ui-text-secondary)",
						children: "Analysis"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "Auto-Analyze"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)}",
							children: "Analyze captures with AI automatically"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: state.autoAnalyze,
							onCheckedChange: setAutoAnalyze
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "Extract Text (OCR)"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)}",
							children: "Run OCR on captured screens"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: state.ocrEnabled,
							onCheckedChange: setOcrEnabled
						})]
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
				className: "flex flex-col gap-4",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
					className: "text-sm font-medium text-(--ui-text-secondary)",
					children: "Privacy"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center justify-between",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "text-sm font-medium",
						children: "Ask Before Capture"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "text-xs text-(--ui-text-tertiary)}",
						children: "Require confirmation before capturing"
					})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
						checked: state.askBeforeCapture,
						onCheckedChange: setAskBeforeCapture
					})]
				})]
			}),
			state.captureHistory.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
				className: "flex flex-col gap-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
					className: "text-sm font-medium text-(--ui-text-secondary)",
					children: "History"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "grid grid-cols-4 gap-2",
					children: state.captureHistory.slice(0, 8).map((capture, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						className: "overflow-hidden rounded-lg border border-(--ui-stroke-tertiary) transition-opacity hover:opacity-80",
						onClick: () => setLastCapture(capture),
						type: "button",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("img", {
							alt: `Capture ${i + 1}`,
							className: "aspect-video w-full object-cover",
							src: capture.dataUrl
						})
					}, i))
				})]
			})
		]
	});
}
//#endregion
export { ScreenCapturePanel };
