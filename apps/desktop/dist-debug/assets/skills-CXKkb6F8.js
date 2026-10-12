import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { t as IconDeviceFloppy } from "./IconDeviceFloppy-DF2vDv8v.js";
import { t as IconEye } from "./IconEye-sqWT6osu.js";
import { A as getToolsetConfig, B as revealEnvVar, J as setEnvVar, K as selectToolsetProvider, O as getSkills, U as runToolsetPostSetup, et as toggleSkill, j as getToolsets, l as getActionStatus, o as deleteEnvVar, tt as toggleToolset } from "./aetheros-DF_uJq_t.js";
import { Di as notify, Gt as DropdownMenuItem, H as prettyName, Hi as IconTrash, I as PAGE_INSET_X, Ia as Codicon, J as toolNames, Kt as DropdownMenuSeparator, La as Button, Na as createReactComponent, O as Badge, Oi as notifyError, P as Switch, R as asText, Ra as cn, Ta as IconCheck, Ut as DropdownMenu, V as includesQuery, Wi as IconTerminal2, Wt as DropdownMenuContent, Y as toolsetDisplayLabel, _a as IconExternalLink, ao as require_jsx_runtime, bt as PageLoader, ca as IconLoader2, cn as triggerHaptic, ki as useI18n, ni as Input, oo as require_react, qt as DropdownMenuTrigger, x as upsertDesktopActionTask } from "./index-B_yd1pEX.js";
import { n as TextTabMeta, t as TextTab } from "./text-tab-zHHaCEaQ.js";
import { t as useRefreshHotkey } from "./use-refresh-hotkey-CjSQqOti.js";
import { t as useRouteEnumParam } from "./use-route-enum-param-BgGOGZCn.js";
import { t as PageSearchShell } from "./page-search-shell-CWZgYH3F.js";
import { i as Pill } from "./primitives-BsyJey4v.js";
var IconEyeOff = createReactComponent("outline", "eye-off", "EyeOff", [
	["path", {
		"d": "M10.585 10.587a2 2 0 0 0 2.829 2.828",
		"key": "svg-0"
	}],
	["path", {
		"d": "M16.681 16.673a8.717 8.717 0 0 1 -4.681 1.327c-3.6 0 -6.6 -2 -9 -6c1.272 -2.12 2.712 -3.678 4.32 -4.674m2.86 -1.146a9.055 9.055 0 0 1 1.82 -.18c3.6 0 6.6 2 9 6c-.666 1.11 -1.379 2.067 -2.138 2.87",
		"key": "svg-1"
	}],
	["path", {
		"d": "M3 3l18 18",
		"key": "svg-2"
	}]
]);
//#endregion
//#region src/lib/tool-registry.ts
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var DEFAULT_TIMEOUT_MS = 12e4;
var PROFILES = {
	terminal: {
		capabilities: ["execute", "system"],
		environments: ["sandbox", "workspace"],
		risk: "high",
		timeoutMs: DEFAULT_TIMEOUT_MS
	},
	execute_code: {
		capabilities: ["execute"],
		environments: ["sandbox"],
		risk: "high",
		timeoutMs: DEFAULT_TIMEOUT_MS
	},
	filesystem: {
		capabilities: ["read", "write"],
		environments: ["workspace"],
		risk: "medium",
		timeoutMs: 3e4
	},
	file: {
		capabilities: ["read", "write"],
		environments: ["workspace"],
		risk: "medium",
		timeoutMs: 3e4
	},
	browser: {
		capabilities: [
			"browser",
			"network",
			"read"
		],
		environments: ["sandbox"],
		risk: "medium",
		timeoutMs: DEFAULT_TIMEOUT_MS
	},
	web: {
		capabilities: ["network", "read"],
		environments: ["sandbox"],
		risk: "low",
		timeoutMs: 6e4
	},
	search: {
		capabilities: ["network", "read"],
		environments: ["sandbox"],
		risk: "low",
		timeoutMs: 6e4
	},
	messaging: {
		capabilities: ["communicate", "network"],
		environments: ["system"],
		risk: "high",
		timeoutMs: DEFAULT_TIMEOUT_MS
	},
	automation: {
		capabilities: ["system", "execute"],
		environments: ["system"],
		risk: "medium",
		timeoutMs: DEFAULT_TIMEOUT_MS
	},
	cron: {
		capabilities: ["system"],
		environments: ["system"],
		risk: "medium",
		timeoutMs: DEFAULT_TIMEOUT_MS
	},
	memory: {
		capabilities: ["read", "write"],
		environments: ["workspace"],
		risk: "low",
		timeoutMs: 3e4
	},
	mcp: {
		capabilities: ["execute", "network"],
		environments: ["sandbox"],
		risk: "high",
		timeoutMs: DEFAULT_TIMEOUT_MS
	},
	admin: {
		capabilities: ["admin", "system"],
		environments: ["system"],
		risk: "destructive",
		timeoutMs: DEFAULT_TIMEOUT_MS
	}
};
var FALLBACK_PROFILE = {
	capabilities: [],
	environments: ["sandbox"],
	risk: "medium",
	timeoutMs: DEFAULT_TIMEOUT_MS
};
function toolsetProfile(name) {
	return PROFILES[name] ?? FALLBACK_PROFILE;
}
/** Join a live toolset with its advisory profile for capability/risk UI. */
function describeToolset(info) {
	const profile = toolsetProfile(info.name);
	return {
		capabilities: profile.capabilities,
		configured: info.configured,
		enabled: info.enabled,
		environments: profile.environments,
		label: info.label || info.name,
		name: info.name,
		risk: profile.risk,
		toolCount: Array.isArray(info.tools) ? info.tools.length : 0
	};
}
var CAPABILITY_LABEL = {
	read: "Read",
	write: "Write",
	execute: "Execute",
	network: "Network",
	browser: "Browser",
	communicate: "Communicate",
	delete: "Delete",
	system: "System",
	admin: "Admin"
};
var RISK_LABEL = {
	low: "Low risk",
	medium: "Medium risk",
	high: "High risk",
	destructive: "Destructive"
};
//#endregion
//#region src/app/settings/env-var-actions-menu.tsx
var import_jsx_runtime = require_jsx_runtime();
function EnvVarActionsMenu({ align = "end", children, clearDisabled = false, docsUrl, isRevealed = false, isSet, label, onClear, onEdit, onReveal, showReveal = true, sideOffset = 6 }) {
	const { t } = useI18n();
	const copy = t.settings.envActions;
	const hasClear = isSet && onClear;
	const hasReveal = isSet && showReveal && onReveal;
	const hasDocs = Boolean(docsUrl?.trim());
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DropdownMenu, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DropdownMenuTrigger, {
		asChild: true,
		children
	}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DropdownMenuContent, {
		align,
		"aria-label": copy.actionsFor(label),
		className: "w-44",
		sideOffset,
		children: [
			hasDocs && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DropdownMenuItem, {
				onSelect: (event) => {
					event.preventDefault();
					triggerHaptic("selection");
					window.open(docsUrl, "_blank", "noopener,noreferrer");
				},
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconExternalLink, { className: "size-3.5" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: copy.docs })]
			}),
			hasReveal && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DropdownMenuItem, {
				onSelect: () => {
					triggerHaptic("selection");
					onReveal();
				},
				children: [isRevealed ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconEyeOff, { className: "size-3.5" }) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconEye, { className: "size-3.5" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: isRevealed ? copy.hideValue : copy.revealValue })]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DropdownMenuItem, {
				onSelect: () => {
					triggerHaptic("selection");
					onEdit();
				},
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
					name: "edit",
					size: "0.875rem"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: isSet ? copy.replace : copy.set })]
			}),
			hasClear && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DropdownMenuSeparator, {}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DropdownMenuItem, {
				disabled: clearDisabled,
				onSelect: () => {
					triggerHaptic("warning");
					onClear();
				},
				variant: "destructive",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconTrash, { className: "size-3.5" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: copy.clear })]
			})] })
		]
	})] });
}
function EnvVarActionsTrigger({ className, label, ...props }) {
	const { t } = useI18n();
	const copy = t.settings.envActions;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
		"aria-label": copy.actionsFor(label),
		className: cn("text-muted-foreground hover:text-foreground", className),
		size: "icon-sm",
		title: copy.credentialActions,
		variant: "ghost",
		...props,
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
			name: "ellipsis",
			size: "0.875rem"
		})
	});
}
//#endregion
//#region src/app/settings/toolset-config-panel.tsx
function providerConfigured(provider, envState) {
	if (provider.env_vars.length === 0) return true;
	return provider.env_vars.every((ev) => envState[ev.key]);
}
function EnvVarField({ envVar, isSet, onSaved, onCleared }) {
	const { t } = useI18n();
	const copy = t.settings.toolsets;
	const [editing, setEditing] = (0, import_react.useState)(false);
	const [value, setValue] = (0, import_react.useState)("");
	const [revealed, setRevealed] = (0, import_react.useState)(null);
	const [busy, setBusy] = (0, import_react.useState)(false);
	async function handleSave() {
		if (!value) return;
		setBusy(true);
		try {
			await setEnvVar(envVar.key, value);
			setEditing(false);
			setValue("");
			onSaved(envVar.key);
			notify({
				kind: "success",
				title: copy.savedTitle,
				message: copy.savedMessage(envVar.key)
			});
		} catch (err) {
			notifyError(err, copy.failedSave(envVar.key));
		} finally {
			setBusy(false);
		}
	}
	async function handleClear() {
		if (!window.confirm(copy.removeConfirm(envVar.key))) return;
		setBusy(true);
		try {
			await deleteEnvVar(envVar.key);
			setRevealed(null);
			onCleared(envVar.key);
			notify({
				kind: "success",
				title: copy.removedTitle,
				message: copy.removedMessage(envVar.key)
			});
		} catch (err) {
			notifyError(err, copy.failedRemove(envVar.key));
		} finally {
			setBusy(false);
		}
	}
	async function handleReveal() {
		if (revealed !== null) {
			setRevealed(null);
			return;
		}
		try {
			setRevealed((await revealEnvVar(envVar.key)).value);
		} catch (err) {
			notifyError(err, copy.failedReveal(envVar.key));
		}
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "grid gap-2 rounded-lg bg-background/55 p-2.5",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-wrap items-start justify-between gap-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "min-w-0",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex flex-wrap items-center gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "font-mono text-xs font-medium",
							children: envVar.key
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Pill, {
							tone: isSet ? "primary" : "muted",
							children: [isSet && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconCheck, { className: "size-3" }), isSet ? copy.set : copy.notSet]
						})]
					}), envVar.prompt && envVar.prompt !== envVar.key && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-0.5 text-[0.7rem] text-muted-foreground",
						children: envVar.prompt
					})]
				}), !editing && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EnvVarActionsMenu, {
					clearDisabled: busy,
					docsUrl: envVar.url,
					isRevealed: revealed !== null,
					isSet,
					label: envVar.key,
					onClear: () => void handleClear(),
					onEdit: () => setEditing(true),
					onReveal: () => void handleReveal(),
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EnvVarActionsTrigger, {
						label: envVar.key,
						onClick: (event) => event.stopPropagation()
					})
				})]
			}),
			isSet && revealed !== null && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "rounded-md bg-background px-2.5 py-1.5 font-mono text-xs text-foreground",
				children: revealed || "---"
			}),
			editing && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-wrap items-center gap-2",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						autoFocus: true,
						className: "min-w-52 flex-1 font-mono",
						onChange: (e) => setValue(e.target.value),
						placeholder: envVar.prompt || envVar.key,
						type: envVar.default ? "text" : "password",
						value
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
						disabled: busy || !value,
						onClick: () => void handleSave(),
						size: "sm",
						children: [busy ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconLoader2, { className: "size-3.5 animate-spin" }) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconDeviceFloppy, {}), t.common.save]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: () => setEditing(false),
						size: "sm",
						variant: "text",
						children: t.common.cancel
					})
				]
			})
		]
	});
}
/**
* Runs a provider's post-setup install hook (npm / pip / binary) via the
* `/api/tools/toolsets/{name}/post-setup` spawn-action and tails the resulting
* log inline — the GUI equivalent of the install step `hermes tools` runs
* after you pick a backend that needs extra dependencies.
*/
function PostSetupRunner({ toolset, postSetupKey, onComplete }) {
	const { t } = useI18n();
	const copy = t.settings.toolsets;
	const [running, setRunning] = (0, import_react.useState)(false);
	const [status, setStatus] = (0, import_react.useState)(null);
	const activeRef = (0, import_react.useRef)(false);
	(0, import_react.useEffect)(() => {
		return () => {
			activeRef.current = false;
		};
	}, []);
	const run = (0, import_react.useCallback)(async () => {
		setRunning(true);
		setStatus(null);
		activeRef.current = true;
		try {
			const started = await runToolsetPostSetup(toolset, postSetupKey);
			if (!started.ok) {
				notifyError(/* @__PURE__ */ new Error("spawn failed"), copy.postSetupFailed(postSetupKey));
				return;
			}
			let last = null;
			for (let attempt = 0; attempt < 150 && activeRef.current; attempt += 1) {
				await new Promise((resolve) => window.setTimeout(resolve, 1200));
				if (!activeRef.current) break;
				const polled = await getActionStatus(started.name, 300);
				last = polled;
				setStatus(polled);
				upsertDesktopActionTask(polled);
				if (!polled.running) break;
			}
			if (activeRef.current) {
				notify(last?.exit_code === 0 ? {
					kind: "success",
					title: copy.postSetupCompleteTitle,
					message: copy.postSetupCompleteMessage(postSetupKey)
				} : {
					kind: "error",
					title: copy.postSetupErrorTitle,
					message: copy.postSetupErrorMessage(postSetupKey)
				});
				onComplete?.();
			}
		} catch (err) {
			if (activeRef.current) notifyError(err, copy.postSetupFailed(postSetupKey));
		} finally {
			if (activeRef.current) setRunning(false);
		}
	}, [
		toolset,
		postSetupKey,
		onComplete,
		copy
	]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "grid gap-2 rounded-lg bg-background/55 p-2.5",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex flex-wrap items-center justify-between gap-2",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "min-w-0",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-[0.72rem] text-muted-foreground",
					children: copy.postSetupHint(postSetupKey)
				})
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
				disabled: running,
				onClick: () => void run(),
				size: "sm",
				children: [running ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconLoader2, { className: "size-3.5 animate-spin" }) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconTerminal2, { className: "size-3.5" }), running ? copy.postSetupRunning : copy.postSetupRun]
			})]
		}), status && (status.lines.length > 0 || status.running) && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
			className: "max-h-48 overflow-y-auto rounded-md bg-background px-2.5 py-1.5 font-mono text-[0.7rem] leading-relaxed text-muted-foreground whitespace-pre-wrap",
			children: status.lines.length > 0 ? status.lines.join("\n") : copy.postSetupStarting
		})]
	});
}
function ToolsetConfigPanel({ toolset, onConfiguredChange }) {
	const { t } = useI18n();
	const copy = t.settings.toolsets;
	const [cfg, setCfg] = (0, import_react.useState)(null);
	const [loading, setLoading] = (0, import_react.useState)(true);
	const [selecting, setSelecting] = (0, import_react.useState)(null);
	const [activeProvider, setActiveProvider] = (0, import_react.useState)(null);
	const [envState, setEnvState] = (0, import_react.useState)({});
	const refresh = (0, import_react.useCallback)(async () => {
		setLoading(true);
		try {
			const next = await getToolsetConfig(toolset);
			setCfg(next);
			const seeded = {};
			for (const provider of next.providers) for (const ev of provider.env_vars) seeded[ev.key] = ev.is_set;
			setEnvState(seeded);
		} catch (err) {
			notifyError(err, copy.failedLoad);
		} finally {
			setLoading(false);
		}
	}, [toolset]);
	(0, import_react.useEffect)(() => {
		refresh();
	}, [refresh]);
	const providers = (0, import_react.useMemo)(() => cfg?.providers ?? [], [cfg]);
	(0, import_react.useEffect)(() => {
		if (activeProvider || providers.length === 0) return;
		setActiveProvider((providers.find((p) => p.is_active) ?? (cfg?.active_provider ? providers.find((p) => p.name === cfg.active_provider) : void 0) ?? providers.find((p) => providerConfigured(p, envState)) ?? providers[0]).name);
	}, [
		activeProvider,
		providers,
		envState,
		cfg
	]);
	async function handleSelect(provider) {
		setActiveProvider(provider.name);
		setSelecting(provider.name);
		try {
			await selectToolsetProvider(toolset, provider.name);
			notify({
				kind: "success",
				title: copy.selectedTitle,
				message: copy.selectedMessage(provider.name)
			});
			onConfiguredChange?.();
		} catch (err) {
			notifyError(err, copy.failedSelect(provider.name));
		} finally {
			setSelecting(null);
		}
	}
	function patchEnv(key, isSet) {
		setEnvState((c) => ({
			...c,
			[key]: isSet
		}));
		onConfiguredChange?.();
	}
	const emptyMessage = (0, import_react.useMemo)(() => {
		if (loading || !cfg) return null;
		if (!cfg.has_category) return copy.noProviderOptions;
		if (providers.length === 0) return copy.noProviders;
		return null;
	}, [
		cfg,
		copy,
		loading,
		providers.length
	]);
	if (loading) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageLoader, {
		className: "min-h-32",
		label: copy.loadingConfig
	});
	if (emptyMessage) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
		className: "px-1 py-3 text-xs text-muted-foreground",
		children: emptyMessage
	});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "mt-3 grid gap-2",
		children: providers.map((provider) => {
			const isActive = activeProvider === provider.name;
			const configured = providerConfigured(provider, envState);
			return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "overflow-hidden rounded-xl bg-background/60",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
					"aria-pressed": isActive,
					className: cn("flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left transition hover:bg-accent/50", isActive && "bg-accent/40"),
					onClick: () => void handleSelect(provider),
					type: "button",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
						className: "flex min-w-0 items-center gap-2",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "truncate text-sm font-medium",
								children: provider.name
							}),
							provider.badge && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Pill, { children: provider.badge }),
							configured && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Pill, {
								tone: "primary",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconCheck, { className: "size-3" }), copy.ready]
							})
						]
					}), selecting === provider.name && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconLoader2, { className: "size-3.5 shrink-0 animate-spin" })]
				}), isActive && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "grid gap-2 bg-muted/20 p-3",
					children: [
						provider.tag && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-[0.72rem] text-muted-foreground",
							children: provider.tag
						}),
						provider.env_vars.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-[0.72rem] text-muted-foreground",
							children: copy.noApiKeyRequired
						}) : provider.env_vars.map((ev) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EnvVarField, {
							envVar: ev,
							isSet: Boolean(envState[ev.key]),
							onCleared: (key) => patchEnv(key, false),
							onSaved: (key) => patchEnv(key, true)
						}, ev.key)),
						provider.post_setup && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PostSetupRunner, {
							onComplete: () => void refresh(),
							postSetupKey: provider.post_setup,
							toolset
						})
					]
				})]
			}, provider.name);
		})
	});
}
//#endregion
//#region src/app/skills/index.tsx
var SKILLS_MODES = ["skills", "toolsets"];
function categoryFor(skill) {
	return asText(skill.category) || "general";
}
function filteredSkills(skills, query, category) {
	const q = query.trim().toLowerCase();
	return skills.filter((skill) => {
		if (category && categoryFor(skill) !== category) return false;
		if (!q) return true;
		return includesQuery(skill.name, q) || includesQuery(skill.description, q) || includesQuery(skill.category, q);
	}).sort((a, b) => asText(a.name).localeCompare(asText(b.name)));
}
function filteredToolsets(toolsets, query) {
	const q = query.trim().toLowerCase();
	return toolsets.filter((toolset) => {
		if (!q) return true;
		const label = toolsetDisplayLabel(toolset);
		return includesQuery(toolset.name, q) || includesQuery(label, q) || includesQuery(toolset.label, q) || includesQuery(toolset.description, q) || toolNames(toolset).some((name) => includesQuery(name, q));
	}).sort((a, b) => toolsetDisplayLabel(a).localeCompare(toolsetDisplayLabel(b)));
}
function SkillsView({ setStatusbarItemGroup: _setStatusbarItemGroup, ...props }) {
	const { t } = useI18n();
	const [mode, setMode] = useRouteEnumParam("tab", SKILLS_MODES, "skills");
	const [query, setQuery] = (0, import_react.useState)("");
	const [skills, setSkills] = (0, import_react.useState)(null);
	const [toolsets, setToolsets] = (0, import_react.useState)(null);
	const [activeCategory, setActiveCategory] = (0, import_react.useState)(null);
	const [refreshing, setRefreshing] = (0, import_react.useState)(false);
	const [savingSkill, setSavingSkill] = (0, import_react.useState)(null);
	const [savingToolset, setSavingToolset] = (0, import_react.useState)(null);
	const [expandedToolset, setExpandedToolset] = (0, import_react.useState)(null);
	const refreshCapabilities = (0, import_react.useCallback)(async () => {
		setRefreshing(true);
		try {
			const [nextSkills, nextToolsets] = await Promise.all([getSkills(), getToolsets()]);
			setSkills(nextSkills);
			setToolsets(nextToolsets);
		} catch (err) {
			notifyError(err, t.skills.skillsLoadFailed);
		} finally {
			setRefreshing(false);
		}
	}, [t]);
	const refreshToolsets = (0, import_react.useCallback)(() => {
		getToolsets().then(setToolsets).catch((err) => notifyError(err, t.skills.toolsetsRefreshFailed));
	}, [t]);
	useRefreshHotkey(refreshCapabilities);
	(0, import_react.useEffect)(() => {
		refreshCapabilities();
	}, [refreshCapabilities]);
	const categories = (0, import_react.useMemo)(() => {
		if (!skills) return [];
		const counts = /* @__PURE__ */ new Map();
		for (const skill of skills) {
			const key = categoryFor(skill);
			counts.set(key, (counts.get(key) || 0) + 1);
		}
		return Array.from(counts.entries()).sort(([a], [b]) => a.localeCompare(b)).map(([key, count]) => ({
			key,
			count
		}));
	}, [skills]);
	const visibleSkills = (0, import_react.useMemo)(() => skills ? filteredSkills(skills, query, mode === "skills" ? activeCategory : null) : [], [
		activeCategory,
		mode,
		query,
		skills
	]);
	const visibleToolsets = (0, import_react.useMemo)(() => toolsets ? filteredToolsets(toolsets, query) : [], [query, toolsets]);
	const skillGroups = (0, import_react.useMemo)(() => {
		const groups = /* @__PURE__ */ new Map();
		for (const skill of visibleSkills) {
			const key = categoryFor(skill);
			groups.set(key, [...groups.get(key) || [], skill]);
		}
		return Array.from(groups.entries()).sort(([a], [b]) => a.localeCompare(b));
	}, [visibleSkills]);
	const totalSkills = skills?.length || 0;
	const enabledToolsets = toolsets?.filter((toolset) => toolset.enabled).length || 0;
	async function handleToggleSkill(skill, enabled) {
		setSavingSkill(skill.name);
		try {
			await toggleSkill(skill.name, enabled);
			setSkills((current) => current?.map((row) => row.name === skill.name ? {
				...row,
				enabled
			} : row) ?? current);
			notify({
				kind: "success",
				title: enabled ? t.skills.skillEnabled : t.skills.skillDisabled,
				message: t.skills.appliesToNewSessions(skill.name)
			});
		} catch (err) {
			notifyError(err, t.skills.failedToUpdate(skill.name));
		} finally {
			setSavingSkill(null);
		}
	}
	async function handleToggleToolset(toolset, enabled) {
		setSavingToolset(toolset.name);
		try {
			await toggleToolset(toolset.name, enabled);
			setToolsets((current) => current?.map((row) => row.name === toolset.name ? {
				...row,
				enabled,
				available: enabled
			} : row) ?? current);
			notify({
				kind: "success",
				title: enabled ? t.skills.toolsetEnabled : t.skills.toolsetDisabled,
				message: t.skills.appliesToNewSessions(toolsetDisplayLabel(toolset))
			});
		} catch (err) {
			notifyError(err, t.skills.failedToUpdate(toolsetDisplayLabel(toolset)));
		} finally {
			setSavingToolset(null);
		}
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageSearchShell, {
		...props,
		filters: mode === "skills" && categories.length > 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(TextTab, {
			active: activeCategory === null,
			onClick: () => setActiveCategory(null),
			children: [
				t.skills.all,
				" ",
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TextTabMeta, { children: totalSkills })
			]
		}), categories.map((category) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(TextTab, {
			active: activeCategory === category.key,
			onClick: () => setActiveCategory(activeCategory === category.key ? null : category.key),
			children: [
				prettyName(category.key),
				" ",
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TextTabMeta, { children: category.count })
			]
		}, category.key))] }) : void 0,
		onSearchChange: setQuery,
		searchHidden: mode === "skills" ? (skills?.length ?? 0) === 0 : (toolsets?.length ?? 0) === 0,
		searchPlaceholder: mode === "skills" ? t.skills.searchSkills : t.skills.searchToolsets,
		searchTrailingAction: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
			"aria-label": refreshing ? t.skills.refreshing : t.skills.refresh,
			className: "text-(--ui-text-tertiary) hover:bg-transparent hover:text-foreground",
			disabled: refreshing,
			onClick: () => void refreshCapabilities(),
			size: "icon-xs",
			title: refreshing ? t.skills.refreshing : t.skills.refresh,
			type: "button",
			variant: "ghost",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
				name: "refresh",
				size: "0.875rem",
				spinning: refreshing
			})
		}),
		searchValue: query,
		tabs: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TextTab, {
			active: mode === "skills",
			onClick: () => setMode("skills"),
			children: t.skills.tabSkills
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(TextTab, {
			active: mode === "toolsets",
			onClick: () => setMode("toolsets"),
			children: t.skills.tabToolsets
		})] }),
		children: !skills || !toolsets ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageLoader, { label: t.skills.loading }) : mode === "skills" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: cn("h-full overflow-y-auto py-3", PAGE_INSET_X),
			children: visibleSkills.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
				description: t.skills.noSkillsDesc,
				title: t.skills.noSkillsTitle
			}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "space-y-4",
				children: skillGroups.map(([category, list]) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "space-y-1.5",
					children: [activeCategory === null && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-muted-foreground",
						children: prettyName(category)
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { children: list.map((skill) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "grid gap-3 px-0 py-2.5 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "min-w-0",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "truncate text-sm font-medium",
								children: skill.name
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "mt-0.5 text-xs text-muted-foreground",
								children: asText(skill.description) || t.skills.noDescription
							})]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: skill.enabled,
							disabled: savingSkill === skill.name,
							onCheckedChange: (checked) => void handleToggleSkill(skill, checked)
						})]
					}, skill.name)) })]
				}, category))
			})
		}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: cn("h-full overflow-y-auto py-3", PAGE_INSET_X),
			children: visibleToolsets.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
				description: t.skills.noToolsetsDesc,
				title: t.skills.noToolsetsTitle
			}) : /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "text-xs text-muted-foreground",
					children: t.skills.toolsetsEnabled(enabledToolsets, toolsets.length)
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { children: visibleToolsets.map((toolset) => {
					const tools = toolNames(toolset);
					const label = toolsetDisplayLabel(toolset);
					const expanded = expandedToolset === toolset.name;
					const profile = describeToolset(toolset);
					return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "px-0 py-2.5",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center justify-between gap-2",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "truncate text-sm font-medium",
									children: label
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex shrink-0 items-center gap-1.5",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
										"aria-expanded": expanded,
										"aria-label": t.skills.configureToolset(label),
										className: "cursor-pointer rounded-full outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
										onClick: () => setExpandedToolset((current) => current === toolset.name ? null : toolset.name),
										type: "button",
										children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatusPill, {
											active: toolset.configured,
											children: toolset.configured ? t.skills.configured : t.skills.needsKeys
										})
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
										"aria-label": t.skills.toggleToolset(label),
										checked: toolset.enabled,
										disabled: savingToolset === toolset.name,
										onCheckedChange: (checked) => void handleToggleToolset(toolset, checked)
									})]
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "mt-1 text-xs text-muted-foreground",
								children: asText(toolset.description) || t.skills.noDescription
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ToolsetTrustRow, {
								capabilities: profile.capabilities,
								risk: profile.risk
							}),
							tools.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "mt-2 flex flex-wrap gap-1",
								children: tools.map((name) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "rounded-md bg-(--ui-bg-quinary) px-1.5 py-0.5 font-mono text-[0.65rem] text-(--ui-text-tertiary)",
									children: name
								}, name))
							}),
							expanded && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ToolsetConfigPanel, {
								onConfiguredChange: refreshToolsets,
								toolset: toolset.name
							})
						]
					}, toolset.name);
				}) })]
			})
		})
	});
}
var RISK_TONE = {
	low: "text-muted-foreground",
	medium: "text-amber-500",
	high: "text-red-500",
	destructive: "font-semibold text-red-500"
};
function ToolsetTrustRow({ capabilities, risk }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mt-1.5 flex flex-wrap items-center gap-1.5",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
			className: cn("text-[0.65rem] font-medium", RISK_TONE[risk]),
			children: RISK_LABEL[risk]
		}), capabilities.map((cap) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
			className: "text-[0.6rem]",
			variant: "outline",
			children: CAPABILITY_LABEL[cap]
		}, cap))]
	});
}
function StatusPill({ active, children }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
		className: active ? "bg-(--ui-bg-tertiary) text-(--ui-text-secondary)" : "bg-(--ui-bg-quinary) text-(--ui-text-tertiary)",
		children
	});
}
function EmptyState({ title, description }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "grid min-h-52 place-items-center text-center",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "text-sm font-medium",
			children: title
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "mt-1 text-xs text-muted-foreground",
			children: description
		})] })
	});
}
//#endregion
export { SkillsView };
