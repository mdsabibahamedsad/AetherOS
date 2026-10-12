import { Ia as Codicon, Ra as cn, ao as require_jsx_runtime } from "./index-B_yd1pEX.js";
//#region src/components/ui/empty-state.tsx
var import_jsx_runtime = require_jsx_runtime();
function EmptyState({ action, children, className, description, icon, title }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: cn("grid place-items-center px-4 py-8 text-center", className),
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
			icon && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
				className: "mx-auto mb-2 text-muted-foreground/40",
				name: icon,
				size: "2rem"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "text-sm font-medium text-muted-foreground",
				children: title
			}),
			description && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "mx-auto mt-1 max-w-sm text-xs text-muted-foreground/60",
				children: description
			}),
			children,
			action && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "mt-3",
				children: action
			})
		] })
	});
}
//#endregion
export { EmptyState as t };
