import { Ra as cn, ao as require_jsx_runtime, ut as Skeleton } from "./index-B_yd1pEX.js";
//#region src/components/ui/table.tsx
var import_jsx_runtime = require_jsx_runtime();
function Table({ children, className, loading: _loading, ...props }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("table", {
		className: cn("w-full text-sm", className),
		...props,
		children
	});
}
function TableHead({ children, className, ...props }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("thead", {
		className: cn("[&_th]:px-3 [&_th]:py-2 [&_th]:text-left [&_th]:text-xs [&_th]:font-medium [&_th]:uppercase [&_th]:tracking-wider [&_th]:text-muted-foreground", className),
		...props,
		children
	});
}
function TableBody({ children, className, ...props }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("tbody", {
		className: cn("[&_td]:border-t [&_td]:border-(--ui-stroke-tertiary) [&_td]:px-3 [&_td]:py-2", className),
		...props,
		children
	});
}
function TableRow({ children, className, ...props }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("tr", {
		className,
		...props,
		children
	});
}
function TableHeader({ children, className, ...props }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("th", {
		className,
		scope: "col",
		...props,
		children
	});
}
function TableCell({ children, className, ...props }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("td", {
		className,
		...props,
		children
	});
}
function TableSkeletonRows({ columns = 3, rows = 5 }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(import_jsx_runtime.Fragment, { children: Array.from({ length: rows }).map((_, r) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(TableRow, { children: Array.from({ length: columns }).map((_, c) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(TableCell, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Skeleton, { className: "h-4 w-full" }) }, c)) }, r)) });
}
//#endregion
export { TableHeader as a, TableHead as i, TableBody as n, TableRow as o, TableCell as r, TableSkeletonRows as s, Table as t };
