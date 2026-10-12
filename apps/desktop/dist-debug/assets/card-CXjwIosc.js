import { Ja as cva, Ra as cn, ao as require_jsx_runtime } from "./index-B_yd1pEX.js";
//#region src/components/ui/card.tsx
var import_jsx_runtime = require_jsx_runtime();
var cardVariants = cva("rounded-xl border transition-all", {
	variants: {
		variant: {
			default: "border-(--ui-stroke-tertiary) bg-(--ui-bg-tertiary)/20",
			elevated: "border-(--ui-stroke-secondary) bg-(--ui-bg-primary) shadow-sm hover:shadow-md",
			glass: "border-white/10 bg-white/5 backdrop-blur-md",
			ghost: "border-transparent bg-(--ui-bg-tertiary)/10"
		},
		padding: {
			none: "",
			sm: "p-3",
			md: "p-4",
			lg: "p-6"
		}
	},
	defaultVariants: {
		variant: "default",
		padding: "md"
	}
});
function Card({ className, variant, padding, ...props }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: cn(cardVariants({
			variant,
			padding
		}), className),
		"data-slot": "card",
		...props
	});
}
function CardHeader({ className, ...props }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: cn("mb-3 flex items-center justify-between", className),
		...props
	});
}
function CardTitle({ className, ...props }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
		className: cn("text-sm font-semibold tracking-tight", className),
		...props
	});
}
function CardDescription({ className, ...props }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
		className: cn("text-xs text-(--ui-text-tertiary)", className),
		...props
	});
}
function CardContent({ className, ...props }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: cn(className),
		...props
	});
}
//#endregion
export { CardTitle as a, CardHeader as i, CardContent as n, CardDescription as r, Card as t };
