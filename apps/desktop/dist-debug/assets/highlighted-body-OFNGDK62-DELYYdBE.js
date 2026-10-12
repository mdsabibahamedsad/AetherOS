import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { ao as require_jsx_runtime, nn as Li, oo as require_react, rn as R$1, tn as At } from "./index-B_yd1pEX.js";
//#region ../../node_modules/streamdown/dist/highlighted-body-OFNGDK62.js
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
var R = ({ code: s, language: e, raw: t, className: h, startLine: d, lineNumbers: m, ...p }) => {
	let { shikiTheme: l } = (0, import_react.useContext)(R$1), o = Li(), [a, i] = (0, import_react.useState)(t);
	return (0, import_react.useEffect)(() => {
		if (!o) {
			i(t);
			return;
		}
		let r = o.highlight({
			code: s,
			language: e,
			themes: l
		}, (c) => {
			i(c);
		});
		r && i(r);
	}, [
		s,
		e,
		l,
		o,
		t
	]), (0, import_jsx_runtime.jsx)(At, {
		className: h,
		language: e,
		lineNumbers: m,
		result: a,
		startLine: d,
		...p
	});
};
//#endregion
export { R as HighlightedCodeBlockBody };
