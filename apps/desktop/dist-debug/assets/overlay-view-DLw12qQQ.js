import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { Ai as translateNow, Ia as Codicon, La as Button, Ra as cn, ao as require_jsx_runtime, cn as triggerHaptic, oo as require_react } from "./index-B_yd1pEX.js";
//#region src/app/overlays/overlay-view.tsx
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
function OverlayView({ children, onClose, closeLabel = translateNow("common.close"), contentClassName, headerContent, rootClassName }) {
	const closeOverlay = () => {
		triggerHaptic("close");
		onClose();
	};
	(0, import_react.useEffect)(() => {
		const onKeyDown = (event) => {
			if (event.key !== "Escape" || event.defaultPrevented) return;
			event.preventDefault();
			triggerHaptic("close");
			onClose();
		};
		window.addEventListener("keydown", onKeyDown);
		return () => window.removeEventListener("keydown", onKeyDown);
	}, [onClose]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "fixed inset-0 z-50 bg-black/22 p-3 backdrop-blur-[0.125rem] sm:p-6",
		onClick: (event) => {
			if (event.target === event.currentTarget) closeOverlay();
		},
		role: "presentation",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: cn("relative flex h-full min-h-0 flex-col overflow-hidden rounded-xl border border-(--ui-stroke-secondary) bg-(--ui-chat-surface-background) shadow-md", rootClassName),
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "pointer-events-none absolute inset-x-0 top-0 z-10 h-[calc(var(--titlebar-height)+0.1875rem)] [-webkit-app-region:drag]",
				children: [headerContent && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "pointer-events-auto absolute left-1/2 top-[calc(0.5rem+var(--titlebar-height)/2)] -translate-x-1/2 -translate-y-1/2 [-webkit-app-region:no-drag]",
					children: headerContent
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					"aria-label": closeLabel,
					className: "pointer-events-auto absolute right-3 top-[calc(0.1875rem+var(--titlebar-height)/2)] -translate-y-1/2 text-(--ui-text-tertiary) hover:bg-(--chrome-action-hover) hover:text-foreground [-webkit-app-region:no-drag]",
					onClick: closeOverlay,
					size: "icon-titlebar",
					variant: "ghost",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
						name: "close",
						size: "1rem"
					})
				})]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: cn("min-h-0 flex flex-1 flex-col", contentClassName),
				children
			})]
		})
	});
}
//#endregion
export { OverlayView as t };
