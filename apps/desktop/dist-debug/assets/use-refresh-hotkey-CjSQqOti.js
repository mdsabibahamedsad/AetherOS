import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { oo as require_react } from "./index-B_yd1pEX.js";
//#region src/app/hooks/use-refresh-hotkey.ts
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
/**
* Binds the bare `r` key to a refresh action while the calling view is mounted.
* Ignored when a modifier is held, the event repeats, or focus is in an
* editable field (so typing "r" in a search/input never triggers it).
*/
function useRefreshHotkey(onRefresh, enabled = true) {
	const ref = (0, import_react.useRef)(onRefresh);
	ref.current = onRefresh;
	(0, import_react.useEffect)(() => {
		if (!enabled) return;
		const onKeyDown = (event) => {
			if (event.key !== "r" && event.key !== "R") return;
			if (event.metaKey || event.ctrlKey || event.altKey || event.shiftKey || event.repeat) return;
			const target = event.target;
			if (target?.isContentEditable || target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement) return;
			event.preventDefault();
			ref.current();
		};
		window.addEventListener("keydown", onKeyDown);
		return () => window.removeEventListener("keydown", onKeyDown);
	}, [enabled]);
}
//#endregion
export { useRefreshHotkey as t };
