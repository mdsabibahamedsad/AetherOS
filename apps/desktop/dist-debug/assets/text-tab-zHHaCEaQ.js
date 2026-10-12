import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { Ra as cn, ao as require_jsx_runtime, oo as require_react } from "./index-B_yd1pEX.js";
//#region src/components/ui/text-tab.tsx
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
function TextTabMeta({ className, ...props }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
		className: cn("text-[0.72em] font-normal text-(--ui-text-tertiary)", className),
		...props
	});
}
function TextTab({ active = false, children, className, type = "button", ...props }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
		className: cn("group/text-tab inline-flex h-7 items-center gap-1 bg-transparent px-1 text-[length:var(--conversation-caption-font-size)] font-medium text-(--ui-text-tertiary) transition-colors hover:bg-transparent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring disabled:pointer-events-none disabled:opacity-50", active && "text-foreground", className),
		"data-active": active,
		type,
		...props,
		children: import_react.Children.map(children, (child) => import_react.isValidElement(child) && child.type === TextTabMeta ? child : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
			className: cn("underline-offset-4 decoration-current/25", active ? "underline" : "group-hover/text-tab:underline"),
			children: child
		}))
	});
}
//#endregion
export { TextTabMeta as n, TextTab as t };
