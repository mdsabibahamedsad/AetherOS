import { I as PAGE_INSET_X, O as Badge, Ra as cn, ao as require_jsx_runtime, bt as PageLoader } from "./index-B_yd1pEX.js";
//#region src/app/settings/primitives.tsx
var import_jsx_runtime = require_jsx_runtime();
function SettingSection({ title, description, children }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "space-y-4",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
			className: "text-sm font-semibold tracking-tight text-foreground",
			children: title
		}), description && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "mt-1 text-xs text-muted-foreground",
			children: description
		})] }), children]
	});
}
function SettingsContent({ children }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("section", {
		className: "min-h-0 overflow-hidden",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: cn("h-full min-h-0 overflow-y-auto pb-20", PAGE_INSET_X),
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "mx-auto w-full max-w-4xl",
				children
			})
		})
	});
}
function Pill({ tone = "muted", children }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
		variant: tone === "primary" ? "default" : "muted",
		children
	});
}
function SectionHeading({ icon: Icon, title, meta }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mb-2.5 flex items-center gap-2 pt-2 text-[length:var(--conversation-text-font-size)] font-semibold",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Icon, { className: "size-4 text-[#00D4FF]" }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "bg-gradient-to-r from-[#0066FF] to-[#00D4FF] bg-clip-text text-transparent",
				children: title
			}),
			meta && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Pill, { children: meta })
		]
	});
}
function ListRow({ title, description, hint, action, below, wide = false }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: cn("grid gap-3 py-3 sm:grid-cols-[minmax(0,1fr)_minmax(15rem,22rem)] sm:items-center", wide && "sm:grid-cols-1 sm:items-start"),
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "min-w-0",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "text-[length:var(--conversation-text-font-size)] font-medium text-foreground",
					children: title
				}),
				description && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "mt-1 text-[length:var(--conversation-caption-font-size)] leading-(--conversation-caption-line-height) text-muted-foreground",
					children: description
				}),
				hint && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "mt-1 block font-mono text-[0.68rem] text-muted-foreground/60",
					children: hint
				}),
				below
			]
		}), action && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: cn("min-w-0", !wide && "sm:justify-self-end"),
			children: action
		})]
	});
}
function LoadingState({ label }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageLoader, { label });
}
function EmptyState({ title, description }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "grid min-h-48 place-items-center text-center",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "rounded-[16px] border border-white/5 bg-white/[0.02] p-8 backdrop-blur-sm",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "text-sm font-semibold text-foreground",
				children: title
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "mt-2 text-xs text-muted-foreground",
				children: description
			})]
		})
	});
}
//#endregion
export { SectionHeading as a, Pill as i, ListRow as n, SettingSection as o, LoadingState as r, SettingsContent as s, EmptyState as t };
