import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { Di as notify, Ia as Codicon, La as Button, O as Badge, P as Switch, Ra as cn, ao as require_jsx_runtime, ni as Input, oo as require_react } from "./index-B_yd1pEX.js";
import { i as PageTitle, n as PageHeader, r as PageShell, t as PageDescription } from "./page-shell-DlpGsnrD.js";
//#region src/app/connection-wizard/index.tsx
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
var STEPS = [
	{
		id: "type",
		label: "Type",
		icon: "plug"
	},
	{
		id: "config",
		label: "Config",
		icon: "gear"
	},
	{
		id: "scope",
		label: "Scope",
		icon: "checklist"
	},
	{
		id: "encryption",
		label: "Encryption",
		icon: "lock"
	},
	{
		id: "test",
		label: "Test",
		icon: "beaker"
	},
	{
		id: "summary",
		label: "Summary",
		icon: "check"
	}
];
var INITIAL_WIZARD = {
	connectionType: null,
	host: "",
	port: "9443",
	instanceName: "",
	scopes: [
		"messages",
		"sessions",
		"memory",
		"files"
	],
	encryption: "tls",
	psk: "",
	autoReconnect: true,
	tested: false
};
var ALL_SCOPES = [
	{
		id: "messages",
		label: "Messages",
		desc: "Conversation history and messages"
	},
	{
		id: "sessions",
		label: "Sessions",
		desc: "Active session state"
	},
	{
		id: "memory",
		label: "Memory",
		desc: "Agent memory and context"
	},
	{
		id: "files",
		label: "Files",
		desc: "Workspace files"
	},
	{
		id: "config",
		label: "Config",
		desc: "Settings and preferences"
	},
	{
		id: "plugins",
		label: "Plugins",
		desc: "Plugin installations"
	},
	{
		id: "skills",
		label: "Skills",
		desc: "Skill definitions"
	}
];
var connectionTypes = [
	{
		id: "direct",
		label: "Direct Connection",
		desc: "Connect directly via IP/hostname",
		icon: "plug"
	},
	{
		id: "relay",
		label: "Relayed",
		desc: "Connect through a relay server",
		icon: "broadcast"
	},
	{
		id: "lan",
		label: "Local Network",
		desc: "Auto-discover on the local network",
		icon: "organization"
	},
	{
		id: "vpn",
		label: "VPN Tunnel",
		desc: "Connect through encrypted tunnel",
		icon: "shield"
	}
];
function ConnectionWizardView() {
	const [currentStep, setCurrentStep] = (0, import_react.useState)(0);
	const [wizard, setWizard] = (0, import_react.useState)(INITIAL_WIZARD);
	const stepId = STEPS[currentStep].id;
	const isFirst = currentStep === 0;
	const isLast = currentStep === STEPS.length - 1;
	const canProceed = (0, import_react.useMemo)(() => {
		switch (stepId) {
			case "type": return wizard.connectionType !== null;
			case "config": return wizard.host.trim().length > 0 && wizard.instanceName.trim().length > 0;
			case "scope": return wizard.scopes.length > 0;
			case "encryption": return true;
			case "test": return true;
			case "summary": return true;
		}
	}, [stepId, wizard]);
	const handleNext = (0, import_react.useCallback)(() => {
		if (isLast) {
			notify({
				kind: "success",
				title: "Connection Created",
				message: `Connection "${wizard.instanceName}" has been configured`
			});
			setCurrentStep(0);
			setWizard(INITIAL_WIZARD);
			return;
		}
		if (canProceed) setCurrentStep((s) => Math.min(s + 1, STEPS.length - 1));
	}, [
		isLast,
		canProceed,
		wizard
	]);
	const handleBack = (0, import_react.useCallback)(() => {
		setCurrentStep((s) => Math.max(s - 1, 0));
	}, []);
	const handleTest = (0, import_react.useCallback)(() => {
		setTimeout(() => {
			setWizard((w) => ({
				...w,
				tested: true
			}));
			notify({
				kind: "success",
				title: "Test Passed",
				message: `Successfully connected to ${wizard.host}:${wizard.port}`
			});
		}, 1500);
	}, [wizard.host, wizard.port]);
	const toggleScope = (0, import_react.useCallback)((scopeId) => {
		setWizard((w) => ({
			...w,
			scopes: w.scopes.includes(scopeId) ? w.scopes.filter((s) => s !== scopeId) : [...w.scopes, scopeId]
		}));
	}, []);
	const renderStep = () => {
		switch (stepId) {
			case "type": return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
					className: "text-xs font-semibold uppercase tracking-wider text-muted-foreground",
					children: "Choose Connection Type"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "grid gap-2",
					children: connectionTypes.map((ct) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
						className: cn("flex items-center gap-3 rounded-lg border p-3 text-left transition-all", wizard.connectionType === ct.id ? "border-primary/40 bg-primary/5 ring-1 ring-primary/20" : "border-(--ui-stroke-tertiary) hover:border-(--ui-stroke-secondary) hover:bg-accent/30"),
						onClick: () => setWizard((w) => ({
							...w,
							connectionType: ct.id
						})),
						type: "button",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: cn("flex size-9 items-center justify-center rounded-lg", wizard.connectionType === ct.id ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"),
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									name: ct.icon,
									size: "1rem"
								})
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-sm font-medium",
								children: ct.label
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "mt-0.5 text-xs text-muted-foreground",
								children: ct.desc
							})] }),
							wizard.connectionType === ct.id && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
								className: "ml-auto text-primary",
								name: "check",
								size: "1rem"
							})
						]
					}, ct.id))
				})]
			});
			case "config": return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
						className: "text-xs font-semibold uppercase tracking-wider text-muted-foreground",
						children: "Connection Configuration"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
						className: "mb-1 block text-xs text-muted-foreground",
						children: "Instance Name"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						onChange: (e) => setWizard((w) => ({
							...w,
							instanceName: e.target.value
						})),
						placeholder: "My Remote Agent",
						value: wizard.instanceName
					})] }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
						className: "mb-1 block text-xs text-muted-foreground",
						children: "Host"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						onChange: (e) => setWizard((w) => ({
							...w,
							host: e.target.value
						})),
						placeholder: "remote.example.com",
						value: wizard.host
					})] }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
						className: "mb-1 block text-xs text-muted-foreground",
						children: "Port"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						onChange: (e) => setWizard((w) => ({
							...w,
							port: e.target.value
						})),
						placeholder: "9443",
						value: wizard.port
					})] }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between rounded-md bg-(--ui-bg-quinary) px-3 py-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-xs font-medium",
							children: "Auto-Reconnect"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-[0.6rem] text-muted-foreground",
							children: "Automatically reconnect on disconnect"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: wizard.autoReconnect,
							onCheckedChange: (v) => setWizard((w) => ({
								...w,
								autoReconnect: v
							}))
						})]
					})
				]
			});
			case "scope": return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
						className: "text-xs font-semibold uppercase tracking-wider text-muted-foreground",
						children: "Select Sync Scopes"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-xs text-muted-foreground",
						children: "Choose which data scopes to synchronize with this connection"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "space-y-1.5",
						children: ALL_SCOPES.map((scope) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: cn("flex items-center justify-between rounded-md border px-3 py-2 transition-colors", wizard.scopes.includes(scope.id) ? "border-primary/30 bg-primary/5" : "border-(--ui-stroke-tertiary)"),
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-xs font-medium",
								children: scope.label
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-[0.6rem] text-muted-foreground",
								children: scope.desc
							})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
								checked: wizard.scopes.includes(scope.id),
								onCheckedChange: () => toggleScope(scope.id)
							})]
						}, scope.id))
					})
				]
			});
			case "encryption": return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
						className: "text-xs font-semibold uppercase tracking-wider text-muted-foreground",
						children: "Encryption Settings"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "space-y-2",
						children: [
							{
								id: "tls",
								label: "TLS",
								desc: "Standard TLS encryption",
								icon: "lock"
							},
							{
								id: "mtls",
								label: "mTLS",
								desc: "Mutual TLS with client certificates",
								icon: "verified"
							},
							{
								id: "psk",
								label: "Pre-Shared Key",
								desc: "Symmetric key encryption",
								icon: "key"
							},
							{
								id: "none",
								label: "None",
								desc: "Unencrypted (not recommended)",
								icon: "unlock"
							}
						].map((enc) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
							className: cn("flex w-full items-center gap-3 rounded-lg border p-3 text-left transition-all", wizard.encryption === enc.id ? "border-primary/40 bg-primary/5 ring-1 ring-primary/20" : "border-(--ui-stroke-tertiary) hover:border-(--ui-stroke-secondary)"),
							onClick: () => setWizard((w) => ({
								...w,
								encryption: enc.id
							})),
							type: "button",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: cn("flex size-8 items-center justify-center rounded-lg", wizard.encryption === enc.id ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"),
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										name: enc.icon,
										size: "0.85rem"
									})
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex-1",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "text-xs font-medium",
										children: enc.label
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "text-[0.6rem] text-muted-foreground",
										children: enc.desc
									})]
								}),
								wizard.encryption === enc.id && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									className: "text-primary",
									name: "check",
									size: "0.85rem"
								})
							]
						}, enc.id))
					}),
					wizard.encryption === "psk" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
						className: "mb-1 block text-xs text-muted-foreground",
						children: "Pre-Shared Key"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						onChange: (e) => setWizard((w) => ({
							...w,
							psk: e.target.value
						})),
						placeholder: "Enter shared key",
						type: "password",
						value: wizard.psk
					})] })
				]
			});
			case "test": return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
						className: "text-xs font-semibold uppercase tracking-wider text-muted-foreground",
						children: "Test Connection"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "space-y-2 rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-bg-quinary) p-3",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center justify-between text-xs",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "text-muted-foreground",
									children: "Host"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [
									wizard.host,
									":",
									wizard.port
								] })]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center justify-between text-xs",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "text-muted-foreground",
									children: "Type"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "capitalize",
									children: wizard.connectionType
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center justify-between text-xs",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "text-muted-foreground",
									children: "Encryption"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: wizard.encryption === "none" ? "None" : wizard.encryption.toUpperCase() })]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center justify-between text-xs",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "text-muted-foreground",
									children: "Scopes"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [wizard.scopes.length, " selected"] })]
							})
						]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
						className: "w-full",
						disabled: wizard.tested,
						onClick: handleTest,
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							name: "beaker",
							size: "0.85rem"
						}), wizard.tested ? "Test Passed" : "Run Connection Test"]
					}),
					wizard.tested && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-2 rounded-md bg-emerald-500/10 px-3 py-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							className: "text-emerald-500",
							name: "check",
							size: "0.85rem"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "text-xs text-emerald-600",
							children: "Connection successful — latency 12ms"
						})]
					})
				]
			});
			case "summary": return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
						className: "text-xs font-semibold uppercase tracking-wider text-muted-foreground",
						children: "Connection Summary"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "space-y-2 rounded-lg border border-(--ui-stroke-tertiary) p-3",
						children: [
							{
								label: "Name",
								value: wizard.instanceName
							},
							{
								label: "Host",
								value: `${wizard.host}:${wizard.port}`
							},
							{
								label: "Type",
								value: wizard.connectionType ?? "--"
							},
							{
								label: "Encryption",
								value: wizard.encryption === "none" ? "None" : wizard.encryption.toUpperCase()
							},
							{
								label: "Scopes",
								value: `${wizard.scopes.length} selected`
							},
							{
								label: "Auto-Reconnect",
								value: wizard.autoReconnect ? "Yes" : "No"
							}
						].map((item) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center justify-between py-0.5 text-xs",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "text-muted-foreground",
								children: item.label
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "font-medium",
								children: item.value
							})]
						}, item.label))
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
						className: "w-full justify-center py-1",
						variant: wizard.tested ? "default" : "outline",
						children: wizard.tested ? "Connection verified" : "Not tested"
					})
				]
			});
		}
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageShell, {
		header: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageHeader, {
			className: "w-full",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, { children: "New Connection" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageDescription, { children: "Set up a new remote connection step by step" })] })
		}),
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mx-auto max-w-lg",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "mb-6",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "flex items-center justify-between",
						children: STEPS.map((step, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex flex-col items-center",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: cn("flex size-8 items-center justify-center rounded-full text-xs font-medium transition-all", i === currentStep ? "bg-primary text-primary-foreground ring-2 ring-primary/30" : i < currentStep ? "bg-primary/20 text-primary" : "bg-muted text-muted-foreground"),
									children: i < currentStep ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										name: "check",
										size: "0.75rem"
									}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										name: step.icon,
										size: "0.75rem"
									})
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: cn("mt-1 text-[0.55rem]", i === currentStep ? "font-medium text-foreground" : "text-muted-foreground"),
									children: step.label
								})]
							}), i < STEPS.length - 1 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { className: cn("mx-2 h-px w-8 sm:w-12", i < currentStep ? "bg-primary/40" : "bg-(--ui-stroke-tertiary)") })]
						}, step.id))
					})
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-chat-surface-background) p-4",
					children: renderStep()
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "mt-4 flex items-center justify-between",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
						disabled: isFirst,
						onClick: handleBack,
						size: "sm",
						variant: "outline",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							name: "arrow-left",
							size: "0.85rem"
						}), "Back"]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
						disabled: !canProceed,
						onClick: handleNext,
						size: "sm",
						children: [isLast ? "Finish" : "Next", !isLast && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							name: "arrow-right",
							size: "0.85rem"
						})]
					})]
				})
			]
		})
	});
}
//#endregion
export { ConnectionWizardView };
