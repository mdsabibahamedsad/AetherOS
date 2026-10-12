import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { P as listOAuthProviders, b as getGlobalModelOptions, v as getEnvVars } from "./aetheros-DF_uJq_t.js";
import { Ci as setCurrentModel, ao as require_jsx_runtime, oo as require_react, ro as useQuery, wi as setCurrentProvider } from "./index-B_yd1pEX.js";
import { r as PageShell } from "./page-shell-DlpGsnrD.js";
import { o as setModels, s as setProviders, t as ModelManager } from "./model-manager-6Ji20XFv.js";
//#region src/app/models/index.tsx
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
function ModelsView() {
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
	const { data: oauthProviders } = useQuery({
		queryKey: ["oauth-providers"],
		queryFn: listOAuthProviders,
		staleTime: 6e4
	});
	(0, import_react.useEffect)(() => {
		if (!modelOptions?.providers) return;
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
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageShell, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ModelManager, {}) });
}
//#endregion
export { ModelsView };
