import { Ra as cn, ao as require_jsx_runtime } from "./index-B_yd1pEX.js";
//#region src/components/ui/segmented-control.tsx
var import_jsx_runtime = require_jsx_runtime();
/**
* Grouped one-row toggle used for small mutually-exclusive choices
* (color mode, tool-call display, usage period, etc.). Flat by design —
* no per-option borders, just a tinted track with a raised active pill.
*/
function SegmentedControl({ options, value, onChange, className }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: cn("inline-grid w-fit auto-cols-fr grid-flow-col gap-0.5 rounded-[5px] bg-(--ui-bg-tertiary) p-0.5", className),
		children: options.map(({ id, label, icon: Icon }) => {
			const active = value === id;
			return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
				"aria-pressed": active,
				className: cn("flex items-center justify-center gap-1 rounded-[3px] px-2.5 py-0.5 text-[0.6875rem] font-medium transition-colors", active ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"),
				onClick: () => onChange(id),
				type: "button",
				children: [Icon && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Icon, { className: "size-3" }), label]
			}, id);
		})
	});
}
//#endregion
export { SegmentedControl as t };
