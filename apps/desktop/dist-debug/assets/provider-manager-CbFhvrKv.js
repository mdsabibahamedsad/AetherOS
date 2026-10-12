import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { E as Subscribable, b as shallowEqualObjects, h as noop, o as notifyManager, u as hashKey, x as shouldThrowError } from "./query-CgPmas81.js";
import { P as listOAuthProviders, b as getGlobalModelOptions, ct as validateProviderCredential, m as getAuxiliaryModels, v as getEnvVars } from "./aetheros-DF_uJq_t.js";
import { At as Loader, C as Select, Ci as setCurrentModel, D as SelectValue, E as SelectTrigger, La as Button, O as Badge, P as Switch, Ra as cn, T as SelectItem, Ya as useStore, ao as require_jsx_runtime, ci as startManualLocalEndpoint, io as useQueryClient, jt as Textarea, k as Label, ni as Input, oo as require_react, ro as useQuery, so as getDefaultState, ui as startManualProviderOAuth, w as SelectContent, wi as setCurrentProvider } from "./index-B_yd1pEX.js";
import { a as addTesterResult, c as setSelectedProvider, d as updateSettings, i as addHealthEvent, l as updateProvider, n as $providerManager, o as setModels, r as ROUTER_TASKS, s as setProviders, t as ModelManager, u as updateRouterRule } from "./model-manager-6Ji20XFv.js";
//#region ../../node_modules/@tanstack/query-core/build/modern/mutationObserver.js
var MutationObserver = class extends Subscribable {
	#client;
	#currentResult = void 0;
	#currentMutation;
	#mutateOptions;
	constructor(client, options) {
		super();
		this.#client = client;
		this.setOptions(options);
		this.bindMethods();
		this.#updateResult();
	}
	bindMethods() {
		this.mutate = this.mutate.bind(this);
		this.reset = this.reset.bind(this);
	}
	setOptions(options) {
		const prevOptions = this.options;
		this.options = this.#client.defaultMutationOptions(options);
		if (!shallowEqualObjects(this.options, prevOptions)) this.#client.getMutationCache().notify({
			type: "observerOptionsUpdated",
			mutation: this.#currentMutation,
			observer: this
		});
		if (prevOptions?.mutationKey && this.options.mutationKey && hashKey(prevOptions.mutationKey) !== hashKey(this.options.mutationKey)) this.reset();
		else if (this.#currentMutation?.state.status === "pending") this.#currentMutation.setOptions(this.options);
	}
	onUnsubscribe() {
		if (!this.hasListeners()) this.#currentMutation?.removeObserver(this);
	}
	onMutationUpdate(action) {
		this.#updateResult();
		this.#notify(action);
	}
	getCurrentResult() {
		return this.#currentResult;
	}
	reset() {
		this.#currentMutation?.removeObserver(this);
		this.#currentMutation = void 0;
		this.#updateResult();
		this.#notify();
	}
	mutate(variables, options) {
		this.#mutateOptions = options;
		this.#currentMutation?.removeObserver(this);
		this.#currentMutation = this.#client.getMutationCache().build(this.#client, this.options);
		this.#currentMutation.addObserver(this);
		return this.#currentMutation.execute(variables);
	}
	#updateResult() {
		const state = this.#currentMutation?.state ?? getDefaultState();
		this.#currentResult = {
			...state,
			isPending: state.status === "pending",
			isSuccess: state.status === "success",
			isError: state.status === "error",
			isIdle: state.status === "idle",
			mutate: this.mutate,
			reset: this.reset
		};
	}
	#notify(action) {
		notifyManager.batch(() => {
			if (this.#mutateOptions && this.hasListeners()) {
				const variables = this.#currentResult.variables;
				const onMutateResult = this.#currentResult.context;
				const context = {
					client: this.#client,
					meta: this.options.meta,
					mutationKey: this.options.mutationKey
				};
				if (action?.type === "success") {
					try {
						this.#mutateOptions.onSuccess?.(action.data, variables, onMutateResult, context);
					} catch (e) {
						Promise.reject(e);
					}
					try {
						this.#mutateOptions.onSettled?.(action.data, null, variables, onMutateResult, context);
					} catch (e) {
						Promise.reject(e);
					}
				} else if (action?.type === "error") {
					try {
						this.#mutateOptions.onError?.(action.error, variables, onMutateResult, context);
					} catch (e) {
						Promise.reject(e);
					}
					try {
						this.#mutateOptions.onSettled?.(void 0, action.error, variables, onMutateResult, context);
					} catch (e) {
						Promise.reject(e);
					}
				}
			}
			this.listeners.forEach((listener) => {
				listener(this.#currentResult);
			});
		});
	}
};
//#endregion
//#region ../../node_modules/@tanstack/react-query/build/modern/useMutation.js
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
function useMutation(options, queryClient) {
	const client = useQueryClient(queryClient);
	const [observer] = import_react.useState(() => new MutationObserver(client, options));
	import_react.useEffect(() => {
		observer.setOptions(options);
	}, [observer, options]);
	const result = import_react.useSyncExternalStore(import_react.useCallback((onStoreChange) => observer.subscribe(notifyManager.batchCalls(onStoreChange)), [observer]), () => observer.getCurrentResult(), () => observer.getCurrentResult());
	const mutate = import_react.useCallback((variables, mutateOptions) => {
		observer.mutate(variables, mutateOptions).catch(noop);
	}, [observer]);
	if (result.error && shouldThrowError(observer.options.throwOnError, [result.error])) throw result.error;
	return {
		...result,
		mutate,
		mutateAsync: result.mutate
	};
}
//#endregion
//#region src/app/provider-manager/health-monitor.tsx
var import_jsx_runtime = require_jsx_runtime();
var HEALTH_GRADIENTS = {
	online: "from-green-500/20 to-green-500/5 border-green-500/30",
	offline: "from-red-500/20 to-red-500/5 border-red-500/30",
	auth_failed: "from-yellow-500/20 to-yellow-500/5 border-yellow-500/30",
	quota_exceeded: "from-orange-500/20 to-orange-500/5 border-orange-500/30",
	slow: "from-yellow-400/20 to-yellow-400/5 border-yellow-400/30",
	unavailable: "from-gray-400/20 to-gray-400/5 border-gray-400/30",
	unknown: "from-gray-300/20 to-gray-300/5 border-gray-300/30"
};
var HEALTH_DOTS = {
	online: "bg-green-500",
	offline: "bg-red-500",
	auth_failed: "bg-yellow-500",
	quota_exceeded: "bg-orange-500",
	slow: "bg-yellow-400",
	unavailable: "bg-gray-400",
	unknown: "bg-gray-300"
};
function HealthMonitor() {
	const state = useStore($providerManager);
	const stats = (0, import_react.useMemo)(() => {
		return {
			total: state.providers.length,
			online: state.providers.filter((p) => p.health === "online").length,
			offline: state.providers.filter((p) => p.health === "offline" || p.health === "unavailable").length,
			authFailed: state.providers.filter((p) => p.health === "auth_failed").length,
			unknown: state.providers.filter((p) => p.health === "unknown").length
		};
	}, [state.providers]);
	const runAllChecks = () => {
		state.providers.forEach((p) => {
			const statuses = [
				"online",
				"online",
				"online",
				"slow",
				"online",
				"auth_failed"
			];
			const status = p.authenticated ? statuses[Math.floor(Math.random() * statuses.length)] : "auth_failed";
			addHealthEvent({
				provider: p.slug,
				status,
				latencyMs: Math.floor(Math.random() * 2e3) + 50,
				timestamp: (/* @__PURE__ */ new Date()).toISOString(),
				error: status === "auth_failed" ? "Authentication failed" : status === "offline" ? "Connection refused" : null
			});
		});
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-1 flex-col overflow-hidden",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center justify-between border-b px-6 py-4",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
					className: "text-lg font-semibold",
					children: "Provider Health"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-sm text-muted-foreground",
					children: "Real-time health monitoring for all providers"
				})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: runAllChecks,
					size: "sm",
					variant: "outline",
					children: "Check All"
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "grid grid-cols-4 gap-4 border-b px-6 py-4",
				children: [
					{
						label: "Online",
						count: stats.online,
						color: "text-green-600"
					},
					{
						label: "Offline",
						count: stats.offline,
						color: "text-red-600"
					},
					{
						label: "Auth Failed",
						count: stats.authFailed,
						color: "text-yellow-600"
					},
					{
						label: "Unknown",
						count: stats.unknown,
						color: "text-gray-500"
					}
				].map((stat) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "rounded-lg border p-3 text-center",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: cn("text-2xl font-bold", stat.color),
						children: stat.count
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "text-xs text-muted-foreground",
						children: stat.label
					})]
				}, stat.label))
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex-1 overflow-y-auto p-6",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "mx-auto max-w-2xl space-y-2",
					children: state.providers.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "py-8 text-center text-sm text-muted-foreground",
						children: "No providers configured"
					}) : state.providers.map((provider) => {
						const gradient = HEALTH_GRADIENTS[provider.health];
						const dot = HEALTH_DOTS[provider.health];
						return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: cn("flex items-center gap-4 rounded-xl border p-4", gradient),
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("h-3 w-3 shrink-0 rounded-full", dot) }),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex-1 min-w-0",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex items-center gap-2",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "font-medium truncate",
											children: provider.name
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
											className: "text-[10px] h-5 capitalize",
											variant: "outline",
											children: provider.health
										})]
									}), provider.latencyMs !== null && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
										className: "text-xs text-muted-foreground",
										children: [
											"Latency: ",
											/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
												className: "font-mono",
												children: [provider.latencyMs, "ms"]
											}),
											provider.lastSync && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [" · Last check: ", new Date(provider.lastSync).toLocaleTimeString()] })
										]
									})]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
									onClick: () => {
										const statuses = [
											"online",
											"online",
											"slow",
											"online"
										];
										const status = provider.authenticated ? statuses[Math.floor(Math.random() * statuses.length)] : "auth_failed";
										addHealthEvent({
											provider: provider.slug,
											status,
											latencyMs: Math.floor(Math.random() * 500) + 30,
											timestamp: (/* @__PURE__ */ new Date()).toISOString(),
											error: null
										});
									},
									size: "sm",
									variant: "ghost",
									children: "Check"
								})
							]
						}, provider.slug);
					})
				})
			})
		]
	});
}
//#endregion
//#region src/app/provider-manager/model-router.tsx
var TASK_ICONS = {
	default: "💬",
	coding: "</>",
	reasoning: "🧠",
	vision: "👁",
	embedding: "📐",
	voice: "🎤",
	automation: "⚡",
	research: "🔍"
};
function ModelRouter(_props) {
	const state = useStore($providerManager);
	const providerOptions = (0, import_react.useMemo)(() => {
		const seen = /* @__PURE__ */ new Set();
		return state.providers.filter((p) => p.authenticated).map((p) => ({
			slug: p.slug,
			name: p.name
		})).filter((p) => {
			const k = p.slug;
			if (seen.has(k)) return false;
			seen.add(k);
			return true;
		});
	}, [state.providers]);
	const getModelsForProvider = (slug) => state.models.filter((m) => m.provider === slug && !m.hidden);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-1 flex-col overflow-hidden",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "border-b px-6 py-4",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "text-lg font-semibold",
				children: "Model Router"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-sm text-muted-foreground",
				children: "Assign default models for different task types"
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "flex-1 overflow-y-auto p-6",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "mx-auto max-w-3xl space-y-4",
				children: ROUTER_TASKS.map((task) => {
					const rule = state.routerRules.find((r) => r.task === task.id);
					if (!rule) return null;
					const availableModels = rule.provider ? getModelsForProvider(rule.provider) : [];
					const selectedModel = availableModels.find((m) => m.id === rule.model);
					return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: cn("rounded-xl border p-5 transition-all", rule.enabled ? "" : "opacity-50"),
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center justify-between",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center gap-3",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-lg",
										children: TASK_ICONS[task.id] || "📋"
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
										className: "font-medium",
										children: task.label
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "text-xs text-muted-foreground",
										children: rule.provider && rule.model ? `Routed to ${selectedModel?.name?.split("/").pop() ?? rule.model} via ${state.providers.find((p) => p.slug === rule.provider)?.name ?? rule.provider}` : "No model assigned — uses default chat model"
									})] })]
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
									checked: rule.enabled,
									onCheckedChange: (v) => updateRouterRule(task.id, { enabled: v })
								})]
							}),
							rule.enabled && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "mt-4 grid grid-cols-2 gap-3",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "space-y-1.5",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
										className: "text-xs text-muted-foreground",
										children: "Provider"
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
										onValueChange: (v) => updateRouterRule(task.id, {
											provider: v || null,
											model: null
										}),
										value: rule.provider ?? "",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, { placeholder: "Auto (use main)" }) }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SelectContent, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
											value: "",
											children: "Auto (use main)"
										}), providerOptions.map((p) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
											value: p.slug,
											children: p.name
										}, p.slug))] })]
									})]
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "space-y-1.5",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
										className: "text-xs text-muted-foreground",
										children: "Model"
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
										disabled: !rule.provider,
										onValueChange: (v) => updateRouterRule(task.id, { model: v || null }),
										value: rule.model ?? "",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, { placeholder: rule.provider ? "Select model" : "Select provider first" }) }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectContent, { children: availableModels.map((m) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
											value: m.id,
											children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
												className: "flex items-center gap-2",
												children: [
													m.name.split("/").pop(),
													m.capabilities.reasoning && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
														className: "text-[10px] h-4",
														variant: "outline",
														children: "R"
													}),
													m.capabilities.vision && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
														className: "text-[10px] h-4",
														variant: "outline",
														children: "V"
													})
												]
											})
										}, m.id)) })]
									})]
								})]
							}),
							rule.provider && rule.model && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "mt-3 flex items-center gap-2 rounded-lg bg-primary/5 px-3 py-2 text-xs text-muted-foreground",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("svg", {
									className: "h-3.5 w-3.5 shrink-0",
									fill: "none",
									stroke: "currentColor",
									strokeWidth: 2,
									viewBox: "0 0 24 24",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", { d: "M9 18l6-6-6-6" })
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
									className: "font-mono",
									children: [
										rule.provider,
										"/",
										rule.model.split("/").pop()
									]
								})]
							})
						]
					}, task.id);
				})
			})
		})]
	});
}
//#endregion
//#region src/app/provider-manager/model-tester.tsx
var TEST_PROMPTS = [
	"Write a short poem about artificial intelligence.",
	"Explain quantum computing in simple terms.",
	"Write a function to sort an array in Python.",
	"What is the capital of France?",
	"Summarize the theory of relativity in one paragraph.",
	"Translate \"Hello, how are you?\" to French, Spanish, and Japanese.",
	"Write a haiku about the ocean."
];
function ModelTester() {
	const state = useStore($providerManager);
	const [provider, setProvider] = (0, import_react.useState)("");
	const [model, setModel] = (0, import_react.useState)("");
	const [prompt, setPrompt] = (0, import_react.useState)("");
	const [testing, setTesting] = (0, import_react.useState)(false);
	const providerOptions = (0, import_react.useMemo)(() => {
		const seen = /* @__PURE__ */ new Set();
		return state.providers.filter((p) => p.authenticated).map((p) => ({
			slug: p.slug,
			name: p.name
		})).filter((p) => {
			const k = p.slug;
			if (seen.has(k)) return false;
			seen.add(k);
			return true;
		});
	}, [state.providers]);
	const modelOptions = (0, import_react.useMemo)(() => {
		if (!provider) return [];
		return state.models.filter((m) => m.provider === provider && !m.hidden);
	}, [state.models, provider]);
	const runTest = async () => {
		if (!provider || !model || !prompt.trim()) return;
		setTesting(true);
		const startTime = performance.now();
		await new Promise((r) => setTimeout(r, 500 + Math.random() * 1500));
		const elapsed = performance.now() - startTime;
		const tokensIn = Math.ceil(prompt.length / 4);
		const tokensOut = Math.floor(Math.random() * 200) + 20;
		const tps = tokensOut / (elapsed / 1e3);
		addTesterResult({
			prompt: prompt.slice(0, 100),
			model,
			provider,
			latencyMs: Math.round(elapsed),
			tokensIn,
			tokensOut,
			tokensPerSecond: Math.round(tps * 10) / 10,
			streaming: true,
			error: null,
			timestamp: (/* @__PURE__ */ new Date()).toISOString()
		});
		setTesting(false);
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-1 flex-col overflow-hidden",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "border-b px-6 py-4",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "text-lg font-semibold",
				children: "Model Tester"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-sm text-muted-foreground",
				children: "Test any model with a custom prompt"
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "flex-1 overflow-y-auto p-6",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mx-auto max-w-3xl space-y-6",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "grid grid-cols-2 gap-4",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "space-y-1.5",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
								className: "text-xs text-muted-foreground",
								children: "Provider"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
								onValueChange: (v) => {
									setProvider(v);
									setModel("");
								},
								value: provider,
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, { placeholder: "Select provider" }) }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectContent, { children: providerOptions.map((p) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: p.slug,
									children: p.name
								}, p.slug)) })]
							})]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "space-y-1.5",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
								className: "text-xs text-muted-foreground",
								children: "Model"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
								disabled: !provider,
								onValueChange: setModel,
								value: model,
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, { placeholder: provider ? "Select model" : "Select provider first" }) }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectContent, { children: modelOptions.map((m) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: m.id,
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: "flex items-center gap-2",
										children: [m.name.split("/").pop(), m.speed === "fast" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
											className: "text-[10px] h-4",
											variant: "outline",
											children: "Fast"
										})]
									})
								}, m.id)) })]
							})]
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "space-y-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center justify-between",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
								className: "text-xs text-muted-foreground",
								children: "Test Prompt"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "flex gap-1",
								children: TEST_PROMPTS.slice(0, 3).map((p, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
									className: "rounded bg-muted px-2 py-0.5 text-[10px] text-muted-foreground hover:bg-accent",
									onClick: () => setPrompt(p),
									type: "button",
									children: ["Prompt ", i + 1]
								}, i))
							})]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Textarea, {
							className: "resize-none font-mono text-sm",
							onChange: (e) => setPrompt(e.target.value),
							placeholder: "Enter a test prompt...",
							rows: 4,
							value: prompt
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						className: "w-full",
						disabled: !provider || !model || !prompt.trim() || testing,
						onClick: runTest,
						children: testing ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
							className: "flex items-center gap-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" }), "Testing..."]
						}) : "Run Test"
					}),
					state.testerResults.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "space-y-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
							className: "text-sm font-medium text-muted-foreground",
							children: "Recent Results"
						}), [...state.testerResults].reverse().slice(0, 5).map((result, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: cn("rounded-xl border p-4", result.error ? "border-red-500/20 bg-red-500/5" : "border-green-500/20 bg-green-500/5"),
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex items-center justify-between text-sm",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex items-center gap-2",
										children: [
											result.error ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
												className: "text-destructive text-xs",
												children: "✗"
											}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
												className: "text-green-600 text-xs",
												children: "✓"
											}),
											/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
												className: "font-medium text-xs",
												children: result.model.split("/").pop()
											}),
											/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
												className: "text-muted-foreground text-xs",
												children: ["via ", result.provider]
											})
										]
									}), !result.error && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex items-center gap-3 text-xs text-muted-foreground",
										children: [
											/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [result.latencyMs, "ms"] }),
											/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [result.tokensPerSecond.toFixed(1), " t/s"] }),
											/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [
												result.tokensIn,
												"→",
												result.tokensOut,
												" tokens"
											] })
										]
									})]
								}),
								result.error && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
									className: "mt-1 text-xs text-destructive",
									children: result.error
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
									className: "mt-1.5 text-xs text-muted-foreground truncate",
									children: result.prompt
								})
							]
						}, i))]
					})
				]
			})
		})]
	});
}
//#endregion
//#region src/app/provider-manager/provider-detail.tsx
var HEALTH_BADGES = {
	online: {
		label: "Online",
		className: "bg-green-500/10 text-green-600 border-green-500/30"
	},
	offline: {
		label: "Offline",
		className: "bg-red-500/10 text-red-600 border-red-500/30"
	},
	auth_failed: {
		label: "Auth Failed",
		className: "bg-yellow-500/10 text-yellow-600 border-yellow-500/30"
	},
	quota_exceeded: {
		label: "Quota Exceeded",
		className: "bg-orange-500/10 text-orange-600 border-orange-500/30"
	},
	slow: {
		label: "Slow",
		className: "bg-yellow-400/10 text-yellow-600 border-yellow-400/30"
	},
	unavailable: {
		label: "Unavailable",
		className: "bg-gray-400/10 text-gray-600 border-gray-400/30"
	},
	unknown: {
		label: "Checking...",
		className: "bg-gray-300/10 text-gray-500 border-gray-300/30"
	}
};
function ModelRow({ model, onAssignRole }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex items-center gap-3 rounded-lg border px-4 py-2.5 text-sm",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { className: cn("h-2 w-2 rounded-full", model.speed === "fast" ? "bg-green-500" : model.capabilities.reasoning ? "bg-purple-500" : "bg-blue-500") }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "flex-1 font-mono",
				children: model.name.split("/").pop()
			}),
			model.pricing?.free && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
				className: "text-[10px] h-5 border-green-500/30 text-green-600",
				variant: "outline",
				children: "Free"
			}),
			model.pricing && !model.pricing.free && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
				className: "text-xs text-muted-foreground",
				children: [
					"$",
					model.pricing.input,
					"/M"
				]
			}),
			model.capabilities.vision && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
				className: "text-[10px] h-5",
				variant: "secondary",
				children: "Vision"
			}),
			model.capabilities.reasoning && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
				className: "text-[10px] h-5",
				variant: "secondary",
				children: "Reasoning"
			})
		]
	});
}
function ProviderDetail({ provider, models, onBack, onMainModelChanged }) {
	const [apiKey, setApiKey] = (0, import_react.useState)("");
	const [baseUrl, setBaseUrl] = (0, import_react.useState)(provider.baseUrl ?? "");
	const [showKey, setShowKey] = (0, import_react.useState)(false);
	const [testing, setTesting] = (0, import_react.useState)(false);
	const [testResult, setTestResult] = (0, import_react.useState)(null);
	const healthBadge = HEALTH_BADGES[provider.health] || HEALTH_BADGES.unknown;
	const validateMutation = useMutation({
		mutationFn: async () => {
			if (!apiKey.trim()) throw new Error("API key required");
			return validateProviderCredential(provider.keyEnv ?? provider.slug, apiKey, apiKey);
		},
		onSuccess: (result) => {
			updateProvider(provider.slug, {
				authenticated: true,
				connected: true,
				health: "online"
			});
			setTestResult("Connection successful");
		},
		onError: (err) => {
			setTestResult(`Failed: ${err.message}`);
		}
	});
	const runHealthCheck = (0, import_react.useCallback)(async () => {
		setTesting(true);
		setTestResult(null);
		await new Promise((r) => setTimeout(r, 1e3));
		updateProvider(provider.slug, { health: provider.authenticated ? "online" : "auth_failed" });
		setTesting(false);
	}, [provider.slug, provider.authenticated]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full flex-col overflow-hidden",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", {
			className: "flex shrink-0 items-center gap-3 border-b px-6 py-3",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
					className: "text-muted-foreground hover:text-foreground",
					onClick: onBack,
					type: "button",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("svg", {
						className: "h-5 w-5",
						fill: "none",
						stroke: "currentColor",
						strokeWidth: 2,
						viewBox: "0 0 24 24",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", { d: "M19 12H5M12 19l-7-7 7-7" })
					})
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-primary/20 to-primary/5 ring-1 ring-primary/20",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "text-xs font-bold",
						children: provider.name.slice(0, 2).toUpperCase()
					})
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex-1",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
						className: "font-semibold",
						children: provider.name
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
						className: "text-xs text-muted-foreground",
						children: [
							provider.slug,
							" · ",
							provider.modelCount,
							" models"
						]
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
					className: cn("border", healthBadge.className),
					children: healthBadge.label
				})
			]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "flex-1 overflow-y-auto p-6",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mx-auto grid max-w-4xl grid-cols-3 gap-6",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "col-span-2 space-y-6",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-xl border p-5",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
							className: "mb-4 text-sm font-medium text-muted-foreground uppercase tracking-wider",
							children: "Authentication"
						}), provider.authType === "api_key" ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "space-y-3",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "space-y-2",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "API Key" }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex gap-2",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
											className: "flex-1 font-mono text-sm",
											onChange: (e) => setApiKey(e.target.value),
											placeholder: provider.authenticated ? "••••••••••" : "sk-...",
											type: showKey ? "text" : "password",
											value: apiKey
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
											"aria-label": showKey ? "Hide API key" : "Show API key",
											className: "shrink-0",
											onClick: () => setShowKey(!showKey),
											size: "icon",
											variant: "outline",
											children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("svg", {
												className: "h-4 w-4",
												fill: "none",
												stroke: "currentColor",
												strokeWidth: 2,
												viewBox: "0 0 24 24",
												children: showKey ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", { d: "M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" }) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", { d: "M1 1l22 22M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" })
											})
										})]
									})]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
									className: "w-full",
									disabled: !apiKey.trim() || validateMutation.isPending,
									onClick: () => validateMutation.mutate(),
									children: validateMutation.isPending ? "Validating..." : provider.authenticated ? "Update Key" : "Connect"
								}),
								testResult && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
									className: cn("text-sm", testResult.includes("successful") ? "text-green-600" : "text-destructive"),
									children: testResult
								})
							]
						}) : provider.authType === "oauth" ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "space-y-3",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-sm text-muted-foreground",
								children: "This provider uses OAuth authentication."
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
								className: "w-full",
								onClick: () => startManualProviderOAuth(provider.slug),
								variant: "default",
								children: ["Sign in with ", provider.name]
							})]
						}) : /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "space-y-3",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "space-y-2",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "Base URL" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
									className: "font-mono text-sm",
									onChange: (e) => setBaseUrl(e.target.value),
									placeholder: provider.slug === "ollama" ? "http://127.0.0.1:11434" : "http://127.0.0.1:8000/v1",
									value: baseUrl
								})]
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								className: "w-full",
								onClick: () => startManualLocalEndpoint(),
								children: "Connect"
							})]
						})]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-xl border p-5",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "mb-4 flex items-center justify-between",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("h3", {
								className: "text-sm font-medium text-muted-foreground uppercase tracking-wider",
								children: [
									"Models (",
									models.length,
									")"
								]
							}), onMainModelChanged && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								size: "sm",
								variant: "outline",
								children: "Set as Default"
							})]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "space-y-2",
							children: [models.slice(0, 20).map((m) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ModelRow, {
								model: m,
								onAssignRole: () => {}
							}, m.id)), models.length > 20 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
								className: "pt-2 text-center text-xs text-muted-foreground",
								children: [
									"+",
									models.length - 20,
									" more models"
								]
							})]
						})]
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "space-y-6",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "rounded-xl border p-5",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
								className: "mb-4 text-sm font-medium text-muted-foreground uppercase tracking-wider",
								children: "Health"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "space-y-3",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex items-center justify-between text-sm",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "text-muted-foreground",
											children: "Status"
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
											className: cn("border", healthBadge.className),
											children: healthBadge.label
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex items-center justify-between text-sm",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "text-muted-foreground",
											children: "Latency"
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "font-mono",
											children: provider.latencyMs ? `${provider.latencyMs}ms` : "—"
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex items-center justify-between text-sm",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "text-muted-foreground",
											children: "Last Sync"
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "text-xs",
											children: provider.lastSync ?? "Never"
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
										className: "w-full",
										disabled: testing,
										onClick: runHealthCheck,
										size: "sm",
										variant: "outline",
										children: [testing ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Loader, { className: "mr-2 h-3 w-3" }) : null, testing ? "Checking..." : "Run Health Check"]
									})
								]
							})]
						}),
						provider.usage && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "rounded-xl border p-5",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
								className: "mb-4 text-sm font-medium text-muted-foreground uppercase tracking-wider",
								children: "Usage"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "space-y-3",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex items-center justify-between text-sm",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "text-muted-foreground",
											children: "Today"
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
											className: "font-mono",
											children: [(provider.usage.dailyTokens / 1e3).toFixed(0), "K tokens"]
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex items-center justify-between text-sm",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "text-muted-foreground",
											children: "This Month"
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
											className: "font-mono",
											children: [(provider.usage.monthlyTokens / 1e6).toFixed(1), "M tokens"]
										})]
									}),
									provider.usage.creditsRemaining !== null && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex items-center justify-between text-sm",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "text-muted-foreground",
											children: "Credits"
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
											className: "font-mono",
											children: ["$", provider.usage.creditsRemaining.toFixed(2)]
										})]
									})
								]
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "rounded-xl border p-5",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
								className: "mb-4 text-sm font-medium text-muted-foreground uppercase tracking-wider",
								children: "Details"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "space-y-2 text-sm",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex justify-between",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "text-muted-foreground",
											children: "Type"
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "capitalize",
											children: provider.category
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex justify-between",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "text-muted-foreground",
											children: "Auth"
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "capitalize",
											children: provider.authType.replace("_", " ")
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex justify-between",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "text-muted-foreground",
											children: "Version"
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: provider.version ?? "—" })]
									})
								]
							})]
						})
					]
				})]
			})
		})]
	});
}
//#endregion
//#region src/app/provider-manager/provider-hub.tsx
var PROVIDER_GRADIENTS = {
	openai: "from-emerald-500/20 to-emerald-500/5 ring-emerald-500/20",
	anthropic: "from-amber-500/20 to-amber-500/5 ring-amber-500/20",
	gemini: "from-blue-500/20 to-blue-500/5 ring-blue-500/20",
	openrouter: "from-purple-500/20 to-purple-500/5 ring-purple-500/20",
	"azure-openai": "from-sky-500/20 to-sky-500/5 ring-sky-500/20",
	deepseek: "from-cyan-500/20 to-cyan-500/5 ring-cyan-500/20",
	mistral: "from-rose-500/20 to-rose-500/5 ring-rose-500/20",
	groq: "from-green-500/20 to-green-500/5 ring-green-500/20",
	"fireworks-ai": "from-orange-500/20 to-orange-500/5 ring-orange-500/20",
	"together-ai": "from-violet-500/20 to-violet-500/5 ring-violet-500/20",
	cerebras: "from-yellow-500/20 to-yellow-500/5 ring-yellow-500/20",
	cohere: "from-blue-600/20 to-blue-600/5 ring-blue-600/20",
	xai: "from-fuchsia-500/20 to-fuchsia-500/5 ring-fuchsia-500/20",
	perplexity: "from-indigo-500/20 to-indigo-500/5 ring-indigo-500/20",
	"hugging-face": "from-yellow-600/20 to-yellow-600/5 ring-yellow-600/20",
	ollama: "from-orange-600/20 to-orange-600/5 ring-orange-600/20",
	"lm-studio": "from-gray-500/20 to-gray-500/5 ring-gray-500/20"
};
var PROVIDER_LOGOS = {
	openai: "O",
	anthropic: "A",
	gemini: "Gm",
	openrouter: "OR",
	"azure-openai": "Az",
	deepseek: "DS",
	mistral: "Mi",
	groq: "Gr",
	"fireworks-ai": "FA",
	"together-ai": "TA",
	cerebras: "C",
	cohere: "Co",
	xai: "X",
	perplexity: "Px",
	"hugging-face": "HF",
	ollama: "Ol",
	"lm-studio": "LM",
	vllm: "vL",
	"llama-cpp": "lCP",
	"text-generation-webui": "TG",
	koboldcpp: "KC",
	local: "Cu"
};
var HEALTH_COLORS = {
	online: "bg-green-500",
	offline: "bg-red-500",
	auth_failed: "bg-yellow-500",
	quota_exceeded: "bg-orange-500",
	slow: "bg-yellow-400",
	unavailable: "bg-gray-400",
	unknown: "bg-gray-300"
};
function ProviderCard({ provider, onSelect }) {
	const gradient = PROVIDER_GRADIENTS[provider.slug] || "from-gray-500/20 to-gray-500/5 ring-gray-500/20";
	const logo = PROVIDER_LOGOS[provider.slug] || provider.slug.slice(0, 2).toUpperCase();
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
		className: "group relative flex flex-col gap-3 rounded-xl border bg-card p-5 text-left transition-all hover:border-muted-foreground/30 hover:shadow-sm",
		onClick: onSelect,
		type: "button",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-start justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: cn("flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br ring-1", gradient),
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "text-sm font-bold text-foreground/80",
						children: logo
					})
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-1.5",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: cn("h-2 w-2 rounded-full", HEALTH_COLORS[provider.health] || HEALTH_COLORS.unknown) }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "text-xs text-muted-foreground capitalize",
						children: provider.health === "unknown" ? provider.authenticated ? "connected" : "disconnected" : provider.health
					})]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
				className: "font-medium",
				children: provider.name
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
				className: "mt-0.5 text-xs text-muted-foreground",
				children: [provider.modelCount, " models"]
			})] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-wrap gap-1.5",
				children: [
					provider.authenticated ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
						className: "border-green-500/30 text-green-600 text-[10px] h-5",
						variant: "outline",
						children: "Connected"
					}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
						className: "text-[10px] h-5",
						variant: "outline",
						children: "Not connected"
					}),
					provider.category === "local" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
						className: "text-[10px] h-5",
						variant: "secondary",
						children: "Local"
					}),
					provider.authType === "oauth" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
						className: "text-[10px] h-5",
						variant: "outline",
						children: "OAuth"
					})
				]
			}),
			provider.usage && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mt-1 space-y-1 text-xs text-muted-foreground",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex justify-between",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: "Today" }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [(provider.usage.dailyTokens / 1e3).toFixed(0), "K tokens"] })]
				}), provider.usage.creditsRemaining !== null && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex justify-between",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: "Credits" }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: ["$", provider.usage.creditsRemaining.toFixed(2)] })]
				})]
			})
		]
	});
}
function ProviderSection({ title, providers, onSelect }) {
	if (providers.length === 0) return null;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "space-y-3",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
			className: "text-sm font-medium text-muted-foreground uppercase tracking-wider",
			children: title
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-4",
			children: providers.map((p) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ProviderCard, {
				onSelect: () => onSelect(p.slug),
				provider: p
			}, p.slug))
		})]
	});
}
function ProviderHub({ providers, search, onSearchChange, onSelectProvider }) {
	const filtered = (0, import_react.useMemo)(() => {
		if (!search.trim()) return providers;
		const q = search.toLowerCase();
		return providers.filter((p) => p.name.toLowerCase().includes(q) || p.slug.toLowerCase().includes(q));
	}, [providers, search]);
	const cloud = filtered.filter((p) => p.category === "cloud");
	const local = filtered.filter((p) => p.category === "local");
	const custom = filtered.filter((p) => p.category === "custom");
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex-1 overflow-y-auto p-6",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "mb-6",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
					className: "max-w-md font-mono text-sm",
					onChange: (e) => onSearchChange(e.target.value),
					placeholder: "Search providers...",
					value: search
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-8",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ProviderSection, {
						onSelect: onSelectProvider,
						providers: cloud,
						title: "Cloud Providers"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ProviderSection, {
						onSelect: onSelectProvider,
						providers: local,
						title: "Local Providers"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ProviderSection, {
						onSelect: onSelectProvider,
						providers: custom,
						title: "Custom & Compatible"
					})
				]
			}),
			filtered.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "py-12 text-center text-sm text-muted-foreground",
				children: "No providers found"
			})
		]
	});
}
//#endregion
//#region src/app/provider-manager/settings.tsx
function ProviderSettings() {
	const settings = useStore($providerManager).settings;
	const providers = useStore($providerManager).providers.filter((p) => p.authenticated);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-1 flex-col overflow-hidden",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "border-b px-6 py-4",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "text-lg font-semibold",
				children: "Provider Settings"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-sm text-muted-foreground",
				children: "Global settings for AI provider connections"
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "flex-1 overflow-y-auto p-6",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mx-auto max-w-2xl space-y-8",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-xl border p-5",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
							className: "mb-4 text-sm font-medium text-muted-foreground uppercase tracking-wider",
							children: "Connection"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "space-y-4",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "grid grid-cols-2 gap-4",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "space-y-2",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "Timeout (ms)" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
											className: "font-mono text-sm",
											onChange: (e) => updateSettings({ timeout: parseInt(e.target.value) || 3e4 }),
											type: "number",
											value: settings.timeout
										})]
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "space-y-2",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "Max Retries" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
											className: "font-mono text-sm",
											onChange: (e) => updateSettings({ retries: parseInt(e.target.value) || 3 }),
											type: "number",
											value: settings.retries
										})]
									})]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "space-y-2",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "Max Concurrent Requests" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
										className: "font-mono text-sm max-w-[200px]",
										onChange: (e) => updateSettings({ maxConcurrency: parseInt(e.target.value) || 5 }),
										type: "number",
										value: settings.maxConcurrency
									})]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "grid grid-cols-2 gap-4",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "space-y-2",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "Fallback Provider" }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
											onValueChange: (v) => updateSettings({ fallbackProvider: v || null }),
											value: settings.fallbackProvider ?? "",
											children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, { placeholder: "None" }) }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SelectContent, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
												value: "",
												children: "None"
											}), providers.map((p) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
												value: p.slug,
												children: p.name
											}, p.slug))] })]
										})]
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "space-y-2",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, { children: "Preferred Provider" }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
											onValueChange: (v) => updateSettings({ preferredProvider: v || null }),
											value: settings.preferredProvider ?? "",
											children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, { placeholder: "Auto" }) }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SelectContent, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
												value: "",
												children: "Auto"
											}), providers.map((p) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
												value: p.slug,
												children: p.name
											}, p.slug))] })]
										})]
									})]
								})
							]
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-xl border p-5",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
							className: "mb-4 text-sm font-medium text-muted-foreground uppercase tracking-wider",
							children: "Features"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "space-y-4",
							children: [
								{
									id: "streaming",
									label: "Streaming",
									description: "Enable streaming responses"
								},
								{
									id: "parallelRequests",
									label: "Parallel Requests",
									description: "Allow concurrent requests to the same provider"
								},
								{
									id: "caching",
									label: "Response Caching",
									description: "Cache responses for identical requests"
								},
								{
									id: "compression",
									label: "Compression",
									description: "Compress request/response data"
								}
							].map((feature) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center justify-between rounded-lg border p-4",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, {
									className: "text-base",
									children: feature.label
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
									className: "text-sm text-muted-foreground",
									children: feature.description
								})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
									checked: settings[feature.id],
									onCheckedChange: (v) => updateSettings({ [feature.id]: v })
								})]
							}, feature.id))
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex justify-end gap-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							variant: "outline",
							children: "Reset to Defaults"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, { children: "Save Settings" })]
					})
				]
			})
		})]
	});
}
//#endregion
//#region src/app/provider-manager/usage-dashboard.tsx
function UsageDashboard() {
	const state = useStore($providerManager);
	const usage = (0, import_react.useMemo)(() => {
		const providers = state.providers.filter((p) => p.usage);
		return {
			totalDailyTokens: providers.reduce((s, p) => s + (p.usage?.dailyTokens ?? 0), 0),
			totalMonthlyTokens: providers.reduce((s, p) => s + (p.usage?.monthlyTokens ?? 0), 0),
			totalDailyCost: providers.reduce((s, p) => s + (p.usage?.dailyCost ?? 0), 0),
			totalMonthlyCost: providers.reduce((s, p) => s + (p.usage?.monthlyCost ?? 0), 0),
			providerCount: providers.length
		};
	}, [state.providers]);
	const modelUsage = (0, import_react.useMemo)(() => {
		return state.models.map((m, i) => ({
			name: m.name.split("/").pop() ?? m.name,
			provider: m.providerName,
			calls: Math.floor(Math.random() * 1e3),
			tokens: Math.floor(Math.random() * 1e6),
			cost: Math.random() * 10
		})).sort((a, b) => b.calls - a.calls).slice(0, 10);
	}, [state.models]);
	const dailyData = [
		"Mon",
		"Tue",
		"Wed",
		"Thu",
		"Fri",
		"Sat",
		"Sun"
	].map((d) => ({
		day: d,
		tokens: Math.floor(Math.random() * 5e5) + 5e4
	}));
	const maxTokens = Math.max(...dailyData.map((d) => d.tokens));
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-1 flex-col overflow-hidden",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "border-b px-6 py-4",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "text-lg font-semibold",
				children: "Usage Dashboard"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-sm text-muted-foreground",
				children: "Token consumption and cost across all providers"
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "flex-1 overflow-y-auto p-6",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mx-auto max-w-4xl space-y-8",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "grid grid-cols-4 gap-4",
						children: [
							{
								label: "Daily Tokens",
								value: `${(usage.totalDailyTokens / 1e3).toFixed(0)}K`,
								sub: `$${usage.totalDailyCost.toFixed(2)}`
							},
							{
								label: "Monthly Tokens",
								value: `${(usage.totalMonthlyTokens / 1e6).toFixed(1)}M`,
								sub: `$${usage.totalMonthlyCost.toFixed(2)}`
							},
							{
								label: "Active Providers",
								value: String(usage.providerCount),
								sub: `${state.providers.length} total`
							},
							{
								label: "Models Used",
								value: String(state.models.filter((m) => m.roles.length > 0).length),
								sub: `${state.models.length} available`
							}
						].map((stat) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "rounded-xl border p-4",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "text-xs text-muted-foreground",
									children: stat.label
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "mt-1 text-2xl font-bold",
									children: stat.value
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "mt-0.5 text-xs text-muted-foreground",
									children: stat.sub
								})
							]
						}, stat.label))
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-xl border p-5",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
							className: "mb-4 text-sm font-medium text-muted-foreground uppercase tracking-wider",
							children: "Daily Token Consumption"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "flex items-end gap-2",
							style: { height: 120 },
							children: dailyData.map((d) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex flex-1 flex-col items-center gap-1",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: "text-[10px] text-muted-foreground",
										children: [(d.tokens / 1e3).toFixed(0), "K"]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
										className: "w-full rounded-t bg-gradient-to-t from-primary/40 to-primary/20 transition-all",
										style: { height: `${d.tokens / maxTokens * 80}px` }
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-[10px] text-muted-foreground",
										children: d.day
									})
								]
							}, d.day))
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-xl border p-5",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
							className: "mb-4 text-sm font-medium text-muted-foreground uppercase tracking-wider",
							children: "Top Models by Usage"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "space-y-2",
							children: modelUsage.map((m, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-3 rounded-lg border px-4 py-2.5 text-sm",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: cn("w-5 text-xs font-medium", i < 3 ? "text-foreground" : "text-muted-foreground"),
										children: i + 1
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "flex-1 min-w-0",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
											className: "truncate font-medium",
											children: m.name
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
											className: "text-xs text-muted-foreground",
											children: m.provider
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "text-right text-xs",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
											className: "font-mono",
											children: [m.calls.toLocaleString(), " calls"]
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
											className: "text-muted-foreground font-mono",
											children: [(m.tokens / 1e3).toFixed(0), "K tokens"]
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										className: "text-right text-xs font-mono text-muted-foreground",
										children: ["$", m.cost.toFixed(2)]
									})
								]
							}, m.name))
						})]
					})
				]
			})
		})]
	});
}
//#endregion
//#region src/app/provider-manager/index.tsx
var TABS = [
	{
		id: "hub",
		label: "Providers",
		icon: "☁"
	},
	{
		id: "models",
		label: "Models",
		icon: "🧠"
	},
	{
		id: "router",
		label: "Router",
		icon: "↗"
	},
	{
		id: "health",
		label: "Health",
		icon: "♥"
	},
	{
		id: "tester",
		label: "Tester",
		icon: "▶"
	},
	{
		id: "usage",
		label: "Usage",
		icon: "📊"
	},
	{
		id: "settings",
		label: "Settings",
		icon: "⚙"
	}
];
function ProviderManagerView({ onClose, onMainModelChanged }) {
	const state = useStore($providerManager);
	const [activeTab, setActiveTab] = (0, import_react.useState)("hub");
	const [searchQuery, setSearchQuery] = (0, import_react.useState)("");
	const { data: modelOptions } = useQuery({
		queryKey: ["model-options"],
		queryFn: getGlobalModelOptions,
		staleTime: 3e4
	});
	const { data: envVars } = useQuery({
		queryKey: ["env-vars"],
		queryFn: getEnvVars,
		staleTime: 3e4
	});
	const { data: auxModels } = useQuery({
		queryKey: ["auxiliary-models"],
		queryFn: getAuxiliaryModels,
		staleTime: 3e4
	});
	const { data: oauthProviders } = useQuery({
		queryKey: ["oauth-providers"],
		queryFn: listOAuthProviders,
		staleTime: 6e4
	});
	(0, import_react.useEffect)(() => {
		if (!modelOptions?.providers) return;
		new Map(Object.entries(envVars ?? {}));
		const oauthSet = new Set((oauthProviders?.providers ?? []).map((p) => p.id));
		const providers = modelOptions.providers.map((p) => {
			const slug = p.provider ?? "";
			const isLocal = [
				"ollama",
				"lm-studio",
				"vllm",
				"llama-cpp",
				"text-generation-webui",
				"koboldcpp",
				"local"
			].includes(slug);
			const isCustom = p.auth_type === "api_key" && !p.is_current && !isLocal && !oauthSet.has(slug);
			return {
				slug,
				name: p.name,
				category: isLocal ? "local" : isCustom ? "custom" : "cloud",
				authType: p.auth_type || "api_key",
				authenticated: !!p.authenticated,
				connected: !!p.authenticated,
				health: "unknown",
				latencyMs: null,
				modelCount: p.models?.length ?? 0,
				version: null,
				lastSync: null,
				usage: null,
				capabilities: [],
				keyEnv: p.key_env ?? null,
				baseUrl: null
			};
		});
		setProviders(providers);
		const allModels = [];
		const seen = /* @__PURE__ */ new Set();
		for (const p of modelOptions.providers) {
			const pricing = p.pricing;
			const caps = p.capabilities;
			for (const m of p.models ?? []) if (!seen.has(m)) {
				seen.add(m);
				const mp = pricing?.[m];
				const mc = caps?.[m];
				allModels.push({
					id: m,
					provider: p.provider ?? "",
					providerName: p.name,
					name: m,
					contextLength: null,
					maxTokens: null,
					pricing: mp ? {
						input: mp.input ?? "—",
						output: mp.output ?? "—",
						cache: mp.cache ?? null,
						free: mp.free ?? false
					} : null,
					capabilities: {
						vision: m.toLowerCase().includes("vision"),
						audio: m.toLowerCase().includes("audio"),
						functionCalling: true,
						reasoning: mc?.reasoning ?? m.toLowerCase().includes("reasoning"),
						streaming: true,
						embedding: m.toLowerCase().includes("embedding"),
						toolSupport: true
					},
					favorite: false,
					pinned: false,
					hidden: false,
					roles: [],
					latencyMs: null,
					speed: mc?.fast ? "fast" : null
				});
			}
		}
		setModels(allModels);
		if (modelOptions?.provider && modelOptions?.model) {
			setCurrentProvider(modelOptions.provider);
			setCurrentModel(modelOptions.model);
		} else {
			const currentProv = providers.find((p) => p.authenticated);
			if (currentProv) {
				setCurrentProvider(currentProv.slug);
				if (currentProv.modelCount > 0) {
					const firstModel = allModels.find((m) => m.provider === currentProv.slug);
					if (firstModel) setCurrentModel(firstModel.name);
				}
			}
		}
	}, [
		modelOptions,
		envVars,
		oauthProviders
	]);
	const selectedProvider = state.providers.find((p) => p.slug === state.selectedProvider);
	if (state.selectedProvider && selectedProvider && activeTab !== "settings") return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ProviderDetail, {
		models: state.models.filter((m) => m.provider === state.selectedProvider),
		onBack: () => setSelectedProvider(null),
		onMainModelChanged,
		provider: selectedProvider
	});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full flex-col overflow-hidden",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", {
				className: "flex shrink-0 items-center justify-between border-b px-6 py-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
					className: "text-xl font-semibold",
					children: "AI Providers"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
					className: "text-sm text-muted-foreground",
					children: [
						state.providers.filter((p) => p.authenticated).length,
						" connected · ",
						state.providers.length,
						" available · ",
						state.models.length,
						" models"
					]
				})] }), onClose && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
					className: "text-muted-foreground hover:text-foreground",
					onClick: onClose,
					type: "button",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("svg", {
						className: "h-5 w-5",
						fill: "none",
						stroke: "currentColor",
						strokeWidth: 2,
						viewBox: "0 0 24 24",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", { d: "M18 6L6 18M6 6l12 12" })
					})
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex shrink-0 items-center gap-1 border-b px-4",
				children: TABS.map((tab) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
					className: cn("flex items-center gap-1.5 border-b-2 px-4 py-3 text-sm font-medium transition-colors", activeTab === tab.id ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"),
					onClick: () => setActiveTab(tab.id),
					type: "button",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "text-xs",
						children: tab.icon
					}), tab.label]
				}, tab.id))
			}),
			activeTab === "hub" && (activeTab === "hub" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ProviderHub, {
				onSearchChange: setSearchQuery,
				onSelectProvider: (slug) => setSelectedProvider(slug),
				providers: state.providers,
				search: searchQuery
			}) : null),
			activeTab === "models" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ModelManager, {}),
			activeTab === "router" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ModelRouter, { auxModels }),
			activeTab === "health" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(HealthMonitor, {}),
			activeTab === "tester" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ModelTester, {}),
			activeTab === "usage" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(UsageDashboard, {}),
			activeTab === "settings" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ProviderSettings, {})
		]
	});
}
//#endregion
export { ProviderManagerView };
