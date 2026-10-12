import { t as IconDeviceFloppy } from "./IconDeviceFloppy-DF2vDv8v.js";
import { Ai as translateNow, H as prettyName, La as Button, Mi as CONTROL_TEXT, Ra as cn, X as withoutKey, _a as IconExternalLink, ao as require_jsx_runtime, ca as IconLoader2, ki as useI18n, ni as Input, wa as IconChevronDown } from "./index-B_yd1pEX.js";
import { n as ListRow } from "./primitives-BsyJey4v.js";
//#region src/app/settings/credential-key-ui.tsx
var import_jsx_runtime = require_jsx_runtime();
/** Matches Advanced / config field controls (ListRow + Input). */
var CREDENTIAL_CONTROL_CLASS = cn("h-8", CONTROL_TEXT);
var isKeyVar = (key, info) => info.is_password || /(?:_API_KEY|_TOKEN|_KEY)$/.test(key);
var friendlyFieldLabel = (key, info) => info.description?.trim() || key.replace(/_/g, " ").toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
var credentialPlaceholder = (key, info, label) => isKeyVar(key, info) ? translateNow("settings.credentials.pasteLabelKey", label) : /URL$/i.test(key) ? "https://…" : translateNow("settings.credentials.optional");
function KeyField({ info, placeholder, rowProps, varKey }) {
	const { t } = useI18n();
	const { edits, onClear, onSave, saving, setEdits } = rowProps;
	const editing = edits[varKey] !== void 0;
	const draft = edits[varKey] ?? "";
	const dirty = draft.trim().length > 0;
	const busy = saving === varKey;
	const masked = info.redacted_value ?? "••••••••";
	const startEdit = () => setEdits((c) => ({
		...c,
		[varKey]: ""
	}));
	const cancel = () => setEdits((c) => withoutKey(c, varKey));
	const update = (e) => setEdits((c) => ({
		...c,
		[varKey]: e.target.value
	}));
	const keydown = (e) => {
		if (e.key === "Enter" && dirty) onSave(varKey);
		else if (e.key === "Escape" && editing) {
			e.preventDefault();
			e.stopPropagation();
			cancel();
		}
	};
	const editType = info.is_password ? "password" : "text";
	if (info.is_set && !editing) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
		className: cn(CREDENTIAL_CONTROL_CLASS, "cursor-pointer text-muted-foreground"),
		onFocus: startEdit,
		readOnly: true,
		value: masked
	});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "grid gap-1",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex items-center gap-2",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
				autoFocus: editing,
				className: cn(CREDENTIAL_CONTROL_CLASS, "min-w-0 flex-1"),
				onChange: update,
				onKeyDown: keydown,
				placeholder: placeholder ?? t.settings.credentials.pasteKey,
				type: editType,
				value: draft
			}), dirty && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
				className: "h-8 shrink-0",
				disabled: busy,
				onClick: () => void onSave(varKey),
				size: "sm",
				children: [busy ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconLoader2, { className: "animate-spin" }) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconDeviceFloppy, {}), busy ? t.settings.credentials.saving : t.common.save]
			})]
		}), editing && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex items-center gap-1 text-[0.6875rem]",
			children: [info.is_set && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
				className: "text-[0.6875rem] text-destructive hover:text-destructive",
				disabled: busy,
				onClick: () => void onClear(varKey),
				size: "inline",
				type: "button",
				variant: "text",
				children: t.settings.credentials.remove
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "text-muted-foreground",
				children: t.settings.credentials.or
			})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "text-muted-foreground",
				children: t.settings.credentials.escToCancel
			})]
		})]
	});
}
function CredentialDocsLink({ href }) {
	const { t } = useI18n();
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("a", {
		className: "inline-flex w-fit items-center gap-1 text-[length:var(--conversation-caption-font-size)] text-(--ui-text-tertiary) underline-offset-4 transition-colors hover:text-foreground hover:underline",
		href,
		onClick: (e) => e.stopPropagation(),
		rel: "noreferrer",
		target: "_blank",
		children: [t.settings.credentials.getKey, /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconExternalLink, { className: "size-3" })]
	});
}
/** One credential row — collapsible; description and docs link expand on click. */
function CredentialKeyCard({ expanded, info, label, onExpand, onToggle, placeholder, rowProps, varKey }) {
	const docsUrl = info.url?.trim();
	const description = info.description?.trim();
	const expandable = Boolean(description || docsUrl);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: cn("group/card rounded-[6px] px-2 py-1 transition-colors", expandable && "cursor-pointer", expandable && !expanded && "hover:bg-(--ui-row-hover-background)", expanded && "bg-(--ui-bg-quaternary) ring-1 ring-(--ui-stroke-secondary)"),
		onClick: expandable ? onToggle : void 0,
		onKeyDown: expandable ? (e) => {
			if (e.key === "Enter" || e.key === " ") {
				e.preventDefault();
				onToggle();
			}
		} : void 0,
		role: expandable ? "button" : void 0,
		tabIndex: expandable ? 0 : void 0,
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "grid gap-3 py-2 sm:grid-cols-[minmax(0,1fr)_minmax(15rem,22rem)] sm:items-center",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex min-w-0 items-center gap-2",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("size-2 shrink-0 rounded-full", info.is_set ? "bg-primary" : "bg-(--ui-stroke-secondary)") }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "min-w-0 truncate text-[length:var(--conversation-text-font-size)] font-medium text-foreground",
						children: label
					}),
					expandable && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconChevronDown, { className: cn("size-3.5 shrink-0 text-muted-foreground transition", expanded ? "rotate-180 opacity-100" : "opacity-0 group-hover/card:opacity-100") })
				]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "min-w-0 sm:justify-self-end",
				onClick: (e) => e.stopPropagation(),
				onFocus: () => {
					if (expandable && !expanded) onExpand();
				},
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(KeyField, {
					info,
					placeholder,
					rowProps,
					varKey
				})
			})]
		}), expandable && expanded && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "grid gap-2.5 pb-2 pl-4",
			onClick: (e) => e.stopPropagation(),
			children: [description && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-[length:var(--conversation-caption-font-size)] leading-(--conversation-caption-line-height) text-(--ui-text-tertiary)",
				children: description
			}), docsUrl && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CredentialDocsLink, { href: docsUrl })]
		})]
	});
}
/** Provider API key group — collapsible card; description, docs link, and advanced fields expand on click. */
function ProviderKeyRows({ expanded, group, onExpand, onToggle, rowProps }) {
	const { t } = useI18n();
	const docsUrl = group.docsUrl?.trim();
	const description = group.description?.trim();
	const expandable = Boolean(description || docsUrl || group.advanced.length > 0);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: cn("group/card rounded-[6px] px-2 py-1 transition-colors", expandable && "cursor-pointer", expandable && !expanded && "hover:bg-(--ui-row-hover-background)", expanded && "bg-(--ui-bg-quaternary) ring-1 ring-(--ui-stroke-secondary)"),
		onClick: expandable ? onToggle : void 0,
		onKeyDown: expandable ? (e) => {
			if (e.key === "Enter" || e.key === " ") {
				e.preventDefault();
				onToggle();
			}
		} : void 0,
		role: expandable ? "button" : void 0,
		tabIndex: expandable ? 0 : void 0,
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "grid gap-3 py-2 sm:grid-cols-[minmax(0,1fr)_minmax(15rem,22rem)] sm:items-center",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex min-w-0 items-center gap-2",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("size-2 shrink-0 rounded-full", group.hasAnySet ? "bg-primary" : "bg-(--ui-stroke-secondary)") }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "min-w-0 truncate text-[length:var(--conversation-text-font-size)] font-medium text-foreground",
						children: group.name
					}),
					expandable && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconChevronDown, { className: cn("size-3.5 shrink-0 text-muted-foreground transition", expanded ? "rotate-180 opacity-100" : "opacity-0 group-hover/card:opacity-100") })
				]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "min-w-0 sm:justify-self-end",
				onClick: (e) => e.stopPropagation(),
				onFocus: () => {
					if (expandable && !expanded) onExpand();
				},
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(KeyField, {
					info: group.primary[1],
					placeholder: t.settings.credentials.pasteLabelKey(group.name),
					rowProps,
					varKey: group.primary[0]
				})
			})]
		}), expandable && expanded && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "grid gap-2.5 pb-2 pl-4",
			onClick: (e) => e.stopPropagation(),
			children: [
				description && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-[length:var(--conversation-caption-font-size)] leading-(--conversation-caption-line-height) text-(--ui-text-tertiary)",
					children: description
				}),
				group.advanced.map(([key, info]) => {
					const fieldLabel = isKeyVar(key, info) ? prettyName(key.replace(/(?:_API_KEY|_TOKEN|_KEY)$/i, "")) : friendlyFieldLabel(key, info);
					return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
						action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(KeyField, {
							info,
							placeholder: credentialPlaceholder(key, info, fieldLabel),
							rowProps,
							varKey: key
						}),
						title: fieldLabel
					}, key);
				}),
				docsUrl && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CredentialDocsLink, { href: docsUrl })
			]
		})]
	});
}
function credentialRowLabel(varKey, info) {
	if (isKeyVar(varKey, info)) return prettyName(varKey.replace(/(?:_API_KEY|_TOKEN|_KEY)$/i, ""));
	return prettyName(varKey);
}
//#endregion
export { credentialRowLabel as a, credentialPlaceholder as i, CredentialKeyCard as n, isKeyVar as o, ProviderKeyRows as r, CREDENTIAL_CONTROL_CLASS as t };
