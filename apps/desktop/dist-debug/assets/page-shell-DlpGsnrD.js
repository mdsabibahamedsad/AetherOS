import { Ra as cn, S as ScrollArea, ao as require_jsx_runtime } from "./index-B_yd1pEX.js";
//#region src/app/page-shell.tsx
var import_jsx_runtime = require_jsx_runtime();
function PageShell({ children, className, header }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: cn("flex h-full flex-col", className),
		children: [header && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "flex h-10 shrink-0 items-center border-b border-(--ui-stroke-tertiary) px-4",
			children: header
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScrollArea, {
			className: "flex-1",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "p-4",
				children
			})
		})]
	});
}
function PageHeader({ children, className }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: cn("flex items-center justify-between", className),
		children
	});
}
function PageTitle({ children }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
		className: "text-lg font-semibold tracking-tight",
		children
	});
}
function PageDescription({ children }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
		className: "mt-0.5 text-sm text-(--ui-text-tertiary)",
		children
	});
}
//#endregion
export { PageTitle as i, PageHeader as n, PageShell as r, PageDescription as t };
