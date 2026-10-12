import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { $ as testMessagingPlatform, B as revealEnvVar, E as getRecommendedDefaultModel, J as setEnvVar, N as listAllProfileSessions, P as listOAuthProviders, S as getMessagingPlatforms, W as saveAetherosConfig, X as setModelAssignment, Z as setSessionArchived, _ as getElevenLabsVoices, b as getGlobalModelOptions, c as deleteSession, ct as validateProviderCredential, d as getAetherosConfigDefaults, f as getAetherosConfigRecord, m as getAuxiliaryModels, o as deleteEnvVar, p as getAetherosConfigSchema, v as getEnvVars, y as getGlobalModelInfo } from "./aetheros-DF_uJq_t.js";
import { $ as CommandInput, Aa as IconAlertTriangle, B as getNested, Bn as $activeGatewayProfile, C as Select, Ca as IconChevronRight, D as SelectValue, Di as notify, E as SelectTrigger, Ei as setSessions, Fi as FIELD_LABELS, Ft as setToolViewMode, G as providerPriority, H as prettyName, Hi as IconTrash, Hn as $profiles, Ii as MODE_OPTIONS, In as useTheme, Ji as IconSettings2, K as redactedValue, Ki as IconSparkles, L as installVscodeThemeFromMarketplace, La as Button, Li as SECTIONS, Ln as isUserTheme, Mi as CONTROL_TEXT, Na as createReactComponent, Oa as IconBolt, Oi as notifyError, P as Switch, Pi as FIELD_DESCRIPTIONS, Pt as $toolViewMode, Q as Command, R as asText, Ra as cn, Ri as fieldCopyForSchemaKey, Rn as removeUserTheme, Sa as IconCircleCheck, T as SelectItem, Ta as IconCheck, U as providerGroup, Ui as IconTool, Un as normalizeProfileKey, W as providerMeta, Wi as IconTerminal2, Wn as refreshActiveProfile, X as withoutKey, Ya as useStore, Zi as IconRefresh, _a as IconExternalLink, _n as openUpdatesWindow, ao as require_jsx_runtime, at as PopoverTrigger, ba as IconCpu, bi as applyConfiguredDefaultProjectDir, ca as IconLoader2, ci as startManualLocalEndpoint, cn as triggerHaptic, da as IconKey, di as $activeSessionId, dn as $desktopVersion, dt as Sheet, et as CommandItem, fa as IconInfoCircle, fn as $updateApply, ft as SheetContent, ga as IconFileText, gn as checkUpdates, gt as SheetTrigger, ha as IconFolderOpen, ht as SheetTitle, ii as BRAND, it as PopoverContent, ja as IconAlertCircle, ji as LOCALE_META, jt as Textarea, ka as IconArchive, ki as useI18n, li as startManualOnboarding, lt as useIsMobile, ma as IconGlobe, mn as $updateStatus, mt as SheetHeader, ni as Input, oa as IconLogin, oo as require_react, pn as $updateChecking, pt as SheetDescription, q as setNested, ri as BrandMark, rt as Popover, si as $desktopOnboarding, ta as IconPalette, to as useSearchParams, tt as CommandList, ui as startManualProviderOAuth, un as sessionTitle, va as IconDownload, vn as refreshDesktopVersion, w as SelectContent, wa as IconChevronDown, xi as ensureDefaultWorkspaceCwd, ya as IconDeviceDesktop, z as enumOptionsFor, zn as resolveTheme, zt as Tip } from "./index-B_yd1pEX.js";
import { t as OverlayView } from "./overlay-view-DLw12qQQ.js";
import { t as useRouteEnumParam } from "./use-route-enum-param-BgGOGZCn.js";
import { t as SegmentedControl } from "./segmented-control-BKG2J5LJ.js";
import { a as OverlaySplitLayout, i as OverlaySidebar, n as OverlayNavItem, t as OverlayMain } from "./overlay-split-layout-DUaHa8tB.js";
import { a as SectionHeading, i as Pill, n as ListRow, r as LoadingState, s as SettingsContent, t as EmptyState } from "./primitives-BsyJey4v.js";
import { a as credentialRowLabel, i as credentialPlaceholder, n as CredentialKeyCard, o as isKeyVar, r as ProviderKeyRows } from "./credential-key-ui-CmZbeXXI.js";
var IconArchiveOff = createReactComponent("outline", "archive-off", "ArchiveOff", [
	["path", {
		"d": "M8 4h11a2 2 0 1 1 0 4h-7m-4 0h-3a2 2 0 0 1 -.826 -3.822",
		"key": "svg-0"
	}],
	["path", {
		"d": "M5 8v10a2 2 0 0 0 2 2h10a2 2 0 0 0 1.824 -1.18m.176 -3.82v-7",
		"key": "svg-1"
	}],
	["path", {
		"d": "M10 12h2",
		"key": "svg-2"
	}],
	["path", {
		"d": "M3 3l18 18",
		"key": "svg-3"
	}]
]);
var IconUpload = createReactComponent("outline", "upload", "Upload", [
	["path", {
		"d": "M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2 -2v-2",
		"key": "svg-0"
	}],
	["path", {
		"d": "M7 9l5 -5l5 5",
		"key": "svg-1"
	}],
	["path", {
		"d": "M12 4l0 12",
		"key": "svg-2"
	}]
]);
//#endregion
//#region src/app/overlays/overlay-chrome.tsx
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
function OverlayActionButton({ children, className, tone = "default", type = "button", ...props }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
		className: cn("inline-flex h-8 items-center rounded-md border px-3 text-xs font-medium transition-colors disabled:cursor-default disabled:opacity-45", tone === "default" && "border-[color-mix(in_srgb,var(--dt-border)_55%,transparent)] bg-[color-mix(in_srgb,var(--dt-card)_80%,transparent)] text-foreground hover:bg-[color-mix(in_srgb,var(--dt-muted)_46%,var(--dt-card))]", tone === "subtle" && "h-7 border-transparent px-2 text-muted-foreground hover:border-[color-mix(in_srgb,var(--dt-border)_54%,transparent)] hover:bg-[color-mix(in_srgb,var(--dt-card)_72%,transparent)] hover:text-foreground", tone === "danger" && "h-7 border-transparent px-2 text-destructive hover:border-[color-mix(in_srgb,var(--dt-destructive)_40%,transparent)] hover:bg-[color-mix(in_srgb,var(--dt-destructive)_10%,transparent)] hover:text-destructive", className),
		type,
		...props,
		children
	});
}
function OverlayIconButton({ children, className, type = "button", ...props }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(OverlayActionButton, {
		className: cn("h-7 w-7 justify-center px-0 [&_svg]:size-4", className),
		tone: "subtle",
		type,
		...props,
		children
	});
}
//#endregion
//#region src/app/settings/uninstall-section.tsx
var OPTIONS = [
	{
		mode: "gui",
		title: "Uninstall Chat GUI only",
		description: "Remove this desktop app. The Aetheros agent, your config, and chats all stay.",
		consequence: "the desktop Chat GUI (this app and its data)",
		needsAgent: false
	},
	{
		mode: "lite",
		title: "Uninstall GUI + agent, keep my data",
		description: "Remove the app and the Aetheros agent, but keep config, chats, and secrets for a future reinstall.",
		consequence: "the Chat GUI and the Aetheros agent (config, chats, and secrets are kept)",
		needsAgent: true
	},
	{
		mode: "full",
		title: "Uninstall everything",
		description: "Remove the app, the agent, and all user data — config, chats, scheduled jobs, secrets, logs.",
		consequence: "EVERYTHING — the Chat GUI, the Aetheros agent, and all of your config, chats, secrets, and logs",
		needsAgent: true
	}
];
function UninstallSection() {
	const [summary, setSummary] = (0, import_react.useState)(null);
	const [loading, setLoading] = (0, import_react.useState)(true);
	const [pending, setPending] = (0, import_react.useState)(null);
	const [running, setRunning] = (0, import_react.useState)(false);
	const [error, setError] = (0, import_react.useState)(null);
	(0, import_react.useEffect)(() => {
		let alive = true;
		const bridge = window.aetherosDesktop?.uninstall;
		if (!bridge) {
			setLoading(false);
			return;
		}
		bridge.summary().then((result) => {
			if (alive) setSummary(result);
		}).catch(() => {}).finally(() => {
			if (alive) setLoading(false);
		});
		return () => {
			alive = false;
		};
	}, []);
	const bridge = window.aetherosDesktop?.uninstall;
	if (!bridge) return null;
	const agentInstalled = summary?.agent_installed ?? false;
	const visibleOptions = OPTIONS.filter((opt) => agentInstalled || !opt.needsAgent);
	const handleConfirm = async () => {
		if (!pending) return;
		setRunning(true);
		setError(null);
		try {
			const result = await bridge.run(pending);
			if (!result.ok) {
				setError(result.message || result.error || "Uninstall could not start.");
				setRunning(false);
				setPending(null);
			}
		} catch (err) {
			setError(err instanceof Error ? err.message : String(err));
			setRunning(false);
			setPending(null);
		}
	};
	const pendingOption = OPTIONS.find((opt) => opt.mode === pending) ?? null;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto mt-8 w-full max-w-2xl",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SectionHeading, {
			icon: IconAlertTriangle,
			title: "Danger zone"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3",
			children: loading ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-2 py-2 text-sm text-muted-foreground",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconLoader2, { className: "size-3.5 animate-spin" }), "Checking what's installed…"]
			}) : pendingOption ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-sm font-medium text-destructive",
					children: "Confirm uninstall"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
					className: "mt-1 text-xs text-muted-foreground",
					children: [
						"This removes ",
						pendingOption.consequence,
						". This can't be undone."
					]
				}),
				summary?.running_app_path && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
					className: "mt-1 font-mono text-[0.68rem] text-muted-foreground/60",
					children: ["App: ", summary.running_app_path]
				}),
				error && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "mt-2 text-xs text-destructive",
					children: error
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "mt-3 flex flex-wrap items-center gap-3",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
						disabled: running,
						onClick: () => void handleConfirm(),
						size: "sm",
						variant: "destructive",
						children: [running && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconLoader2, { className: "size-3 animate-spin" }), running ? "Uninstalling…" : "Yes, uninstall"]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						disabled: running,
						onClick: () => setPending(null),
						size: "sm",
						variant: "text",
						children: "Cancel"
					})]
				})
			] }) : /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-col gap-2",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-sm font-medium",
						children: "Uninstall Aetheros"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-xs text-muted-foreground",
						children: "Choose how much to remove. The app closes to finish the job; reopen the installer any time to come back."
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "mt-1 flex flex-col gap-2",
						children: visibleOptions.map((opt) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
							className: cn("flex items-start gap-3 rounded-lg border border-border/60 bg-background/40 px-3 py-2.5 text-left transition", "hover:border-destructive/40 hover:bg-destructive/5"),
							onClick: () => {
								setError(null);
								setPending(opt.mode);
							},
							type: "button",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconTrash, { className: "mt-0.5 size-4 shrink-0 text-muted-foreground" }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
								className: "min-w-0",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "block text-sm font-medium text-foreground",
									children: opt.title
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "mt-0.5 block text-xs text-muted-foreground",
									children: opt.description
								})]
							})]
						}, opt.mode))
					})
				]
			})
		})]
	});
}
//#endregion
//#region src/app/settings/about-settings.tsx
var RELEASE_NOTES_URL = "https://github.com/aetheros/aetheros/releases";
function relativeTime(ms, a) {
	if (!ms) return a.never;
	const diff = Date.now() - ms;
	if (diff < 6e4) return a.justNow;
	if (diff < 36e5) return a.minAgo(Math.round(diff / 6e4));
	if (diff < 864e5) return a.hoursAgo(Math.round(diff / 36e5));
	return a.daysAgo(Math.round(diff / 864e5));
}
function AboutSettings() {
	const { t } = useI18n();
	const a = t.settings.about;
	const version = useStore($desktopVersion);
	const status = useStore($updateStatus);
	const apply = useStore($updateApply);
	const checking = useStore($updateChecking);
	const [justChecked, setJustChecked] = (0, import_react.useState)(false);
	(0, import_react.useEffect)(() => {
		refreshDesktopVersion();
	}, []);
	const behind = status?.behind ?? 0;
	const supported = status?.supported !== false;
	const applying = apply.applying || apply.stage === "restart";
	const handleCheck = async () => {
		setJustChecked(false);
		const next = await checkUpdates();
		setJustChecked(Boolean(next));
	};
	let statusLine;
	let statusTone = "idle";
	if (!supported) {
		statusLine = status?.message ?? a.cantUpdate;
		statusTone = "error";
	} else if (status?.error) {
		statusLine = a.cantReach;
		statusTone = "error";
	} else if (applying) {
		statusLine = a.installing;
		statusTone = "available";
	} else if (behind > 0) {
		statusLine = a.updateReady(behind);
		statusTone = "available";
	} else if (status) statusLine = a.onLatest;
	else statusLine = a.tapCheck;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SettingsContent, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-col items-center gap-4 pt-8 pb-4 text-center",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "relative",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { className: "absolute inset-0 rounded-full bg-gradient-to-r from-[#0066FF] via-[#00D4FF] to-[#9933FF] opacity-20 blur-xl" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "relative rounded-[20px] border border-white/10 bg-[rgba(11,16,32,0.8)] p-4 backdrop-blur-md",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(BrandMark, { className: "size-20" })
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "text-xl font-bold tracking-tight",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: BRAND.textGradient,
					children: a.heading
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-1 text-xs text-muted-foreground",
				children: version?.appVersion ? a.version(version.appVersion) : a.versionUnavailable
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-2 text-[10px] uppercase tracking-widest text-muted-foreground/60",
				children: "AI Operating System"
			})
		] })]
	}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto mt-4 w-full max-w-2xl",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SectionHeading, {
				icon: IconRefresh,
				title: a.updates
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: cn("rounded-[12px] border px-4 py-3 text-sm backdrop-blur-sm", statusTone === "available" && "border-[#00D4FF]/30 bg-[rgba(0,212,255,0.05)] text-foreground", statusTone === "error" && "border-destructive/35 bg-destructive/5 text-destructive", statusTone === "idle" && "border-white/5 bg-white/[0.02] text-foreground"),
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-start gap-2",
					children: [statusTone === "available" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconSparkles, { className: "mt-0.5 size-4 shrink-0 text-primary" }) : statusTone === "error" ? null : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconCircleCheck, { className: "mt-0.5 size-4 shrink-0 text-emerald-600 dark:text-emerald-400" }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "min-w-0",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "font-medium",
							children: statusLine
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
							className: "mt-1 text-xs text-muted-foreground",
							children: [a.lastChecked(relativeTime(status?.fetchedAt, a)), justChecked && !checking ? a.justNowSuffix : ""]
						})]
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "mt-3 flex flex-wrap items-center gap-4",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
							disabled: checking || applying || !supported,
							onClick: () => void handleCheck(),
							size: "sm",
							variant: "textStrong",
							children: [checking ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconLoader2, { className: "size-3 animate-spin" }) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconRefresh, { className: "size-3" }), checking ? a.checking : a.checkNow]
						}),
						behind > 0 && supported && !applying && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							onClick: () => openUpdatesWindow(),
							size: "sm",
							children: a.seeWhatsNew
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							asChild: true,
							className: "ml-auto",
							size: "sm",
							variant: "text",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("a", {
								href: RELEASE_NOTES_URL,
								onClick: (event) => {
									event.preventDefault();
									window.aetherosDesktop?.openExternal?.(RELEASE_NOTES_URL);
								},
								rel: "noreferrer",
								target: "_blank",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconExternalLink, { className: "size-3" }), a.releaseNotes]
							})
						})
					]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
				description: a.automaticUpdatesDesc,
				hint: a.branchCommit(status?.branch ?? "unknown", status?.currentSha?.slice(0, 7) ?? "unknown"),
				title: a.automaticUpdates
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(UninstallSection, {})
		]
	})] });
}
//#endregion
//#region src/components/language-switcher.tsx
function LanguageSwitcher({ className, collapsed = false, dropUp = false }) {
	const { isSavingLocale, locale, setLocale, t } = useI18n();
	const [open, setOpen] = (0, import_react.useState)(false);
	const isMobile = useIsMobile();
	const useMobileSheet = Boolean(dropUp && isMobile);
	const current = LOCALE_META[locale];
	const allLocales = Object.entries(LOCALE_META);
	const title = t.language.switchTo;
	const selectLocale = async (code) => {
		if (code === locale || isSavingLocale) {
			setOpen(false);
			return;
		}
		triggerHaptic("selection");
		try {
			await setLocale(code);
			setOpen(false);
			triggerHaptic("success");
		} catch (error) {
			notifyError(error, t.language.saveError);
		}
	};
	const trigger = /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
		"aria-expanded": open,
		"aria-label": title,
		className: cn("min-w-32 justify-between gap-2 border-(--ui-stroke-tertiary) bg-(--ui-bg-quinary) px-2.5 text-left text-muted-foreground hover:text-foreground", collapsed && "min-w-0 px-2", className),
		disabled: isSavingLocale,
		size: "sm",
		title,
		type: "button",
		variant: "outline",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
			className: "inline-flex min-w-0 items-center gap-2",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconGlobe, { className: "size-3.5 shrink-0" }), !collapsed && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "truncate",
				children: current.name
			})]
		}), !collapsed && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconChevronDown, { className: "size-3 shrink-0 opacity-70" })]
	});
	if (useMobileSheet) return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Sheet, {
		onOpenChange: setOpen,
		open,
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SheetTrigger, {
			asChild: true,
			children: trigger
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SheetContent, {
			className: "max-h-[min(28rem,80vh)] rounded-t-xl",
			side: "bottom",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SheetHeader, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SheetTitle, { children: title }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SheetDescription, { children: t.language.description })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(LanguageCommand, {
				allLocales,
				disabled: isSavingLocale,
				locale,
				noResults: t.language.noResults,
				onSelect: (code) => void selectLocale(code),
				searchPlaceholder: t.language.searchPlaceholder
			})]
		})]
	});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Popover, {
		onOpenChange: setOpen,
		open,
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PopoverTrigger, {
			asChild: true,
			children: trigger
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PopoverContent, {
			align: "end",
			className: "w-56 p-0",
			side: dropUp ? "top" : "bottom",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(LanguageCommand, {
				allLocales,
				autoFocus: true,
				disabled: isSavingLocale,
				locale,
				noResults: t.language.noResults,
				onSelect: (code) => void selectLocale(code),
				searchPlaceholder: t.language.searchPlaceholder
			})
		})]
	});
}
function LanguageCommand({ allLocales, autoFocus, disabled, locale, noResults, onSelect, searchPlaceholder }) {
	const [search, setSearch] = (0, import_react.useState)("");
	const q = search.trim().toLowerCase();
	const filtered = allLocales.filter(([code, meta]) => !q || meta.name.toLowerCase().includes(q) || meta.englishName.toLowerCase().includes(q) || code.toLowerCase().includes(q));
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Command, {
		className: "bg-transparent",
		shouldFilter: false,
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CommandInput, {
			autoFocus,
			onValueChange: setSearch,
			placeholder: searchPlaceholder,
			value: search
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CommandList, {
			className: "max-h-80 p-1",
			children: filtered.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "py-6 text-center text-sm text-muted-foreground",
				children: noResults
			}) : filtered.map(([code, meta]) => {
				const selected = code === locale;
				return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(CommandItem, {
					className: cn(selected ? "font-medium text-foreground" : "text-muted-foreground"),
					disabled,
					onSelect: () => onSelect(code),
					value: code,
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconCheck, { className: cn("size-3.5 shrink-0 text-primary", !selected && "invisible") }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "min-w-0 flex-1 truncate",
							children: meta.name
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "font-mono text-[0.65rem] uppercase text-(--ui-text-tertiary)",
							children: code
						})
					]
				}, code);
			})
		})]
	});
}
//#endregion
//#region src/app/settings/appearance-settings.tsx
function ThemePreview({ name }) {
	const t = resolveTheme(name);
	if (!t) return null;
	const c = t.colors;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "h-20 overflow-hidden rounded-xl border shadow-xs",
		style: {
			backgroundColor: c.background,
			borderColor: c.border
		},
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex h-full",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "w-12 border-r",
				style: {
					backgroundColor: c.sidebarBackground ?? c.muted,
					borderColor: c.sidebarBorder ?? c.border
				}
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-1 flex-col gap-2 p-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "h-2.5 w-16 rounded-full",
						style: { backgroundColor: c.foreground }
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "h-2 w-24 rounded-full",
						style: { backgroundColor: c.mutedForeground }
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "mt-auto flex justify-end",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "h-5 w-16 rounded-full border",
							style: {
								backgroundColor: c.userBubble ?? c.muted,
								borderColor: c.userBubbleBorder ?? c.border
							}
						})
					})
				]
			})]
		})
	});
}
function VscodeThemeInstaller() {
	const { t } = useI18n();
	const { setTheme } = useTheme();
	const a = t.settings.appearance;
	const [id, setId] = (0, import_react.useState)("");
	const [busy, setBusy] = (0, import_react.useState)(false);
	const [status, setStatus] = (0, import_react.useState)(null);
	const install = async () => {
		const trimmed = id.trim();
		if (!trimmed || busy) return;
		setBusy(true);
		setStatus(null);
		try {
			const theme = await installVscodeThemeFromMarketplace(trimmed);
			triggerHaptic("crisp");
			setTheme(theme.name);
			setStatus({
				kind: "success",
				text: a.installed(theme.label)
			});
			setId("");
		} catch (error) {
			setStatus({
				kind: "error",
				text: error instanceof Error ? error.message : a.installError
			});
		} finally {
			setBusy(false);
		}
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mt-3",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex flex-wrap items-center gap-2",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				className: "min-w-0 flex-1 rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-bg-quinary) px-3 py-1.5 font-mono text-[length:var(--conversation-caption-font-size)] outline-none placeholder:text-(--ui-text-tertiary) focus:border-(--ui-stroke-secondary)",
				disabled: busy,
				onChange: (event) => {
					setId(event.target.value);
					setStatus(null);
				},
				onKeyDown: (event) => {
					if (event.key === "Enter") install();
				},
				placeholder: a.installPlaceholder,
				spellCheck: false,
				value: id
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
				className: "inline-flex items-center gap-1.5 rounded-lg border border-(--ui-stroke-secondary) bg-(--ui-bg-tertiary) px-3 py-1.5 text-[length:var(--conversation-caption-font-size)] font-medium transition hover:bg-(--chrome-action-hover) disabled:opacity-50",
				disabled: busy || !id.trim(),
				onClick: () => void install(),
				type: "button",
				children: [busy ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconLoader2, { className: "size-3.5 animate-spin" }) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconDownload, { className: "size-3.5" }), busy ? a.installing : a.installButton]
			})]
		}), status && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: cn("mt-2 text-[length:var(--conversation-caption-font-size)] leading-(--conversation-caption-line-height)", status.kind === "error" ? "text-(--ui-red)" : "text-(--ui-text-tertiary)"),
			children: status.text
		})]
	});
}
function AppearanceSettings() {
	const { t, isSavingLocale } = useI18n();
	const { themeName, mode, availableThemes, setTheme, setMode } = useTheme();
	const toolViewMode = useStore($toolViewMode);
	const profiles = useStore($profiles);
	const activeProfileKey = normalizeProfileKey(useStore($activeGatewayProfile));
	const a = t.settings.appearance;
	const showProfileNote = profiles.length > 1;
	const activeProfileName = profiles.find((profile) => normalizeProfileKey(profile.name) === activeProfileKey)?.name ?? activeProfileKey;
	const modeOptions = MODE_OPTIONS.map(({ id, icon }) => ({
		icon,
		id,
		label: t.settings.modeOptions[id].label
	}));
	const toolOptions = [{
		id: "product",
		label: a.product
	}, {
		id: "technical",
		label: a.technical
	}];
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SettingsContent, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SectionHeading, {
			icon: IconPalette,
			title: a.title
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "max-w-2xl text-[length:var(--conversation-caption-font-size)] leading-(--conversation-caption-line-height) text-(--ui-text-tertiary)",
			children: a.intro
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mt-2 divide-y divide-(--ui-stroke-tertiary)",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
					action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(LanguageSwitcher, {}),
					description: isSavingLocale ? t.language.saving : t.language.description,
					title: t.language.label
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
					action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SegmentedControl, {
						onChange: (id) => {
							triggerHaptic("crisp");
							setMode(id);
						},
						options: modeOptions,
						value: mode
					}),
					description: a.colorModeDesc,
					title: a.colorMode
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
					below: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-3",
							children: availableThemes.map((theme) => {
								const active = themeName === theme.name;
								const removable = isUserTheme(theme.name);
								return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "group relative",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
										className: cn("w-full rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-bg-quinary) p-2 text-left transition hover:bg-(--chrome-action-hover)", active && "border-(--ui-stroke-secondary) bg-(--ui-bg-tertiary)"),
										onClick: () => {
											triggerHaptic("crisp");
											setTheme(theme.name);
										},
										type: "button",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ThemePreview, { name: theme.name }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
											className: "mt-3 flex items-start justify-between gap-3 px-1",
											children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
												className: "min-w-0",
												children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
													className: "truncate text-[length:var(--conversation-text-font-size)] font-medium",
													children: theme.label
												}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
													className: "mt-0.5 line-clamp-2 text-[length:var(--conversation-caption-font-size)] leading-(--conversation-caption-line-height) text-(--ui-text-tertiary)",
													children: theme.description
												})]
											}), active && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
												className: "mt-0.5 grid size-5 shrink-0 place-items-center rounded-full bg-primary text-primary-foreground",
												children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconCheck, { className: "size-3.5" })
											})]
										})]
									}), removable && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
										"aria-label": a.removeTheme,
										className: "absolute right-1.5 top-1.5 grid size-6 place-items-center rounded-md bg-(--ui-bg-elevated)/80 text-(--ui-text-tertiary) opacity-0 backdrop-blur-sm transition hover:text-(--ui-red) focus-visible:opacity-100 group-hover:opacity-100",
										onClick: () => {
											triggerHaptic("crisp");
											removeUserTheme(theme.name);
											if (active) setTheme(theme.name);
										},
										title: a.removeTheme,
										type: "button",
										children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconTrash, { className: "size-3.5" })
									})]
								}, theme.name);
							})
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(VscodeThemeInstaller, {}),
						showProfileNote && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-3 text-[length:var(--conversation-caption-font-size)] leading-(--conversation-caption-line-height) text-(--ui-text-tertiary)",
							children: a.themeProfileNote(activeProfileName)
						})
					] }),
					description: a.themeDesc,
					title: a.themeTitle,
					wide: true
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
					action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SegmentedControl, {
						onChange: (id) => {
							triggerHaptic("selection");
							setToolViewMode(id);
						},
						options: toolOptions,
						value: toolViewMode
					}),
					description: a.toolViewDesc,
					title: a.toolViewTitle
				})
			]
		})
	] }) });
}
//#endregion
//#region src/app/settings/model-settings.tsx
function isProviderReady(p) {
	return !!p && (p.authenticated !== false || (p.models?.length ?? 0) > 0);
}
var AUX_TASKS = [
	{ key: "vision" },
	{ key: "web_extract" },
	{ key: "compression" },
	{ key: "skills_hub" },
	{ key: "approval" },
	{ key: "mcp" },
	{ key: "title_generation" },
	{ key: "curator" }
];
var NO_PROVIDERS = [{
	name: "—",
	slug: "",
	models: []
}];
function StaleAuxWarning({ applying, onReset, slots, taskLabel }) {
	if (!slots.length) return null;
	const provider = slots[0].provider;
	const allSameProvider = slots.every((slot) => slot.provider === provider);
	const names = slots.map((slot) => taskLabel(slot.task)).join(", ");
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-wrap items-center gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-200",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconAlertTriangle, { className: "size-3.5 shrink-0" }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
				className: "grow",
				children: [
					slots.length,
					" auxiliary task",
					slots.length === 1 ? "" : "s",
					" (",
					names,
					") still run on",
					" ",
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "font-mono",
						children: allSameProvider ? provider : "other providers"
					}),
					", not your main model."
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
				disabled: applying,
				onClick: onReset,
				size: "sm",
				variant: "textStrong",
				children: "Reset all to main"
			})
		]
	});
}
function ModelSettings({ onMainModelChanged }) {
	const { t } = useI18n();
	const m = t.settings.model;
	const [loading, setLoading] = (0, import_react.useState)(true);
	const [error, setError] = (0, import_react.useState)("");
	const [mainModel, setMainModel] = (0, import_react.useState)(null);
	const [providers, setProviders] = (0, import_react.useState)([]);
	const [selectedProvider, setSelectedProvider] = (0, import_react.useState)("");
	const [selectedModel, setSelectedModel] = (0, import_react.useState)("");
	const [auxiliary, setAuxiliary] = (0, import_react.useState)(null);
	const [applying, setApplying] = (0, import_react.useState)(false);
	const [editingAuxTask, setEditingAuxTask] = (0, import_react.useState)(null);
	const [auxDraft, setAuxDraft] = (0, import_react.useState)({
		model: "",
		provider: ""
	});
	const [switchStaleAux, setSwitchStaleAux] = (0, import_react.useState)([]);
	const [apiKeyDraft, setApiKeyDraft] = (0, import_react.useState)("");
	const [activating, setActivating] = (0, import_react.useState)(false);
	const refresh = (0, import_react.useCallback)(async () => {
		setLoading(true);
		setError("");
		try {
			const [modelInfo, modelOptions, auxiliaryModels] = await Promise.all([
				getGlobalModelInfo(),
				getGlobalModelOptions(),
				getAuxiliaryModels()
			]);
			setMainModel({
				model: modelInfo.model,
				provider: modelInfo.provider
			});
			setProviders(modelOptions.providers || []);
			setSelectedProvider((prev) => prev || modelInfo.provider);
			setSelectedModel((prev) => prev || modelInfo.model);
			setAuxiliary(auxiliaryModels);
		} catch (err) {
			setError(err instanceof Error ? err.message : String(err));
		} finally {
			setLoading(false);
		}
	}, []);
	(0, import_react.useEffect)(() => {
		refresh();
	}, [refresh]);
	const providerOptions = providers.length ? providers : NO_PROVIDERS;
	const selectedProviderRow = (0, import_react.useMemo)(() => providers.find((provider) => provider.slug === selectedProvider), [providers, selectedProvider]);
	const selectedProviderModels = selectedProviderRow?.models ?? [];
	const needsSetup = !!selectedProvider && !isProviderReady(selectedProviderRow);
	const setupIsApiKey = needsSetup && selectedProviderRow?.auth_type === "api_key" && !!selectedProviderRow?.key_env;
	(0, import_react.useEffect)(() => {
		setApiKeyDraft("");
	}, [selectedProvider]);
	const auxDraftProviderModels = (0, import_react.useMemo)(() => providers.find((provider) => provider.slug === auxDraft.provider)?.models ?? [], [auxDraft.provider, providers]);
	const auxiliaryTaskLabel = (0, import_react.useCallback)((key) => m.tasks[key]?.label ?? key, [m.tasks]);
	const persistentStaleAux = (0, import_react.useMemo)(() => {
		const mainProvider = (mainModel?.provider ?? "").toLowerCase();
		if (!mainProvider || !auxiliary) return [];
		return auxiliary.tasks.filter((entry) => {
			const p = (entry.provider ?? "").toLowerCase();
			return p && p !== "auto" && p !== mainProvider;
		}).map((entry) => ({
			task: entry.task,
			provider: entry.provider,
			model: entry.model
		}));
	}, [auxiliary, mainModel]);
	const activateApiKeyProvider = (0, import_react.useCallback)(async () => {
		const keyEnv = selectedProviderRow?.key_env;
		const slug = selectedProviderRow?.slug;
		if (!keyEnv || !slug || !apiKeyDraft.trim()) return;
		setActivating(true);
		setError("");
		try {
			await setEnvVar(keyEnv, apiKeyDraft.trim());
			setApiKeyDraft("");
			let nextModel = "";
			try {
				nextModel = (await getRecommendedDefaultModel(slug)).model || "";
			} catch {
				nextModel = "";
			}
			const options = await getGlobalModelOptions();
			setProviders(options.providers || []);
			const fallbackModel = (options.providers?.find((p) => p.slug === slug))?.models?.[0] ?? "";
			setSelectedModel(nextModel || fallbackModel);
		} catch (err) {
			setError(err instanceof Error ? err.message : String(err));
		} finally {
			setActivating(false);
		}
	}, [apiKeyDraft, selectedProviderRow]);
	const startProviderSetup = (0, import_react.useCallback)(() => {
		const slug = selectedProviderRow?.slug;
		if (!slug) return;
		const lower = slug.toLowerCase();
		if (lower === "custom" || lower === "local" || lower.startsWith("custom:")) startManualLocalEndpoint();
		else startManualProviderOAuth(slug);
	}, [selectedProviderRow]);
	const applyMainModel = (0, import_react.useCallback)(async () => {
		if (!selectedProvider || !selectedModel) return;
		setApplying(true);
		setError("");
		try {
			const result = await setModelAssignment({
				model: selectedModel,
				provider: selectedProvider,
				scope: "main"
			});
			const provider = result.provider || selectedProvider;
			const model = result.model || selectedModel;
			setMainModel({
				provider,
				model
			});
			setSwitchStaleAux(result.stale_aux ?? []);
			onMainModelChanged?.(provider, model);
			await refresh();
		} catch (err) {
			setError(err instanceof Error ? err.message : String(err));
		} finally {
			setApplying(false);
		}
	}, [
		onMainModelChanged,
		refresh,
		selectedModel,
		selectedProvider
	]);
	const setAuxiliaryToMain = (0, import_react.useCallback)(async (task) => {
		if (!mainModel) return;
		setApplying(true);
		setError("");
		try {
			await setModelAssignment({
				model: mainModel.model,
				provider: mainModel.provider,
				scope: "auxiliary",
				task
			});
			await refresh();
		} catch (err) {
			setError(err instanceof Error ? err.message : String(err));
		} finally {
			setApplying(false);
		}
	}, [mainModel, refresh]);
	const applyAuxiliaryDraft = (0, import_react.useCallback)(async (task) => {
		if (!auxDraft.provider || !auxDraft.model) return;
		setApplying(true);
		setError("");
		try {
			await setModelAssignment({
				model: auxDraft.model,
				provider: auxDraft.provider,
				scope: "auxiliary",
				task
			});
			setEditingAuxTask(null);
			await refresh();
		} catch (err) {
			setError(err instanceof Error ? err.message : String(err));
		} finally {
			setApplying(false);
		}
	}, [auxDraft, refresh]);
	const beginAuxiliaryEdit = (0, import_react.useCallback)((task) => {
		const current = auxiliary?.tasks.find((entry) => entry.task === task);
		setAuxDraft({
			provider: current?.provider && current.provider !== "auto" ? current.provider : mainModel?.provider ?? "",
			model: current?.model || mainModel?.model || ""
		});
		setEditingAuxTask(task);
	}, [auxiliary, mainModel]);
	const resetAuxiliaryModels = (0, import_react.useCallback)(async () => {
		if (!mainModel) return;
		setApplying(true);
		setError("");
		try {
			await setModelAssignment({
				model: mainModel.model,
				provider: mainModel.provider,
				scope: "auxiliary",
				task: "__reset__"
			});
			setSwitchStaleAux([]);
			await refresh();
		} catch (err) {
			setError(err instanceof Error ? err.message : String(err));
		} finally {
			setApplying(false);
		}
	}, [mainModel, refresh]);
	if (loading && !mainModel) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(LoadingState, { label: m.loading });
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "grid gap-6",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mb-3 text-xs text-muted-foreground",
				children: m.appliesDesc
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-wrap items-center gap-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
					onValueChange: setSelectedProvider,
					value: selectedProvider,
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
						className: cn("min-w-40", CONTROL_TEXT),
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, { placeholder: m.provider })
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectContent, { children: providerOptions.map((provider) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
						trailing: !isProviderReady(provider) ? m.setUpHint : void 0,
						value: provider.slug || "none",
						children: provider.name
					}, provider.slug || "none")) })]
				}), needsSetup ? setupIsApiKey ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
					autoComplete: "off",
					className: cn("min-w-60 flex-1", CONTROL_TEXT),
					onChange: (event) => setApiKeyDraft(event.target.value),
					onKeyDown: (event) => {
						if (event.key === "Enter") activateApiKeyProvider();
					},
					placeholder: `Paste ${selectedProviderRow?.key_env ?? "API key"}`,
					type: "password",
					value: apiKeyDraft
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
					disabled: !apiKeyDraft.trim() || activating,
					onClick: () => void activateApiKeyProvider(),
					size: "sm",
					children: [activating && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconLoader2, { className: "size-3.5 animate-spin" }), activating ? "Activating..." : "Activate"]
				})] }) : /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
					onClick: startProviderSetup,
					size: "sm",
					variant: "textStrong",
					children: ["Set up ", selectedProviderRow?.name ?? "provider"]
				}) : /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
					onValueChange: setSelectedModel,
					value: selectedModel,
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
						className: cn("min-w-60", CONTROL_TEXT),
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, { placeholder: m.model })
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectContent, { children: (selectedProviderModels.length ? selectedProviderModels : []).map((model) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
						value: model,
						children: model
					}, model)) })]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
					disabled: !selectedProvider || !selectedModel || applying,
					onClick: () => void applyMainModel(),
					size: "sm",
					children: [applying && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconLoader2, { className: "size-3.5 animate-spin" }), applying ? m.applying : t.common.apply]
				})] })]
			}),
			needsSetup && !setupIsApiKey && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-2 text-xs text-muted-foreground",
				children: selectedProviderRow?.auth_type === "api_key" ? `${selectedProviderRow?.name} needs an API key — set it up to choose a model.` : `${selectedProviderRow?.name} signs in through your browser — AetherOS runs the flow for you.`
			}),
			error && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "mt-2 text-xs text-destructive",
				children: error
			}),
			switchStaleAux.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "mt-2",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(StaleAuxWarning, {
					applying,
					onReset: () => void resetAuxiliaryModels(),
					slots: switchStaleAux,
					taskLabel: auxiliaryTaskLabel
				})
			})
		] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mb-2.5 flex items-center justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SectionHeading, {
					icon: IconCpu,
					title: m.auxiliaryTitle
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					disabled: !mainModel || applying,
					onClick: () => void resetAuxiliaryModels(),
					size: "sm",
					variant: "textStrong",
					children: m.resetAllToMain
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mb-2 text-xs text-muted-foreground",
				children: m.auxiliaryDesc
			}),
			switchStaleAux.length === 0 && persistentStaleAux.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "mb-2.5",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(StaleAuxWarning, {
					applying,
					onReset: () => void resetAuxiliaryModels(),
					slots: persistentStaleAux,
					taskLabel: auxiliaryTaskLabel
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "grid gap-1",
				children: AUX_TASKS.map((meta) => {
					const copy = m.tasks[meta.key] ?? {
						label: meta.key,
						hint: meta.key
					};
					const current = auxiliary?.tasks.find((entry) => entry.task === meta.key);
					const isAuto = !current || !current.provider || current.provider === "auto";
					const isEditing = editingAuxTask === meta.key;
					return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
						action: !isEditing && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex shrink-0 items-center gap-1.5",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								disabled: !mainModel || applying,
								onClick: () => void setAuxiliaryToMain(meta.key),
								size: "sm",
								variant: "text",
								children: m.setToMain
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								disabled: !providers.length || applying,
								onClick: () => beginAuxiliaryEdit(meta.key),
								size: "sm",
								variant: "textStrong",
								children: m.change
							})]
						}),
						below: isEditing && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "mt-2 flex flex-wrap items-center gap-2 pt-1",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
									onValueChange: (value) => setAuxDraft((prev) => ({
										...prev,
										provider: value,
										model: ""
									})),
									value: auxDraft.provider,
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
										className: cn("min-w-32", "text-xs"),
										children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, { placeholder: m.provider })
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectContent, { children: providerOptions.map((provider) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
										value: provider.slug || "none",
										children: provider.name
									}, provider.slug || "none")) })]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
									onValueChange: (value) => setAuxDraft((prev) => ({
										...prev,
										model: value
									})),
									value: auxDraft.model,
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
										className: cn("min-w-48", "text-xs"),
										children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, { placeholder: m.model })
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectContent, { children: (auxDraftProviderModels.length ? auxDraftProviderModels : []).map((model) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
										value: model,
										children: model
									}, model)) })]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
									disabled: !auxDraft.provider || !auxDraft.model || applying,
									onClick: () => void applyAuxiliaryDraft(meta.key),
									size: "sm",
									children: applying ? m.applying : t.common.apply
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
									onClick: () => setEditingAuxTask(null),
									size: "sm",
									variant: "ghost",
									children: t.common.cancel
								})
							]
						}),
						description: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "font-mono text-[0.68rem]",
							children: isAuto ? m.autoUseMain : `${current.provider} · ${current.model || m.providerDefault}`
						}),
						title: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
							className: "flex items-baseline gap-2",
							children: [copy.label, /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Pill, { children: copy.hint })]
						})
					}, meta.key);
				})
			})
		] })]
	});
}
//#endregion
//#region src/app/settings/config-settings.tsx
function ConfigField({ schemaKey, schema, value, enumOptions, optionLabels, onChange }) {
	const { t } = useI18n();
	const c = t.settings.config;
	const label = fieldCopyForSchemaKey(t.settings.fieldLabels, schemaKey) ?? fieldCopyForSchemaKey(FIELD_LABELS, schemaKey) ?? prettyName(schemaKey.split(".").pop() ?? schemaKey);
	const normalize = (v) => v.toLowerCase().replace(/[^a-z0-9]+/g, "");
	const rawDescription = (fieldCopyForSchemaKey(t.settings.fieldDescriptions, schemaKey) ?? fieldCopyForSchemaKey(FIELD_DESCRIPTIONS, schemaKey) ?? schema.description ?? "").trim();
	const normalizedDesc = normalize(rawDescription);
	const description = rawDescription && normalizedDesc !== normalize(label) && normalizedDesc !== normalize(schemaKey) ? rawDescription : void 0;
	const row = (action, wide = false) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
		action,
		description,
		title: label,
		wide
	});
	if (schema.type === "boolean") return row(/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "flex items-center justify-end",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
			checked: Boolean(value),
			onCheckedChange: onChange
		})
	}));
	const selectOptions = enumOptions ?? (schema.type === "select" ? (schema.options ?? []).map(String) : void 0);
	if (selectOptions) return row(/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
		onValueChange: (next) => onChange(next === "__aetheros_empty__" ? "" : next),
		value: String(value ?? "") || "__aetheros_empty__",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
			className: CONTROL_TEXT,
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectContent, { children: selectOptions.map((option) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
			value: option || "__aetheros_empty__",
			children: option ? optionLabels?.[option] ?? prettyName(option) : schemaKey === "display.personality" ? c.none : c.noneParen
		}, option || "__aetheros_empty__")) })]
	}));
	if (schema.type === "number") return row(/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
		className: CONTROL_TEXT,
		onChange: (e) => {
			const raw = e.target.value;
			const n = raw === "" ? 0 : Number(raw);
			if (!Number.isNaN(n)) onChange(n);
		},
		placeholder: c.notSet,
		type: "number",
		value: value === void 0 || value === null ? "" : String(value)
	}));
	if (schema.type === "list") return row(/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
		className: CONTROL_TEXT,
		onChange: (e) => onChange(e.target.value.split(",").map((s) => s.trim()).filter(Boolean)),
		placeholder: c.commaSeparated,
		value: Array.isArray(value) ? value.join(", ") : String(value ?? "")
	}));
	if (typeof value === "object" && value !== null) return row(/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Textarea, {
		className: cn("min-h-28 resize-y bg-background font-mono", CONTROL_TEXT),
		onChange: (e) => {
			try {
				onChange(JSON.parse(e.target.value));
			} catch {}
		},
		placeholder: c.notSet,
		spellCheck: false,
		value: JSON.stringify(value, null, 2)
	}), true);
	const isLong = schema.type === "text" || String(value ?? "").length > 100;
	return row(isLong ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Textarea, {
		className: cn("min-h-24 resize-y bg-background", CONTROL_TEXT),
		onChange: (e) => onChange(e.target.value),
		placeholder: c.notSet,
		value: String(value ?? "")
	}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
		className: CONTROL_TEXT,
		onChange: (e) => onChange(e.target.value),
		placeholder: c.notSet,
		value: String(value ?? "")
	}), isLong);
}
function ConfigSettings({ activeSectionId, onConfigSaved, onMainModelChanged, importInputRef }) {
	const { t } = useI18n();
	const c = t.settings.config;
	const [config, setConfig] = (0, import_react.useState)(null);
	const [_defaults, setDefaults] = (0, import_react.useState)(null);
	const [schema, setSchema] = (0, import_react.useState)(null);
	const [elevenLabsVoiceOptions, setElevenLabsVoiceOptions] = (0, import_react.useState)(null);
	const [elevenLabsVoiceLabels, setElevenLabsVoiceLabels] = (0, import_react.useState)({});
	const saveVersionRef = (0, import_react.useRef)(0);
	const [saveVersion, setSaveVersion] = (0, import_react.useState)(0);
	(0, import_react.useEffect)(() => {
		let cancelled = false;
		Promise.all([
			getAetherosConfigRecord(),
			getAetherosConfigDefaults(),
			getAetherosConfigSchema()
		]).then(([c, d, s]) => {
			if (cancelled) return;
			setConfig(c);
			setDefaults(d);
			setSchema(s.fields);
		}).catch((err) => notifyError(err, c.failedLoad));
		return () => void (cancelled = true);
	}, []);
	(0, import_react.useEffect)(() => {
		let cancelled = false;
		getElevenLabsVoices().then((result) => {
			if (cancelled || !result.available) return;
			setElevenLabsVoiceOptions(result.voices.map((voice) => voice.voice_id));
			setElevenLabsVoiceLabels(Object.fromEntries(result.voices.map((voice) => [voice.voice_id, voice.label])));
		}).catch(() => {
			if (!cancelled) {
				setElevenLabsVoiceOptions(null);
				setElevenLabsVoiceLabels({});
			}
		});
		return () => void (cancelled = true);
	}, []);
	(0, import_react.useEffect)(() => {
		if (!config || saveVersion === 0) return;
		const v = saveVersion;
		const t = window.setTimeout(() => {
			(async () => {
				try {
					await saveAetherosConfig(config);
					if (saveVersionRef.current === v) onConfigSaved?.();
				} catch (err) {
					if (saveVersionRef.current === v) notifyError(err, c.autosaveFailed);
				}
			})();
		}, 550);
		return () => window.clearTimeout(t);
	}, [
		config,
		onConfigSaved,
		saveVersion
	]);
	const updateConfig = (next) => {
		saveVersionRef.current += 1;
		setConfig(next);
		setSaveVersion(saveVersionRef.current);
	};
	const fields = (0, import_react.useMemo)(() => {
		if (!schema) return /* @__PURE__ */ new Map();
		return new Map(SECTIONS.map((s) => [s.id, s.keys.flatMap((k) => schema[k] ? [[k, schema[k]]] : [])]));
	}, [schema]).get(activeSectionId) ?? [];
	const [searchParams, setSearchParams] = useSearchParams();
	const targetField = searchParams.get("field");
	(0, import_react.useEffect)(() => {
		if (!targetField || !config || !schema) return;
		const element = document.getElementById(`setting-field-${targetField}`);
		if (!element) return;
		element.scrollIntoView({
			behavior: "smooth",
			block: "center"
		});
		element.classList.add("setting-field-highlight");
		const timeout = window.setTimeout(() => element.classList.remove("setting-field-highlight"), 1600);
		setSearchParams((previous) => {
			const next = new URLSearchParams(previous);
			next.delete("field");
			return next;
		}, { replace: true });
		return () => window.clearTimeout(timeout);
	}, [
		config,
		schema,
		setSearchParams,
		targetField
	]);
	function handleImport(e) {
		const file = e.target.files?.[0];
		if (!file) return;
		const reader = new FileReader();
		reader.onload = () => {
			try {
				updateConfig(JSON.parse(String(reader.result)));
				notify({
					kind: "success",
					title: c.imported,
					message: t.common.saving
				});
			} catch (err) {
				notifyError(err, c.invalidJson);
			}
		};
		reader.readAsText(file);
		e.target.value = "";
	}
	if (!config || !schema) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(LoadingState, { label: c.loading });
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SettingsContent, { children: [
		activeSectionId === "model" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "mb-6",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ModelSettings, { onMainModelChanged })
		}),
		fields.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
			description: c.emptyDesc,
			title: c.emptyTitle
		}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "grid gap-1",
			children: fields.map(([key, field]) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "scroll-mt-6 rounded-lg",
				id: `setting-field-${key}`,
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ConfigField, {
					enumOptions: key === "tts.elevenlabs.voice_id" ? enumOptionsFor(key, getNested(config, key), config, elevenLabsVoiceOptions ?? void 0) : enumOptionsFor(key, getNested(config, key), config),
					onChange: (value) => updateConfig(setNested(config, key, value)),
					optionLabels: key === "tts.elevenlabs.voice_id" ? elevenLabsVoiceLabels : void 0,
					schema: field,
					schemaKey: key,
					value: getNested(config, key)
				})
			}, key))
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
			accept: ".json,application/json",
			className: "hidden",
			onChange: handleImport,
			ref: importInputRef,
			type: "file"
		})
	] });
}
//#endregion
//#region src/app/settings/gateway-settings.tsx
var EMPTY_STATE = {
	envOverride: false,
	mode: "local",
	remoteAuthMode: "token",
	remoteOauthConnected: false,
	remoteTokenPreview: null,
	remoteTokenSet: false,
	remoteUrl: ""
};
function ModeCard({ active, description, disabled, icon: Icon, onSelect, title }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
		className: cn("rounded-xl border p-3 text-left transition", active ? "border-(--ui-stroke-secondary) bg-(--ui-bg-tertiary)" : "border-(--ui-stroke-tertiary) bg-(--ui-bg-quinary) hover:bg-(--chrome-action-hover)", disabled && "cursor-not-allowed opacity-50"),
		disabled,
		onClick: onSelect,
		type: "button",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex items-center gap-2 text-[length:var(--conversation-text-font-size)] font-medium",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Icon, { className: "size-4 text-muted-foreground" }),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: title }),
				active ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconCheck, { className: "ml-auto size-4 text-primary" }) : null
			]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "mt-1.5 text-[length:var(--conversation-caption-font-size)] leading-(--conversation-caption-line-height) text-(--ui-text-tertiary)",
			children: description
		})]
	});
}
function ScopeChip({ active, label, onSelect }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
		className: cn("rounded-full border px-3 py-1 text-[length:var(--conversation-caption-font-size)] transition", active ? "border-(--ui-stroke-secondary) bg-(--ui-bg-tertiary) text-(--ui-text-primary)" : "border-(--ui-stroke-tertiary) bg-(--ui-bg-quinary) text-(--ui-text-tertiary) hover:bg-(--chrome-action-hover)"),
		onClick: onSelect,
		type: "button",
		children: label
	});
}
function GatewaySettings() {
	const { t } = useI18n();
	const g = t.settings.gateway;
	const [loading, setLoading] = (0, import_react.useState)(true);
	const [saving, setSaving] = (0, import_react.useState)(false);
	const [testing, setTesting] = (0, import_react.useState)(false);
	const [signingIn, setSigningIn] = (0, import_react.useState)(false);
	const [state, setState] = (0, import_react.useState)(EMPTY_STATE);
	const [remoteToken, setRemoteToken] = (0, import_react.useState)("");
	const [lastTest, setLastTest] = (0, import_react.useState)(null);
	const [scope, setScope] = (0, import_react.useState)(null);
	const profiles = useStore($profiles);
	(0, import_react.useEffect)(() => {
		refreshActiveProfile();
	}, []);
	const [probeStatus, setProbeStatus] = (0, import_react.useState)("idle");
	const [probe, setProbe] = (0, import_react.useState)(null);
	const probeSeq = (0, import_react.useRef)(0);
	(0, import_react.useEffect)(() => {
		let cancelled = false;
		const desktop = window.aetherosDesktop;
		if (!desktop?.getConnectionConfig) {
			setLoading(false);
			return () => void (cancelled = true);
		}
		setLoading(true);
		setRemoteToken("");
		setLastTest(null);
		desktop.getConnectionConfig(scope).then((config) => {
			if (cancelled) return;
			setState(config);
		}).catch((err) => notifyError(err, g.failedLoad)).finally(() => {
			if (!cancelled) setLoading(false);
		});
		return () => void (cancelled = true);
	}, [scope]);
	const trimmedUrl = state.remoteUrl.trim();
	(0, import_react.useEffect)(() => {
		if (state.mode !== "remote" || !trimmedUrl || !/^https?:\/\//i.test(trimmedUrl)) {
			setProbeStatus("idle");
			setProbe(null);
			return;
		}
		const desktop = window.aetherosDesktop;
		if (!desktop?.probeConnectionConfig) return;
		const seq = ++probeSeq.current;
		setProbeStatus("probing");
		const timer = setTimeout(() => {
			desktop.probeConnectionConfig(trimmedUrl).then((result) => {
				if (seq !== probeSeq.current) return;
				setProbe(result);
				setProbeStatus(result.reachable ? "done" : "error");
			}).catch(() => {
				if (seq !== probeSeq.current) return;
				setProbe(null);
				setProbeStatus("error");
			});
		}, 500);
		return () => clearTimeout(timer);
	}, [state.mode, trimmedUrl]);
	const authMode = (0, import_react.useMemo)(() => {
		if (probeStatus === "done" && probe && probe.authMode !== "unknown") return probe.authMode;
		return state.remoteAuthMode;
	}, [
		probe,
		probeStatus,
		state.remoteAuthMode
	]);
	const hasSavedRemote = state.remoteTokenSet || state.remoteOauthConnected;
	const authResolved = (0, import_react.useMemo)(() => {
		if (probeStatus === "done") return true;
		return probeStatus === "idle" && hasSavedRemote;
	}, [probeStatus, hasSavedRemote]);
	const providerLabel = (0, import_react.useMemo)(() => {
		const providers = probe?.providers ?? [];
		if (providers.length === 1) return providers[0].displayName || providers[0].name;
		if (providers.length > 1) return providers.map((p) => p.displayName || p.name).join(" / ");
		return t.boot.failure.identityProvider;
	}, [probe, t.boot.failure.identityProvider]);
	const isPasswordProvider = (0, import_react.useMemo)(() => {
		const providers = probe?.providers ?? [];
		return providers.length > 0 && providers.every((p) => p.supportsPassword);
	}, [probe]);
	const namedProfiles = (0, import_react.useMemo)(() => profiles.filter((profile) => profile.name !== "default"), [profiles]);
	const oauthConnected = state.remoteOauthConnected;
	const canUseRemote = (0, import_react.useMemo)(() => {
		if (!trimmedUrl) return false;
		if (authMode === "oauth") return oauthConnected;
		return Boolean(remoteToken.trim()) || state.remoteTokenSet;
	}, [
		authMode,
		oauthConnected,
		remoteToken,
		state.remoteTokenSet,
		trimmedUrl
	]);
	const payload = () => ({
		mode: state.mode,
		profile: scope ?? void 0,
		remoteAuthMode: authMode,
		remoteToken: authMode === "token" ? remoteToken.trim() || void 0 : void 0,
		remoteUrl: trimmedUrl
	});
	const save = async (apply) => {
		if (state.mode === "remote" && !canUseRemote) {
			notify({
				kind: "warning",
				title: g.incompleteTitle,
				message: authMode === "oauth" ? g.incompleteSignIn : g.incompleteToken
			});
			return;
		}
		setSaving(true);
		try {
			setState(apply ? await window.aetherosDesktop.applyConnectionConfig(payload()) : await window.aetherosDesktop.saveConnectionConfig(payload()));
			setRemoteToken("");
			notify({
				kind: "success",
				title: apply ? g.restartingTitle : g.savedTitle,
				message: apply ? g.restartingMessage : g.savedMessage
			});
		} catch (err) {
			notifyError(err, apply ? g.applyFailed : g.saveFailed);
		} finally {
			setSaving(false);
		}
	};
	const signIn = async () => {
		if (!trimmedUrl) {
			notify({
				kind: "warning",
				title: g.incompleteTitle,
				message: g.enterUrlFirst
			});
			return;
		}
		setSigningIn(true);
		try {
			setState(await window.aetherosDesktop.saveConnectionConfig({
				mode: state.mode,
				profile: scope ?? void 0,
				remoteAuthMode: "oauth",
				remoteUrl: trimmedUrl
			}));
			if ((await window.aetherosDesktop.oauthLoginConnectionConfig(trimmedUrl)).connected) {
				setState(await window.aetherosDesktop.getConnectionConfig(scope));
				notify({
					kind: "success",
					title: g.signedIn,
					message: g.connectedTo(providerLabel)
				});
			} else notify({
				kind: "warning",
				title: t.boot.failure.signInIncompleteTitle,
				message: t.boot.failure.signInIncompleteMessage
			});
		} catch (err) {
			notifyError(err, g.signInFailed);
		} finally {
			setSigningIn(false);
		}
	};
	const signOut = async () => {
		setSigningIn(true);
		try {
			await window.aetherosDesktop.oauthLogoutConnectionConfig(trimmedUrl || void 0);
			setState(await window.aetherosDesktop.getConnectionConfig(scope));
			notify({
				kind: "success",
				title: g.signedOutTitle,
				message: g.signedOutMessage
			});
		} catch (err) {
			notifyError(err, g.signOutFailed);
		} finally {
			setSigningIn(false);
		}
	};
	const testRemote = async () => {
		if (!canUseRemote) {
			notify({
				kind: "warning",
				title: g.incompleteTitle,
				message: authMode === "oauth" ? g.incompleteSignInTest : g.incompleteTokenTest
			});
			return;
		}
		setTesting(true);
		setLastTest(null);
		try {
			const result = await window.aetherosDesktop.testConnectionConfig({
				mode: "remote",
				profile: scope ?? void 0,
				remoteAuthMode: authMode,
				remoteToken: authMode === "token" ? remoteToken.trim() || void 0 : void 0,
				remoteUrl: trimmedUrl
			});
			const message = g.connectedTo(result.baseUrl, result.version ?? void 0);
			setLastTest(message);
			notify({
				kind: "success",
				title: g.reachableTitle,
				message
			});
		} catch (err) {
			notifyError(err, g.testFailed);
		} finally {
			setTesting(false);
		}
	};
	if (loading) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(LoadingState, { label: g.loading });
	if (!window.aetherosDesktop?.getConnectionConfig) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
		description: g.unavailableDesc,
		title: g.unavailableTitle
	});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SettingsContent, { children: [
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mb-5",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-2 text-[length:var(--conversation-text-font-size)] font-medium",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconGlobe, { className: "size-4 text-muted-foreground" }),
					g.title,
					state.envOverride ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Pill, {
						tone: "primary",
						children: g.envOverride
					}) : null
				]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-2 max-w-2xl text-[length:var(--conversation-caption-font-size)] leading-(--conversation-caption-line-height) text-(--ui-text-tertiary)",
				children: g.intro
			})]
		}),
		namedProfiles.length > 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mb-5 grid gap-2",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "text-[length:var(--conversation-caption-font-size)] font-medium text-(--ui-text-secondary)",
					children: g.appliesTo
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex flex-wrap gap-1.5",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScopeChip, {
						active: scope === null,
						label: g.allProfiles,
						onSelect: () => setScope(null)
					}), namedProfiles.map((profile) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ScopeChip, {
						active: scope === profile.name,
						label: profile.name,
						onSelect: () => setScope(profile.name)
					}, profile.name))]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-[length:var(--conversation-caption-font-size)] leading-(--conversation-caption-line-height) text-(--ui-text-tertiary)",
					children: scope === null ? g.defaultConnection : g.profileConnection(scope)
				})
			]
		}) : null,
		state.envOverride ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mb-5 flex items-start gap-2 rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2.5 text-[length:var(--conversation-caption-font-size)] text-destructive",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconAlertCircle, { className: "mt-0.5 size-4 shrink-0" }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "font-medium",
				children: g.envOverrideTitle
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "mt-1 leading-5",
				children: g.envOverrideDesc
			})] })]
		}) : null,
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "grid gap-3 sm:grid-cols-2",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ModeCard, {
				active: state.mode === "local",
				description: g.localDesc,
				disabled: state.envOverride,
				icon: IconDeviceDesktop,
				onSelect: () => setState((current) => ({
					...current,
					mode: "local"
				})),
				title: g.localTitle
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ModeCard, {
				active: state.mode === "remote",
				description: g.remoteDesc,
				disabled: state.envOverride,
				icon: IconGlobe,
				onSelect: () => setState((current) => ({
					...current,
					mode: "remote"
				})),
				title: g.remoteTitle
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mt-5 grid gap-1",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
					action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						className: cn("h-8", CONTROL_TEXT),
						disabled: state.envOverride,
						onChange: (event) => setState((current) => ({
							...current,
							remoteUrl: event.target.value
						})),
						placeholder: "https://gateway.example.com/aetheros",
						value: state.remoteUrl
					}),
					description: g.remoteUrlDesc,
					title: g.remoteUrlTitle
				}),
				state.mode === "remote" && probeStatus === "probing" ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-2 py-3 text-[length:var(--conversation-caption-font-size)] text-(--ui-text-tertiary)",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconLoader2, { className: "size-4 animate-spin" }), g.probing]
				}) : null,
				state.mode === "remote" && probeStatus === "error" ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-start gap-2 py-3 text-[length:var(--conversation-caption-font-size)] text-(--ui-text-tertiary)",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconAlertCircle, { className: "mt-0.5 size-4 shrink-0" }), g.probeError]
				}) : null,
				state.mode === "remote" && authResolved && authMode === "oauth" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
					action: oauthConnected ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Pill, {
							tone: "primary",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconCheck, { className: "size-3" }),
								" ",
								g.signedIn
							]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
							disabled: signingIn || state.envOverride,
							onClick: () => void signOut(),
							variant: "outline",
							children: [signingIn ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconLoader2, { className: "animate-spin" }) : null, g.signOut]
						})]
					}) : /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
						disabled: signingIn || state.envOverride || !trimmedUrl,
						onClick: () => void signIn(),
						children: [signingIn ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconLoader2, { className: "animate-spin" }) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconLogin, {}), isPasswordProvider ? g.signIn : g.signInWith(providerLabel)]
					}),
					description: oauthConnected ? isPasswordProvider ? g.authSignedInPassword : g.authSignedInOauth : isPasswordProvider ? g.authNeedsPassword : g.authNeedsOauth(providerLabel),
					title: g.authTitle
				}) : null,
				state.mode === "remote" && authResolved && authMode === "token" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
					action: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						autoComplete: "off",
						className: cn("h-8 font-mono", CONTROL_TEXT),
						disabled: state.envOverride,
						onChange: (event) => setRemoteToken(event.target.value),
						placeholder: state.remoteTokenSet ? g.existingToken(state.remoteTokenPreview ?? g.savedToken) : g.pasteSessionToken,
						type: "password",
						value: remoteToken
					}),
					description: g.tokenDesc,
					title: g.tokenTitle
				}) : null
			]
		}),
		lastTest ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "mt-4 text-xs text-primary",
			children: lastTest
		}) : null,
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mt-6 flex flex-wrap items-center justify-end gap-4",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
					className: "mr-auto",
					disabled: state.envOverride || testing || !canUseRemote,
					onClick: () => void testRemote(),
					size: "sm",
					variant: "text",
					children: [testing ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconLoader2, { className: "animate-spin" }) : null, g.testRemote]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					disabled: state.envOverride || saving,
					onClick: () => void save(false),
					size: "sm",
					variant: "textStrong",
					children: g.saveForRestart
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
					disabled: state.envOverride || saving,
					onClick: () => void save(true),
					size: "sm",
					children: [saving ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconLoader2, { className: "animate-spin" }) : null, g.saveAndReconnect]
				})
			]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "mt-6 grid gap-1",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
				action: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
					onClick: () => void window.aetherosDesktop?.revealLogs(),
					size: "sm",
					variant: "textStrong",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconFileText, {}), g.openLogs]
				}),
				description: g.diagnosticsDesc,
				title: g.diagnostics
			})
		})
	] });
}
//#endregion
//#region src/app/settings/env-credentials.tsx
function SettingsCategoryHeading({ count, icon: Icon, title }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mb-3 flex items-center gap-2 text-[length:var(--conversation-text-font-size)] font-medium",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Icon, { className: "size-4 text-muted-foreground" }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: title }),
			count && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Pill, { children: count })
		]
	});
}
function useEnvCredentials() {
	const { t } = useI18n();
	const credentials = t.settings.credentials;
	const toolsets = t.settings.toolsets;
	const [vars, setVars] = (0, import_react.useState)(null);
	const [edits, setEdits] = (0, import_react.useState)({});
	const [revealed, setRevealed] = (0, import_react.useState)({});
	const [saving, setSaving] = (0, import_react.useState)(null);
	(0, import_react.useEffect)(() => {
		try {
			window.localStorage.removeItem("desktop.settings.keys.show_advanced");
		} catch {}
	}, []);
	(0, import_react.useEffect)(() => {
		let cancelled = false;
		(async () => {
			try {
				const next = await getEnvVars();
				if (!cancelled) setVars(next);
			} catch (err) {
				notifyError(err, t.settings.keys.failedLoad);
			}
		})();
		return () => void (cancelled = true);
	}, []);
	function patchVar(key, patch) {
		setVars((c) => c ? {
			...c,
			[key]: {
				...c[key],
				...patch
			}
		} : c);
	}
	function clearLocalState(key) {
		setEdits((c) => withoutKey(c, key));
		setRevealed((c) => withoutKey(c, key));
	}
	async function handleSave(key) {
		const value = edits[key];
		if (!value) return;
		setSaving(key);
		try {
			await setEnvVar(key, value);
			patchVar(key, {
				is_set: true,
				redacted_value: redactedValue(value)
			});
			clearLocalState(key);
			notify({
				kind: "success",
				title: toolsets.savedTitle,
				message: toolsets.savedMessage(key)
			});
		} catch (err) {
			notifyError(err, toolsets.failedSave(key));
		} finally {
			setSaving(null);
		}
	}
	async function saveValue(key, value) {
		const trimmed = value.trim();
		if (!trimmed) return {
			message: credentials.enterValueFirst,
			ok: false
		};
		setSaving(key);
		try {
			await setEnvVar(key, trimmed);
			patchVar(key, {
				is_set: true,
				redacted_value: redactedValue(trimmed)
			});
			clearLocalState(key);
			notify({
				kind: "success",
				message: toolsets.savedMessage(key),
				title: toolsets.savedTitle
			});
			return { ok: true };
		} catch (err) {
			notifyError(err, toolsets.failedSave(key));
			return {
				message: err instanceof Error ? err.message : credentials.couldNotSave,
				ok: false
			};
		} finally {
			setSaving(null);
		}
	}
	async function handleClear(key) {
		if (!window.confirm(toolsets.removeConfirm(key))) return;
		setSaving(key);
		try {
			await deleteEnvVar(key);
			patchVar(key, {
				is_set: false,
				redacted_value: null
			});
			clearLocalState(key);
			notify({
				kind: "success",
				title: toolsets.removedTitle,
				message: toolsets.removedMessage(key)
			});
		} catch (err) {
			notifyError(err, toolsets.failedRemove(key));
		} finally {
			setSaving(null);
		}
	}
	async function handleReveal(key) {
		if (revealed[key]) {
			setRevealed((c) => withoutKey(c, key));
			return;
		}
		try {
			const result = await revealEnvVar(key);
			setRevealed((c) => ({
				...c,
				[key]: result.value
			}));
		} catch (err) {
			notifyError(err, toolsets.failedReveal(key));
		}
	}
	return {
		saveValue,
		vars,
		rowProps: {
			edits,
			revealed,
			saving,
			setEdits,
			onSave: handleSave,
			onClear: handleClear,
			onReveal: handleReveal
		}
	};
}
//#endregion
//#region src/app/settings/keys-settings.tsx
var KEYS_VIEWS = ["tools", "settings"];
var VIEW_CATEGORIES = {
	settings: ["setting", "messaging"],
	tools: ["tool"]
};
function KeysSettings({ view }) {
	const { t } = useI18n();
	const { rowProps, vars } = useEnvCredentials();
	const [openKey, setOpenKey] = (0, import_react.useState)(null);
	(0, import_react.useEffect)(() => {
		setOpenKey(null);
	}, [view]);
	const groups = (0, import_react.useMemo)(() => {
		if (!vars) return [];
		return KEYS_VIEWS.flatMap((v) => {
			const cats = VIEW_CATEGORIES[v];
			const entries = Object.entries(vars).filter(([, info]) => !info.channel_managed && cats.includes(asText(info.category))).sort(([a], [b]) => a.localeCompare(b));
			return entries.length === 0 ? [] : [{
				category: v,
				entries
			}];
		});
	}, [vars]);
	if (!vars) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(LoadingState, { label: t.settings.keys.loading });
	const visible = groups.filter((g) => g.category === view);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SettingsContent, { children: [visible.map((group) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "grid gap-2",
		children: group.entries.map(([key, info]) => {
			const label = credentialRowLabel(key, info);
			return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CredentialKeyCard, {
				expanded: openKey === key,
				info,
				label,
				onExpand: () => setOpenKey(key),
				onToggle: () => setOpenKey((prev) => prev === key ? null : key),
				placeholder: credentialPlaceholder(key, info, label),
				rowProps,
				varKey: key
			}, key);
		})
	}, group.category)), visible.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "rounded-lg border border-dashed border-(--ui-stroke-tertiary) px-4 py-8 text-center text-[length:var(--conversation-caption-font-size)] text-muted-foreground",
		children: t.settings.keys.empty
	})] });
}
//#endregion
//#region src/app/settings/use-deep-link-highlight.ts
function useDeepLinkHighlight({ param, ready, elementId, onResolve, block = "center" }) {
	const [searchParams, setSearchParams] = useSearchParams();
	const target = searchParams.get(param);
	(0, import_react.useEffect)(() => {
		if (!target || !ready(target)) return;
		onResolve?.(target);
		const scrollTimeout = window.setTimeout(() => {
			const element = document.getElementById(elementId(target));
			if (!element) return;
			element.scrollIntoView({
				behavior: "smooth",
				block
			});
			element.classList.add("setting-field-highlight");
			window.setTimeout(() => element.classList.remove("setting-field-highlight"), 1600);
		}, 80);
		setSearchParams((previous) => {
			const next = new URLSearchParams(previous);
			next.delete(param);
			return next;
		}, { replace: true });
		return () => window.clearTimeout(scrollTimeout);
	}, [
		block,
		elementId,
		onResolve,
		param,
		ready,
		setSearchParams,
		target
	]);
	return target;
}
//#endregion
//#region src/app/settings/mcp-settings.tsx
var EMPTY_SERVER = {
	command: "",
	args: [],
	env: {}
};
function getServers(config) {
	const raw = config?.mcp_servers;
	return raw && typeof raw === "object" && !Array.isArray(raw) ? raw : {};
}
var transportLabel = (server) => typeof server.transport === "string" ? server.transport : typeof server.url === "string" ? "http" : typeof server.command === "string" ? "stdio" : "custom";
function McpSettings({ gateway, onConfigSaved }) {
	const { t } = useI18n();
	const m = t.settings.mcp;
	const activeSessionId = useStore($activeSessionId);
	const [config, setConfig] = (0, import_react.useState)(null);
	const [selected, setSelected] = (0, import_react.useState)(null);
	const [name, setName] = (0, import_react.useState)("");
	const [body, setBody] = (0, import_react.useState)("");
	const [saving, setSaving] = (0, import_react.useState)(false);
	const [reloading, setReloading] = (0, import_react.useState)(false);
	(0, import_react.useEffect)(() => {
		let cancelled = false;
		getAetherosConfigRecord().then((next) => {
			if (cancelled) return;
			setConfig(next);
			setSelected(Object.keys(getServers(next)).sort()[0] ?? null);
		}).catch((err) => notifyError(err, m.failedLoad));
		return () => void (cancelled = true);
	}, []);
	const servers = (0, import_react.useMemo)(() => getServers(config), [config]);
	const names = (0, import_react.useMemo)(() => Object.keys(servers).sort(), [servers]);
	useDeepLinkHighlight({
		block: "nearest",
		elementId: (serverName) => `mcp-server-${serverName}`,
		onResolve: setSelected,
		param: "server",
		ready: (serverName) => Boolean(config) && serverName in servers
	});
	(0, import_react.useEffect)(() => {
		const server = selected ? servers[selected] : null;
		setName(selected ?? "");
		setBody(JSON.stringify(server ?? EMPTY_SERVER, null, 2));
	}, [selected, servers]);
	if (!config) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(LoadingState, { label: m.loading });
	const saveServer = async () => {
		const nextName = name.trim();
		if (!nextName) {
			notify({
				kind: "error",
				title: m.nameRequiredTitle,
				message: m.nameRequiredMessage
			});
			return;
		}
		let parsed;
		try {
			const raw = JSON.parse(body);
			if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error(m.objectRequired);
			parsed = raw;
		} catch (err) {
			notifyError(err, m.invalidJson);
			return;
		}
		setSaving(true);
		try {
			const nextServers = { ...servers };
			if (selected && selected !== nextName) delete nextServers[selected];
			nextServers[nextName] = parsed;
			const nextConfig = {
				...config,
				mcp_servers: nextServers
			};
			await saveAetherosConfig(nextConfig);
			setConfig(nextConfig);
			setSelected(nextName);
			onConfigSaved?.();
			notify({
				kind: "success",
				title: m.savedTitle,
				message: m.savedMessage(nextName)
			});
		} catch (err) {
			notifyError(err, m.saveFailed);
		} finally {
			setSaving(false);
		}
	};
	const removeServer = async (serverName) => {
		setSaving(true);
		try {
			const nextServers = { ...servers };
			delete nextServers[serverName];
			const nextConfig = {
				...config,
				mcp_servers: nextServers
			};
			await saveAetherosConfig(nextConfig);
			setConfig(nextConfig);
			setSelected(Object.keys(nextServers).sort()[0] ?? null);
			onConfigSaved?.();
		} catch (err) {
			notifyError(err, m.removeFailed);
		} finally {
			setSaving(false);
		}
	};
	const reloadMcp = async () => {
		if (!gateway) {
			notify({
				kind: "warning",
				title: m.gatewayUnavailableTitle,
				message: m.gatewayUnavailableMessage
			});
			return;
		}
		setReloading(true);
		try {
			await gateway.request("reload.mcp", {
				confirm: true,
				session_id: activeSessionId ?? void 0
			});
			notify({
				kind: "success",
				title: m.reloadedTitle,
				message: m.reloadedMessage
			});
		} catch (err) {
			notifyError(err, m.reloadFailed);
		} finally {
			setReloading(false);
		}
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SettingsContent, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mb-4 flex items-center justify-end gap-4",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
			onClick: () => setSelected(null),
			size: "xs",
			variant: "text",
			children: m.newServer
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
			disabled: reloading,
			onClick: () => void reloadMcp(),
			size: "xs",
			variant: "text",
			children: reloading ? m.reloading : m.reload
		})]
	}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "grid min-h-0 gap-6 lg:grid-cols-[16rem_minmax(0,1fr)]",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "min-h-64",
			children: names.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
				description: m.emptyDesc,
				title: m.emptyTitle
			}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "grid gap-0.5",
				children: names.map((serverName) => {
					const server = servers[serverName];
					return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
						className: cn("scroll-mt-2 rounded-md px-2 py-2 text-left transition-colors hover:bg-(--chrome-action-hover)", selected === serverName ? "bg-(--ui-bg-tertiary) text-foreground" : "text-muted-foreground"),
						id: `mcp-server-${serverName}`,
						onClick: () => setSelected(serverName),
						type: "button",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "truncate text-sm font-medium",
							children: serverName
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "mt-1 flex items-center gap-1.5",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Pill, { children: transportLabel(server) }), server.disabled === true && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Pill, { children: m.disabled })]
						})]
					}, serverName);
				})
			})
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "grid content-start gap-3",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-2 text-sm font-medium",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconTool, { className: "size-4 text-muted-foreground" }), selected ? m.editServer : m.newServer]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
					className: "grid gap-1.5",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "text-xs text-muted-foreground",
						children: m.name
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						onChange: (event) => setName(event.currentTarget.value),
						placeholder: "filesystem",
						value: name
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
					className: "grid gap-1.5",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "text-xs text-muted-foreground",
						children: m.serverJson
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Textarea, {
						className: "min-h-80 font-mono text-xs",
						onChange: (event) => setBody(event.currentTarget.value),
						spellCheck: false,
						value: body
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center justify-between",
					children: [selected ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						className: "text-destructive hover:text-destructive",
						disabled: saving,
						onClick: () => void removeServer(selected),
						size: "xs",
						variant: "text",
						children: m.remove
					}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						disabled: saving,
						onClick: () => void saveServer(),
						size: "sm",
						children: saving ? t.common.saving : m.saveServer
					})]
				})
			]
		})]
	})] });
}
//#endregion
//#region src/app/settings/onboarding-settings.tsx
function OnboardingSettings() {
	const [testingProviders, setTestingProviders] = (0, import_react.useState)(false);
	const [testingIntegrations, setTestingIntegrations] = (0, import_react.useState)(false);
	const [results, setResults] = (0, import_react.useState)(null);
	const handleRerun = () => {
		startManualOnboarding("Re-run the onboarding wizard to update your configuration.");
	};
	const handleDiagnoseAll = async () => {
		setTestingProviders(true);
		setTestingIntegrations(true);
		setResults(null);
		let providerOk = 0;
		let integrationOk = 0;
		for (const key of [
			"OPENAI_API_KEY",
			"ANTHROPIC_API_KEY",
			"GEMINI_API_KEY",
			"OPENROUTER_API_KEY",
			"GROQ_API_KEY",
			"MISTRAL_API_KEY",
			"DEEPSEEK_API_KEY",
			"TOGETHER_API_KEY",
			"XAI_API_KEY",
			"NOVITA_API_KEY",
			"DASHSCOPE_API_KEY"
		]) try {
			const result = await validateProviderCredential(key, "probe", "");
			if (result.ok && result.reachable) providerOk++;
		} catch {}
		try {
			const platforms = await getMessagingPlatforms();
			for (const platform of platforms.platforms) if (platform.configured && platform.enabled) try {
				if ((await testMessagingPlatform(platform.id)).ok) integrationOk++;
			} catch {}
		} catch {}
		setResults({
			providers: providerOk,
			integrations: integrationOk
		});
		setTestingProviders(false);
		setTestingIntegrations(false);
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-2xl space-y-6 p-6",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
			className: "text-xl font-bold tracking-tight",
			children: "Onboarding & Setup"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "mt-1 text-sm text-muted-foreground",
			children: "Re-run the onboarding wizard or diagnose your current configuration."
		})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "space-y-4",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "rounded-lg border border-border bg-card/30 p-5",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-sm font-medium",
							children: "Re-run Onboarding Wizard"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-xs text-muted-foreground mt-0.5",
							children: "Go through the full setup process again to configure providers, gateway, and integrations."
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
							onClick: handleRerun,
							size: "sm",
							children: ["Open Wizard", /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconChevronRight, { className: "size-4 ml-1" })]
						})]
					})
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "rounded-lg border border-border bg-card/30 p-5",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-sm font-medium",
							children: "Diagnose Connections"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-xs text-muted-foreground mt-0.5",
							children: "Test all configured provider keys and messaging integrations."
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
							disabled: testingProviders || testingIntegrations,
							onClick: () => void handleDiagnoseAll(),
							size: "sm",
							variant: "outline",
							children: [testingProviders || testingIntegrations ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconLoader2, { className: "size-3 animate-spin mr-1" }) : null, "Run Diagnostics"]
						})]
					}), results && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "mt-4 space-y-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2 text-sm",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconCheck, { className: cn("size-4", results.providers > 0 ? "text-emerald-500" : "text-muted-foreground") }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [
								results.providers,
								" active provider",
								results.providers !== 1 ? "s" : ""
							] })]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2 text-sm",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconCheck, { className: cn("size-4", results.integrations > 0 ? "text-emerald-500" : "text-muted-foreground") }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [
								results.integrations,
								" active integration",
								results.integrations !== 1 ? "s" : ""
							] })]
						})]
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "rounded-lg border border-border bg-card/30 p-5",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-sm font-medium mb-2",
						children: "Quick Actions"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "grid gap-2 sm:grid-cols-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(QuickAction, {
							description: "Add or switch AI providers",
							label: "Manage Providers",
							onClick: startManualOnboarding
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(QuickAction, {
							description: "View and edit all API keys",
							href: "#",
							label: "Manage API Keys"
						})]
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "rounded-lg border border-border bg-card/30 p-5",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-sm font-medium mb-3",
						children: "Supported Providers"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "grid gap-2 sm:grid-cols-2 lg:grid-cols-3",
						children: [
							{
								name: "OpenAI",
								url: "https://platform.openai.com/api-keys"
							},
							{
								name: "Anthropic",
								url: "https://console.anthropic.com/settings/keys"
							},
							{
								name: "Google Gemini",
								url: "https://aistudio.google.com/app/apikey"
							},
							{
								name: "OpenRouter",
								url: "https://openrouter.ai/keys"
							},
							{
								name: "Groq",
								url: "https://console.groq.com/keys"
							},
							{
								name: "Mistral",
								url: "https://console.mistral.ai/api-keys"
							},
							{
								name: "DeepSeek",
								url: "https://platform.deepseek.com/api_keys"
							},
							{
								name: "Together AI",
								url: "https://api.together.ai/settings/api-keys"
							},
							{
								name: "Azure OpenAI",
								url: "https://portal.azure.com/"
							},
							{
								name: "xAI",
								url: "https://console.x.ai/"
							},
							{
								name: "Novita",
								url: "https://novita.ai/settings/api-keys"
							}
						].map((p) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("a", {
							className: "inline-flex items-center gap-1.5 rounded-lg border border-border/50 bg-card/20 px-3 py-2 text-xs text-muted-foreground hover:text-foreground hover:border-primary/30 transition-all",
							href: p.url,
							rel: "noopener noreferrer",
							target: "_blank",
							children: [p.name, /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconExternalLink, { className: "size-3" })]
						}, p.name))
					})]
				})
			]
		})]
	});
}
function QuickAction({ label, description, onClick, href }) {
	const content = /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "rounded-lg border border-border/50 bg-card/20 p-3 hover:bg-card/40 hover:border-primary/30 transition-all cursor-pointer",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "text-sm font-medium",
			children: label
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "text-xs text-muted-foreground mt-0.5",
			children: description
		})]
	});
	if (href) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("a", {
		href,
		children: content
	});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
		onClick,
		type: "button",
		children: content
	});
}
//#endregion
//#region src/components/desktop-onboarding-overlay.tsx
var PROVIDER_DISPLAY = {
	"openai-codex": {
		order: 0,
		title: "OpenAI OAuth (ChatGPT)"
	},
	"minimax-oauth": {
		order: 1,
		title: "MiniMax"
	},
	"qwen-oauth": {
		order: 2,
		title: "Qwen Code"
	},
	"xai-oauth": {
		order: 3,
		title: "xAI Grok"
	},
	anthropic: {
		order: 4,
		title: "Anthropic API Key"
	},
	"claude-code": {
		order: 5,
		title: "Anthropic OAuth: Required Extra Usage Credits to Use Subscription"
	}
};
var providerTitle = (p) => PROVIDER_DISPLAY[p.id]?.title ?? p.name;
var orderOf = (p) => PROVIDER_DISPLAY[p.id]?.order ?? 99;
var sortProviders = (providers) => [...providers].sort((a, b) => orderOf(a) - orderOf(b) || a.name.localeCompare(b.name));
function ConnectedTag() {
	const { t } = useI18n();
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
		className: "inline-flex items-center gap-1 bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconCheck, { className: "size-3" }), t.onboarding.connected]
	});
}
var PROVIDER_ROW_CLASS = "group flex w-full items-center justify-between gap-3 rounded-[6px] px-3 py-2.5 text-left transition-colors hover:bg-(--ui-control-hover-background)";
function KeyProviderRow({ onClick }) {
	const { t } = useI18n();
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
		className: PROVIDER_ROW_CLASS,
		onClick,
		type: "button",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "min-w-0",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "text-[length:var(--conversation-text-font-size)] font-semibold",
				children: "OpenRouter"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-1 text-xs leading-5 text-muted-foreground",
				children: t.onboarding.openRouterPitch
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconChevronRight, { className: "size-4 text-muted-foreground transition group-hover:text-foreground" })]
	});
}
function ProviderRow({ onSelect, provider }) {
	const { t } = useI18n();
	const loggedIn = provider.status?.logged_in;
	const Trail = provider.flow === "external" ? IconTerminal2 : IconChevronRight;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
		className: PROVIDER_ROW_CLASS,
		onClick: () => onSelect(provider),
		type: "button",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "min-w-0",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "text-[length:var(--conversation-text-font-size)] font-semibold",
					children: providerTitle(provider)
				}), loggedIn ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ConnectedTag, {}) : null]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-1 text-xs leading-5 text-muted-foreground",
				children: t.onboarding.flowSubtitles[provider.flow]
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Trail, { className: "size-4 text-muted-foreground transition group-hover:text-foreground" })]
	});
}
//#endregion
//#region src/app/settings/providers-settings.tsx
var PROVIDER_VIEWS = ["accounts", "keys"];
function buildProviderKeyGroups(vars) {
	const buckets = /* @__PURE__ */ new Map();
	for (const [key, info] of Object.entries(vars)) {
		if (info.category !== "provider") continue;
		const name = providerGroup(key);
		if (name === "Other") continue;
		buckets.set(name, [...buckets.get(name) ?? [], [key, info]]);
	}
	const groups = [];
	for (const [name, entries] of buckets) {
		const primary = entries.find(([k, i]) => !i.advanced && isKeyVar(k, i)) ?? entries.find(([k, i]) => isKeyVar(k, i));
		if (!primary) continue;
		const meta = providerMeta(name);
		groups.push({
			advanced: entries.filter(([k, i]) => k !== primary[0] && (!isKeyVar(k, i) || i.is_set)).sort(([a], [b]) => a.localeCompare(b)),
			description: meta?.description ?? primary[1].description,
			docsUrl: meta?.docsUrl ?? primary[1].url ?? void 0,
			hasAnySet: entries.some(([, i]) => i.is_set),
			name,
			primary,
			priority: providerPriority(name)
		});
	}
	return groups.sort((a, b) => a.priority - b.priority || a.name.localeCompare(b.name));
}
function OAuthPicker({ onWantApiKey, providers }) {
	const { t } = useI18n();
	const p = t.settings.providers;
	const [showAll, setShowAll] = (0, import_react.useState)(false);
	const ordered = (0, import_react.useMemo)(() => sortProviders(providers), [providers]);
	if (ordered.length === 0) return null;
	const select = (p) => startManualProviderOAuth(p.id);
	const connected = ordered.filter((p) => p.status?.logged_in);
	const others = ordered.filter((p) => !p.status?.logged_in);
	const collapsible = others.length > 0;
	const showOthers = !collapsible || showAll;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
		className: "mb-5 grid gap-2",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-wrap items-baseline justify-between gap-x-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SettingsCategoryHeading, {
					icon: IconKey,
					title: p.connectAccount
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					className: "text-[length:var(--conversation-caption-font-size)]",
					onClick: onWantApiKey,
					size: "inline",
					type: "button",
					variant: "textStrong",
					children: p.haveApiKey
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "-mt-2 mb-1 text-[length:var(--conversation-caption-font-size)] leading-(--conversation-caption-line-height) text-(--ui-text-tertiary)",
				children: p.intro
			}),
			connected.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-1 px-0.5 text-[length:var(--conversation-caption-font-size)] font-medium text-(--ui-text-tertiary)",
				children: p.connected
			}), connected.map((p) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ProviderRow, {
				onSelect: select,
				provider: p
			}, p.id))] }),
			showOthers && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [others.map((p) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ProviderRow, {
				onSelect: select,
				provider: p
			}, p.id)), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(KeyProviderRow, { onClick: onWantApiKey })] }),
			collapsible && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
				className: "py-1 text-[length:var(--conversation-caption-font-size)]",
				onClick: () => setShowAll((v) => !v),
				size: "inline",
				type: "button",
				variant: "text",
				children: [showAll ? p.collapse : connected.length > 0 ? p.connectAnother : p.otherProviders, /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconChevronDown, { className: cn("size-3.5 transition", showAll && "rotate-180") })]
			})
		]
	});
}
function NoProviderKeys() {
	const { t } = useI18n();
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "grid min-h-32 place-items-center px-4 py-8 text-center text-[length:var(--conversation-caption-font-size)] text-muted-foreground",
		children: t.settings.providers.noProviderKeys
	});
}
function ProvidersSettings({ onViewChange, view }) {
	const { t } = useI18n();
	const { rowProps, vars } = useEnvCredentials();
	const [oauthProviders, setOauthProviders] = (0, import_react.useState)([]);
	const [openProvider, setOpenProvider] = (0, import_react.useState)(null);
	const onboardingActive = useStore($desktopOnboarding).manual;
	(0, import_react.useEffect)(() => {
		if (onboardingActive) return;
		let cancelled = false;
		(async () => {
			try {
				const { providers } = await listOAuthProviders();
				if (!cancelled) setOauthProviders(providers);
			} catch {}
		})();
		return () => void (cancelled = true);
	}, [onboardingActive]);
	if (!vars) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(LoadingState, { label: t.settings.providers.loading });
	const hasOauth = oauthProviders.length > 0;
	const showApiKeys = view === "keys" || !hasOauth;
	const keyGroups = buildProviderKeyGroups(vars);
	if (showApiKeys) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SettingsContent, { children: keyGroups.length > 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "grid gap-2",
		children: keyGroups.map((group) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ProviderKeyRows, {
			expanded: openProvider === group.name,
			group,
			onExpand: () => setOpenProvider(group.name),
			onToggle: () => setOpenProvider((prev) => prev === group.name ? null : group.name),
			rowProps
		}, group.name))
	}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(NoProviderKeys, {}) });
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SettingsContent, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(OAuthPicker, {
		onWantApiKey: () => onViewChange("keys"),
		providers: oauthProviders
	}) });
}
//#endregion
//#region src/app/settings/sessions-settings.tsx
var ARCHIVED_FETCH_LIMIT = 200;
function workspaceLabel(cwd) {
	const path = cwd?.trim();
	if (!path) return "";
	return path.replace(/[/\\]+$/, "").split(/[/\\]/).filter(Boolean).pop() ?? path;
}
function SessionsSettings() {
	const { t } = useI18n();
	const s = t.settings.sessions;
	const [sessions, setLocalSessions] = (0, import_react.useState)([]);
	const [loading, setLoading] = (0, import_react.useState)(true);
	const [busyId, setBusyId] = (0, import_react.useState)(null);
	const load = (0, import_react.useCallback)(async () => {
		setLoading(true);
		try {
			setLocalSessions((await listAllProfileSessions(ARCHIVED_FETCH_LIMIT, 0, "only")).sessions);
		} catch (err) {
			notifyError(err, s.failedLoad);
		} finally {
			setLoading(false);
		}
	}, [s.failedLoad]);
	(0, import_react.useEffect)(() => {
		load();
	}, [load]);
	const unarchive = (0, import_react.useCallback)(async (session) => {
		setBusyId(session.id);
		try {
			await setSessionArchived(session.id, false, session.profile);
			setLocalSessions((prev) => prev.filter((s) => s.id !== session.id));
			setSessions((prev) => [{
				...session,
				archived: false
			}, ...prev.filter((s) => s.id !== session.id)]);
			triggerHaptic("selection");
			notify({
				durationMs: 2e3,
				kind: "success",
				message: s.restored
			});
		} catch (err) {
			notifyError(err, s.unarchiveFailed);
		} finally {
			setBusyId(null);
		}
	}, [s]);
	const remove = (0, import_react.useCallback)(async (session) => {
		if (!window.confirm(s.deleteConfirm(sessionTitle(session)))) return;
		setBusyId(session.id);
		try {
			await deleteSession(session.id, session.profile);
			setLocalSessions((prev) => prev.filter((s) => s.id !== session.id));
			triggerHaptic("warning");
		} catch (err) {
			notifyError(err, s.deleteFailed);
		} finally {
			setBusyId(null);
		}
	}, [s]);
	useDeepLinkHighlight({
		elementId: (id) => `archived-session-${id}`,
		param: "session",
		ready: (id) => !loading && sessions.some((session) => session.id === id)
	});
	if (loading) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(LoadingState, { label: s.loading });
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SettingsContent, { children: [
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DefaultProjectDirSetting, {}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SectionHeading, {
			icon: IconArchive,
			meta: sessions.length ? String(sessions.length) : void 0,
			title: s.archivedTitle
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "mb-2 text-[length:var(--conversation-caption-font-size)] text-(--ui-text-tertiary)",
			children: s.archivedIntro
		}),
		sessions.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EmptyState, {
			description: s.emptyArchivedDesc,
			title: s.emptyArchivedTitle
		}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "grid gap-1",
			children: sessions.map((session) => {
				const label = workspaceLabel(session.cwd);
				const busy = busyId === session.id;
				return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "scroll-mt-6 rounded-lg",
					id: `archived-session-${session.id}`,
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
						action: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-1.5",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
								disabled: busy,
								onClick: () => void unarchive(session),
								size: "sm",
								type: "button",
								variant: "textStrong",
								children: [busy ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconLoader2, { className: "size-3.5 animate-spin" }) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconArchiveOff, { className: "size-3.5" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: s.unarchive })]
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Tip, {
								label: s.deletePermanently,
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
									"aria-label": s.deletePermanently,
									className: "text-muted-foreground hover:text-destructive",
									disabled: busy,
									onClick: () => void remove(session),
									size: "icon",
									type: "button",
									variant: "ghost",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconTrash, { className: "size-3.5" })
								})
							})]
						}),
						description: session.preview || void 0,
						hint: label ? `${label} · ${s.messages(session.message_count)}` : s.messages(session.message_count),
						title: sessionTitle(session)
					})
				}, session.id);
			})
		})
	] });
}
function DefaultProjectDirSetting() {
	const { t } = useI18n();
	const s = t.settings.sessions;
	const [dir, setDir] = (0, import_react.useState)(null);
	const [fallback, setFallback] = (0, import_react.useState)("");
	const [busy, setBusy] = (0, import_react.useState)(false);
	(0, import_react.useEffect)(() => {
		const settings = window.aetherosDesktop?.settings;
		if (!settings) return;
		let alive = true;
		settings.getDefaultProjectDir().then((result) => {
			if (!alive) return;
			setDir(result.dir);
			setFallback(result.defaultLabel);
			applyConfiguredDefaultProjectDir(result.dir);
		});
		return () => {
			alive = false;
		};
	}, []);
	const choose = (0, import_react.useCallback)(async () => {
		const settings = window.aetherosDesktop?.settings;
		if (!settings) return;
		setBusy(true);
		try {
			const picked = await settings.pickDefaultProjectDir();
			if (picked.canceled || !picked.dir) return;
			const result = await settings.setDefaultProjectDir(picked.dir);
			setDir(result.dir);
			applyConfiguredDefaultProjectDir(result.dir);
			notify({
				durationMs: 4e3,
				kind: "success",
				message: s.defaultDirUpdated
			});
		} catch (err) {
			notifyError(err, s.updateDirFailed);
		} finally {
			setBusy(false);
		}
	}, [s]);
	const clear = (0, import_react.useCallback)(async () => {
		const settings = window.aetherosDesktop?.settings;
		if (!settings) return;
		setBusy(true);
		try {
			await settings.setDefaultProjectDir(null);
			setDir(null);
			applyConfiguredDefaultProjectDir(null);
			await ensureDefaultWorkspaceCwd();
		} catch (err) {
			notifyError(err, s.clearDirFailed);
		} finally {
			setBusy(false);
		}
	}, [s]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mb-6",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SectionHeading, {
				icon: IconFolderOpen,
				title: s.defaultDirTitle
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mb-2 text-[length:var(--conversation-caption-font-size)] text-(--ui-text-tertiary)",
				children: s.defaultDirDesc
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ListRow, {
				action: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-3",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
						disabled: busy,
						onClick: () => void choose(),
						size: "sm",
						type: "button",
						variant: "textStrong",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconFolderOpen, { className: "size-3.5" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: dir ? s.change : s.choose })]
					}), dir && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						disabled: busy,
						onClick: () => void clear(),
						size: "sm",
						type: "button",
						variant: "text",
						children: s.clear
					})]
				}),
				description: dir || s.defaultsTo(fallback || "~"),
				title: dir ? dir : s.notSet
			})
		]
	});
}
//#endregion
//#region src/app/settings/index.tsx
var SETTINGS_VIEWS = [
	...SECTIONS.map((s) => `config:${s.id}`),
	"providers",
	"gateway",
	"keys",
	"mcp",
	"onboarding",
	"sessions",
	"about"
];
function SettingsView({ gateway, onClose, onConfigSaved, onMainModelChanged }) {
	const { t } = useI18n();
	const [activeView, setActiveView] = useRouteEnumParam("tab", SETTINGS_VIEWS, "config:model");
	const [providerView, setProviderView] = useRouteEnumParam("pview", PROVIDER_VIEWS, "accounts");
	const [keysView, setKeysView] = useRouteEnumParam("kview", KEYS_VIEWS, "tools");
	const openProviderView = (view) => {
		setActiveView("providers");
		setProviderView(view);
	};
	const openKeysView = (view) => {
		setActiveView("keys");
		setKeysView(view);
	};
	const importInputRef = (0, import_react.useRef)(null);
	const exportConfig = async () => {
		try {
			const cfg = await getAetherosConfigRecord();
			const blob = new Blob([JSON.stringify(cfg, null, 2)], { type: "application/json" });
			const url = URL.createObjectURL(blob);
			const a = document.createElement("a");
			a.href = url;
			a.download = "aetheros-config.json";
			a.click();
			URL.revokeObjectURL(url);
			triggerHaptic("success");
		} catch (err) {
			notifyError(err, t.settings.exportFailed);
		}
	};
	const resetConfig = async () => {
		if (!window.confirm(t.settings.resetConfirm)) return;
		try {
			await saveAetherosConfig(await getAetherosConfigDefaults());
			triggerHaptic("success");
			onConfigSaved?.();
		} catch (err) {
			notifyError(err, t.settings.resetFailed);
		}
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(OverlayView, {
		closeLabel: t.settings.closeSettings,
		onClose,
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(OverlaySplitLayout, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(OverlaySidebar, { children: [
			SECTIONS.map((s) => {
				const view = `config:${s.id}`;
				return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(OverlayNavItem, {
					active: activeView === view,
					icon: s.icon,
					label: t.settings.sections[s.id] ?? s.label,
					onClick: () => setActiveView(view)
				}, s.id);
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { className: "my-2 h-px bg-border/30" }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(OverlayNavItem, {
				active: activeView === "providers",
				icon: IconBolt,
				label: t.settings.nav.providers,
				onClick: () => setActiveView("providers")
			}),
			activeView === "providers" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "ml-3.5 flex flex-col gap-0.5 pl-1.5",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(OverlayNavItem, {
					active: providerView === "accounts",
					icon: IconSparkles,
					label: t.settings.nav.providerAccounts,
					nested: true,
					onClick: () => openProviderView("accounts")
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(OverlayNavItem, {
					active: providerView === "keys",
					icon: IconKey,
					label: t.settings.nav.providerApiKeys,
					nested: true,
					onClick: () => openProviderView("keys")
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(OverlayNavItem, {
				active: activeView === "gateway",
				icon: IconGlobe,
				label: t.settings.nav.gateway,
				onClick: () => setActiveView("gateway")
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(OverlayNavItem, {
				active: activeView === "keys",
				icon: IconKey,
				label: t.settings.nav.apiKeys,
				onClick: () => setActiveView("keys")
			}),
			activeView === "keys" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "ml-3.5 flex flex-col gap-0.5 pl-1.5",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(OverlayNavItem, {
					active: keysView === "tools",
					icon: IconTool,
					label: t.settings.nav.keysTools,
					nested: true,
					onClick: () => openKeysView("tools")
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(OverlayNavItem, {
					active: keysView === "settings",
					icon: IconSettings2,
					label: t.settings.nav.keysSettings,
					nested: true,
					onClick: () => openKeysView("settings")
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(OverlayNavItem, {
				active: activeView === "mcp",
				icon: IconTool,
				label: t.settings.nav.mcp,
				onClick: () => setActiveView("mcp")
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(OverlayNavItem, {
				active: activeView === "onboarding",
				icon: IconSparkles,
				label: "Onboarding",
				onClick: () => setActiveView("onboarding")
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(OverlayNavItem, {
				active: activeView === "sessions",
				icon: IconArchive,
				label: t.settings.nav.archivedChats,
				onClick: () => setActiveView("sessions")
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { className: "my-2 h-px bg-border/30" }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(OverlayNavItem, {
				active: activeView === "about",
				icon: IconInfoCircle,
				label: t.settings.nav.about,
				onClick: () => setActiveView("about")
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mt-auto flex items-center gap-1 pt-2",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Tip, {
						label: t.settings.exportConfig,
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(OverlayIconButton, {
							"aria-label": t.settings.exportConfig,
							onClick: () => void exportConfig(),
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconDownload, { className: "size-3.5" })
						})
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Tip, {
						label: t.settings.importConfig,
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(OverlayIconButton, {
							"aria-label": t.settings.importConfig,
							onClick: () => {
								triggerHaptic("open");
								importInputRef.current?.click();
							},
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconUpload, { className: "size-3.5" })
						})
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Tip, {
						label: t.settings.resetToDefaults,
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(OverlayIconButton, {
							"aria-label": t.settings.resetToDefaults,
							className: "hover:text-destructive",
							onClick: () => {
								triggerHaptic("warning");
								resetConfig();
							},
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconRefresh, { className: "size-3.5" })
						})
					})
				]
			})
		] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(OverlayMain, {
			className: "px-0 pb-0 pt-[calc(var(--titlebar-height)+1rem)]",
			children: activeView === "config:appearance" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(AppearanceSettings, {}) : activeView === "about" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(AboutSettings, {}) : activeView === "gateway" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(GatewaySettings, {}) : activeView.startsWith("config:") ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ConfigSettings, {
				activeSectionId: activeView.slice(7),
				importInputRef,
				onConfigSaved,
				onMainModelChanged
			}) : activeView === "providers" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ProvidersSettings, {
				onViewChange: setProviderView,
				view: providerView
			}) : activeView === "keys" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(KeysSettings, { view: keysView }) : activeView === "mcp" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(McpSettings, {
				gateway,
				onConfigSaved
			}) : activeView === "onboarding" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(OnboardingSettings, {}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SessionsSettings, {})
		})] })
	});
}
//#endregion
export { SettingsView as SettingsPage, SettingsView };
