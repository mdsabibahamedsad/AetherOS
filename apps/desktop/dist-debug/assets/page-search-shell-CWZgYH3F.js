import { Ra as cn, ao as require_jsx_runtime, vt as SearchField } from "./index-B_yd1pEX.js";
//#region src/app/page-search-shell.tsx
var import_jsx_runtime = require_jsx_runtime();
function PageSearchShell({ children, className, tabs, filters, onSearchChange, searchPlaceholder, searchTrailingAction, searchValue, searchHidden = false, ...props }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
		...props,
		className: cn("flex h-full min-w-0 flex-col overflow-hidden bg-(--ui-chat-surface-background)", className),
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "shrink-0",
			children: [(tabs || !searchHidden) && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-3 px-3 pb-2 pt-[calc(var(--titlebar-height)+0.5rem)]",
				children: [tabs ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex min-w-0 flex-1 flex-wrap items-center gap-x-2 gap-y-1",
					children: tabs
				}) : null, !searchHidden && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: cn("flex shrink-0 items-center", !tabs && "flex-1"),
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SearchField, {
						containerClassName: "max-w-[45vw]",
						onChange: onSearchChange,
						placeholder: searchPlaceholder,
						trailingAction: searchTrailingAction,
						value: searchValue
					})
				})]
			}), filters ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex flex-wrap items-center gap-x-2 gap-y-1 px-3 pb-2",
				children: filters
			}) : null]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "min-h-0 flex-1 overflow-hidden bg-(--ui-chat-surface-background)",
			children
		})]
	});
}
//#endregion
export { PageSearchShell as t };
