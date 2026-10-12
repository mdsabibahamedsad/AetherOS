import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { $a as useLocation, eo as useNavigate, oo as require_react } from "./index-B_yd1pEX.js";
//#region src/app/hooks/use-route-enum-param.ts
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
function useRouteEnumParam(key, values, fallback) {
	const { hash, pathname, search } = useLocation();
	const navigate = useNavigate();
	return [(0, import_react.useMemo)(() => {
		const raw = new URLSearchParams(search).get(key);
		return raw && values.includes(raw) ? raw : fallback;
	}, [
		fallback,
		key,
		search,
		values
	]), (0, import_react.useCallback)((next) => {
		const params = new URLSearchParams(search);
		if (next === fallback) params.delete(key);
		else params.set(key, next);
		const qs = params.toString();
		navigate({
			hash,
			pathname,
			search: qs ? `?${qs}` : ""
		}, { replace: true });
	}, [
		fallback,
		hash,
		key,
		navigate,
		pathname,
		search
	])];
}
//#endregion
export { useRouteEnumParam as t };
