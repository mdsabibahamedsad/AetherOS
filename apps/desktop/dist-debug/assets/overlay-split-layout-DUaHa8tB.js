import { I as PAGE_INSET_X, Ia as Codicon, La as Button, Ra as cn, ao as require_jsx_runtime } from "./index-B_yd1pEX.js";
//#region src/app/overlays/overlay-split-layout.tsx
var import_jsx_runtime = require_jsx_runtime();
function OverlaySplitLayout({ children, className }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: cn("grid h-full min-h-0 flex-1 grid-cols-[13rem_minmax(0,1fr)] overflow-hidden bg-transparent max-[47.5rem]:grid-cols-1", className),
		children
	});
}
function OverlaySidebar({ children, className }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("aside", {
		className: cn("flex min-h-0 flex-col gap-0.5 overflow-y-auto bg-(--ui-sidebar-surface-background) px-2.5 pb-3 pt-[calc(var(--titlebar-height)+1rem)]", className),
		children
	});
}
function OverlayMain({ children, className }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("main", {
		className: cn("flex min-h-0 flex-1 flex-col overflow-hidden bg-transparent pb-3 pt-[calc(var(--titlebar-height)+1rem)]", PAGE_INSET_X, className),
		children
	});
}
function OverlayNewButton({ icon = "add", label, onClick }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
		className: "group mb-1 w-full justify-start gap-2 text-muted-foreground hover:bg-transparent hover:text-foreground",
		onClick,
		size: "sm",
		variant: "ghost",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, { name: icon }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
			className: "underline-offset-4 group-hover:underline",
			children: label
		})]
	});
}
function OverlayNavItem({ active, icon: Icon, label, nested, onClick, trailing }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
		className: cn("flex h-7 w-full items-center justify-start gap-2 rounded-md border px-2 text-left text-[length:var(--conversation-text-font-size)] font-normal transition-colors", nested ? active ? "border-transparent bg-(--chrome-action-hover) font-medium text-foreground" : "border-transparent bg-transparent text-(--ui-text-tertiary) hover:bg-(--chrome-action-hover) hover:text-foreground" : active ? "border-(--ui-stroke-tertiary) bg-(--ui-bg-tertiary) text-foreground" : "border-transparent bg-transparent text-(--ui-text-secondary) hover:bg-(--chrome-action-hover) hover:text-foreground"),
		onClick,
		type: "button",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Icon, { className: cn("shrink-0", nested ? "size-3.5" : "size-4", active ? "text-foreground/80" : "text-muted-foreground/80") }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "min-w-0 flex-1 truncate",
				children: label
			}),
			trailing
		]
	});
}
//#endregion
export { OverlaySplitLayout as a, OverlaySidebar as i, OverlayNavItem as n, OverlayNewButton as r, OverlayMain as t };
