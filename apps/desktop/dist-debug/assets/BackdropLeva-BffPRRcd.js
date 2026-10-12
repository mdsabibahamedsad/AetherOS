import { a as __toESM, t as __commonJSMin } from "./chunk-DKxDMwdo.js";
import { Ba as Content2, Ga as __generator, Ha as Root3, Ka as __spread, Ot as $backdropSettings, Ua as Trigger, Va as Provider, Wa as __awaiter, ao as require_jsx_runtime, kt as $radiusScalar, no as require_client, oo as require_react, qa as Root, za as Arrow2 } from "./index-B_yd1pEX.js";
//#region ../../node_modules/dequal/lite/index.mjs
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var has = Object.prototype.hasOwnProperty;
function dequal(foo, bar) {
	var ctor, len;
	if (foo === bar) return true;
	if (foo && bar && (ctor = foo.constructor) === bar.constructor) {
		if (ctor === Date) return foo.getTime() === bar.getTime();
		if (ctor === RegExp) return foo.toString() === bar.toString();
		if (ctor === Array) {
			if ((len = foo.length) === bar.length) while (len-- && dequal(foo[len], bar[len]));
			return len === -1;
		}
		if (!ctor || typeof foo === "object") {
			len = 0;
			for (ctor in foo) {
				if (has.call(foo, ctor) && ++len && !has.call(bar, ctor)) return false;
				if (!(ctor in bar) || !dequal(foo[ctor], bar[ctor])) return false;
			}
			return Object.keys(bar).length === len;
		}
	}
	return foo !== foo && bar !== bar;
}
//#endregion
//#region ../../node_modules/leva/node_modules/zustand/esm/shallow.js
function shallow(objA, objB) {
	if (Object.is(objA, objB)) return true;
	if (typeof objA !== "object" || objA === null || typeof objB !== "object" || objB === null) return false;
	const keysA = Object.keys(objA);
	if (keysA.length !== Object.keys(objB).length) return false;
	for (let i = 0; i < keysA.length; i++) if (!Object.prototype.hasOwnProperty.call(objB, keysA[i]) || !Object.is(objA[keysA[i]], objB[keysA[i]])) return false;
	return true;
}
//#endregion
//#region ../../node_modules/v8n/dist/v8n.esm.js
var Rule = function Rule(name, fn, args, modifiers) {
	this.name = name;
	this.fn = fn;
	this.args = args;
	this.modifiers = modifiers;
};
Rule.prototype._test = function _test(value) {
	var fn = this.fn;
	try {
		testAux(this.modifiers.slice(), fn, this)(value);
	} catch (ex) {
		fn = function() {
			return false;
		};
	}
	try {
		return testAux(this.modifiers.slice(), fn, this)(value);
	} catch (ex$1) {
		return false;
	}
};
Rule.prototype._check = function _check(value) {
	try {
		testAux(this.modifiers.slice(), this.fn, this)(value);
	} catch (ex) {
		if (testAux(this.modifiers.slice(), function(it) {
			return it;
		}, this)(false)) return;
	}
	if (!testAux(this.modifiers.slice(), this.fn, this)(value)) throw null;
};
Rule.prototype._testAsync = function _testAsync(value) {
	var this$1 = this;
	return new Promise(function(resolve, reject) {
		testAsyncAux(this$1.modifiers.slice(), this$1.fn, this$1)(value).then(function(valid) {
			if (valid) resolve(value);
			else reject(null);
		}).catch(function(ex) {
			return reject(ex);
		});
	});
};
function pickFn(fn, variant) {
	if (variant === void 0) variant = "simple";
	return typeof fn === "object" ? fn[variant] : fn;
}
function testAux(modifiers, fn, rule) {
	if (modifiers.length) {
		var modifier = modifiers.shift();
		var nextFn = testAux(modifiers, fn, rule);
		return modifier.perform(nextFn, rule);
	} else return pickFn(fn);
}
function testAsyncAux(modifiers, fn, rule) {
	if (modifiers.length) {
		var modifier = modifiers.shift();
		var nextFn = testAsyncAux(modifiers, fn, rule);
		return modifier.performAsync(nextFn, rule);
	} else return function(value) {
		return Promise.resolve(pickFn(fn, "async")(value));
	};
}
var Modifier = function Modifier(name, perform, performAsync) {
	this.name = name;
	this.perform = perform;
	this.performAsync = performAsync;
};
var ValidationError = /* @__PURE__ */ function(Error) {
	function ValidationError(rule, value, cause, target) {
		var remaining = [], len = arguments.length - 4;
		while (len-- > 0) remaining[len] = arguments[len + 4];
		Error.call(this, remaining);
		if (Error.captureStackTrace) Error.captureStackTrace(this, ValidationError);
		this.rule = rule;
		this.value = value;
		this.cause = cause;
		this.target = target;
	}
	if (Error) ValidationError.__proto__ = Error;
	ValidationError.prototype = Object.create(Error && Error.prototype);
	ValidationError.prototype.constructor = ValidationError;
	return ValidationError;
}(Error);
var Context = function Context(chain, nextRuleModifiers) {
	if (chain === void 0) chain = [];
	if (nextRuleModifiers === void 0) nextRuleModifiers = [];
	this.chain = chain;
	this.nextRuleModifiers = nextRuleModifiers;
};
Context.prototype._applyRule = function _applyRule(ruleFn, name) {
	var this$1 = this;
	return function() {
		var args = [], len = arguments.length;
		while (len--) args[len] = arguments[len];
		this$1.chain.push(new Rule(name, ruleFn.apply(this$1, args), args, this$1.nextRuleModifiers));
		this$1.nextRuleModifiers = [];
		return this$1;
	};
};
Context.prototype._applyModifier = function _applyModifier(modifier, name) {
	this.nextRuleModifiers.push(new Modifier(name, modifier.simple, modifier.async));
	return this;
};
Context.prototype._clone = function _clone() {
	return new Context(this.chain.slice(), this.nextRuleModifiers.slice());
};
Context.prototype.test = function test(value) {
	return this.chain.every(function(rule) {
		return rule._test(value);
	});
};
Context.prototype.testAll = function testAll(value) {
	var err = [];
	this.chain.forEach(function(rule) {
		try {
			rule._check(value);
		} catch (ex) {
			err.push(new ValidationError(rule, value, ex));
		}
	});
	return err;
};
Context.prototype.check = function check(value) {
	this.chain.forEach(function(rule) {
		try {
			rule._check(value);
		} catch (ex) {
			throw new ValidationError(rule, value, ex);
		}
	});
};
Context.prototype.testAsync = function testAsync(value) {
	var this$1 = this;
	return new Promise(function(resolve, reject) {
		executeAsyncRules(value, this$1.chain.slice(), resolve, reject);
	});
};
function executeAsyncRules(value, rules, resolve, reject) {
	if (rules.length) {
		var rule = rules.shift();
		rule._testAsync(value).then(function() {
			executeAsyncRules(value, rules, resolve, reject);
		}, function(cause) {
			reject(new ValidationError(rule, value, cause));
		});
	} else resolve(value);
}
var consideredEmpty = function(value, considerTrimmedEmptyString) {
	if (considerTrimmedEmptyString && typeof value === "string" && value.trim().length === 0) return true;
	return value === void 0 || value === null;
};
function optional(validation, considerTrimmedEmptyString) {
	if (considerTrimmedEmptyString === void 0) considerTrimmedEmptyString = false;
	return {
		simple: function(value) {
			return consideredEmpty(value, considerTrimmedEmptyString) || validation.check(value) === void 0;
		},
		async: function(value) {
			return consideredEmpty(value, considerTrimmedEmptyString) || validation.testAsync(value);
		}
	};
}
function v8n() {
	return typeof Proxy !== "undefined" ? proxyContext(new Context()) : proxylessContext(new Context());
}
var customRules = {};
v8n.extend = function(newRules) {
	Object.assign(customRules, newRules);
};
v8n.clearCustomRules = function() {
	customRules = {};
};
function proxyContext(context) {
	return new Proxy(context, { get: function get(obj, prop) {
		if (prop in obj) return obj[prop];
		var newContext = proxyContext(context._clone());
		if (prop in availableModifiers) return newContext._applyModifier(availableModifiers[prop], prop);
		if (prop in customRules) return newContext._applyRule(customRules[prop], prop);
		if (prop in availableRules) return newContext._applyRule(availableRules[prop], prop);
	} });
}
function proxylessContext(context) {
	var addRuleSet = function(ruleSet, targetContext) {
		Object.keys(ruleSet).forEach(function(prop) {
			targetContext[prop] = function() {
				var args = [], len = arguments.length;
				while (len--) args[len] = arguments[len];
				return proxylessContext(targetContext._clone())._applyRule(ruleSet[prop], prop).apply(void 0, args);
			};
		});
		return targetContext;
	};
	var contextWithAvailableRules = addRuleSet(availableRules, context);
	var contextWithAllRules = addRuleSet(customRules, contextWithAvailableRules);
	Object.keys(availableModifiers).forEach(function(prop) {
		Object.defineProperty(contextWithAllRules, prop, { get: function() {
			return proxylessContext(contextWithAllRules._clone())._applyModifier(availableModifiers[prop], prop);
		} });
	});
	return contextWithAllRules;
}
var availableModifiers = {
	not: {
		simple: function(fn) {
			return function(value) {
				return !fn(value);
			};
		},
		async: function(fn) {
			return function(value) {
				return Promise.resolve(fn(value)).then(function(result) {
					return !result;
				}).catch(function() {
					return true;
				});
			};
		}
	},
	some: {
		simple: function(fn) {
			return function(value) {
				return split(value).some(function(item) {
					try {
						return fn(item);
					} catch (ex) {
						return false;
					}
				});
			};
		},
		async: function(fn) {
			return function(value) {
				return Promise.all(split(value).map(function(item) {
					try {
						return fn(item).catch(function() {
							return false;
						});
					} catch (ex) {
						return false;
					}
				})).then(function(result) {
					return result.some(Boolean);
				});
			};
		}
	},
	every: {
		simple: function(fn) {
			return function(value) {
				return value !== false && split(value).every(fn);
			};
		},
		async: function(fn) {
			return function(value) {
				return Promise.all(split(value).map(fn)).then(function(result) {
					return result.every(Boolean);
				});
			};
		}
	},
	strict: {
		simple: function(fn, rule) {
			return function(value) {
				if (isSchemaRule(rule) && value && typeof value === "object") return Object.keys(rule.args[0]).length === Object.keys(value).length && fn(value);
				return fn(value);
			};
		},
		async: function(fn, rule) {
			return function(value) {
				return Promise.resolve(fn(value)).then(function(result) {
					if (isSchemaRule(rule) && value && typeof value === "object") return Object.keys(rule.args[0]).length === Object.keys(value).length && result;
					return result;
				}).catch(function() {
					return false;
				});
			};
		}
	}
};
function isSchemaRule(rule) {
	return rule && rule.name === "schema" && rule.args.length > 0 && typeof rule.args[0] === "object";
}
function split(value) {
	if (typeof value === "string") return value.split("");
	return value;
}
var availableRules = {
	equal: function(expected) {
		return function(value) {
			return value == expected;
		};
	},
	exact: function(expected) {
		return function(value) {
			return value === expected;
		};
	},
	number: function(allowInfinite) {
		if (allowInfinite === void 0) allowInfinite = true;
		return function(value) {
			return typeof value === "number" && (allowInfinite || isFinite(value));
		};
	},
	integer: function() {
		return function(value) {
			return (Number.isInteger || isIntegerPolyfill)(value);
		};
	},
	numeric: function() {
		return function(value) {
			return !isNaN(parseFloat(value)) && isFinite(value);
		};
	},
	string: function() {
		return testType("string");
	},
	boolean: function() {
		return testType("boolean");
	},
	undefined: function() {
		return testType("undefined");
	},
	null: function() {
		return testType("null");
	},
	array: function() {
		return testType("array");
	},
	object: function() {
		return testType("object");
	},
	instanceOf: function(instance) {
		return function(value) {
			return value instanceof instance;
		};
	},
	pattern: function(expected) {
		return function(value) {
			return expected.test(value);
		};
	},
	lowercase: function() {
		return function(value) {
			return typeof value === "boolean" || value === value.toLowerCase() && value.trim() !== "";
		};
	},
	uppercase: function() {
		return function(value) {
			return value === value.toUpperCase() && value.trim() !== "";
		};
	},
	vowel: function() {
		return function(value) {
			return /^[aeiou]+$/i.test(value);
		};
	},
	consonant: function() {
		return function(value) {
			return /^(?=[^aeiou])([a-z]+)$/i.test(value);
		};
	},
	first: function(expected) {
		return function(value) {
			return value[0] == expected;
		};
	},
	last: function(expected) {
		return function(value) {
			return value[value.length - 1] == expected;
		};
	},
	empty: function() {
		return function(value) {
			return value.length === 0;
		};
	},
	length: function(min, max) {
		return function(value) {
			return value.length >= min && value.length <= (max || min);
		};
	},
	minLength: function(min) {
		return function(value) {
			return value.length >= min;
		};
	},
	maxLength: function(max) {
		return function(value) {
			return value.length <= max;
		};
	},
	negative: function() {
		return function(value) {
			return value < 0;
		};
	},
	positive: function() {
		return function(value) {
			return value >= 0;
		};
	},
	between: function(a, b) {
		return function(value) {
			return value >= a && value <= b;
		};
	},
	range: function(a, b) {
		return function(value) {
			return value >= a && value <= b;
		};
	},
	lessThan: function(n) {
		return function(value) {
			return value < n;
		};
	},
	lessThanOrEqual: function(n) {
		return function(value) {
			return value <= n;
		};
	},
	greaterThan: function(n) {
		return function(value) {
			return value > n;
		};
	},
	greaterThanOrEqual: function(n) {
		return function(value) {
			return value >= n;
		};
	},
	even: function() {
		return function(value) {
			return value % 2 === 0;
		};
	},
	odd: function() {
		return function(value) {
			return value % 2 !== 0;
		};
	},
	includes: function(expected) {
		return function(value) {
			return ~value.indexOf(expected);
		};
	},
	schema: function(schema) {
		return testSchema(schema);
	},
	passesAnyOf: function() {
		var validations = [], len = arguments.length;
		while (len--) validations[len] = arguments[len];
		return function(value) {
			return validations.some(function(validation) {
				return validation.test(value);
			});
		};
	},
	optional
};
function testType(expected) {
	return function(value) {
		return Array.isArray(value) && expected === "array" || value === null && expected === "null" || typeof value === expected;
	};
}
function isIntegerPolyfill(value) {
	return typeof value === "number" && isFinite(value) && Math.floor(value) === value;
}
function testSchema(schema) {
	return {
		simple: function(value) {
			var causes = [];
			Object.keys(schema).forEach(function(key) {
				var nestedValidation = schema[key];
				try {
					nestedValidation.check((value || {})[key]);
				} catch (ex) {
					ex.target = key;
					causes.push(ex);
				}
			});
			if (causes.length > 0) throw causes;
			return true;
		},
		async: function(value) {
			var causes = [];
			var nested = Object.keys(schema).map(function(key) {
				return schema[key].testAsync((value || {})[key]).catch(function(ex) {
					ex.target = key;
					causes.push(ex);
				});
			});
			return Promise.all(nested).then(function() {
				if (causes.length > 0) throw causes;
				return true;
			});
		}
	};
}
//#endregion
//#region ../../node_modules/@stitches/react/dist/index.mjs
var e$2 = "colors", t$2 = "sizes", r$2 = "space", n$2 = {
	gap: r$2,
	gridGap: r$2,
	columnGap: r$2,
	gridColumnGap: r$2,
	rowGap: r$2,
	gridRowGap: r$2,
	inset: r$2,
	insetBlock: r$2,
	insetBlockEnd: r$2,
	insetBlockStart: r$2,
	insetInline: r$2,
	insetInlineEnd: r$2,
	insetInlineStart: r$2,
	margin: r$2,
	marginTop: r$2,
	marginRight: r$2,
	marginBottom: r$2,
	marginLeft: r$2,
	marginBlock: r$2,
	marginBlockEnd: r$2,
	marginBlockStart: r$2,
	marginInline: r$2,
	marginInlineEnd: r$2,
	marginInlineStart: r$2,
	padding: r$2,
	paddingTop: r$2,
	paddingRight: r$2,
	paddingBottom: r$2,
	paddingLeft: r$2,
	paddingBlock: r$2,
	paddingBlockEnd: r$2,
	paddingBlockStart: r$2,
	paddingInline: r$2,
	paddingInlineEnd: r$2,
	paddingInlineStart: r$2,
	top: r$2,
	right: r$2,
	bottom: r$2,
	left: r$2,
	scrollMargin: r$2,
	scrollMarginTop: r$2,
	scrollMarginRight: r$2,
	scrollMarginBottom: r$2,
	scrollMarginLeft: r$2,
	scrollMarginX: r$2,
	scrollMarginY: r$2,
	scrollMarginBlock: r$2,
	scrollMarginBlockEnd: r$2,
	scrollMarginBlockStart: r$2,
	scrollMarginInline: r$2,
	scrollMarginInlineEnd: r$2,
	scrollMarginInlineStart: r$2,
	scrollPadding: r$2,
	scrollPaddingTop: r$2,
	scrollPaddingRight: r$2,
	scrollPaddingBottom: r$2,
	scrollPaddingLeft: r$2,
	scrollPaddingX: r$2,
	scrollPaddingY: r$2,
	scrollPaddingBlock: r$2,
	scrollPaddingBlockEnd: r$2,
	scrollPaddingBlockStart: r$2,
	scrollPaddingInline: r$2,
	scrollPaddingInlineEnd: r$2,
	scrollPaddingInlineStart: r$2,
	fontSize: "fontSizes",
	background: e$2,
	backgroundColor: e$2,
	backgroundImage: e$2,
	borderImage: e$2,
	border: e$2,
	borderBlock: e$2,
	borderBlockEnd: e$2,
	borderBlockStart: e$2,
	borderBottom: e$2,
	borderBottomColor: e$2,
	borderColor: e$2,
	borderInline: e$2,
	borderInlineEnd: e$2,
	borderInlineStart: e$2,
	borderLeft: e$2,
	borderLeftColor: e$2,
	borderRight: e$2,
	borderRightColor: e$2,
	borderTop: e$2,
	borderTopColor: e$2,
	caretColor: e$2,
	color: e$2,
	columnRuleColor: e$2,
	fill: e$2,
	outline: e$2,
	outlineColor: e$2,
	stroke: e$2,
	textDecorationColor: e$2,
	fontFamily: "fonts",
	fontWeight: "fontWeights",
	lineHeight: "lineHeights",
	letterSpacing: "letterSpacings",
	blockSize: t$2,
	minBlockSize: t$2,
	maxBlockSize: t$2,
	inlineSize: t$2,
	minInlineSize: t$2,
	maxInlineSize: t$2,
	width: t$2,
	minWidth: t$2,
	maxWidth: t$2,
	height: t$2,
	minHeight: t$2,
	maxHeight: t$2,
	flexBasis: t$2,
	gridTemplateColumns: t$2,
	gridTemplateRows: t$2,
	borderWidth: "borderWidths",
	borderTopWidth: "borderWidths",
	borderRightWidth: "borderWidths",
	borderBottomWidth: "borderWidths",
	borderLeftWidth: "borderWidths",
	borderStyle: "borderStyles",
	borderTopStyle: "borderStyles",
	borderRightStyle: "borderStyles",
	borderBottomStyle: "borderStyles",
	borderLeftStyle: "borderStyles",
	borderRadius: "radii",
	borderTopLeftRadius: "radii",
	borderTopRightRadius: "radii",
	borderBottomRightRadius: "radii",
	borderBottomLeftRadius: "radii",
	boxShadow: "shadows",
	textShadow: "shadows",
	transition: "transitions",
	zIndex: "zIndices"
}, i$2 = (e, t) => "function" == typeof t ? { "()": Function.prototype.toString.call(t) } : t, o$2 = () => {
	const e = Object.create(null);
	return (t, r, ...n) => {
		const o = ((e) => JSON.stringify(e, i$2))(t);
		return o in e ? e[o] : e[o] = r(t, ...n);
	};
}, l$2 = Symbol.for("sxs.internal"), s$2 = (e, t) => Object.defineProperties(e, Object.getOwnPropertyDescriptors(t)), a$2 = (e) => {
	for (const t in e) return !0;
	return !1;
}, { hasOwnProperty: c$2 } = Object.prototype, d$2 = (e) => e.includes("-") ? e : e.replace(/[A-Z]/g, ((e) => "-" + e.toLowerCase())), g$2 = /\s+(?![^()]*\))/, p$2 = (e) => (t) => e(..."string" == typeof t ? String(t).split(g$2) : [t]), u$2 = {
	appearance: (e) => ({
		WebkitAppearance: e,
		appearance: e
	}),
	backfaceVisibility: (e) => ({
		WebkitBackfaceVisibility: e,
		backfaceVisibility: e
	}),
	backdropFilter: (e) => ({
		WebkitBackdropFilter: e,
		backdropFilter: e
	}),
	backgroundClip: (e) => ({
		WebkitBackgroundClip: e,
		backgroundClip: e
	}),
	boxDecorationBreak: (e) => ({
		WebkitBoxDecorationBreak: e,
		boxDecorationBreak: e
	}),
	clipPath: (e) => ({
		WebkitClipPath: e,
		clipPath: e
	}),
	content: (e) => ({ content: e.includes("\"") || e.includes("'") || /^([A-Za-z]+\([^]*|[^]*-quote|inherit|initial|none|normal|revert|unset)$/.test(e) ? e : `"${e}"` }),
	hyphens: (e) => ({
		WebkitHyphens: e,
		hyphens: e
	}),
	maskImage: (e) => ({
		WebkitMaskImage: e,
		maskImage: e
	}),
	maskSize: (e) => ({
		WebkitMaskSize: e,
		maskSize: e
	}),
	tabSize: (e) => ({
		MozTabSize: e,
		tabSize: e
	}),
	textSizeAdjust: (e) => ({
		WebkitTextSizeAdjust: e,
		textSizeAdjust: e
	}),
	userSelect: (e) => ({
		WebkitUserSelect: e,
		userSelect: e
	}),
	marginBlock: p$2(((e, t) => ({
		marginBlockStart: e,
		marginBlockEnd: t || e
	}))),
	marginInline: p$2(((e, t) => ({
		marginInlineStart: e,
		marginInlineEnd: t || e
	}))),
	maxSize: p$2(((e, t) => ({
		maxBlockSize: e,
		maxInlineSize: t || e
	}))),
	minSize: p$2(((e, t) => ({
		minBlockSize: e,
		minInlineSize: t || e
	}))),
	paddingBlock: p$2(((e, t) => ({
		paddingBlockStart: e,
		paddingBlockEnd: t || e
	}))),
	paddingInline: p$2(((e, t) => ({
		paddingInlineStart: e,
		paddingInlineEnd: t || e
	})))
}, h$2 = /([\d.]+)([^]*)/, f$2 = (e, t) => e.length ? e.reduce(((e, r) => (e.push(...t.map(((e) => e.includes("&") ? e.replace(/&/g, /[ +>|~]/.test(r) && /&.*&/.test(e) ? `:is(${r})` : r) : r + " " + e))), e)), []) : t, m$2 = (e, t) => e in b$2 && "string" == typeof t ? t.replace(/^((?:[^]*[^\w-])?)(fit-content|stretch)((?:[^\w-][^]*)?)$/, ((t, r, n, i) => r + ("stretch" === n ? `-moz-available${i};${d$2(e)}:${r}-webkit-fill-available` : `-moz-fit-content${i};${d$2(e)}:${r}fit-content`) + i)) : String(t), b$2 = {
	blockSize: 1,
	height: 1,
	inlineSize: 1,
	maxBlockSize: 1,
	maxHeight: 1,
	maxInlineSize: 1,
	maxWidth: 1,
	minBlockSize: 1,
	minHeight: 1,
	minInlineSize: 1,
	minWidth: 1,
	width: 1
}, S$2 = (e) => e ? e + "-" : "", k$2 = (e, t, r) => e.replace(/([+-])?((?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?)?(\$|--)([$\w-]+)/g, ((e, n, i, o, l) => "$" == o == !!i ? e : (n || "--" == o ? "calc(" : "") + "var(--" + ("$" === o ? S$2(t) + (l.includes("$") ? "" : S$2(r)) + l.replace(/\$/g, "-") : l) + ")" + (n || "--" == o ? "*" + (n || "") + (i || "1") + ")" : ""))), y$2 = /\s*,\s*(?![^()]*\))/, B$1 = Object.prototype.toString, $$2 = (e, t, r, n, i) => {
	let o, l, s;
	const a = (e, t, r) => {
		let c, g;
		const p = (e) => {
			for (c in e) {
				const R = 64 === c.charCodeAt(0);
				for (g of R && Array.isArray(e[c]) ? e[c] : [e[c]]) {
					const e = /[A-Z]/.test($ = c) ? $ : $.replace(/-[^]/g, ((e) => e[1].toUpperCase())), z = "object" == typeof g && g && g.toString === B$1 && (!n.utils[e] || !t.length);
					if (e in n.utils && !z) {
						const t = n.utils[e];
						if (t !== l) {
							l = t, p(t(g)), l = null;
							continue;
						}
					} else if (e in u$2) {
						const t = u$2[e];
						if (t !== s) {
							s = t, p(t(g)), s = null;
							continue;
						}
					}
					if (R && (b = c.slice(1) in n.media ? "@media " + n.media[c.slice(1)] : c, c = b.replace(/\(\s*([\w-]+)\s*(=|<|<=|>|>=)\s*([\w-]+)\s*(?:(<|<=|>|>=)\s*([\w-]+)\s*)?\)/g, ((e, t, r, n, i, o) => {
						const l = h$2.test(t), s = .0625 * (l ? -1 : 1), [a, c] = l ? [n, t] : [t, n];
						return "(" + ("=" === r[0] ? "" : ">" === r[0] === l ? "max-" : "min-") + a + ":" + ("=" !== r[0] && 1 === r.length ? c.replace(h$2, ((e, t, n) => Number(t) + s * (">" === r ? 1 : -1) + n)) : c) + (i ? ") and (" + (">" === i[0] ? "min-" : "max-") + a + ":" + (1 === i.length ? o.replace(h$2, ((e, t, r) => Number(t) + s * (">" === i ? -1 : 1) + r)) : o) : "") + ")";
					}))), z) {
						const e = R ? r.concat(c) : [...r], n = R ? [...t] : f$2(t, c.split(y$2));
						void 0 !== o && i(x$2(...o)), o = void 0, a(g, n, e);
					} else void 0 === o && (o = [
						[],
						t,
						r
					]), c = R || 36 !== c.charCodeAt(0) ? c : `--${S$2(n.prefix)}${c.slice(1).replace(/\$/g, "-")}`, g = z ? g : "number" == typeof g ? g && e in I$2 ? String(g) + "px" : String(g) : k$2(m$2(e, null == g ? "" : g), n.prefix, n.themeMap[e]), o[0].push(`${R ? `${c} ` : `${d$2(c)}:`}${g}`);
				}
			}
			var b, $;
		};
		p(e), void 0 !== o && i(x$2(...o)), o = void 0;
	};
	a(e, t, r);
}, x$2 = (e, t, r) => `${r.map(((e) => `${e}{`)).join("")}${t.length ? `${t.join(",")}{` : ""}${e.join(";")}${t.length ? "}" : ""}${Array(r.length ? r.length + 1 : 0).join("}")}`, I$2 = {
	animationDelay: 1,
	animationDuration: 1,
	backgroundSize: 1,
	blockSize: 1,
	border: 1,
	borderBlock: 1,
	borderBlockEnd: 1,
	borderBlockEndWidth: 1,
	borderBlockStart: 1,
	borderBlockStartWidth: 1,
	borderBlockWidth: 1,
	borderBottom: 1,
	borderBottomLeftRadius: 1,
	borderBottomRightRadius: 1,
	borderBottomWidth: 1,
	borderEndEndRadius: 1,
	borderEndStartRadius: 1,
	borderInlineEnd: 1,
	borderInlineEndWidth: 1,
	borderInlineStart: 1,
	borderInlineStartWidth: 1,
	borderInlineWidth: 1,
	borderLeft: 1,
	borderLeftWidth: 1,
	borderRadius: 1,
	borderRight: 1,
	borderRightWidth: 1,
	borderSpacing: 1,
	borderStartEndRadius: 1,
	borderStartStartRadius: 1,
	borderTop: 1,
	borderTopLeftRadius: 1,
	borderTopRightRadius: 1,
	borderTopWidth: 1,
	borderWidth: 1,
	bottom: 1,
	columnGap: 1,
	columnRule: 1,
	columnRuleWidth: 1,
	columnWidth: 1,
	containIntrinsicSize: 1,
	flexBasis: 1,
	fontSize: 1,
	gap: 1,
	gridAutoColumns: 1,
	gridAutoRows: 1,
	gridTemplateColumns: 1,
	gridTemplateRows: 1,
	height: 1,
	inlineSize: 1,
	inset: 1,
	insetBlock: 1,
	insetBlockEnd: 1,
	insetBlockStart: 1,
	insetInline: 1,
	insetInlineEnd: 1,
	insetInlineStart: 1,
	left: 1,
	letterSpacing: 1,
	margin: 1,
	marginBlock: 1,
	marginBlockEnd: 1,
	marginBlockStart: 1,
	marginBottom: 1,
	marginInline: 1,
	marginInlineEnd: 1,
	marginInlineStart: 1,
	marginLeft: 1,
	marginRight: 1,
	marginTop: 1,
	maxBlockSize: 1,
	maxHeight: 1,
	maxInlineSize: 1,
	maxWidth: 1,
	minBlockSize: 1,
	minHeight: 1,
	minInlineSize: 1,
	minWidth: 1,
	offsetDistance: 1,
	offsetRotate: 1,
	outline: 1,
	outlineOffset: 1,
	outlineWidth: 1,
	overflowClipMargin: 1,
	padding: 1,
	paddingBlock: 1,
	paddingBlockEnd: 1,
	paddingBlockStart: 1,
	paddingBottom: 1,
	paddingInline: 1,
	paddingInlineEnd: 1,
	paddingInlineStart: 1,
	paddingLeft: 1,
	paddingRight: 1,
	paddingTop: 1,
	perspective: 1,
	right: 1,
	rowGap: 1,
	scrollMargin: 1,
	scrollMarginBlock: 1,
	scrollMarginBlockEnd: 1,
	scrollMarginBlockStart: 1,
	scrollMarginBottom: 1,
	scrollMarginInline: 1,
	scrollMarginInlineEnd: 1,
	scrollMarginInlineStart: 1,
	scrollMarginLeft: 1,
	scrollMarginRight: 1,
	scrollMarginTop: 1,
	scrollPadding: 1,
	scrollPaddingBlock: 1,
	scrollPaddingBlockEnd: 1,
	scrollPaddingBlockStart: 1,
	scrollPaddingBottom: 1,
	scrollPaddingInline: 1,
	scrollPaddingInlineEnd: 1,
	scrollPaddingInlineStart: 1,
	scrollPaddingLeft: 1,
	scrollPaddingRight: 1,
	scrollPaddingTop: 1,
	shapeMargin: 1,
	textDecoration: 1,
	textDecorationThickness: 1,
	textIndent: 1,
	textUnderlineOffset: 1,
	top: 1,
	transitionDelay: 1,
	transitionDuration: 1,
	verticalAlign: 1,
	width: 1,
	wordSpacing: 1
}, R$1 = (e) => String.fromCharCode(e + (e > 25 ? 39 : 97)), z$1 = (e) => ((e) => {
	let t, r = "";
	for (t = Math.abs(e); t > 52; t = t / 52 | 0) r = R$1(t % 52) + r;
	return R$1(t % 52) + r;
})(((e, t) => {
	let r = t.length;
	for (; r;) e = 33 * e ^ t.charCodeAt(--r);
	return e;
})(5381, JSON.stringify(e)) >>> 0), W$1 = [
	"themed",
	"global",
	"styled",
	"onevar",
	"resonevar",
	"allvar",
	"inline"
], j$2 = (e) => {
	if (e.href && !e.href.startsWith(location.origin)) return !1;
	try {
		return !!e.cssRules;
	} catch (e) {
		return !1;
	}
}, E$2 = (e) => {
	let t;
	const r = () => {
		const { cssRules: e } = t.sheet;
		return [].map.call(e, ((r, n) => {
			const { cssText: i } = r;
			let o = "";
			if (i.startsWith("--sxs")) return "";
			if (e[n - 1] && (o = e[n - 1].cssText).startsWith("--sxs")) {
				if (!r.cssRules.length) return "";
				for (const e in t.rules) if (t.rules[e].group === r) return `--sxs{--sxs:${[...t.rules[e].cache].join(" ")}}${i}`;
				return r.cssRules.length ? `${o}${i}` : "";
			}
			return i;
		})).join("");
	}, n = () => {
		if (t) {
			const { rules: e, sheet: r } = t;
			if (!r.deleteRule) {
				for (; 3 === Object(Object(r.cssRules)[0]).type;) r.cssRules.splice(0, 1);
				r.cssRules = [];
			}
			for (const t in e) delete e[t];
		}
		const i = Object(e).styleSheets || [];
		for (const e of i) if (j$2(e)) {
			for (let i = 0, o = e.cssRules; o[i]; ++i) {
				const l = Object(o[i]);
				if (1 !== l.type) continue;
				const s = Object(o[i + 1]);
				if (4 !== s.type) continue;
				++i;
				const { cssText: a } = l;
				if (!a.startsWith("--sxs")) continue;
				const c = a.slice(14, -3).trim().split(/\s+/), d = W$1[c[0]];
				d && (t || (t = {
					sheet: e,
					reset: n,
					rules: {},
					toString: r
				}), t.rules[d] = {
					group: s,
					index: i,
					cache: new Set(c)
				});
			}
			if (t) break;
		}
		if (!t) {
			const i = (e, t) => ({
				type: t,
				cssRules: [],
				insertRule(e, t) {
					this.cssRules.splice(t, 0, i(e, {
						import: 3,
						undefined: 1
					}[(e.toLowerCase().match(/^@([a-z]+)/) || [])[1]] || 4));
				},
				get cssText() {
					return "@media{}" === e ? `@media{${[].map.call(this.cssRules, ((e) => e.cssText)).join("")}}` : e;
				}
			});
			t = {
				sheet: e ? (e.head || e).appendChild(document.createElement("style")).sheet : i("", "text/css"),
				rules: {},
				reset: n,
				toString: r
			};
		}
		const { sheet: o, rules: l } = t;
		for (let e = W$1.length - 1; e >= 0; --e) {
			const t = W$1[e];
			if (!l[t]) {
				const r = W$1[e + 1], n = l[r] ? l[r].index : o.cssRules.length;
				o.insertRule("@media{}", n), o.insertRule(`--sxs{--sxs:${e}}`, n), l[t] = {
					group: o.cssRules[n + 1],
					index: n,
					cache: new Set([e])
				};
			}
			v$2(l[t]);
		}
	};
	return n(), t;
}, v$2 = (e) => {
	const t = e.group;
	let r = t.cssRules.length;
	e.apply = (e) => {
		try {
			t.insertRule(e, r), ++r;
		} catch (e) {}
	};
}, T$1 = Symbol(), w$2 = o$2(), M$2 = (e, t) => w$2(e, (() => (...r) => {
	let n = {
		type: null,
		composers: /* @__PURE__ */ new Set()
	};
	for (const t of r) if (null != t) if (t[l$2]) {
		n.type ??= t[l$2].type;
		for (const e of t[l$2].composers) n.composers.add(e);
	} else t.constructor !== Object || t.$$typeof ? n.type ??= t : n.composers.add(C$1(t, e));
	return n.type ??= "span", n.composers.size || n.composers.add([
		"PJLV",
		{},
		[],
		[],
		{},
		[]
	]), P$1(e, n, t);
})), C$1 = ({ variants: e, compoundVariants: t, defaultVariants: r, ...n }, i) => {
	const o = `${S$2(i.prefix)}c-${z$1(n)}`, l = [], s = [], d = Object.create(null), g = [];
	for (const e in r) d[e] = String(r[e]);
	if ("object" == typeof e && e) for (const t in e) {
		p = d, u = t, c$2.call(p, u) || (d[t] = "undefined");
		const r = e[t];
		for (const e in r) {
			const n = { [t]: String(e) };
			"undefined" === String(e) && g.push(t);
			const i = r[e], o = [
				n,
				i,
				!a$2(i)
			];
			l.push(o);
		}
	}
	var p, u;
	if ("object" == typeof t && t) for (const e of t) {
		let { css: t, ...r } = e;
		t = "object" == typeof t && t || {};
		for (const e in r) r[e] = String(r[e]);
		const n = [
			r,
			t,
			!a$2(t)
		];
		s.push(n);
	}
	return [
		o,
		n,
		l,
		s,
		d,
		g
	];
}, P$1 = (e, t, r) => {
	const [n, i, o, a] = L$1(t.composers), c = "function" == typeof t.type || t.type.$$typeof ? ((e) => {
		function t() {
			for (let r = 0; r < t[T$1].length; r++) {
				const [n, i] = t[T$1][r];
				e.rules[n].apply(i);
			}
			return t[T$1] = [], null;
		}
		return t[T$1] = [], t.rules = {}, W$1.forEach(((e) => t.rules[e] = { apply: (r) => t[T$1].push([e, r]) })), t;
	})(r) : null, d = (c || r).rules, g = `.${n}${i.length > 1 ? `:where(.${i.slice(1).join(".")})` : ""}`, p = (l) => {
		l = "object" == typeof l && l || A$1;
		const { css: s, ...p } = l, u = {};
		for (const e in o) if (delete p[e], e in l) {
			let t = l[e];
			"object" == typeof t && t ? u[e] = {
				"@initial": o[e],
				...t
			} : (t = String(t), u[e] = "undefined" !== t || a.has(e) ? t : o[e]);
		} else u[e] = o[e];
		const h = new Set([...i]);
		for (const [n, i, o, l] of t.composers) {
			r.rules.styled.cache.has(n) || (r.rules.styled.cache.add(n), $$2(i, [`.${n}`], [], e, ((e) => {
				d.styled.apply(e);
			})));
			const t = O$1(o, u, e.media), s = O$1(l, u, e.media, !0);
			for (const i of t) if (void 0 !== i) for (const [t, o, l] of i) {
				const i = `${n}-${z$1(o)}-${t}`;
				h.add(i);
				const s = (l ? r.rules.resonevar : r.rules.onevar).cache, a = l ? d.resonevar : d.onevar;
				s.has(i) || (s.add(i), $$2(o, [`.${i}`], [], e, ((e) => {
					a.apply(e);
				})));
			}
			for (const t of s) if (void 0 !== t) for (const [i, o] of t) {
				const t = `${n}-${z$1(o)}-${i}`;
				h.add(t), r.rules.allvar.cache.has(t) || (r.rules.allvar.cache.add(t), $$2(o, [`.${t}`], [], e, ((e) => {
					d.allvar.apply(e);
				})));
			}
		}
		if ("object" == typeof s && s) {
			const t = `${n}-i${z$1(s)}-css`;
			h.add(t), r.rules.inline.cache.has(t) || (r.rules.inline.cache.add(t), $$2(s, [`.${t}`], [], e, ((e) => {
				d.inline.apply(e);
			})));
		}
		for (const e of String(l.className || "").trim().split(/\s+/)) e && h.add(e);
		const f = p.className = [...h].join(" ");
		return {
			type: t.type,
			className: f,
			selector: g,
			props: p,
			toString: () => f,
			deferredInjector: c
		};
	};
	return s$2(p, {
		className: n,
		selector: g,
		[l$2]: t,
		toString: () => (r.rules.styled.cache.has(n) || p(), n)
	});
}, L$1 = (e) => {
	let t = "";
	const r = [], n = {}, i = [];
	for (const [o, , , , l, s] of e) {
		"" === t && (t = o), r.push(o), i.push(...s);
		for (const e in l) {
			const t = l[e];
			(void 0 === n[e] || "undefined" !== t || s.includes(t)) && (n[e] = t);
		}
	}
	return [
		t,
		r,
		n,
		new Set(i)
	];
}, O$1 = (e, t, r, n) => {
	const i = [];
	e: for (let [o, l, s] of e) {
		if (s) continue;
		let e, a = 0, c = !1;
		for (e in o) {
			const n = o[e];
			let i = t[e];
			if (i !== n) {
				if ("object" != typeof i || !i) continue e;
				{
					let e, t, o = 0;
					for (const l in i) {
						if (n === String(i[l])) {
							if ("@initial" !== l) {
								const e = l.slice(1);
								(t = t || []).push(e in r ? r[e] : l.replace(/^@media ?/, "")), c = !0;
							}
							a += o, e = !0;
						}
						++o;
					}
					if (t && t.length && (l = { ["@media " + t.join(", ")]: l }), !e) continue e;
				}
			}
		}
		(i[a] = i[a] || []).push([
			n ? "cv" : `${e}-${o[e]}`,
			l,
			c
		]);
	}
	return i;
}, A$1 = {}, N$2 = o$2(), D$1 = (e, t) => N$2(e, (() => (...r) => {
	const n = () => {
		for (let n of r) {
			n = "object" == typeof n && n || {};
			let r = z$1(n);
			if (!t.rules.global.cache.has(r)) {
				if (t.rules.global.cache.add(r), "@import" in n) {
					let e = [].indexOf.call(t.sheet.cssRules, t.rules.themed.group) - 1;
					for (let r of [].concat(n["@import"])) r = r.includes("\"") || r.includes("'") ? r : `"${r}"`, t.sheet.insertRule(`@import ${r};`, e++);
					delete n["@import"];
				}
				$$2(n, [], [], e, ((e) => {
					t.rules.global.apply(e);
				}));
			}
		}
		return "";
	};
	return s$2(n, { toString: n });
})), H$2 = o$2(), V$2 = (e, t) => H$2(e, (() => (r) => {
	const n = `${S$2(e.prefix)}k-${z$1(r)}`, i = () => {
		if (!t.rules.global.cache.has(n)) {
			t.rules.global.cache.add(n);
			const i = [];
			$$2(r, [], [], e, ((e) => i.push(e)));
			const o = `@keyframes ${n}{${i.join("")}}`;
			t.rules.global.apply(o);
		}
		return n;
	};
	return s$2(i, {
		get name() {
			return i();
		},
		toString: i
	});
})), G$1 = class {
	constructor(e, t, r, n) {
		this.token = null == e ? "" : String(e), this.value = null == t ? "" : String(t), this.scale = null == r ? "" : String(r), this.prefix = null == n ? "" : String(n);
	}
	get computedValue() {
		return "var(" + this.variable + ")";
	}
	get variable() {
		return "--" + S$2(this.prefix) + S$2(this.scale) + this.token;
	}
	toString() {
		return this.computedValue;
	}
}, F$1 = o$2(), J$1 = (e, t) => F$1(e, (() => (r, n) => {
	n = "object" == typeof r && r || Object(n);
	const i = `.${r = (r = "string" == typeof r ? r : "") || `${S$2(e.prefix)}t-${z$1(n)}`}`, o = {}, l = [];
	for (const t in n) {
		o[t] = {};
		for (const r in n[t]) {
			const i = `--${S$2(e.prefix)}${t}-${r}`, s = k$2(String(n[t][r]), e.prefix, t);
			o[t][r] = new G$1(r, s, t, e.prefix), l.push(`${i}:${s}`);
		}
	}
	const s = () => {
		if (l.length && !t.rules.themed.cache.has(r)) {
			t.rules.themed.cache.add(r);
			const i = `${n === e.theme ? ":root," : ""}.${r}{${l.join(";")}}`;
			t.rules.themed.apply(i);
		}
		return r;
	};
	return {
		...o,
		get className() {
			return s();
		},
		selector: i,
		toString: s
	};
})), U$1 = o$2(), Y$1 = o$2(), q$1 = (e) => {
	const t = ((e) => {
		let t = !1;
		const r = U$1(e, ((e) => {
			t = !0;
			const r = "prefix" in (e = "object" == typeof e && e || {}) ? String(e.prefix) : "", i = "object" == typeof e.media && e.media || {}, o = "object" == typeof e.root ? e.root || null : globalThis.document || null, l = "object" == typeof e.theme && e.theme || {}, s = {
				prefix: r,
				media: i,
				theme: l,
				themeMap: "object" == typeof e.themeMap && e.themeMap || { ...n$2 },
				utils: "object" == typeof e.utils && e.utils || {}
			}, a = E$2(o), c = {
				css: M$2(s, a),
				globalCss: D$1(s, a),
				keyframes: V$2(s, a),
				createTheme: J$1(s, a),
				reset() {
					a.reset(), c.theme.toString();
				},
				theme: {},
				sheet: a,
				config: s,
				prefix: r,
				getCssText: a.toString,
				toString: a.toString
			};
			return String(c.theme = c.createTheme(l)), c;
		}));
		return t || r.reset(), r;
	})(e);
	return t.styled = (({ config: e, sheet: t }) => Y$1(e, (() => {
		const r = M$2(e, t);
		return (...e) => {
			const t = r(...e), n = t[l$2].type, i = import_react.forwardRef(((e, r) => {
				const i = e && e.as || n, { props: o, deferredInjector: l } = t(e);
				return delete o.as, o.ref = r, l ? import_react.createElement(import_react.Fragment, null, import_react.createElement(i, o), import_react.createElement(l, null)) : import_react.createElement(i, o);
			}));
			return i.className = t.className, i.displayName = `Styled.${n.displayName || n.name || n}`, i.selector = t.selector, i.toString = () => t.selector, i[l$2] = t[l$2], i;
		};
	})))(t), t;
};
//#endregion
//#region ../../node_modules/@use-gesture/core/dist/maths-0ab39ae9.esm.js
function clamp$1(v, min, max) {
	return Math.max(min, Math.min(v, max));
}
var V$1 = {
	toVector(v, fallback) {
		if (v === void 0) v = fallback;
		return Array.isArray(v) ? v : [v, v];
	},
	add(v1, v2) {
		return [v1[0] + v2[0], v1[1] + v2[1]];
	},
	sub(v1, v2) {
		return [v1[0] - v2[0], v1[1] - v2[1]];
	},
	addTo(v1, v2) {
		v1[0] += v2[0];
		v1[1] += v2[1];
	},
	subTo(v1, v2) {
		v1[0] -= v2[0];
		v1[1] -= v2[1];
	}
};
function rubberband(distance, dimension, constant) {
	if (dimension === 0 || Math.abs(dimension) === Infinity) return Math.pow(distance, constant * 5);
	return distance * dimension * constant / (dimension + constant * distance);
}
function rubberbandIfOutOfBounds(position, min, max, constant = .15) {
	if (constant === 0) return clamp$1(position, min, max);
	if (position < min) return -rubberband(min - position, max - min, constant) + min;
	if (position > max) return +rubberband(position - max, max - min, constant) + max;
	return position;
}
function computeRubberband(bounds, [Vx, Vy], [Rx, Ry]) {
	const [[X0, X1], [Y0, Y1]] = bounds;
	return [rubberbandIfOutOfBounds(Vx, X0, X1, Rx), rubberbandIfOutOfBounds(Vy, Y0, Y1, Ry)];
}
//#endregion
//#region ../../node_modules/@use-gesture/core/dist/actions-fe213e88.esm.js
function _toPrimitive$1(input, hint) {
	if (typeof input !== "object" || input === null) return input;
	var prim = input[Symbol.toPrimitive];
	if (prim !== void 0) {
		var res = prim.call(input, hint || "default");
		if (typeof res !== "object") return res;
		throw new TypeError("@@toPrimitive must return a primitive value.");
	}
	return (hint === "string" ? String : Number)(input);
}
function _toPropertyKey$1(arg) {
	var key = _toPrimitive$1(arg, "string");
	return typeof key === "symbol" ? key : String(key);
}
function _defineProperty$3(obj, key, value) {
	key = _toPropertyKey$1(key);
	if (key in obj) Object.defineProperty(obj, key, {
		value,
		enumerable: true,
		configurable: true,
		writable: true
	});
	else obj[key] = value;
	return obj;
}
function ownKeys$3(e, r) {
	var t = Object.keys(e);
	if (Object.getOwnPropertySymbols) {
		var o = Object.getOwnPropertySymbols(e);
		r && (o = o.filter(function(r) {
			return Object.getOwnPropertyDescriptor(e, r).enumerable;
		})), t.push.apply(t, o);
	}
	return t;
}
function _objectSpread2$1(e) {
	for (var r = 1; r < arguments.length; r++) {
		var t = null != arguments[r] ? arguments[r] : {};
		r % 2 ? ownKeys$3(Object(t), !0).forEach(function(r) {
			_defineProperty$3(e, r, t[r]);
		}) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(t)) : ownKeys$3(Object(t)).forEach(function(r) {
			Object.defineProperty(e, r, Object.getOwnPropertyDescriptor(t, r));
		});
	}
	return e;
}
var EVENT_TYPE_MAP = {
	pointer: {
		start: "down",
		change: "move",
		end: "up"
	},
	mouse: {
		start: "down",
		change: "move",
		end: "up"
	},
	touch: {
		start: "start",
		change: "move",
		end: "end"
	},
	gesture: {
		start: "start",
		change: "change",
		end: "end"
	}
};
function capitalize(string) {
	if (!string) return "";
	return string[0].toUpperCase() + string.slice(1);
}
var actionsWithoutCaptureSupported = ["enter", "leave"];
function hasCapture(capture = false, actionKey) {
	return capture && !actionsWithoutCaptureSupported.includes(actionKey);
}
function toHandlerProp(device, action = "", capture = false) {
	const deviceProps = EVENT_TYPE_MAP[device];
	const actionKey = deviceProps ? deviceProps[action] || action : action;
	return "on" + capitalize(device) + capitalize(actionKey) + (hasCapture(capture, actionKey) ? "Capture" : "");
}
var pointerCaptureEvents = ["gotpointercapture", "lostpointercapture"];
function parseProp(prop) {
	let eventKey = prop.substring(2).toLowerCase();
	const passive = !!~eventKey.indexOf("passive");
	if (passive) eventKey = eventKey.replace("passive", "");
	const captureKey = pointerCaptureEvents.includes(eventKey) ? "capturecapture" : "capture";
	const capture = !!~eventKey.indexOf(captureKey);
	if (capture) eventKey = eventKey.replace("capture", "");
	return {
		device: eventKey,
		capture,
		passive
	};
}
function toDomEventType(device, action = "") {
	const deviceProps = EVENT_TYPE_MAP[device];
	return device + (deviceProps ? deviceProps[action] || action : action);
}
function isTouch(event) {
	return "touches" in event;
}
function getPointerType(event) {
	if (isTouch(event)) return "touch";
	if ("pointerType" in event) return event.pointerType;
	return "mouse";
}
function getCurrentTargetTouchList(event) {
	return Array.from(event.touches).filter((e) => {
		var _event$currentTarget, _event$currentTarget$;
		return e.target === event.currentTarget || ((_event$currentTarget = event.currentTarget) === null || _event$currentTarget === void 0 || (_event$currentTarget$ = _event$currentTarget.contains) === null || _event$currentTarget$ === void 0 ? void 0 : _event$currentTarget$.call(_event$currentTarget, e.target));
	});
}
function getTouchList(event) {
	return event.type === "touchend" || event.type === "touchcancel" ? event.changedTouches : event.targetTouches;
}
function getValueEvent(event) {
	return isTouch(event) ? getTouchList(event)[0] : event;
}
function touchIds(event) {
	return getCurrentTargetTouchList(event).map((touch) => touch.identifier);
}
function pointerId(event) {
	const valueEvent = getValueEvent(event);
	return isTouch(event) ? valueEvent.identifier : valueEvent.pointerId;
}
function pointerValues(event) {
	const valueEvent = getValueEvent(event);
	return [valueEvent.clientX, valueEvent.clientY];
}
function getEventDetails(event) {
	const payload = {};
	if ("buttons" in event) payload.buttons = event.buttons;
	if ("shiftKey" in event) {
		const { shiftKey, altKey, metaKey, ctrlKey } = event;
		Object.assign(payload, {
			shiftKey,
			altKey,
			metaKey,
			ctrlKey
		});
	}
	return payload;
}
function call(v, ...args) {
	if (typeof v === "function") return v(...args);
	else return v;
}
function noop$1() {}
function chain(...fns) {
	if (fns.length === 0) return noop$1;
	if (fns.length === 1) return fns[0];
	return function() {
		let result;
		for (const fn of fns) result = fn.apply(this, arguments) || result;
		return result;
	};
}
function assignDefault(value, fallback) {
	return Object.assign({}, fallback, value || {});
}
var BEFORE_LAST_KINEMATICS_DELAY = 32;
var Engine = class {
	constructor(ctrl, args, key) {
		this.ctrl = ctrl;
		this.args = args;
		this.key = key;
		if (!this.state) {
			this.state = {};
			this.computeValues([0, 0]);
			this.computeInitial();
			if (this.init) this.init();
			this.reset();
		}
	}
	get state() {
		return this.ctrl.state[this.key];
	}
	set state(state) {
		this.ctrl.state[this.key] = state;
	}
	get shared() {
		return this.ctrl.state.shared;
	}
	get eventStore() {
		return this.ctrl.gestureEventStores[this.key];
	}
	get timeoutStore() {
		return this.ctrl.gestureTimeoutStores[this.key];
	}
	get config() {
		return this.ctrl.config[this.key];
	}
	get sharedConfig() {
		return this.ctrl.config.shared;
	}
	get handler() {
		return this.ctrl.handlers[this.key];
	}
	reset() {
		const { state, shared, ingKey, args } = this;
		shared[ingKey] = state._active = state.active = state._blocked = state._force = false;
		state._step = [false, false];
		state.intentional = false;
		state._movement = [0, 0];
		state._distance = [0, 0];
		state._direction = [0, 0];
		state._delta = [0, 0];
		state._bounds = [[-Infinity, Infinity], [-Infinity, Infinity]];
		state.args = args;
		state.axis = void 0;
		state.memo = void 0;
		state.elapsedTime = state.timeDelta = 0;
		state.direction = [0, 0];
		state.distance = [0, 0];
		state.overflow = [0, 0];
		state._movementBound = [false, false];
		state.velocity = [0, 0];
		state.movement = [0, 0];
		state.delta = [0, 0];
		state.timeStamp = 0;
	}
	start(event) {
		const state = this.state;
		const config = this.config;
		if (!state._active) {
			this.reset();
			this.computeInitial();
			state._active = true;
			state.target = event.target;
			state.currentTarget = event.currentTarget;
			state.lastOffset = config.from ? call(config.from, state) : state.offset;
			state.offset = state.lastOffset;
			state.startTime = state.timeStamp = event.timeStamp;
		}
	}
	computeValues(values) {
		const state = this.state;
		state._values = values;
		state.values = this.config.transform(values);
	}
	computeInitial() {
		const state = this.state;
		state._initial = state._values;
		state.initial = state.values;
	}
	compute(event) {
		const { state, config, shared } = this;
		state.args = this.args;
		let dt = 0;
		if (event) {
			state.event = event;
			if (config.preventDefault && event.cancelable) state.event.preventDefault();
			state.type = event.type;
			shared.touches = this.ctrl.pointerIds.size || this.ctrl.touchIds.size;
			shared.locked = !!document.pointerLockElement;
			Object.assign(shared, getEventDetails(event));
			shared.down = shared.pressed = shared.buttons % 2 === 1 || shared.touches > 0;
			dt = event.timeStamp - state.timeStamp;
			state.timeStamp = event.timeStamp;
			state.elapsedTime = state.timeStamp - state.startTime;
		}
		if (state._active) {
			const _absoluteDelta = state._delta.map(Math.abs);
			V$1.addTo(state._distance, _absoluteDelta);
		}
		if (this.axisIntent) this.axisIntent(event);
		const [_m0, _m1] = state._movement;
		const [t0, t1] = config.threshold;
		const { _step, values } = state;
		if (config.hasCustomTransform) {
			if (_step[0] === false) _step[0] = Math.abs(_m0) >= t0 && values[0];
			if (_step[1] === false) _step[1] = Math.abs(_m1) >= t1 && values[1];
		} else {
			if (_step[0] === false) _step[0] = Math.abs(_m0) >= t0 && Math.sign(_m0) * t0;
			if (_step[1] === false) _step[1] = Math.abs(_m1) >= t1 && Math.sign(_m1) * t1;
		}
		state.intentional = _step[0] !== false || _step[1] !== false;
		if (!state.intentional) return;
		const movement = [0, 0];
		if (config.hasCustomTransform) {
			const [v0, v1] = values;
			movement[0] = _step[0] !== false ? v0 - _step[0] : 0;
			movement[1] = _step[1] !== false ? v1 - _step[1] : 0;
		} else {
			movement[0] = _step[0] !== false ? _m0 - _step[0] : 0;
			movement[1] = _step[1] !== false ? _m1 - _step[1] : 0;
		}
		if (this.restrictToAxis && !state._blocked) this.restrictToAxis(movement);
		const previousOffset = state.offset;
		const gestureIsActive = state._active && !state._blocked || state.active;
		if (gestureIsActive) {
			state.first = state._active && !state.active;
			state.last = !state._active && state.active;
			state.active = shared[this.ingKey] = state._active;
			if (event) {
				if (state.first) {
					if ("bounds" in config) state._bounds = call(config.bounds, state);
					if (this.setup) this.setup();
				}
				state.movement = movement;
				this.computeOffset();
			}
		}
		const [ox, oy] = state.offset;
		const [[x0, x1], [y0, y1]] = state._bounds;
		state.overflow = [ox < x0 ? -1 : ox > x1 ? 1 : 0, oy < y0 ? -1 : oy > y1 ? 1 : 0];
		state._movementBound[0] = state.overflow[0] ? state._movementBound[0] === false ? state._movement[0] : state._movementBound[0] : false;
		state._movementBound[1] = state.overflow[1] ? state._movementBound[1] === false ? state._movement[1] : state._movementBound[1] : false;
		const rubberband = state._active ? config.rubberband || [0, 0] : [0, 0];
		state.offset = computeRubberband(state._bounds, state.offset, rubberband);
		state.delta = V$1.sub(state.offset, previousOffset);
		this.computeMovement();
		if (gestureIsActive && (!state.last || dt > BEFORE_LAST_KINEMATICS_DELAY)) {
			state.delta = V$1.sub(state.offset, previousOffset);
			const absoluteDelta = state.delta.map(Math.abs);
			V$1.addTo(state.distance, absoluteDelta);
			state.direction = state.delta.map(Math.sign);
			state._direction = state._delta.map(Math.sign);
			if (!state.first && dt > 0) {
				state.velocity = [absoluteDelta[0] / dt, absoluteDelta[1] / dt];
				state.timeDelta = dt;
			}
		}
	}
	emit() {
		const state = this.state;
		const shared = this.shared;
		const config = this.config;
		if (!state._active) this.clean();
		if ((state._blocked || !state.intentional) && !state._force && !config.triggerAllEvents) return;
		const memo = this.handler(_objectSpread2$1(_objectSpread2$1(_objectSpread2$1({}, shared), state), {}, { [this.aliasKey]: state.values }));
		if (memo !== void 0) state.memo = memo;
	}
	clean() {
		this.eventStore.clean();
		this.timeoutStore.clean();
	}
};
function selectAxis([dx, dy], threshold) {
	const absDx = Math.abs(dx);
	const absDy = Math.abs(dy);
	if (absDx > absDy && absDx > threshold) return "x";
	if (absDy > absDx && absDy > threshold) return "y";
}
var CoordinatesEngine = class extends Engine {
	constructor(...args) {
		super(...args);
		_defineProperty$3(this, "aliasKey", "xy");
	}
	reset() {
		super.reset();
		this.state.axis = void 0;
	}
	init() {
		this.state.offset = [0, 0];
		this.state.lastOffset = [0, 0];
	}
	computeOffset() {
		this.state.offset = V$1.add(this.state.lastOffset, this.state.movement);
	}
	computeMovement() {
		this.state.movement = V$1.sub(this.state.offset, this.state.lastOffset);
	}
	axisIntent(event) {
		const state = this.state;
		const config = this.config;
		if (!state.axis && event) {
			const threshold = typeof config.axisThreshold === "object" ? config.axisThreshold[getPointerType(event)] : config.axisThreshold;
			state.axis = selectAxis(state._movement, threshold);
		}
		state._blocked = (config.lockDirection || !!config.axis) && !state.axis || !!config.axis && config.axis !== state.axis;
	}
	restrictToAxis(v) {
		if (this.config.axis || this.config.lockDirection) switch (this.state.axis) {
			case "x":
				v[1] = 0;
				break;
			case "y":
				v[0] = 0;
				break;
		}
	}
};
var identity = (v) => v;
var DEFAULT_RUBBERBAND = .15;
var commonConfigResolver = {
	enabled(value = true) {
		return value;
	},
	eventOptions(value, _k, config) {
		return _objectSpread2$1(_objectSpread2$1({}, config.shared.eventOptions), value);
	},
	preventDefault(value = false) {
		return value;
	},
	triggerAllEvents(value = false) {
		return value;
	},
	rubberband(value = 0) {
		switch (value) {
			case true: return [DEFAULT_RUBBERBAND, DEFAULT_RUBBERBAND];
			case false: return [0, 0];
			default: return V$1.toVector(value);
		}
	},
	from(value) {
		if (typeof value === "function") return value;
		if (value != null) return V$1.toVector(value);
	},
	transform(value, _k, config) {
		const transform = value || config.shared.transform;
		this.hasCustomTransform = !!transform;
		return transform || identity;
	},
	threshold(value) {
		return V$1.toVector(value, 0);
	}
};
var DEFAULT_AXIS_THRESHOLD = 0;
var coordinatesConfigResolver = _objectSpread2$1(_objectSpread2$1({}, commonConfigResolver), {}, {
	axis(_v, _k, { axis }) {
		this.lockDirection = axis === "lock";
		if (!this.lockDirection) return axis;
	},
	axisThreshold(value = DEFAULT_AXIS_THRESHOLD) {
		return value;
	},
	bounds(value = {}) {
		if (typeof value === "function") return (state) => coordinatesConfigResolver.bounds(value(state));
		if ("current" in value) return () => value.current;
		if (typeof HTMLElement === "function" && value instanceof HTMLElement) return value;
		const { left = -Infinity, right = Infinity, top = -Infinity, bottom = Infinity } = value;
		return [[left, right], [top, bottom]];
	}
});
var KEYS_DELTA_MAP = {
	ArrowRight: (displacement, factor = 1) => [displacement * factor, 0],
	ArrowLeft: (displacement, factor = 1) => [-1 * displacement * factor, 0],
	ArrowUp: (displacement, factor = 1) => [0, -1 * displacement * factor],
	ArrowDown: (displacement, factor = 1) => [0, displacement * factor]
};
var DragEngine = class extends CoordinatesEngine {
	constructor(...args) {
		super(...args);
		_defineProperty$3(this, "ingKey", "dragging");
	}
	reset() {
		super.reset();
		const state = this.state;
		state._pointerId = void 0;
		state._pointerActive = false;
		state._keyboardActive = false;
		state._preventScroll = false;
		state._delayed = false;
		state.swipe = [0, 0];
		state.tap = false;
		state.canceled = false;
		state.cancel = this.cancel.bind(this);
	}
	setup() {
		const state = this.state;
		if (state._bounds instanceof HTMLElement) {
			const boundRect = state._bounds.getBoundingClientRect();
			const targetRect = state.currentTarget.getBoundingClientRect();
			const _bounds = {
				left: boundRect.left - targetRect.left + state.offset[0],
				right: boundRect.right - targetRect.right + state.offset[0],
				top: boundRect.top - targetRect.top + state.offset[1],
				bottom: boundRect.bottom - targetRect.bottom + state.offset[1]
			};
			state._bounds = coordinatesConfigResolver.bounds(_bounds);
		}
	}
	cancel() {
		const state = this.state;
		if (state.canceled) return;
		state.canceled = true;
		state._active = false;
		setTimeout(() => {
			this.compute();
			this.emit();
		}, 0);
	}
	setActive() {
		this.state._active = this.state._pointerActive || this.state._keyboardActive;
	}
	clean() {
		this.pointerClean();
		this.state._pointerActive = false;
		this.state._keyboardActive = false;
		super.clean();
	}
	pointerDown(event) {
		const config = this.config;
		const state = this.state;
		if (event.buttons != null && (Array.isArray(config.pointerButtons) ? !config.pointerButtons.includes(event.buttons) : config.pointerButtons !== -1 && config.pointerButtons !== event.buttons)) return;
		const ctrlIds = this.ctrl.setEventIds(event);
		if (config.pointerCapture) event.target.setPointerCapture(event.pointerId);
		if (ctrlIds && ctrlIds.size > 1 && state._pointerActive) return;
		this.start(event);
		this.setupPointer(event);
		state._pointerId = pointerId(event);
		state._pointerActive = true;
		this.computeValues(pointerValues(event));
		this.computeInitial();
		if (config.preventScrollAxis && getPointerType(event) !== "mouse") {
			state._active = false;
			this.setupScrollPrevention(event);
		} else if (config.delay > 0) {
			this.setupDelayTrigger(event);
			if (config.triggerAllEvents) {
				this.compute(event);
				this.emit();
			}
		} else this.startPointerDrag(event);
	}
	startPointerDrag(event) {
		const state = this.state;
		state._active = true;
		state._preventScroll = true;
		state._delayed = false;
		this.compute(event);
		this.emit();
	}
	pointerMove(event) {
		const state = this.state;
		const config = this.config;
		if (!state._pointerActive) return;
		const id = pointerId(event);
		if (state._pointerId !== void 0 && id !== state._pointerId) return;
		const _values = pointerValues(event);
		if (document.pointerLockElement === event.target) state._delta = [event.movementX, event.movementY];
		else {
			state._delta = V$1.sub(_values, state._values);
			this.computeValues(_values);
		}
		V$1.addTo(state._movement, state._delta);
		this.compute(event);
		if (state._delayed && state.intentional) {
			this.timeoutStore.remove("dragDelay");
			state.active = false;
			this.startPointerDrag(event);
			return;
		}
		if (config.preventScrollAxis && !state._preventScroll) if (state.axis) if (state.axis === config.preventScrollAxis || config.preventScrollAxis === "xy") {
			state._active = false;
			this.clean();
			return;
		} else {
			this.timeoutStore.remove("startPointerDrag");
			this.startPointerDrag(event);
			return;
		}
		else return;
		this.emit();
	}
	pointerUp(event) {
		this.ctrl.setEventIds(event);
		try {
			if (this.config.pointerCapture && event.target.hasPointerCapture(event.pointerId)) event.target.releasePointerCapture(event.pointerId);
		} catch (_unused) {}
		const state = this.state;
		const config = this.config;
		if (!state._active || !state._pointerActive) return;
		const id = pointerId(event);
		if (state._pointerId !== void 0 && id !== state._pointerId) return;
		this.state._pointerActive = false;
		this.setActive();
		this.compute(event);
		const [dx, dy] = state._distance;
		state.tap = dx <= config.tapsThreshold && dy <= config.tapsThreshold;
		if (state.tap && config.filterTaps) state._force = true;
		else {
			const [_dx, _dy] = state._delta;
			const [_mx, _my] = state._movement;
			const [svx, svy] = config.swipe.velocity;
			const [sx, sy] = config.swipe.distance;
			const sdt = config.swipe.duration;
			if (state.elapsedTime < sdt) {
				const _vx = Math.abs(_dx / state.timeDelta);
				const _vy = Math.abs(_dy / state.timeDelta);
				if (_vx > svx && Math.abs(_mx) > sx) state.swipe[0] = Math.sign(_dx);
				if (_vy > svy && Math.abs(_my) > sy) state.swipe[1] = Math.sign(_dy);
			}
		}
		this.emit();
	}
	pointerClick(event) {
		if (!this.state.tap && event.detail > 0) {
			event.preventDefault();
			event.stopPropagation();
		}
	}
	setupPointer(event) {
		const config = this.config;
		const device = config.device;
		if (config.pointerLock) event.currentTarget.requestPointerLock();
		if (!config.pointerCapture) {
			this.eventStore.add(this.sharedConfig.window, device, "change", this.pointerMove.bind(this));
			this.eventStore.add(this.sharedConfig.window, device, "end", this.pointerUp.bind(this));
			this.eventStore.add(this.sharedConfig.window, device, "cancel", this.pointerUp.bind(this));
		}
	}
	pointerClean() {
		if (this.config.pointerLock && document.pointerLockElement === this.state.currentTarget) document.exitPointerLock();
	}
	preventScroll(event) {
		if (this.state._preventScroll && event.cancelable) event.preventDefault();
	}
	setupScrollPrevention(event) {
		this.state._preventScroll = false;
		persistEvent(event);
		const remove = this.eventStore.add(this.sharedConfig.window, "touch", "change", this.preventScroll.bind(this), { passive: false });
		this.eventStore.add(this.sharedConfig.window, "touch", "end", remove);
		this.eventStore.add(this.sharedConfig.window, "touch", "cancel", remove);
		this.timeoutStore.add("startPointerDrag", this.startPointerDrag.bind(this), this.config.preventScrollDelay, event);
	}
	setupDelayTrigger(event) {
		this.state._delayed = true;
		this.timeoutStore.add("dragDelay", () => {
			this.state._step = [0, 0];
			this.startPointerDrag(event);
		}, this.config.delay);
	}
	keyDown(event) {
		const deltaFn = KEYS_DELTA_MAP[event.key];
		if (deltaFn) {
			const state = this.state;
			const factor = event.shiftKey ? 10 : event.altKey ? .1 : 1;
			this.start(event);
			state._delta = deltaFn(this.config.keyboardDisplacement, factor);
			state._keyboardActive = true;
			V$1.addTo(state._movement, state._delta);
			this.compute(event);
			this.emit();
		}
	}
	keyUp(event) {
		if (!(event.key in KEYS_DELTA_MAP)) return;
		this.state._keyboardActive = false;
		this.setActive();
		this.compute(event);
		this.emit();
	}
	bind(bindFunction) {
		const device = this.config.device;
		bindFunction(device, "start", this.pointerDown.bind(this));
		if (this.config.pointerCapture) {
			bindFunction(device, "change", this.pointerMove.bind(this));
			bindFunction(device, "end", this.pointerUp.bind(this));
			bindFunction(device, "cancel", this.pointerUp.bind(this));
			bindFunction("lostPointerCapture", "", this.pointerUp.bind(this));
		}
		if (this.config.keys) {
			bindFunction("key", "down", this.keyDown.bind(this));
			bindFunction("key", "up", this.keyUp.bind(this));
		}
		if (this.config.filterTaps) bindFunction("click", "", this.pointerClick.bind(this), {
			capture: true,
			passive: false
		});
	}
};
function persistEvent(event) {
	"persist" in event && typeof event.persist === "function" && event.persist();
}
var isBrowser = typeof window !== "undefined" && window.document && window.document.createElement;
function supportsTouchEvents() {
	return isBrowser && "ontouchstart" in window;
}
function isTouchScreen() {
	return supportsTouchEvents() || isBrowser && window.navigator.maxTouchPoints > 1;
}
function supportsPointerEvents() {
	return isBrowser && "onpointerdown" in window;
}
function supportsPointerLock() {
	return isBrowser && "exitPointerLock" in window.document;
}
function supportsGestureEvents() {
	try {
		return "constructor" in GestureEvent;
	} catch (e) {
		return false;
	}
}
var SUPPORT = {
	isBrowser,
	gesture: supportsGestureEvents(),
	touch: supportsTouchEvents(),
	touchscreen: isTouchScreen(),
	pointer: supportsPointerEvents(),
	pointerLock: supportsPointerLock()
};
var DEFAULT_PREVENT_SCROLL_DELAY = 250;
var DEFAULT_DRAG_DELAY = 180;
var DEFAULT_SWIPE_VELOCITY = .5;
var DEFAULT_SWIPE_DISTANCE = 50;
var DEFAULT_SWIPE_DURATION = 250;
var DEFAULT_KEYBOARD_DISPLACEMENT = 10;
var DEFAULT_DRAG_AXIS_THRESHOLD = {
	mouse: 0,
	touch: 0,
	pen: 8
};
var dragConfigResolver = _objectSpread2$1(_objectSpread2$1({}, coordinatesConfigResolver), {}, {
	device(_v, _k, { pointer: { touch = false, lock = false, mouse = false } = {} }) {
		this.pointerLock = lock && SUPPORT.pointerLock;
		if (SUPPORT.touch && touch) return "touch";
		if (this.pointerLock) return "mouse";
		if (SUPPORT.pointer && !mouse) return "pointer";
		if (SUPPORT.touch) return "touch";
		return "mouse";
	},
	preventScrollAxis(value, _k, { preventScroll }) {
		this.preventScrollDelay = typeof preventScroll === "number" ? preventScroll : preventScroll || preventScroll === void 0 && value ? DEFAULT_PREVENT_SCROLL_DELAY : void 0;
		if (!SUPPORT.touchscreen || preventScroll === false) return void 0;
		return value ? value : preventScroll !== void 0 ? "y" : void 0;
	},
	pointerCapture(_v, _k, { pointer: { capture = true, buttons = 1, keys = true } = {} }) {
		this.pointerButtons = buttons;
		this.keys = keys;
		return !this.pointerLock && this.device === "pointer" && capture;
	},
	threshold(value, _k, { filterTaps = false, tapsThreshold = 3, axis = void 0 }) {
		const threshold = V$1.toVector(value, filterTaps ? tapsThreshold : axis ? 1 : 0);
		this.filterTaps = filterTaps;
		this.tapsThreshold = tapsThreshold;
		return threshold;
	},
	swipe({ velocity = DEFAULT_SWIPE_VELOCITY, distance = DEFAULT_SWIPE_DISTANCE, duration = DEFAULT_SWIPE_DURATION } = {}) {
		return {
			velocity: this.transform(V$1.toVector(velocity)),
			distance: this.transform(V$1.toVector(distance)),
			duration
		};
	},
	delay(value = 0) {
		switch (value) {
			case true: return DEFAULT_DRAG_DELAY;
			case false: return 0;
			default: return value;
		}
	},
	axisThreshold(value) {
		if (!value) return DEFAULT_DRAG_AXIS_THRESHOLD;
		return _objectSpread2$1(_objectSpread2$1({}, DEFAULT_DRAG_AXIS_THRESHOLD), value);
	},
	keyboardDisplacement(value = DEFAULT_KEYBOARD_DISPLACEMENT) {
		return value;
	}
});
_objectSpread2$1(_objectSpread2$1({}, commonConfigResolver), {}, {
	device(_v, _k, { shared, pointer: { touch = false } = {} }) {
		if (shared.target && !SUPPORT.touch && SUPPORT.gesture) return "gesture";
		if (SUPPORT.touch && touch) return "touch";
		if (SUPPORT.touchscreen) {
			if (SUPPORT.pointer) return "pointer";
			if (SUPPORT.touch) return "touch";
		}
	},
	bounds(_v, _k, { scaleBounds = {}, angleBounds = {} }) {
		const _scaleBounds = (state) => {
			const D = assignDefault(call(scaleBounds, state), {
				min: -Infinity,
				max: Infinity
			});
			return [D.min, D.max];
		};
		const _angleBounds = (state) => {
			const A = assignDefault(call(angleBounds, state), {
				min: -Infinity,
				max: Infinity
			});
			return [A.min, A.max];
		};
		if (typeof scaleBounds !== "function" && typeof angleBounds !== "function") return [_scaleBounds(), _angleBounds()];
		return (state) => [_scaleBounds(state), _angleBounds(state)];
	},
	threshold(value, _k, config) {
		this.lockDirection = config.axis === "lock";
		return V$1.toVector(value, this.lockDirection ? [.1, 3] : 0);
	},
	modifierKey(value) {
		if (value === void 0) return "ctrlKey";
		return value;
	},
	pinchOnWheel(value = true) {
		return value;
	}
});
_objectSpread2$1(_objectSpread2$1({}, coordinatesConfigResolver), {}, { mouseOnly: (value = true) => value });
_objectSpread2$1(_objectSpread2$1({}, coordinatesConfigResolver), {}, { mouseOnly: (value = true) => value });
var EngineMap = /* @__PURE__ */ new Map();
var ConfigResolverMap = /* @__PURE__ */ new Map();
function registerAction(action) {
	EngineMap.set(action.key, action.engine);
	ConfigResolverMap.set(action.key, action.resolver);
}
var dragAction = {
	key: "drag",
	engine: DragEngine,
	resolver: dragConfigResolver
};
//#endregion
//#region ../../node_modules/@use-gesture/core/dist/use-gesture-core.esm.js
function _objectWithoutPropertiesLoose$2(source, excluded) {
	if (source == null) return {};
	var target = {};
	var sourceKeys = Object.keys(source);
	var key, i;
	for (i = 0; i < sourceKeys.length; i++) {
		key = sourceKeys[i];
		if (excluded.indexOf(key) >= 0) continue;
		target[key] = source[key];
	}
	return target;
}
function _objectWithoutProperties$2(source, excluded) {
	if (source == null) return {};
	var target = _objectWithoutPropertiesLoose$2(source, excluded);
	var key, i;
	if (Object.getOwnPropertySymbols) {
		var sourceSymbolKeys = Object.getOwnPropertySymbols(source);
		for (i = 0; i < sourceSymbolKeys.length; i++) {
			key = sourceSymbolKeys[i];
			if (excluded.indexOf(key) >= 0) continue;
			if (!Object.prototype.propertyIsEnumerable.call(source, key)) continue;
			target[key] = source[key];
		}
	}
	return target;
}
var sharedConfigResolver = {
	target(value) {
		if (value) return () => "current" in value ? value.current : value;
	},
	enabled(value = true) {
		return value;
	},
	window(value = SUPPORT.isBrowser ? window : void 0) {
		return value;
	},
	eventOptions({ passive = true, capture = false } = {}) {
		return {
			passive,
			capture
		};
	},
	transform(value) {
		return value;
	}
};
var _excluded$11 = [
	"target",
	"eventOptions",
	"window",
	"enabled",
	"transform"
];
function resolveWith(config = {}, resolvers) {
	const result = {};
	for (const [key, resolver] of Object.entries(resolvers)) switch (typeof resolver) {
		case "function":
			result[key] = resolver.call(result, config[key], key, config);
			break;
		case "object":
			result[key] = resolveWith(config[key], resolver);
			break;
		case "boolean":
			if (resolver) result[key] = config[key];
			break;
	}
	return result;
}
function parse$1(newConfig, gestureKey, _config = {}) {
	const _ref = newConfig, { target, eventOptions, window, enabled, transform } = _ref, rest = _objectWithoutProperties$2(_ref, _excluded$11);
	_config.shared = resolveWith({
		target,
		eventOptions,
		window,
		enabled,
		transform
	}, sharedConfigResolver);
	if (gestureKey) {
		const resolver = ConfigResolverMap.get(gestureKey);
		_config[gestureKey] = resolveWith(_objectSpread2$1({ shared: _config.shared }, rest), resolver);
	} else for (const key in rest) {
		const resolver = ConfigResolverMap.get(key);
		if (resolver) _config[key] = resolveWith(_objectSpread2$1({ shared: _config.shared }, rest[key]), resolver);
	}
	return _config;
}
var EventStore = class {
	constructor(ctrl, gestureKey) {
		_defineProperty$3(this, "_listeners", /* @__PURE__ */ new Set());
		this._ctrl = ctrl;
		this._gestureKey = gestureKey;
	}
	add(element, device, action, handler, options) {
		const listeners = this._listeners;
		const type = toDomEventType(device, action);
		const eventOptions = _objectSpread2$1(_objectSpread2$1({}, this._gestureKey ? this._ctrl.config[this._gestureKey].eventOptions : {}), options);
		element.addEventListener(type, handler, eventOptions);
		const remove = () => {
			element.removeEventListener(type, handler, eventOptions);
			listeners.delete(remove);
		};
		listeners.add(remove);
		return remove;
	}
	clean() {
		this._listeners.forEach((remove) => remove());
		this._listeners.clear();
	}
};
var TimeoutStore = class {
	constructor() {
		_defineProperty$3(this, "_timeouts", /* @__PURE__ */ new Map());
	}
	add(key, callback, ms = 140, ...args) {
		this.remove(key);
		this._timeouts.set(key, window.setTimeout(callback, ms, ...args));
	}
	remove(key) {
		const timeout = this._timeouts.get(key);
		if (timeout) window.clearTimeout(timeout);
	}
	clean() {
		this._timeouts.forEach((timeout) => void window.clearTimeout(timeout));
		this._timeouts.clear();
	}
};
var Controller = class {
	constructor(handlers) {
		_defineProperty$3(this, "gestures", /* @__PURE__ */ new Set());
		_defineProperty$3(this, "_targetEventStore", new EventStore(this));
		_defineProperty$3(this, "gestureEventStores", {});
		_defineProperty$3(this, "gestureTimeoutStores", {});
		_defineProperty$3(this, "handlers", {});
		_defineProperty$3(this, "config", {});
		_defineProperty$3(this, "pointerIds", /* @__PURE__ */ new Set());
		_defineProperty$3(this, "touchIds", /* @__PURE__ */ new Set());
		_defineProperty$3(this, "state", { shared: {
			shiftKey: false,
			metaKey: false,
			ctrlKey: false,
			altKey: false
		} });
		resolveGestures(this, handlers);
	}
	setEventIds(event) {
		if (isTouch(event)) {
			this.touchIds = new Set(touchIds(event));
			return this.touchIds;
		} else if ("pointerId" in event) {
			if (event.type === "pointerup" || event.type === "pointercancel") this.pointerIds.delete(event.pointerId);
			else if (event.type === "pointerdown") this.pointerIds.add(event.pointerId);
			return this.pointerIds;
		}
	}
	applyHandlers(handlers, nativeHandlers) {
		this.handlers = handlers;
		this.nativeHandlers = nativeHandlers;
	}
	applyConfig(config, gestureKey) {
		this.config = parse$1(config, gestureKey, this.config);
	}
	clean() {
		this._targetEventStore.clean();
		for (const key of this.gestures) {
			this.gestureEventStores[key].clean();
			this.gestureTimeoutStores[key].clean();
		}
	}
	effect() {
		if (this.config.shared.target) this.bind();
		return () => this._targetEventStore.clean();
	}
	bind(...args) {
		const sharedConfig = this.config.shared;
		const props = {};
		let target;
		if (sharedConfig.target) {
			target = sharedConfig.target();
			if (!target) return;
		}
		if (sharedConfig.enabled) {
			for (const gestureKey of this.gestures) {
				const gestureConfig = this.config[gestureKey];
				const bindFunction = bindToProps(props, gestureConfig.eventOptions, !!target);
				if (gestureConfig.enabled) new (EngineMap.get(gestureKey))(this, args, gestureKey).bind(bindFunction);
			}
			const nativeBindFunction = bindToProps(props, sharedConfig.eventOptions, !!target);
			for (const eventKey in this.nativeHandlers) nativeBindFunction(eventKey, "", (event) => this.nativeHandlers[eventKey](_objectSpread2$1(_objectSpread2$1({}, this.state.shared), {}, {
				event,
				args
			})), void 0, true);
		}
		for (const handlerProp in props) props[handlerProp] = chain(...props[handlerProp]);
		if (!target) return props;
		for (const handlerProp in props) {
			const { device, capture, passive } = parseProp(handlerProp);
			this._targetEventStore.add(target, device, "", props[handlerProp], {
				capture,
				passive
			});
		}
	}
};
function setupGesture(ctrl, gestureKey) {
	ctrl.gestures.add(gestureKey);
	ctrl.gestureEventStores[gestureKey] = new EventStore(ctrl, gestureKey);
	ctrl.gestureTimeoutStores[gestureKey] = new TimeoutStore();
}
function resolveGestures(ctrl, internalHandlers) {
	if (internalHandlers.drag) setupGesture(ctrl, "drag");
	if (internalHandlers.wheel) setupGesture(ctrl, "wheel");
	if (internalHandlers.scroll) setupGesture(ctrl, "scroll");
	if (internalHandlers.move) setupGesture(ctrl, "move");
	if (internalHandlers.pinch) setupGesture(ctrl, "pinch");
	if (internalHandlers.hover) setupGesture(ctrl, "hover");
}
var bindToProps = (props, eventOptions, withPassiveOption) => (device, action, handler, options = {}, isNative = false) => {
	var _options$capture, _options$passive;
	const capture = (_options$capture = options.capture) !== null && _options$capture !== void 0 ? _options$capture : eventOptions.capture;
	const passive = (_options$passive = options.passive) !== null && _options$passive !== void 0 ? _options$passive : eventOptions.passive;
	let handlerProp = isNative ? device : toHandlerProp(device, action, capture);
	if (withPassiveOption && passive) handlerProp += "Passive";
	props[handlerProp] = props[handlerProp] || [];
	props[handlerProp].push(handler);
};
//#endregion
//#region ../../node_modules/@use-gesture/react/dist/use-gesture-react.esm.js
function useRecognizers(handlers, config = {}, gestureKey, nativeHandlers) {
	const ctrl = import_react.useMemo(() => new Controller(handlers), []);
	ctrl.applyHandlers(handlers, nativeHandlers);
	ctrl.applyConfig(config, gestureKey);
	import_react.useEffect(ctrl.effect.bind(ctrl));
	import_react.useEffect(() => {
		return ctrl.clean.bind(ctrl);
	}, []);
	if (config.target === void 0) return ctrl.bind.bind(ctrl);
}
function useDrag$1(handler, config) {
	registerAction(dragAction);
	return useRecognizers({ drag: handler }, config || {}, "drag");
}
//#endregion
//#region ../../node_modules/leva/dist/vector-plugin-5e122f40.esm.js
function _objectWithoutPropertiesLoose$1(r, e) {
	if (null == r) return {};
	var t = {};
	for (var n in r) if ({}.hasOwnProperty.call(r, n)) {
		if (-1 !== e.indexOf(n)) continue;
		t[n] = r[n];
	}
	return t;
}
function _objectWithoutProperties$1(e, t) {
	if (null == e) return {};
	var o, r, i = _objectWithoutPropertiesLoose$1(e, t);
	if (Object.getOwnPropertySymbols) {
		var n = Object.getOwnPropertySymbols(e);
		for (r = 0; r < n.length; r++) o = n[r], -1 === t.indexOf(o) && {}.propertyIsEnumerable.call(e, o) && (i[o] = e[o]);
	}
	return i;
}
var LevaErrors = function(LevaErrors) {
	LevaErrors[LevaErrors["UNSUPPORTED_INPUT"] = 0] = "UNSUPPORTED_INPUT";
	LevaErrors[LevaErrors["NO_COMPONENT_FOR_TYPE"] = 1] = "NO_COMPONENT_FOR_TYPE";
	LevaErrors[LevaErrors["UNKNOWN_INPUT"] = 2] = "UNKNOWN_INPUT";
	LevaErrors[LevaErrors["DUPLICATE_KEYS"] = 3] = "DUPLICATE_KEYS";
	LevaErrors[LevaErrors["ALREADY_REGISTERED_TYPE"] = 4] = "ALREADY_REGISTERED_TYPE";
	LevaErrors[LevaErrors["CLIPBOARD_ERROR"] = 5] = "CLIPBOARD_ERROR";
	LevaErrors[LevaErrors["THEME_ERROR"] = 6] = "THEME_ERROR";
	LevaErrors[LevaErrors["PATH_DOESNT_EXIST"] = 7] = "PATH_DOESNT_EXIST";
	LevaErrors[LevaErrors["INPUT_TYPE_OVERRIDE"] = 8] = "INPUT_TYPE_OVERRIDE";
	LevaErrors[LevaErrors["EMPTY_KEY"] = 9] = "EMPTY_KEY";
	return LevaErrors;
}({});
var ErrorList = {
	[LevaErrors.UNSUPPORTED_INPUT]: (type, path) => [`An input with type \`${type}\` input was found at path \`${path}\` but it's not supported yet.`],
	[LevaErrors.NO_COMPONENT_FOR_TYPE]: (type, path) => [`Type \`${type}\` found at path \`${path}\` can't be displayed in panel because no component supports it yet.`],
	[LevaErrors.UNKNOWN_INPUT]: (path, value) => [`input at path \`${path}\` is not recognized.`, value],
	[LevaErrors.DUPLICATE_KEYS]: (key, path, prevPath) => [`Key \`${key}\` of path \`${path}\` already exists at path \`${prevPath}\`. Even nested keys need to be unique. Rename one of the keys.`],
	[LevaErrors.ALREADY_REGISTERED_TYPE]: (type) => [`Type ${type} has already been registered. You can't register a component with the same type.`],
	[LevaErrors.CLIPBOARD_ERROR]: (value) => [`Error copying the value`, value],
	[LevaErrors.THEME_ERROR]: (category, key) => [`Error accessing the theme \`${category}.${key}\` value.`],
	[LevaErrors.PATH_DOESNT_EXIST]: (path) => [`Error getting the value at path \`${path}\`. There is probably an error in your \`render\` function.`],
	[LevaErrors.INPUT_TYPE_OVERRIDE]: (path, type, wrongType) => [`Input at path \`${path}\` already exists with type: \`${type}\`. Its type cannot be overridden with type \`${wrongType}\`.`],
	[LevaErrors.EMPTY_KEY]: () => ["Keys can not be empty, if you want to hide a label use whitespace."]
};
function _log(fn, errorType, ...args) {
	const errorFn = ErrorList[errorType];
	const [message, ...rest] = errorFn(...args);
	console[fn]("LEVA: " + message, ...rest);
}
var warn = _log.bind(null, "warn");
var log = _log.bind(null, "log");
var _excluded$a = ["value"], _excluded2$4 = ["schema"], _excluded3$1 = ["value"];
var Schemas = [];
var Plugins = {};
function getValueType(_ref) {
	let { value } = _ref, settings = _objectWithoutProperties$1(_ref, _excluded$a);
	for (let checker of Schemas) {
		const type = checker(value, settings);
		if (type) return type;
	}
}
function register(type, _ref2) {
	let { schema } = _ref2, plugin = _objectWithoutProperties$1(_ref2, _excluded2$4);
	if (type in Plugins) {
		warn(LevaErrors.ALREADY_REGISTERED_TYPE, type);
		return;
	}
	Schemas.push((value, settings) => schema(value, settings) && type);
	Plugins[type] = plugin;
}
function createInternalPlugin(plugin) {
	return plugin;
}
function normalize$3$1(type, input, path, data) {
	const { normalize: _normalize } = Plugins[type];
	if (_normalize) return _normalize(input, path, data);
	if (typeof input !== "object" || !("value" in input)) return { value: input };
	const { value } = input;
	return {
		value,
		settings: _objectWithoutProperties$1(input, _excluded3$1)
	};
}
function sanitize$4(type, value, settings, prevValue, path, store) {
	const { sanitize } = Plugins[type];
	if (sanitize) return sanitize(value, settings, prevValue, path, store);
	return value;
}
function format$2(type, value, settings) {
	const { format } = Plugins[type];
	if (format) return format(value, settings);
	return value;
}
function _toPrimitive(t, r) {
	if ("object" != typeof t || !t) return t;
	var e = t[Symbol.toPrimitive];
	if (void 0 !== e) {
		var i = e.call(t, r || "default");
		if ("object" != typeof i) return i;
		throw new TypeError("@@toPrimitive must return a primitive value.");
	}
	return ("string" === r ? String : Number)(t);
}
function _toPropertyKey(t) {
	var i = _toPrimitive(t, "string");
	return "symbol" == typeof i ? i : i + "";
}
function _defineProperty$2(e, r, t) {
	return (r = _toPropertyKey(r)) in e ? Object.defineProperty(e, r, {
		value: t,
		enumerable: !0,
		configurable: !0,
		writable: !0
	}) : e[r] = t, e;
}
function ownKeys$2(e, r) {
	var t = Object.keys(e);
	if (Object.getOwnPropertySymbols) {
		var o = Object.getOwnPropertySymbols(e);
		r && (o = o.filter(function(r) {
			return Object.getOwnPropertyDescriptor(e, r).enumerable;
		})), t.push.apply(t, o);
	}
	return t;
}
function _objectSpread2(e) {
	for (var r = 1; r < arguments.length; r++) {
		var t = null != arguments[r] ? arguments[r] : {};
		r % 2 ? ownKeys$2(Object(t), !0).forEach(function(r) {
			_defineProperty$2(e, r, t[r]);
		}) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(t)) : ownKeys$2(Object(t)).forEach(function(r) {
			Object.defineProperty(e, r, Object.getOwnPropertyDescriptor(t, r));
		});
	}
	return e;
}
var clamp = (x, min, max) => x > max ? max : x < min ? min : x;
var parseNumber = (v) => {
	if (v === "" || typeof v === "number") return v;
	try {
		const _v = evaluate(v);
		if (!isNaN(_v)) return _v;
	} catch (_unused) {}
	return parseFloat(v);
};
var log10 = Math.log(10);
function getStep(number) {
	let n = Math.abs(+String(number).replace(".", ""));
	if (n === 0) return .01;
	while (n !== 0 && n % 10 === 0) n /= 10;
	const significantDigits = Math.floor(Math.log(n) / log10) + 1;
	const step = Math.pow(10, Math.floor(Math.log10(Math.abs(number))) - significantDigits);
	return Math.max(step, .001);
}
var range = (v, min, max) => {
	if (max === min) return 0;
	return (clamp(v, min, max) - min) / (max - min);
};
var invertedRange = (p, min, max) => p * (max - min) + min;
var getUid = () => "_" + Math.random().toString(36).substr(2, 9);
var parens = /\(([^\(\)]+)\)/;
var exp = /(-?\d+(?:\.\d+)?)\s*\^\s*(-?\d+(?:\.\d+)?)/;
var muldiv = /(-?\d+(?:\.\d+)?)\s*([*/])\s*(-?\d+(?:\.\d+)?)/;
var addsub = /(-?\d+(?:\.\d+)?)\s*([+-])\s*(-?\d+(?:\.\d+)?)/;
function evaluate(expr) {
	expr = expr.replace(/\s+/g, "");
	if (parens.test(expr)) return evaluate(expr.replace(parens, (_, subExpr) => evaluate(subExpr).toString()));
	if (exp.test(expr)) return evaluate(expr.replace(exp, (_, a, b) => Math.pow(Number(a), Number(b)).toString()));
	if (muldiv.test(expr)) return evaluate(expr.replace(muldiv, (_, a, op, b) => op === "*" ? (Number(a) * Number(b)).toString() : Number(b) === 0 ? (() => {
		throw new Error("Division by zero");
	})() : (Number(a) / Number(b)).toString()));
	if (addsub.test(expr)) return evaluate(expr.replace(addsub, (_, a, op, b) => op === "+" ? (Number(a) + Number(b)).toString() : (Number(a) - Number(b)).toString()));
	return Number(expr);
}
function pick(object, keys) {
	return keys.reduce((obj, key) => {
		if (!!object && object.hasOwnProperty(key)) obj[key] = object[key];
		return obj;
	}, {});
}
function omit(object, keys) {
	const obj = _objectSpread2({}, object);
	keys.forEach((k) => k in object && delete obj[k]);
	return obj;
}
function mapArrayToKeys(value, keys) {
	return value.reduce((acc, v, i) => Object.assign(acc, { [keys[i]]: v }), {});
}
function isObject$1(variable) {
	return Object.prototype.toString.call(variable) === "[object Object]";
}
var isEmptyObject = (obj) => isObject$1(obj) && Object.keys(obj).length === 0;
var SpecialInputs = function(SpecialInputs) {
	SpecialInputs["BUTTON"] = "BUTTON";
	SpecialInputs["BUTTON_GROUP"] = "BUTTON_GROUP";
	SpecialInputs["MONITOR"] = "MONITOR";
	SpecialInputs["FOLDER"] = "FOLDER";
	return SpecialInputs;
}({});
var LevaInputs = function(LevaInputs) {
	LevaInputs["SELECT"] = "SELECT";
	LevaInputs["IMAGE"] = "IMAGE";
	LevaInputs["NUMBER"] = "NUMBER";
	LevaInputs["COLOR"] = "COLOR";
	LevaInputs["STRING"] = "STRING";
	LevaInputs["BOOLEAN"] = "BOOLEAN";
	LevaInputs["INTERVAL"] = "INTERVAL";
	LevaInputs["VECTOR3D"] = "VECTOR3D";
	LevaInputs["VECTOR2D"] = "VECTOR2D";
	return LevaInputs;
}({});
var _excluded$9 = ["type", "__customInput"], _excluded2$3 = [
	"render",
	"label",
	"optional",
	"order",
	"disabled",
	"hint",
	"onChange",
	"onEditStart",
	"onEditEnd",
	"transient"
], _excluded3$2 = ["type"];
function parseOptions(_input, key, mergedOptions = {}, customType) {
	var _commonOptions$option, _commonOptions$disabl;
	if (typeof _input !== "object" || Array.isArray(_input)) return {
		type: customType,
		input: _input,
		options: _objectSpread2({
			key,
			label: key,
			optional: false,
			disabled: false,
			order: 0
		}, mergedOptions)
	};
	if ("__customInput" in _input) {
		const { type: _type, __customInput } = _input;
		return parseOptions(__customInput, key, _objectWithoutProperties$1(_input, _excluded$9), _type);
	}
	const { render, label, optional, order = 0, disabled, hint, onChange, onEditStart, onEditEnd, transient } = _input, inputWithType = _objectWithoutProperties$1(_input, _excluded2$3);
	const commonOptions = _objectSpread2({
		render,
		key,
		label: label !== null && label !== void 0 ? label : key,
		hint,
		transient: transient !== null && transient !== void 0 ? transient : !!onChange,
		onEditStart,
		onEditEnd,
		disabled,
		optional,
		order
	}, mergedOptions);
	let { type } = inputWithType, input = _objectWithoutProperties$1(inputWithType, _excluded3$2);
	type = customType !== null && customType !== void 0 ? customType : type;
	if (type in SpecialInputs) return {
		type,
		input,
		options: commonOptions
	};
	let computedInput;
	if (customType && isObject$1(input) && "value" in input) computedInput = input.value;
	else computedInput = isEmptyObject(input) ? void 0 : input;
	return {
		type,
		input: computedInput,
		options: _objectSpread2(_objectSpread2({}, commonOptions), {}, {
			onChange,
			optional: (_commonOptions$option = commonOptions.optional) !== null && _commonOptions$option !== void 0 ? _commonOptions$option : false,
			disabled: (_commonOptions$disabl = commonOptions.disabled) !== null && _commonOptions$disabl !== void 0 ? _commonOptions$disabl : false
		})
	};
}
function normalizeInput(_input, key, path, data) {
	const parsedInputAndOptions = parseOptions(_input, key);
	const { type, input: parsedInput, options } = parsedInputAndOptions;
	if (type) {
		if (type in SpecialInputs) return parsedInputAndOptions;
		return {
			type,
			input: normalize$3$1(type, parsedInput, path, data),
			options
		};
	}
	let inputType = getValueType(parsedInput);
	if (inputType) return {
		type: inputType,
		input: normalize$3$1(inputType, parsedInput, path, data),
		options
	};
	inputType = getValueType({ value: parsedInput });
	if (inputType) return {
		type: inputType,
		input: normalize$3$1(inputType, { value: parsedInput }, path, data),
		options
	};
	return false;
}
function updateInput(input, newValue, path, store, fromPanel) {
	const { value, type, settings } = input;
	input.value = sanitizeValue({
		type,
		value,
		settings
	}, newValue, path, store);
	input.fromPanel = fromPanel;
}
var ValueError = function ValueError(message, value, error) {
	this.type = "LEVA_ERROR";
	this.message = "LEVA: " + message;
	this.previousValue = value;
	this.error = error;
};
function sanitizeValue({ type, value, settings }, newValue, path, store) {
	const _newValue = type !== "SELECT" && typeof newValue === "function" ? newValue(value) : newValue;
	let sanitizedNewValue;
	try {
		sanitizedNewValue = sanitize$4(type, _newValue, settings, value, path, store);
	} catch (e) {
		throw new ValueError(`The value \`${newValue}\` did not result in a correct value.`, value, e);
	}
	if (dequal(sanitizedNewValue, value)) return value;
	return sanitizedNewValue;
}
var debounce = (callback, wait, immediate = false) => {
	let timeout = 0;
	return function() {
		const args = arguments;
		const callNow = immediate && !timeout;
		const next = () => callback.apply(this, args);
		window.clearTimeout(timeout);
		timeout = window.setTimeout(next, wait);
		if (callNow) next();
	};
};
var multiplyStep = (event) => event.shiftKey ? 5 : event.altKey ? 1 / 5 : 1;
var _excluded$8 = ["value"], _excluded2$2$1 = ["min", "max"];
var schema$3 = (v) => {
	if (typeof v === "number") return true;
	if (typeof v === "string") {
		const _v = parseFloat(v);
		if (isNaN(_v)) return false;
		return v.substring(("" + _v).length).trim().length < 4;
	}
	return false;
};
var sanitize$3 = (v, { min: _min = -Infinity, max: _max = Infinity, suffix }) => {
	const _v = parseFloat(v);
	if (v === "" || isNaN(_v)) throw Error("Invalid number");
	const f = clamp(_v, _min, _max);
	return suffix ? f + suffix : f;
};
var format$1$1 = (v, { pad: _pad = 0, suffix }) => {
	const f = parseFloat(v).toFixed(_pad);
	return suffix ? f + suffix : f;
};
var normalize$2$1 = (_ref) => {
	let { value } = _ref, settings = _objectWithoutProperties$1(_ref, _excluded$8);
	const { min = -Infinity, max = Infinity } = settings, _settings = _objectWithoutProperties$1(settings, _excluded2$2$1);
	let _value = parseFloat(value);
	const suffix = typeof value === "string" ? value.substring(("" + _value).length) : void 0;
	_value = clamp(_value, min, max);
	let step = settings.step;
	if (!step) {
		if (Number.isFinite(min)) if (Number.isFinite(max)) step = +(Math.abs(max - min) / 100).toPrecision(1);
		else step = +(Math.abs(_value - min) / 100).toPrecision(1);
		else if (Number.isFinite(max)) step = +(Math.abs(max - _value) / 100).toPrecision(1);
	}
	const padStep = step ? getStep(step) * 10 : getStep(_value);
	step = step || padStep / 10;
	const pad = Math.round(clamp(Math.log10(1 / padStep), 0, 2));
	return {
		value: suffix ? _value + suffix : _value,
		settings: _objectSpread2({
			initialValue: _value,
			step,
			pad,
			min,
			max,
			suffix
		}, _settings)
	};
};
var sanitizeStep$1 = (v, { step, initialValue }) => {
	return initialValue + Math.round((v - initialValue) / step) * step;
};
var props$3 = /* @__PURE__ */ Object.freeze({
	__proto__: null,
	schema: schema$3,
	sanitize: sanitize$3,
	format: format$1$1,
	normalize: normalize$2$1,
	sanitizeStep: sanitizeStep$1
});
function _extends() {
	return _extends = Object.assign ? Object.assign.bind() : function(n) {
		for (var e = 1; e < arguments.length; e++) {
			var t = arguments[e];
			for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]);
		}
		return n;
	}, _extends.apply(null, arguments);
}
var InputContext = (0, import_react.createContext)({});
function useInputContext() {
	return (0, import_react.useContext)(InputContext);
}
var ThemeContext = (0, import_react.createContext)(null);
var StoreContext = (0, import_react.createContext)(null);
var PanelSettingsContext = (0, import_react.createContext)(null);
function useStoreContext() {
	return (0, import_react.useContext)(StoreContext);
}
function usePanelSettingsContext() {
	return (0, import_react.useContext)(PanelSettingsContext);
}
var getDefaultTheme = () => ({
	colors: {
		elevation1: "#292d39",
		elevation2: "#181c20",
		elevation3: "#373c4b",
		accent1: "#0066dc",
		accent2: "#007bff",
		accent3: "#3c93ff",
		highlight1: "#535760",
		highlight2: "#8c92a4",
		highlight3: "#fefefe",
		vivid1: "#ffcc00",
		folderWidgetColor: "$highlight2",
		folderTextColor: "$highlight3",
		toolTipBackground: "$highlight3",
		toolTipText: "$elevation2"
	},
	radii: {
		xs: "2px",
		sm: "3px",
		lg: "10px"
	},
	space: {
		xs: "3px",
		sm: "6px",
		md: "10px",
		rowGap: "7px",
		colGap: "7px"
	},
	fonts: {
		mono: `ui-monospace, SFMono-Regular, Menlo, 'Roboto Mono', monospace`,
		sans: `system-ui, sans-serif`
	},
	fontSizes: {
		root: "11px",
		toolTip: "$root"
	},
	sizes: {
		rootWidth: "280px",
		controlWidth: "160px",
		numberInputMinWidth: "38px",
		scrubberWidth: "8px",
		scrubberHeight: "16px",
		rowHeight: "24px",
		folderTitleHeight: "20px",
		checkboxSize: "16px",
		joystickWidth: "100px",
		joystickHeight: "100px",
		colorPickerWidth: "$controlWidth",
		colorPickerHeight: "100px",
		imagePreviewWidth: "$controlWidth",
		imagePreviewHeight: "100px",
		monitorHeight: "60px",
		titleBarHeight: "39px"
	},
	shadows: {
		level1: "0 0 9px 0 #00000088",
		level2: "0 4px 14px #00000033"
	},
	borderWidths: {
		root: "0px",
		input: "1px",
		focus: "1px",
		hover: "1px",
		active: "1px",
		folder: "1px"
	},
	fontWeights: {
		label: "normal",
		folder: "normal",
		button: "normal"
	}
});
function createStateClass(value, options) {
	const [borderColor, bgColor] = value.split(" ");
	const css = {};
	if (borderColor !== "none") css.boxShadow = `${options.inset ? "inset " : ""}0 0 0 $borderWidths${[options.key]} $colors${borderColor !== "default" && borderColor || options.borderColor}`;
	if (bgColor) css.backgroundColor = bgColor;
	return css;
}
var utils = {
	$inputStyle: () => (value) => createStateClass(value, {
		key: "$input",
		borderColor: "$highlight1",
		inset: true
	}),
	$focusStyle: () => (value) => createStateClass(value, {
		key: "$focus",
		borderColor: "$accent2"
	}),
	$hoverStyle: () => (value) => createStateClass(value, {
		key: "$hover",
		borderColor: "$accent1",
		inset: true
	}),
	$activeStyle: () => (value) => createStateClass(value, {
		key: "$active",
		borderColor: "$accent1",
		inset: true
	})
};
var stitches = q$1({
	prefix: "leva",
	theme: getDefaultTheme(),
	utils: _objectSpread2(_objectSpread2({}, utils), {}, {
		$flex: () => ({
			display: "flex",
			alignItems: "center"
		}),
		$flexCenter: () => ({
			display: "flex",
			alignItems: "center",
			justifyContent: "center"
		}),
		$reset: () => ({
			outline: "none",
			fontSize: "inherit",
			fontWeight: "inherit",
			color: "inherit",
			fontFamily: "inherit",
			border: "none",
			backgroundColor: "transparent",
			appearance: "none"
		}),
		$draggable: () => ({
			touchAction: "none",
			WebkitUserDrag: "none",
			userSelect: "none"
		}),
		$focus: (value) => ({ "&:focus": utils.$focusStyle()(value) }),
		$focusWithin: (value) => ({ "&:focus-within": utils.$focusStyle()(value) }),
		$hover: (value) => ({ "&:hover": utils.$hoverStyle()(value) }),
		$active: (value) => ({ "&:active": utils.$activeStyle()(value) })
	})
});
var styled = stitches.styled;
stitches.css;
var createTheme = stitches.createTheme;
var globalCss = stitches.globalCss;
stitches.keyframes;
var globalStyles = globalCss({ ".leva__panel__dragged": {
	WebkitUserDrag: "none",
	userSelect: "none",
	input: { userSelect: "none" },
	"*": { cursor: "ew-resize !important" }
} });
function mergeTheme(newTheme) {
	const defaultTheme = getDefaultTheme();
	if (!newTheme) return {
		theme: defaultTheme,
		className: ""
	};
	Object.keys(newTheme).forEach((key) => {
		Object.assign(defaultTheme[key], newTheme[key]);
	});
	return {
		theme: defaultTheme,
		className: createTheme(defaultTheme).className
	};
}
function useTh(category, key) {
	const { theme } = (0, import_react.useContext)(ThemeContext);
	if (!(category in theme) || !(key in theme[category])) {
		warn(LevaErrors.THEME_ERROR, category, key);
		return "";
	}
	let _key = key;
	while (true) {
		let value = theme[category][_key];
		if (typeof value === "string" && value.charAt(0) === "$") _key = value.substr(1);
		else return value;
	}
}
var StyledInput = styled("input", {
	$reset: "",
	padding: "0 $sm",
	width: 0,
	minWidth: 0,
	flex: 1,
	height: "100%",
	variants: {
		levaType: { number: { textAlign: "right" } },
		as: { textarea: { padding: "$sm" } }
	}
});
var InnerLabel = styled("div", {
	$draggable: "",
	height: "100%",
	$flexCenter: "",
	position: "relative",
	padding: "0 $xs",
	fontSize: "0.8em",
	opacity: .8,
	cursor: "default",
	touchAction: "none",
	[`& + ${StyledInput}`]: { paddingLeft: 0 }
});
var InnerNumberLabel = styled(InnerLabel, {
	cursor: "ew-resize",
	marginRight: "-$xs",
	textTransform: "uppercase",
	opacity: .3,
	"&:hover": { opacity: 1 },
	variants: { dragging: { true: {
		backgroundColor: "$accent2",
		opacity: 1
	} } }
});
var InputContainer = styled("div", {
	$flex: "",
	position: "relative",
	borderRadius: "$sm",
	overflow: "hidden",
	color: "inherit",
	height: "$rowHeight",
	backgroundColor: "$elevation3",
	$inputStyle: "$elevation1",
	$hover: "",
	$focusWithin: "",
	variants: { textArea: { true: { height: "auto" } } }
});
var _excluded$7$1 = [
	"innerLabel",
	"value",
	"onUpdate",
	"onChange",
	"onKeyDown",
	"type",
	"id",
	"inputType",
	"rows"
], _excluded2$1$3 = ["onUpdate"];
function ValueInput(_ref) {
	let { innerLabel, value, onUpdate, onChange, onKeyDown, type, id, inputType = "text", rows = 0 } = _ref, props = _objectWithoutProperties$1(_ref, _excluded$7$1);
	const { id: _id, emitOnEditStart, emitOnEditEnd, disabled } = useInputContext();
	const inputId = id || _id;
	const inputRef = (0, import_react.useRef)(null);
	const isTextArea = rows > 0;
	const asType = isTextArea ? "textarea" : "input";
	const update = (0, import_react.useCallback)((fn) => (event) => {
		const _value = event.currentTarget.value;
		fn(_value);
	}, []);
	import_react.useEffect(() => {
		const ref = inputRef.current;
		const _onUpdate = update((value) => {
			onUpdate(value);
			emitOnEditEnd();
		});
		ref === null || ref === void 0 || ref.addEventListener("blur", _onUpdate);
		return () => ref === null || ref === void 0 ? void 0 : ref.removeEventListener("blur", _onUpdate);
	}, [
		update,
		onUpdate,
		emitOnEditEnd
	]);
	const onKeyPress = (0, import_react.useCallback)((event) => {
		if (event.key === "Enter") update(onUpdate)(event);
	}, [update, onUpdate]);
	const inputProps = Object.assign({ as: asType }, isTextArea ? { rows } : {}, props);
	return import_react.createElement(InputContainer, { textArea: isTextArea }, innerLabel && typeof innerLabel === "string" ? import_react.createElement(InnerLabel, null, innerLabel) : innerLabel, import_react.createElement(StyledInput, _extends({
		levaType: type,
		ref: inputRef,
		id: inputId,
		type: inputType,
		autoComplete: "off",
		spellCheck: "false",
		value,
		onChange: update(onChange),
		onFocus: () => emitOnEditStart(),
		onKeyPress,
		onKeyDown,
		disabled
	}, inputProps)));
}
function NumberInput(_ref2) {
	let { onUpdate } = _ref2, props = _objectWithoutProperties$1(_ref2, _excluded2$1$3);
	const _onUpdate = (0, import_react.useCallback)((v) => onUpdate(parseNumber(v)), [onUpdate]);
	const onKeyDown = (0, import_react.useCallback)((event) => {
		const dir = event.key === "ArrowUp" ? 1 : event.key === "ArrowDown" ? -1 : 0;
		if (dir) {
			event.preventDefault();
			const step = event.altKey ? .1 : event.shiftKey ? 10 : 1;
			onUpdate((v) => parseFloat(v) + dir * step);
		}
	}, [onUpdate]);
	return import_react.createElement(ValueInput, _extends({}, props, {
		onUpdate: _onUpdate,
		onKeyDown,
		type: "number"
	}));
}
var StyledFolder = styled("div", {});
var StyledWrapper = styled("div", {
	position: "relative",
	background: "$elevation2",
	transition: "height 300ms ease",
	variants: {
		fill: {
			true: {},
			false: {}
		},
		flat: {
			false: {},
			true: {}
		},
		isRoot: {
			true: {},
			false: {
				paddingLeft: "$md",
				"&::after": {
					content: "\"\"",
					position: "absolute",
					left: 0,
					top: 0,
					width: "$borderWidths$folder",
					height: "100%",
					backgroundColor: "$folderWidgetColor",
					opacity: .4,
					transform: "translateX(-50%)"
				}
			}
		}
	},
	compoundVariants: [{
		isRoot: true,
		fill: false,
		css: {
			overflowY: "auto",
			maxHeight: "calc(100vh - 20px - $$titleBarHeight)"
		}
	}, {
		isRoot: true,
		flat: false,
		css: { borderRadius: "$lg" }
	}]
});
var StyledTitle = styled("div", {
	$flex: "",
	color: "$folderTextColor",
	userSelect: "none",
	cursor: "pointer",
	height: "$folderTitleHeight",
	fontWeight: "$folder",
	"> svg": {
		marginLeft: -4,
		marginRight: 4,
		cursor: "pointer",
		fill: "$folderWidgetColor",
		opacity: .6
	},
	"&:hover > svg": { fill: "$folderWidgetColor" },
	[`&:hover + ${StyledWrapper}::after`]: { opacity: .6 },
	[`${StyledFolder}:hover > & + ${StyledWrapper}::after`]: { opacity: .6 },
	[`${StyledFolder}:hover > & > svg`]: { opacity: 1 }
});
var StyledContent = styled("div", {
	position: "relative",
	display: "grid",
	gridTemplateColumns: "100%",
	rowGap: "$rowGap",
	transition: "opacity 250ms ease",
	variants: {
		toggled: {
			true: {
				opacity: 1,
				transitionDelay: "250ms"
			},
			false: {
				opacity: 0,
				transitionDelay: "0ms",
				pointerEvents: "none"
			}
		},
		isRoot: { true: {
			"& > div": {
				paddingLeft: "$md",
				paddingRight: "$md"
			},
			"& > div:first-of-type": { paddingTop: "$sm" },
			"& > div:last-of-type": { paddingBottom: "$sm" },
			[`> ${StyledFolder}:not(:first-of-type)`]: {
				paddingTop: "$sm",
				marginTop: "$md",
				borderTop: "$borderWidths$folder solid $colors$elevation1"
			}
		} }
	}
});
var StyledRow = styled("div", {
	position: "relative",
	zIndex: 100,
	display: "grid",
	rowGap: "$rowGap",
	gridTemplateRows: "minmax($sizes$rowHeight, max-content)",
	alignItems: "center",
	color: "$highlight2",
	[`${StyledContent} > &`]: {
		"&:first-of-type": { marginTop: "$rowGap" },
		"&:last-of-type": { marginBottom: "$rowGap" }
	},
	variants: { disabled: {
		true: { pointerEvents: "none" },
		false: { "&:hover,&:focus-within": { color: "$highlight3" } }
	} }
});
var StyledInputRow = styled(StyledRow, {
	gridTemplateColumns: "auto $sizes$controlWidth",
	columnGap: "$colGap"
});
var CopyLabelContainer = styled("div", {
	$flex: "",
	height: "100%",
	position: "relative",
	overflow: "hidden",
	"& > div": {
		marginLeft: "$colGap",
		padding: "0 $xs",
		opacity: .4
	},
	"& > div:hover": { opacity: .8 },
	"& > div > svg": {
		display: "none",
		cursor: "pointer",
		width: 13,
		minWidth: 13,
		height: 13,
		backgroundColor: "$elevation2"
	},
	"&:hover > div > svg": { display: "block" },
	variants: { align: { top: {
		height: "100%",
		alignItems: "flex-start",
		paddingTop: "$sm"
	} } }
});
var StyledOptionalToggle = styled("input", {
	$reset: "",
	height: 0,
	width: 0,
	opacity: 0,
	margin: 0,
	"& + label": {
		position: "relative",
		$flexCenter: "",
		height: "100%",
		userSelect: "none",
		cursor: "pointer",
		paddingLeft: 2,
		paddingRight: "$sm",
		pointerEvents: "auto"
	},
	"& + label:after": {
		content: "\"\"",
		width: 6,
		height: 6,
		backgroundColor: "$elevation3",
		borderRadius: "50%",
		$activeStyle: ""
	},
	"&:focus + label:after": { $focusStyle: "" },
	"& + label:active:after": {
		backgroundColor: "$accent1",
		$focusStyle: ""
	},
	"&:checked + label:after": { backgroundColor: "$accent1" }
});
var StyledLabel = styled("label", {
	fontWeight: "$label",
	overflow: "hidden",
	textOverflow: "ellipsis",
	whiteSpace: "nowrap",
	"& > svg": { display: "block" }
});
var StyledInputWrapper$1 = styled("div", {
	opacity: 1,
	variants: { disabled: { true: {
		opacity: .6,
		pointerEvents: "none",
		[`& ${StyledLabel}`]: { pointerEvents: "auto" }
	} } }
});
var Overlay = styled("div", {
	position: "fixed",
	top: 0,
	bottom: 0,
	right: 0,
	left: 0,
	zIndex: 1e3,
	userSelect: "none"
});
var StyledToolTipContent = styled("div", {
	background: "$toolTipBackground",
	fontFamily: "$sans",
	fontSize: "$toolTip",
	padding: "$xs $sm",
	color: "$toolTipText",
	borderRadius: "$xs",
	boxShadow: "$level2",
	maxWidth: 260
});
var ToolTipArrow = styled(Arrow2, { fill: "$toolTipBackground" });
function Portal({ children, container = ((_globalThis$document) => globalThis === null || globalThis === void 0 || (_globalThis$document = globalThis.document) === null || _globalThis$document === void 0 ? void 0 : _globalThis$document.body)() }) {
	const { className } = (0, import_react.useContext)(ThemeContext);
	return import_react.createElement(Root, {
		className,
		container
	}, children);
}
var _excluded$6$1 = ["align"];
function OptionalToggle() {
	const { id, disable, disabled } = useInputContext();
	return import_react.createElement(import_react.Fragment, null, import_react.createElement(StyledOptionalToggle, {
		id: id + "__disable",
		type: "checkbox",
		checked: !disabled,
		onChange: () => disable(!disabled)
	}), import_react.createElement("label", { htmlFor: id + "__disable" }));
}
function RawLabel(props) {
	const { id, optional, hint } = useInputContext();
	const htmlForProp = props.htmlFor || (id ? id : void 0);
	const titleProp = !hint && typeof props.children === "string" ? props.children : void 0;
	return import_react.createElement(import_react.Fragment, null, optional && import_react.createElement(OptionalToggle, null), hint !== void 0 ? import_react.createElement(Root3, null, import_react.createElement(Trigger, { asChild: true }, import_react.createElement(StyledLabel, _extends({ htmlFor: htmlForProp }, props))), import_react.createElement(Content2, {
		side: "top",
		sideOffset: 2
	}, import_react.createElement(StyledToolTipContent, null, hint, import_react.createElement(ToolTipArrow, null)))) : import_react.createElement(StyledLabel, _extends({
		htmlFor: htmlForProp,
		title: titleProp
	}, props)));
}
function Label(_ref) {
	let { align } = _ref, props = _objectWithoutProperties$1(_ref, _excluded$6$1);
	const { value, label, key, disabled } = useInputContext();
	const { hideCopyButton } = usePanelSettingsContext();
	const copyEnabled = !hideCopyButton && key !== void 0;
	const [copied, setCopied] = (0, import_react.useState)(false);
	const handleClick = async () => {
		try {
			await navigator.clipboard.writeText(JSON.stringify({ [key]: value !== null && value !== void 0 ? value : "" }));
			setCopied(true);
		} catch (_unused) {
			warn(LevaErrors.CLIPBOARD_ERROR, { [key]: value });
		}
	};
	return import_react.createElement(CopyLabelContainer, {
		align,
		onPointerLeave: () => setCopied(false)
	}, import_react.createElement(RawLabel, props), copyEnabled && !disabled && import_react.createElement("div", { title: `Click to copy ${typeof label === "string" ? label : key} value` }, !copied ? import_react.createElement("svg", {
		onClick: handleClick,
		xmlns: "http://www.w3.org/2000/svg",
		viewBox: "0 0 20 20",
		fill: "currentColor"
	}, import_react.createElement("path", { d: "M8 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" }), import_react.createElement("path", { d: "M6 3a2 2 0 00-2 2v11a2 2 0 002 2h8a2 2 0 002-2V5a2 2 0 00-2-2 3 3 0 01-3 3H9a3 3 0 01-3-3z" })) : import_react.createElement("svg", {
		xmlns: "http://www.w3.org/2000/svg",
		viewBox: "0 0 20 20",
		fill: "currentColor"
	}, import_react.createElement("path", { d: "M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" }), import_react.createElement("path", {
		fillRule: "evenodd",
		d: "M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm9.707 5.707a1 1 0 00-1.414-1.414L9 12.586l-1.293-1.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z",
		clipRule: "evenodd"
	}))));
}
var _excluded$5$1 = ["toggled"];
var Svg = styled("svg", {
	fill: "currentColor",
	transition: "transform 350ms ease, fill 250ms ease"
});
function Chevron(_ref) {
	let { toggled } = _ref, props = _objectWithoutProperties$1(_ref, _excluded$5$1);
	return import_react.createElement(Svg, _extends({
		width: "9",
		height: "5",
		viewBox: "0 0 9 5",
		xmlns: "http://www.w3.org/2000/svg",
		style: { transform: `rotate(${toggled ? 0 : -90}deg)` }
	}, props), import_react.createElement("path", { d: "M3.8 4.4c.4.3 1 .3 1.4 0L8 1.7A1 1 0 007.4 0H1.6a1 1 0 00-.7 1.7l3 2.7z" }));
}
var _excluded$4$1 = ["input"];
function Row(_ref) {
	let { input } = _ref, props = _objectWithoutProperties$1(_ref, _excluded$4$1);
	if (input) return import_react.createElement(StyledInputRow, props);
	return import_react.createElement(StyledRow, props);
}
function useInputSetters({ value, type, settings, setValue }) {
	const [displayValue, setDisplayValue] = (0, import_react.useState)(format$2(type, value, settings));
	const previousValueRef = (0, import_react.useRef)(value);
	const settingsRef = (0, import_react.useRef)(settings);
	settingsRef.current = settings;
	const setFormat = (0, import_react.useCallback)((v) => setDisplayValue(format$2(type, v, settingsRef.current)), [type]);
	const onUpdate = (0, import_react.useCallback)((updatedValue) => {
		try {
			setValue(updatedValue);
		} catch (error) {
			const { type, previousValue } = error;
			if (type !== "LEVA_ERROR") throw error;
			setFormat(previousValue);
		}
	}, [setFormat, setValue]);
	(0, import_react.useEffect)(() => {
		if (!dequal(value, previousValueRef.current)) setFormat(value);
		previousValueRef.current = value;
	}, [value, setFormat]);
	return {
		displayValue,
		onChange: setDisplayValue,
		onUpdate
	};
}
function useDrag(handler, config) {
	const { emitOnEditStart, emitOnEditEnd } = useInputContext();
	return useDrag$1((state) => {
		if (state.first) {
			document.body.classList.add("leva__panel__dragged");
			emitOnEditStart === null || emitOnEditStart === void 0 || emitOnEditStart();
		}
		const result = handler(state);
		if (state.last) {
			document.body.classList.remove("leva__panel__dragged");
			emitOnEditEnd === null || emitOnEditEnd === void 0 || emitOnEditEnd();
		}
		return result;
	}, config);
}
function useCanvas2d(fn) {
	const canvas = (0, import_react.useRef)(null);
	const ctx = (0, import_react.useRef)(null);
	const hasFired = (0, import_react.useRef)(false);
	(0, import_react.useEffect)(() => {
		const handleCanvas = debounce(() => {
			canvas.current.width = canvas.current.offsetWidth * window.devicePixelRatio;
			canvas.current.height = canvas.current.offsetHeight * window.devicePixelRatio;
			fn(canvas.current, ctx.current);
		}, 250);
		window.addEventListener("resize", handleCanvas);
		if (!hasFired.current) {
			handleCanvas();
			hasFired.current = true;
		}
		return () => window.removeEventListener("resize", handleCanvas);
	}, [fn]);
	(0, import_react.useEffect)(() => {
		ctx.current = canvas.current.getContext("2d");
	}, []);
	return [canvas, ctx];
}
function useTransform() {
	const ref = (0, import_react.useRef)(null);
	const local = (0, import_react.useRef)({
		x: 0,
		y: 0
	});
	return [ref, (0, import_react.useCallback)((point) => {
		Object.assign(local.current, point);
		if (ref.current) ref.current.style.transform = `translate3d(${local.current.x}px, ${local.current.y}px, 0)`;
	}, [])];
}
var _excluded$3$1 = ["__refCount"];
var getInputAtPath = (data, path) => {
	if (!data[path]) return null;
	const _data$path = data[path];
	return _objectWithoutProperties$1(_data$path, _excluded$3$1);
};
function useInput(path) {
	const store = useStoreContext();
	const [state, setState] = (0, import_react.useState)(getInputAtPath(store.getData(), path));
	const set = (0, import_react.useCallback)((value) => store.setValueAtPath(path, value, true), [path, store]);
	const setSettings = (0, import_react.useCallback)((settings) => store.setSettingsAtPath(path, settings), [path, store]);
	const disable = (0, import_react.useCallback)((flag) => store.disableInputAtPath(path, flag), [path, store]);
	const emitOnEditStart = (0, import_react.useCallback)(() => store.emitOnEditStart(path), [path, store]);
	const emitOnEditEnd = (0, import_react.useCallback)(() => store.emitOnEditEnd(path), [path, store]);
	(0, import_react.useEffect)(() => {
		setState(getInputAtPath(store.getData(), path));
		const unsub = store.useStore.subscribe((s) => getInputAtPath(s.data, path), setState, { equalityFn: shallow });
		return () => unsub();
	}, [store, path]);
	return [state, {
		set,
		setSettings,
		disable,
		storeId: store.storeId,
		emitOnEditStart,
		emitOnEditEnd
	}];
}
var RangeGrid = styled("div", { variants: { hasRange: { true: {
	position: "relative",
	display: "grid",
	gridTemplateColumns: "auto $sizes$numberInputMinWidth",
	columnGap: "$colGap",
	alignItems: "center"
} } } });
var Range = styled("div", {
	position: "relative",
	width: "100%",
	height: 2,
	borderRadius: "$xs",
	backgroundColor: "$elevation1"
});
var Scrubber = styled("div", {
	position: "absolute",
	width: "$scrubberWidth",
	height: "$scrubberHeight",
	borderRadius: "$xs",
	boxShadow: "0 0 0 2px $colors$elevation2",
	backgroundColor: "$accent2",
	cursor: "pointer",
	$active: "none $accent1",
	$hover: "none $accent3",
	variants: { position: {
		left: {
			borderTopRightRadius: 0,
			borderBottomRightRadius: 0,
			transform: "translateX(calc(-0.5 * ($sizes$scrubberWidth + 4px)))"
		},
		right: {
			borderTopLeftRadius: 0,
			borderBottomLeftRadius: 0,
			transform: "translateX(calc(0.5 * ($sizes$scrubberWidth + 4px)))"
		}
	} }
});
var RangeWrapper = styled("div", {
	position: "relative",
	$flex: "",
	height: "100%",
	cursor: "pointer",
	touchAction: "none"
});
var Indicator = styled("div", {
	position: "absolute",
	height: "100%",
	backgroundColor: "$accent2"
});
function RangeSlider({ value, min, max, onDrag, step, initialValue }) {
	const ref = (0, import_react.useRef)(null);
	const scrubberRef = (0, import_react.useRef)(null);
	const rangeWidth = (0, import_react.useRef)(0);
	const scrubberWidth = useTh("sizes", "scrubberWidth");
	const bind = useDrag(({ event, first, xy: [x], movement: [mx], memo }) => {
		if (first) {
			const { width, left } = ref.current.getBoundingClientRect();
			rangeWidth.current = width - parseFloat(scrubberWidth);
			memo = (event === null || event === void 0 ? void 0 : event.target) === scrubberRef.current ? value : invertedRange((x - left) / width, min, max);
		}
		onDrag(sanitizeStep$1(memo + invertedRange(mx / rangeWidth.current, 0, max - min), {
			step,
			initialValue
		}));
		return memo;
	});
	const pos = range(value, min, max);
	return import_react.createElement(RangeWrapper, _extends({ ref }, bind()), import_react.createElement(Range, null, import_react.createElement(Indicator, { style: {
		left: 0,
		right: `${(1 - pos) * 100}%`
	} })), import_react.createElement(Scrubber, {
		ref: scrubberRef,
		style: { left: `calc(${pos} * (100% - ${scrubberWidth}))` }
	}));
}
var DraggableLabel = import_react.memo(({ label, onUpdate, step, innerLabelTrim }) => {
	const [dragging, setDragging] = (0, import_react.useState)(false);
	const bind = useDrag(({ active, delta: [dx], event, memo: _memo = 0, first, last, target }) => {
		if (first) target.requestPointerLock();
		if (last) document.exitPointerLock();
		setDragging(active);
		_memo += dx / 2;
		if (Math.abs(_memo) >= 1) {
			onUpdate((v) => parseFloat(v) + Math.floor(_memo) * step * multiplyStep(event));
			_memo = 0;
		}
		return _memo;
	});
	return import_react.createElement(InnerNumberLabel, _extends({
		dragging,
		title: label.length > 1 ? label : ""
	}, bind()), label.slice(0, innerLabelTrim));
});
function Number$1({ label, id, displayValue, onUpdate, onChange, settings, innerLabelTrim = 1 }) {
	const InnerLabel = innerLabelTrim > 0 && import_react.createElement(DraggableLabel, {
		label,
		step: settings.step,
		onUpdate,
		innerLabelTrim
	});
	return import_react.createElement(NumberInput, {
		id,
		value: String(displayValue),
		onUpdate,
		onChange,
		innerLabel: InnerLabel
	});
}
function NumberComponent() {
	const props = useInputContext();
	const { label, value, onUpdate, settings, id } = props;
	const { min, max } = settings;
	const hasRange = max !== Infinity && min !== -Infinity;
	return import_react.createElement(Row, { input: true }, import_react.createElement(Label, null, label), import_react.createElement(RangeGrid, { hasRange }, hasRange && import_react.createElement(RangeSlider, _extends({
		value: parseFloat(value),
		onDrag: onUpdate
	}, settings)), import_react.createElement(Number$1, _extends({}, props, {
		id,
		label: "value",
		innerLabelTrim: hasRange ? 0 : 1
	}))));
}
var { sanitizeStep } = props$3, rest = _objectWithoutProperties$1(props$3, ["sanitizeStep"]);
var number$1 = createInternalPlugin(_objectSpread2({ component: NumberComponent }, rest));
var schema$2$1 = (_o, s) => v8n().schema({ options: v8n().passesAnyOf(v8n().object(), v8n().array()) }).test(s);
var sanitize$2$1 = (value, { values }) => {
	if (values.indexOf(value) < 0) throw Error(`Selected value doesn't match Select options`);
	return value;
};
var format$3 = (value, { values }) => {
	return values.indexOf(value);
};
var normalize$1$1 = (input) => {
	let { value, options } = input;
	let keys;
	let values;
	if (Array.isArray(options)) {
		values = options;
		keys = options.map((o) => String(o));
	} else {
		values = Object.values(options);
		keys = Object.keys(options);
	}
	if (!("value" in input)) value = values[0];
	else if (!values.includes(value)) {
		keys.unshift(String(value));
		values.unshift(value);
	}
	if (!Object.values(options).includes(value)) options[String(value)] = value;
	return {
		value,
		settings: {
			keys,
			values
		}
	};
};
var props$2$1 = /* @__PURE__ */ Object.freeze({
	__proto__: null,
	schema: schema$2$1,
	sanitize: sanitize$2$1,
	format: format$3,
	normalize: normalize$1$1
});
var SelectContainer = styled("div", {
	$flexCenter: "",
	position: "relative",
	"> svg": {
		pointerEvents: "none",
		position: "absolute",
		right: "$md"
	}
});
var NativeSelect = styled("select", {
	position: "absolute",
	top: 0,
	left: 0,
	width: "100%",
	height: "100%",
	opacity: 0
});
var PresentationalSelect = styled("div", {
	display: "flex",
	alignItems: "center",
	width: "100%",
	height: "$rowHeight",
	backgroundColor: "$elevation3",
	borderRadius: "$sm",
	padding: "0 $sm",
	cursor: "pointer",
	[`${NativeSelect}:focus + &`]: { $focusStyle: "" },
	[`${NativeSelect}:hover + &`]: { $hoverStyle: "" }
});
function Select({ displayValue, value, onUpdate, id, settings, disabled }) {
	const { keys, values } = settings;
	const lastDisplayedValue = (0, import_react.useRef)();
	if (value === values[displayValue]) lastDisplayedValue.current = keys[displayValue];
	return import_react.createElement(SelectContainer, null, import_react.createElement(NativeSelect, {
		id,
		value: displayValue,
		onChange: (e) => onUpdate(values[Number(e.currentTarget.value)]),
		disabled
	}, keys.map((key, index) => import_react.createElement("option", {
		key,
		value: index
	}, key))), import_react.createElement(PresentationalSelect, null, lastDisplayedValue.current), import_react.createElement(Chevron, { toggled: true }));
}
function SelectComponent() {
	const { label, value, displayValue, onUpdate, id, disabled, settings } = useInputContext();
	return import_react.createElement(Row, { input: true }, import_react.createElement(Label, null, label), import_react.createElement(Select, {
		id,
		value,
		displayValue,
		onUpdate,
		settings,
		disabled
	}));
}
var select = createInternalPlugin(_objectSpread2({ component: SelectComponent }, props$2$1));
var schema$1$1 = (o) => v8n().string().test(o);
var sanitize$1$1 = (v) => {
	if (typeof v !== "string") throw Error(`Invalid string`);
	return v;
};
var normalize$4 = ({ value, editable: _editable = true, rows: _rows = false }) => {
	return {
		value,
		settings: {
			editable: _editable,
			rows: typeof _rows === "number" ? _rows : _rows ? 5 : 0
		}
	};
};
var props$1$1 = /* @__PURE__ */ Object.freeze({
	__proto__: null,
	schema: schema$1$1,
	sanitize: sanitize$1$1,
	normalize: normalize$4
});
var _excluded$2$1 = [
	"displayValue",
	"onUpdate",
	"onChange",
	"editable"
];
var NonEditableString = styled("div", { whiteSpace: "pre-wrap" });
function String$1(_ref) {
	let { displayValue, onUpdate, onChange, editable = true } = _ref, props = _objectWithoutProperties$1(_ref, _excluded$2$1);
	if (editable) return import_react.createElement(ValueInput, _extends({
		value: displayValue,
		onUpdate,
		onChange
	}, props));
	return import_react.createElement(NonEditableString, null, displayValue);
}
function StringComponent() {
	const { label, settings, displayValue, onUpdate, onChange } = useInputContext();
	return import_react.createElement(Row, { input: true }, import_react.createElement(Label, null, label), import_react.createElement(String$1, _extends({
		displayValue,
		onUpdate,
		onChange
	}, settings)));
}
var string = createInternalPlugin(_objectSpread2({ component: StringComponent }, props$1$1));
var schema$4 = (o) => v8n().boolean().test(o);
var sanitize$5 = (v) => {
	if (typeof v !== "boolean") throw Error("Invalid boolean");
	return v;
};
var props$4 = /* @__PURE__ */ Object.freeze({
	__proto__: null,
	schema: schema$4,
	sanitize: sanitize$5
});
var StyledInputWrapper = styled("div", {
	position: "relative",
	$flex: "",
	height: "$rowHeight",
	input: {
		$reset: "",
		height: 0,
		width: 0,
		opacity: 0,
		margin: 0
	},
	label: {
		position: "relative",
		$flexCenter: "",
		userSelect: "none",
		cursor: "pointer",
		height: "$checkboxSize",
		width: "$checkboxSize",
		backgroundColor: "$elevation3",
		borderRadius: "$sm",
		$hover: ""
	},
	"input:focus + label": { $focusStyle: "" },
	"input:focus:checked + label, input:checked + label:hover": { $hoverStyle: "$accent3" },
	"input + label:active": { backgroundColor: "$accent1" },
	"input:checked + label:active": { backgroundColor: "$accent1" },
	"label > svg": {
		display: "none",
		width: "90%",
		height: "90%",
		stroke: "$highlight3"
	},
	"input:checked + label": { backgroundColor: "$accent2" },
	"input:checked + label > svg": { display: "block" }
});
function Boolean$1({ value, onUpdate, id, disabled }) {
	return import_react.createElement(StyledInputWrapper, null, import_react.createElement("input", {
		id,
		type: "checkbox",
		checked: value,
		onChange: (e) => onUpdate(e.currentTarget.checked),
		disabled
	}), import_react.createElement("label", { htmlFor: id }, import_react.createElement("svg", {
		xmlns: "http://www.w3.org/2000/svg",
		fill: "none",
		viewBox: "0 0 24 24"
	}, import_react.createElement("path", {
		strokeLinecap: "round",
		strokeLinejoin: "round",
		strokeWidth: 2,
		d: "M5 13l4 4L19 7"
	}))));
}
function BooleanComponent() {
	const { label, value, onUpdate, disabled, id } = useInputContext();
	return import_react.createElement(Row, { input: true }, import_react.createElement(Label, null, label), import_react.createElement(Boolean$1, {
		value,
		onUpdate,
		id,
		disabled
	}));
}
var boolean = createInternalPlugin(_objectSpread2({ component: BooleanComponent }, props$4));
var _excluded$1$1 = ["locked"];
function Coordinate({ value, id, valueKey, settings, onUpdate, innerLabelTrim }) {
	const valueRef = (0, import_react.useRef)(value[valueKey]);
	valueRef.current = value[valueKey];
	const setValue = (0, import_react.useCallback)((newValue) => onUpdate({ [valueKey]: sanitizeValue({
		type: "NUMBER",
		value: valueRef.current,
		settings
	}, newValue) }), [
		onUpdate,
		settings,
		valueKey
	]);
	const number = useInputSetters({
		type: "NUMBER",
		value: value[valueKey],
		settings,
		setValue
	});
	return import_react.createElement(Number$1, {
		id,
		label: valueKey,
		value: value[valueKey],
		displayValue: number.displayValue,
		onUpdate: number.onUpdate,
		onChange: number.onChange,
		settings,
		innerLabelTrim
	});
}
var Container$2 = styled("div", {
	display: "grid",
	columnGap: "$colGap",
	gridAutoFlow: "column dense",
	alignItems: "center",
	variants: { withLock: { true: {
		gridTemplateColumns: "10px auto",
		"> svg": { cursor: "pointer" }
	} } }
});
function Lock(_ref) {
	let { locked } = _ref, props = _objectWithoutProperties$1(_ref, _excluded$1$1);
	return import_react.createElement("svg", _extends({
		width: "10",
		height: "10",
		viewBox: "0 0 15 15",
		fill: "none",
		xmlns: "http://www.w3.org/2000/svg"
	}, props), locked ? import_react.createElement("path", {
		d: "M5 4.63601C5 3.76031 5.24219 3.1054 5.64323 2.67357C6.03934 2.24705 6.64582 1.9783 7.5014 1.9783C8.35745 1.9783 8.96306 2.24652 9.35823 2.67208C9.75838 3.10299 10 3.75708 10 4.63325V5.99999H5V4.63601ZM4 5.99999V4.63601C4 3.58148 4.29339 2.65754 4.91049 1.99307C5.53252 1.32329 6.42675 0.978302 7.5014 0.978302C8.57583 0.978302 9.46952 1.32233 10.091 1.99162C10.7076 2.65557 11 3.57896 11 4.63325V5.99999H12C12.5523 5.99999 13 6.44771 13 6.99999V13C13 13.5523 12.5523 14 12 14H3C2.44772 14 2 13.5523 2 13V6.99999C2 6.44771 2.44772 5.99999 3 5.99999H4ZM3 6.99999H12V13H3V6.99999Z",
		fill: "currentColor",
		fillRule: "evenodd",
		clipRule: "evenodd"
	}) : import_react.createElement("path", {
		d: "M9 3.63601C9 2.76044 9.24207 2.11211 9.64154 1.68623C10.0366 1.26502 10.6432 1 11.5014 1C12.4485 1 13.0839 1.30552 13.4722 1.80636C13.8031 2.23312 14 2.84313 14 3.63325H15C15 2.68242 14.7626 1.83856 14.2625 1.19361C13.6389 0.38943 12.6743 0 11.5014 0C10.4294 0 9.53523 0.337871 8.91218 1.0021C8.29351 1.66167 8 2.58135 8 3.63601V6H1C0.447715 6 0 6.44772 0 7V13C0 13.5523 0.447715 14 1 14H10C10.5523 14 11 13.5523 11 13V7C11 6.44772 10.5523 6 10 6H9V3.63601ZM1 7H10V13H1V7Z",
		fill: "currentColor",
		fillRule: "evenodd",
		clipRule: "evenodd"
	}));
}
function Vector({ value, onUpdate, settings, innerLabelTrim }) {
	const { id, setSettings } = useInputContext();
	const { lock, locked } = settings;
	return import_react.createElement(Container$2, { withLock: lock }, lock && import_react.createElement(Lock, {
		locked,
		onClick: () => setSettings({ locked: !locked })
	}), Object.keys(value).map((key, i) => import_react.createElement(Coordinate, {
		id: i === 0 ? id : `${id}.${key}`,
		key,
		valueKey: key,
		value,
		settings: settings[key],
		onUpdate,
		innerLabelTrim
	})));
}
var normalizeKeyedNumberSettings = (value, settings) => {
	const _settings = {};
	let maxStep = 0;
	let minPad = Infinity;
	Object.entries(value).forEach(([key, v]) => {
		_settings[key] = normalize$2$1(_objectSpread2({ value: v }, settings[key])).settings;
		maxStep = Math.max(maxStep, _settings[key].step);
		minPad = Math.min(minPad, _settings[key].pad);
	});
	for (let key in _settings) {
		const { step, min, max } = settings[key] || {};
		if (!isFinite(step) && (!isFinite(min) || !isFinite(max))) {
			_settings[key].step = maxStep;
			_settings[key].pad = minPad;
		}
	}
	return _settings;
};
var _excluded$10 = ["lock"], _excluded2$5 = ["value"];
function getVectorSchema(dimension) {
	const isVectorArray = v8n().array().length(dimension).every.number();
	const isVectorObject = (o) => {
		if (!o || typeof o !== "object") return false;
		const values = Object.values(o);
		return values.length === dimension && values.every((v) => isFinite(v));
	};
	return (o) => {
		return isVectorArray.test(o) || isVectorObject(o);
	};
}
function getVectorType(value) {
	return Array.isArray(value) ? "array" : "object";
}
function convert$1(value, format, keys) {
	if (getVectorType(value) === format) return value;
	return format === "array" ? Object.values(value) : mapArrayToKeys(value, keys);
}
var sanitizeVector = (value, settings, previousValue) => {
	const _value = convert$1(value, "object", settings.keys);
	for (let key in _value) _value[key] = sanitize$3(_value[key], settings[key]);
	const _valueKeys = Object.keys(_value);
	let newValue = {};
	if (_valueKeys.length === settings.keys.length) newValue = _value;
	else {
		const _previousValue = convert$1(previousValue, "object", settings.keys);
		if (_valueKeys.length === 1 && settings.locked) {
			const lockedKey = _valueKeys[0];
			const lockedCoordinate = _value[lockedKey];
			const previousLockedCoordinate = _previousValue[lockedKey];
			const ratio = previousLockedCoordinate !== 0 ? lockedCoordinate / previousLockedCoordinate : 1;
			for (let key in _previousValue) if (key === lockedKey) newValue[lockedKey] = lockedCoordinate;
			else newValue[key] = _previousValue[key] * ratio;
		} else newValue = _objectSpread2(_objectSpread2({}, _previousValue), _value);
	}
	return convert$1(newValue, settings.format, settings.keys);
};
var formatVector = (value, settings) => convert$1(value, "object", settings.keys);
var isNumberSettings = (o) => !!o && ("step" in o || "min" in o || "max" in o);
function normalizeVector(value, settings, defaultKeys = []) {
	const { lock = false } = settings, _settings = _objectWithoutProperties$1(settings, _excluded$10);
	const format = Array.isArray(value) ? "array" : "object";
	const keys = format === "object" ? Object.keys(value) : defaultKeys;
	const _value = convert$1(value, "object", keys);
	const numberSettings = normalizeKeyedNumberSettings(_value, isNumberSettings(_settings) ? keys.reduce((acc, k) => Object.assign(acc, { [k]: _settings }), {}) : _settings);
	return {
		value: format === "array" ? value : _value,
		settings: _objectSpread2(_objectSpread2({}, numberSettings), {}, {
			format,
			keys,
			lock,
			locked: false
		})
	};
}
function getVectorPlugin(defaultKeys) {
	return {
		schema: getVectorSchema(defaultKeys.length),
		normalize: (_ref) => {
			let { value } = _ref;
			return normalizeVector(value, _objectWithoutProperties$1(_ref, _excluded2$5), defaultKeys);
		},
		format: (value, settings) => formatVector(value, settings),
		sanitize: (value, settings, prevValue) => sanitizeVector(value, settings, prevValue)
	};
}
//#endregion
//#region ../../node_modules/colord/index.mjs
var r$1 = {
	grad: .9,
	turn: 360,
	rad: 360 / (2 * Math.PI)
}, t$1 = function(r) {
	return "string" == typeof r ? r.length > 0 : "number" == typeof r;
}, n$1 = function(r, t, n) {
	return void 0 === t && (t = 0), void 0 === n && (n = Math.pow(10, t)), Math.round(n * r) / n + 0;
}, e$1 = function(r, t, n) {
	return void 0 === t && (t = 0), void 0 === n && (n = 1), r > n ? n : r > t ? r : t;
}, u$1 = function(r) {
	return (r = isFinite(r) ? r % 360 : 0) > 0 ? r : r + 360;
}, a$1 = function(r) {
	return {
		r: e$1(r.r, 0, 255),
		g: e$1(r.g, 0, 255),
		b: e$1(r.b, 0, 255),
		a: e$1(r.a)
	};
}, o$1 = function(r) {
	return {
		r: n$1(r.r),
		g: n$1(r.g),
		b: n$1(r.b),
		a: n$1(r.a, 3)
	};
}, i$1 = /^#([0-9a-f]{3,8})$/i, s$1 = function(r) {
	var t = r.toString(16);
	return t.length < 2 ? "0" + t : t;
}, h$1 = function(r) {
	var t = r.r, n = r.g, e = r.b, u = r.a, a = Math.max(t, n, e), o = a - Math.min(t, n, e), i = o ? a === t ? (n - e) / o : a === n ? 2 + (e - t) / o : 4 + (t - n) / o : 0;
	return {
		h: 60 * (i < 0 ? i + 6 : i),
		s: a ? o / a * 100 : 0,
		v: a / 255 * 100,
		a: u
	};
}, b$1 = function(r) {
	var t = r.h, n = r.s, e = r.v, u = r.a;
	t = t / 360 * 6, n /= 100, e /= 100;
	var a = Math.floor(t), o = e * (1 - n), i = e * (1 - (t - a) * n), s = e * (1 - (1 - t + a) * n), h = a % 6;
	return {
		r: 255 * [
			e,
			i,
			o,
			o,
			s,
			e
		][h],
		g: 255 * [
			s,
			e,
			e,
			i,
			o,
			o
		][h],
		b: 255 * [
			o,
			o,
			s,
			e,
			e,
			i
		][h],
		a: u
	};
}, g$1 = function(r) {
	return {
		h: u$1(r.h),
		s: e$1(r.s, 0, 100),
		l: e$1(r.l, 0, 100),
		a: e$1(r.a)
	};
}, d$1 = function(r) {
	return {
		h: n$1(r.h),
		s: n$1(r.s),
		l: n$1(r.l),
		a: n$1(r.a, 3)
	};
}, f$1 = function(r) {
	return b$1((n = (t = r).s, {
		h: t.h,
		s: (n *= ((e = t.l) < 50 ? e : 100 - e) / 100) > 0 ? 2 * n / (e + n) * 100 : 0,
		v: e + n,
		a: t.a
	}));
	var t, n, e;
}, c$1 = function(r) {
	return {
		h: (t = h$1(r)).h,
		s: (u = (200 - (n = t.s)) * (e = t.v) / 100) > 0 && u < 200 ? n * e / 100 / (u <= 100 ? u : 200 - u) * 100 : 0,
		l: u / 2,
		a: t.a
	};
	var t, n, e, u;
}, l$1 = /^hsla?\(\s*([+-]?\d*\.?\d+)(deg|rad|grad|turn)?\s*,\s*([+-]?\d*\.?\d+)%\s*,\s*([+-]?\d*\.?\d+)%\s*(?:,\s*([+-]?\d*\.?\d+)(%)?\s*)?\)$/i, p$1 = /^hsla?\(\s*([+-]?\d*\.?\d+)(deg|rad|grad|turn)?\s+([+-]?\d*\.?\d+)%\s+([+-]?\d*\.?\d+)%\s*(?:\/\s*([+-]?\d*\.?\d+)(%)?\s*)?\)$/i, v$1 = /^rgba?\(\s*([+-]?\d*\.?\d+)(%)?\s*,\s*([+-]?\d*\.?\d+)(%)?\s*,\s*([+-]?\d*\.?\d+)(%)?\s*(?:,\s*([+-]?\d*\.?\d+)(%)?\s*)?\)$/i, m$1 = /^rgba?\(\s*([+-]?\d*\.?\d+)(%)?\s+([+-]?\d*\.?\d+)(%)?\s+([+-]?\d*\.?\d+)(%)?\s*(?:\/\s*([+-]?\d*\.?\d+)(%)?\s*)?\)$/i, y$1 = {
	string: [
		[function(r) {
			var t = i$1.exec(r);
			return t ? (r = t[1]).length <= 4 ? {
				r: parseInt(r[0] + r[0], 16),
				g: parseInt(r[1] + r[1], 16),
				b: parseInt(r[2] + r[2], 16),
				a: 4 === r.length ? n$1(parseInt(r[3] + r[3], 16) / 255, 2) : 1
			} : 6 === r.length || 8 === r.length ? {
				r: parseInt(r.substr(0, 2), 16),
				g: parseInt(r.substr(2, 2), 16),
				b: parseInt(r.substr(4, 2), 16),
				a: 8 === r.length ? n$1(parseInt(r.substr(6, 2), 16) / 255, 2) : 1
			} : null : null;
		}, "hex"],
		[function(r) {
			var t = v$1.exec(r) || m$1.exec(r);
			return t ? t[2] !== t[4] || t[4] !== t[6] ? null : a$1({
				r: Number(t[1]) / (t[2] ? 100 / 255 : 1),
				g: Number(t[3]) / (t[4] ? 100 / 255 : 1),
				b: Number(t[5]) / (t[6] ? 100 / 255 : 1),
				a: void 0 === t[7] ? 1 : Number(t[7]) / (t[8] ? 100 : 1)
			}) : null;
		}, "rgb"],
		[function(t) {
			var n = l$1.exec(t) || p$1.exec(t);
			if (!n) return null;
			var e, u;
			return f$1(g$1({
				h: (e = n[1], u = n[2], void 0 === u && (u = "deg"), Number(e) * (r$1[u] || 1)),
				s: Number(n[3]),
				l: Number(n[4]),
				a: void 0 === n[5] ? 1 : Number(n[5]) / (n[6] ? 100 : 1)
			}));
		}, "hsl"]
	],
	object: [
		[function(r) {
			var n = r.r, e = r.g, u = r.b, o = r.a, i = void 0 === o ? 1 : o;
			return t$1(n) && t$1(e) && t$1(u) ? a$1({
				r: Number(n),
				g: Number(e),
				b: Number(u),
				a: Number(i)
			}) : null;
		}, "rgb"],
		[function(r) {
			var n = r.h, e = r.s, u = r.l, a = r.a, o = void 0 === a ? 1 : a;
			if (!t$1(n) || !t$1(e) || !t$1(u)) return null;
			return f$1(g$1({
				h: Number(n),
				s: Number(e),
				l: Number(u),
				a: Number(o)
			}));
		}, "hsl"],
		[function(r) {
			var n = r.h, a = r.s, o = r.v, i = r.a, s = void 0 === i ? 1 : i;
			if (!t$1(n) || !t$1(a) || !t$1(o)) return null;
			return b$1(function(r) {
				return {
					h: u$1(r.h),
					s: e$1(r.s, 0, 100),
					v: e$1(r.v, 0, 100),
					a: e$1(r.a)
				};
			}({
				h: Number(n),
				s: Number(a),
				v: Number(o),
				a: Number(s)
			}));
		}, "hsv"]
	]
}, N$1 = function(r, t) {
	for (var n = 0; n < t.length; n++) {
		var e = t[n][0](r);
		if (e) return [e, t[n][1]];
	}
	return [null, void 0];
}, x$1 = function(r) {
	return "string" == typeof r ? N$1(r.trim(), y$1.string) : "object" == typeof r && null !== r ? N$1(r, y$1.object) : [null, void 0];
}, I$1 = function(r) {
	return x$1(r)[1];
}, M$1 = function(r, t) {
	var n = c$1(r);
	return {
		h: n.h,
		s: e$1(n.s + 100 * t, 0, 100),
		l: n.l,
		a: n.a
	};
}, H$1 = function(r) {
	return (299 * r.r + 587 * r.g + 114 * r.b) / 1e3 / 255;
}, $$1 = function(r, t) {
	var n = c$1(r);
	return {
		h: n.h,
		s: n.s,
		l: e$1(n.l + 100 * t, 0, 100),
		a: n.a
	};
}, j$1 = function() {
	function r(r) {
		this.parsed = x$1(r)[0], this.rgba = this.parsed || {
			r: 0,
			g: 0,
			b: 0,
			a: 1
		};
	}
	return r.prototype.isValid = function() {
		return null !== this.parsed;
	}, r.prototype.brightness = function() {
		return n$1(H$1(this.rgba), 2);
	}, r.prototype.isDark = function() {
		return H$1(this.rgba) < .5;
	}, r.prototype.isLight = function() {
		return H$1(this.rgba) >= .5;
	}, r.prototype.toHex = function() {
		return r = o$1(this.rgba), t = r.r, e = r.g, u = r.b, i = (a = r.a) < 1 ? s$1(n$1(255 * a)) : "", "#" + s$1(t) + s$1(e) + s$1(u) + i;
		var r, t, e, u, a, i;
	}, r.prototype.toRgb = function() {
		return o$1(this.rgba);
	}, r.prototype.toRgbString = function() {
		return r = o$1(this.rgba), t = r.r, n = r.g, e = r.b, (u = r.a) < 1 ? "rgba(" + t + ", " + n + ", " + e + ", " + u + ")" : "rgb(" + t + ", " + n + ", " + e + ")";
		var r, t, n, e, u;
	}, r.prototype.toHsl = function() {
		return d$1(c$1(this.rgba));
	}, r.prototype.toHslString = function() {
		return r = d$1(c$1(this.rgba)), t = r.h, n = r.s, e = r.l, (u = r.a) < 1 ? "hsla(" + t + ", " + n + "%, " + e + "%, " + u + ")" : "hsl(" + t + ", " + n + "%, " + e + "%)";
		var r, t, n, e, u;
	}, r.prototype.toHsv = function() {
		return r = h$1(this.rgba), {
			h: n$1(r.h),
			s: n$1(r.s),
			v: n$1(r.v),
			a: n$1(r.a, 3)
		};
		var r;
	}, r.prototype.invert = function() {
		return w$1({
			r: 255 - (r = this.rgba).r,
			g: 255 - r.g,
			b: 255 - r.b,
			a: r.a
		});
		var r;
	}, r.prototype.saturate = function(r) {
		return void 0 === r && (r = .1), w$1(M$1(this.rgba, r));
	}, r.prototype.desaturate = function(r) {
		return void 0 === r && (r = .1), w$1(M$1(this.rgba, -r));
	}, r.prototype.grayscale = function() {
		return w$1(M$1(this.rgba, -1));
	}, r.prototype.lighten = function(r) {
		return void 0 === r && (r = .1), w$1($$1(this.rgba, r));
	}, r.prototype.darken = function(r) {
		return void 0 === r && (r = .1), w$1($$1(this.rgba, -r));
	}, r.prototype.rotate = function(r) {
		return void 0 === r && (r = 15), this.hue(this.hue() + r);
	}, r.prototype.alpha = function(r) {
		return "number" == typeof r ? w$1({
			r: (t = this.rgba).r,
			g: t.g,
			b: t.b,
			a: r
		}) : n$1(this.rgba.a, 3);
		var t;
	}, r.prototype.hue = function(r) {
		var t = c$1(this.rgba);
		return "number" == typeof r ? w$1({
			h: r,
			s: t.s,
			l: t.l,
			a: t.a
		}) : n$1(t.h);
	}, r.prototype.isEqual = function(r) {
		return this.toHex() === w$1(r).toHex();
	}, r;
}(), w$1 = function(r) {
	return r instanceof j$1 ? r : new j$1(r);
}, S$1 = [], k$1 = function(r) {
	r.forEach(function(r) {
		S$1.indexOf(r) < 0 && (r(j$1, y$1), S$1.push(r));
	});
};
//#endregion
//#region ../../node_modules/colord/plugins/names.mjs
function names_default(e, f) {
	var a = {
		white: "#ffffff",
		bisque: "#ffe4c4",
		blue: "#0000ff",
		cadetblue: "#5f9ea0",
		chartreuse: "#7fff00",
		chocolate: "#d2691e",
		coral: "#ff7f50",
		antiquewhite: "#faebd7",
		aqua: "#00ffff",
		azure: "#f0ffff",
		whitesmoke: "#f5f5f5",
		papayawhip: "#ffefd5",
		plum: "#dda0dd",
		blanchedalmond: "#ffebcd",
		black: "#000000",
		gold: "#ffd700",
		goldenrod: "#daa520",
		gainsboro: "#dcdcdc",
		cornsilk: "#fff8dc",
		cornflowerblue: "#6495ed",
		burlywood: "#deb887",
		aquamarine: "#7fffd4",
		beige: "#f5f5dc",
		crimson: "#dc143c",
		cyan: "#00ffff",
		darkblue: "#00008b",
		darkcyan: "#008b8b",
		darkgoldenrod: "#b8860b",
		darkkhaki: "#bdb76b",
		darkgray: "#a9a9a9",
		darkgreen: "#006400",
		darkgrey: "#a9a9a9",
		peachpuff: "#ffdab9",
		darkmagenta: "#8b008b",
		darkred: "#8b0000",
		darkorchid: "#9932cc",
		darkorange: "#ff8c00",
		darkslateblue: "#483d8b",
		gray: "#808080",
		darkslategray: "#2f4f4f",
		darkslategrey: "#2f4f4f",
		deeppink: "#ff1493",
		deepskyblue: "#00bfff",
		wheat: "#f5deb3",
		firebrick: "#b22222",
		floralwhite: "#fffaf0",
		ghostwhite: "#f8f8ff",
		darkviolet: "#9400d3",
		magenta: "#ff00ff",
		green: "#008000",
		dodgerblue: "#1e90ff",
		grey: "#808080",
		honeydew: "#f0fff0",
		hotpink: "#ff69b4",
		blueviolet: "#8a2be2",
		forestgreen: "#228b22",
		lawngreen: "#7cfc00",
		indianred: "#cd5c5c",
		indigo: "#4b0082",
		fuchsia: "#ff00ff",
		brown: "#a52a2a",
		maroon: "#800000",
		mediumblue: "#0000cd",
		lightcoral: "#f08080",
		darkturquoise: "#00ced1",
		lightcyan: "#e0ffff",
		ivory: "#fffff0",
		lightyellow: "#ffffe0",
		lightsalmon: "#ffa07a",
		lightseagreen: "#20b2aa",
		linen: "#faf0e6",
		mediumaquamarine: "#66cdaa",
		lemonchiffon: "#fffacd",
		lime: "#00ff00",
		khaki: "#f0e68c",
		mediumseagreen: "#3cb371",
		limegreen: "#32cd32",
		mediumspringgreen: "#00fa9a",
		lightskyblue: "#87cefa",
		lightblue: "#add8e6",
		midnightblue: "#191970",
		lightpink: "#ffb6c1",
		mistyrose: "#ffe4e1",
		moccasin: "#ffe4b5",
		mintcream: "#f5fffa",
		lightslategray: "#778899",
		lightslategrey: "#778899",
		navajowhite: "#ffdead",
		navy: "#000080",
		mediumvioletred: "#c71585",
		powderblue: "#b0e0e6",
		palegoldenrod: "#eee8aa",
		oldlace: "#fdf5e6",
		paleturquoise: "#afeeee",
		mediumturquoise: "#48d1cc",
		mediumorchid: "#ba55d3",
		rebeccapurple: "#663399",
		lightsteelblue: "#b0c4de",
		mediumslateblue: "#7b68ee",
		thistle: "#d8bfd8",
		tan: "#d2b48c",
		orchid: "#da70d6",
		mediumpurple: "#9370db",
		purple: "#800080",
		pink: "#ffc0cb",
		skyblue: "#87ceeb",
		springgreen: "#00ff7f",
		palegreen: "#98fb98",
		red: "#ff0000",
		yellow: "#ffff00",
		slateblue: "#6a5acd",
		lavenderblush: "#fff0f5",
		peru: "#cd853f",
		palevioletred: "#db7093",
		violet: "#ee82ee",
		teal: "#008080",
		slategray: "#708090",
		slategrey: "#708090",
		aliceblue: "#f0f8ff",
		darkseagreen: "#8fbc8f",
		darkolivegreen: "#556b2f",
		greenyellow: "#adff2f",
		seagreen: "#2e8b57",
		seashell: "#fff5ee",
		tomato: "#ff6347",
		silver: "#c0c0c0",
		sienna: "#a0522d",
		lavender: "#e6e6fa",
		lightgreen: "#90ee90",
		orange: "#ffa500",
		orangered: "#ff4500",
		steelblue: "#4682b4",
		royalblue: "#4169e1",
		turquoise: "#40e0d0",
		yellowgreen: "#9acd32",
		salmon: "#fa8072",
		saddlebrown: "#8b4513",
		sandybrown: "#f4a460",
		rosybrown: "#bc8f8f",
		darksalmon: "#e9967a",
		lightgoldenrodyellow: "#fafad2",
		snow: "#fffafa",
		lightgrey: "#d3d3d3",
		lightgray: "#d3d3d3",
		dimgray: "#696969",
		dimgrey: "#696969",
		olivedrab: "#6b8e23",
		olive: "#808000"
	}, r = {};
	for (var d in a) r[a[d]] = d;
	var l = {};
	e.prototype.toName = function(f) {
		if (!(this.rgba.a || this.rgba.r || this.rgba.g || this.rgba.b)) return "transparent";
		var d, i, n = r[this.toHex()];
		if (n) return n;
		if (null == f ? void 0 : f.closest) {
			var o = this.toRgb(), t = Infinity, b = "black";
			if (!l.length) for (var c in a) l[c] = new e(a[c]).toRgb();
			for (var g in a) {
				var u = (d = o, i = l[g], Math.pow(d.r - i.r, 2) + Math.pow(d.g - i.g, 2) + Math.pow(d.b - i.b, 2));
				u < t && (t = u, b = g);
			}
			return b;
		}
	};
	f.string.push([function(f) {
		var r = f.toLowerCase(), d = "transparent" === r ? "#0000" : a[r];
		return d ? new e(d).toRgb() : null;
	}, "name"]);
}
//#endregion
//#region ../../node_modules/react-colorful/dist/index.mjs
function u() {
	return (u = Object.assign || function(e) {
		for (var r = 1; r < arguments.length; r++) {
			var t = arguments[r];
			for (var n in t) Object.prototype.hasOwnProperty.call(t, n) && (e[n] = t[n]);
		}
		return e;
	}).apply(this, arguments);
}
function c(e, r) {
	if (null == e) return {};
	var t, n, o = {}, a = Object.keys(e);
	for (n = 0; n < a.length; n++) r.indexOf(t = a[n]) >= 0 || (o[t] = e[t]);
	return o;
}
function i(e) {
	var t = (0, import_react.useRef)(e), n = (0, import_react.useRef)(function(e) {
		t.current && t.current(e);
	});
	return t.current = e, n.current;
}
var s = function(e, r, t) {
	return void 0 === r && (r = 0), void 0 === t && (t = 1), e > t ? t : e < r ? r : e;
}, f = function(e) {
	return "touches" in e;
}, v = function(e) {
	return e && e.ownerDocument.defaultView || self;
}, d = function(e, r, t) {
	var n = e.getBoundingClientRect(), o = f(r) ? function(e, r) {
		for (var t = 0; t < e.length; t++) if (e[t].identifier === r) return e[t];
		return e[0];
	}(r.touches, t) : r;
	return {
		left: s((o.pageX - (n.left + v(e).pageXOffset)) / n.width),
		top: s((o.pageY - (n.top + v(e).pageYOffset)) / n.height)
	};
}, h = function(e) {
	!f(e) && e.preventDefault();
}, m = import_react.memo(function(o) {
	var a = o.onMove, l = o.onKey, s = c(o, ["onMove", "onKey"]), m = (0, import_react.useRef)(null), g = i(a), p = i(l), b = (0, import_react.useRef)(null), _ = (0, import_react.useRef)(!1), x = (0, import_react.useMemo)(function() {
		var e = function(e) {
			h(e), (f(e) ? e.touches.length > 0 : e.buttons > 0) && m.current ? g(d(m.current, e, b.current)) : t(!1);
		}, r = function() {
			return t(!1);
		};
		function t(t) {
			var n = _.current, o = v(m.current), a = t ? o.addEventListener : o.removeEventListener;
			a(n ? "touchmove" : "mousemove", e), a(n ? "touchend" : "mouseup", r);
		}
		return [
			function(e) {
				var r = e.nativeEvent, n = m.current;
				if (n && (h(r), !function(e, r) {
					return r && !f(e);
				}(r, _.current) && n)) {
					if (f(r)) {
						_.current = !0;
						var o = r.changedTouches || [];
						o.length && (b.current = o[0].identifier);
					}
					n.focus(), g(d(n, r, b.current)), t(!0);
				}
			},
			function(e) {
				var r = e.which || e.keyCode;
				r < 37 || r > 40 || (e.preventDefault(), p({
					left: 39 === r ? .05 : 37 === r ? -.05 : 0,
					top: 40 === r ? .05 : 38 === r ? -.05 : 0
				}));
			},
			t
		];
	}, [p, g]), C = x[0], E = x[1], H = x[2];
	return (0, import_react.useEffect)(function() {
		return H;
	}, [H]), import_react.createElement("div", u({}, s, {
		onTouchStart: C,
		onMouseDown: C,
		className: "react-colorful__interactive",
		ref: m,
		onKeyDown: E,
		tabIndex: 0,
		role: "slider"
	}));
}), g = function(e) {
	return e.filter(Boolean).join(" ");
}, p = function(r) {
	var t = r.color, n = r.left, o = r.top, a = void 0 === o ? .5 : o, l = g(["react-colorful__pointer", r.className]);
	return import_react.createElement("div", {
		className: l,
		style: {
			top: 100 * a + "%",
			left: 100 * n + "%"
		}
	}, import_react.createElement("div", {
		className: "react-colorful__pointer-fill",
		style: { backgroundColor: t }
	}));
}, b = function(e, r, t) {
	return void 0 === r && (r = 0), void 0 === t && (t = Math.pow(10, r)), Math.round(t * e) / t;
};
360 / (2 * Math.PI);
var y = function(e) {
	var r = e.s, t = e.v, n = e.a, o = (200 - r) * t / 100;
	return {
		h: b(e.h),
		s: b(o > 0 && o < 200 ? r * t / 100 / (o <= 100 ? o : 200 - o) * 100 : 0),
		l: b(o / 2),
		a: b(n, 2)
	};
}, q = function(e) {
	var r = y(e);
	return "hsl(" + r.h + ", " + r.s + "%, " + r.l + "%)";
}, k = function(e) {
	var r = y(e);
	return "hsla(" + r.h + ", " + r.s + "%, " + r.l + "%, " + r.a + ")";
}, I = function(e) {
	var r = e.h, t = e.s, n = e.v, o = e.a;
	r = r / 360 * 6, t /= 100, n /= 100;
	var a = Math.floor(r), l = n * (1 - t), u = n * (1 - (r - a) * t), c = n * (1 - (1 - r + a) * t), i = a % 6;
	return {
		r: b(255 * [
			n,
			u,
			l,
			l,
			c,
			n
		][i]),
		g: b(255 * [
			c,
			n,
			n,
			u,
			l,
			l
		][i]),
		b: b(255 * [
			l,
			l,
			c,
			n,
			n,
			u
		][i]),
		a: b(o, 2)
	};
}, L = function(e) {
	var r = e.r, t = e.g, n = e.b, o = e.a, a = Math.max(r, t, n), l = a - Math.min(r, t, n), u = l ? a === r ? (t - n) / l : a === t ? 2 + (n - r) / l : 4 + (r - t) / l : 0;
	return {
		h: b(60 * (u < 0 ? u + 6 : u)),
		s: b(a ? l / a * 100 : 0),
		v: b(a / 255 * 100),
		a: o
	};
}, S = import_react.memo(function(r) {
	var t = r.hue, n = r.onChange, o = g(["react-colorful__hue", r.className]);
	return import_react.createElement("div", { className: o }, import_react.createElement(m, {
		onMove: function(e) {
			n({ h: 360 * e.left });
		},
		onKey: function(e) {
			n({ h: s(t + 360 * e.left, 0, 360) });
		},
		"aria-label": "Hue",
		"aria-valuenow": b(t),
		"aria-valuemax": "360",
		"aria-valuemin": "0"
	}, import_react.createElement(p, {
		className: "react-colorful__hue-pointer",
		left: t / 360,
		color: q({
			h: t,
			s: 100,
			v: 100,
			a: 1
		})
	})));
}), T = import_react.memo(function(r) {
	var t = r.hsva, n = r.onChange, o = { backgroundColor: q({
		h: t.h,
		s: 100,
		v: 100,
		a: 1
	}) };
	return import_react.createElement("div", {
		className: "react-colorful__saturation",
		style: o
	}, import_react.createElement(m, {
		onMove: function(e) {
			n({
				s: 100 * e.left,
				v: 100 - 100 * e.top
			});
		},
		onKey: function(e) {
			n({
				s: s(t.s + 100 * e.left, 0, 100),
				v: s(t.v - 100 * e.top, 0, 100)
			});
		},
		"aria-label": "Color",
		"aria-valuetext": "Saturation " + b(t.s) + "%, Brightness " + b(t.v) + "%"
	}, import_react.createElement(p, {
		className: "react-colorful__saturation-pointer",
		top: 1 - t.v / 100,
		left: t.s / 100,
		color: q(t)
	})));
}), F = function(e, r) {
	if (e === r) return !0;
	for (var t in e) if (e[t] !== r[t]) return !1;
	return !0;
};
function Y(e, t, l) {
	var u = i(l), c = (0, import_react.useState)(function() {
		return e.toHsva(t);
	}), s = c[0], f = c[1], v = (0, import_react.useRef)({
		color: t,
		hsva: s
	});
	(0, import_react.useEffect)(function() {
		if (!e.equal(t, v.current.color)) {
			var r = e.toHsva(t);
			v.current = {
				hsva: r,
				color: t
			}, f(r);
		}
	}, [t, e]), (0, import_react.useEffect)(function() {
		var r;
		F(s, v.current.hsva) || e.equal(r = e.fromHsva(s), v.current.color) || (v.current = {
			hsva: s,
			color: r
		}, u(r));
	}, [
		s,
		e,
		u
	]);
	return [s, (0, import_react.useCallback)(function(e) {
		f(function(r) {
			return Object.assign({}, r, e);
		});
	}, [])];
}
var R, V = "undefined" != typeof window ? import_react.useLayoutEffect : import_react.useEffect, $ = function() {
	return R || ("undefined" != typeof __webpack_nonce__ ? __webpack_nonce__ : void 0);
}, J = /* @__PURE__ */ new Map(), Q = function(e) {
	V(function() {
		var r = e.current ? e.current.ownerDocument : document;
		if (void 0 !== r && !J.has(r)) {
			var t = r.createElement("style");
			t.innerHTML = ".react-colorful{position:relative;display:flex;flex-direction:column;width:200px;height:200px;-webkit-user-select:none;-moz-user-select:none;-ms-user-select:none;user-select:none;cursor:default}.react-colorful__saturation{position:relative;flex-grow:1;border-color:transparent;border-bottom:12px solid #000;border-radius:8px 8px 0 0;background-image:linear-gradient(0deg,#000,transparent),linear-gradient(90deg,#fff,hsla(0,0%,100%,0))}.react-colorful__alpha-gradient,.react-colorful__pointer-fill{content:\"\";position:absolute;left:0;top:0;right:0;bottom:0;pointer-events:none;border-radius:inherit}.react-colorful__alpha-gradient,.react-colorful__saturation{box-shadow:inset 0 0 0 1px rgba(0,0,0,.05)}.react-colorful__alpha,.react-colorful__hue{position:relative;height:24px}.react-colorful__hue{background:linear-gradient(90deg,red 0,#ff0 17%,#0f0 33%,#0ff 50%,#00f 67%,#f0f 83%,red)}.react-colorful__last-control{border-radius:0 0 8px 8px}.react-colorful__interactive{position:absolute;left:0;top:0;right:0;bottom:0;border-radius:inherit;outline:none;touch-action:none}.react-colorful__pointer{position:absolute;z-index:1;box-sizing:border-box;width:28px;height:28px;transform:translate(-50%,-50%);background-color:#fff;border:2px solid #fff;border-radius:50%;box-shadow:0 2px 4px rgba(0,0,0,.2)}.react-colorful__interactive:focus .react-colorful__pointer{transform:translate(-50%,-50%) scale(1.1)}.react-colorful__alpha,.react-colorful__alpha-pointer{background-color:#fff;background-image:url('data:image/svg+xml;charset=utf-8,<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"16\" height=\"16\" fill-opacity=\".05\"><path d=\"M8 0h8v8H8zM0 8h8v8H0z\"/></svg>')}.react-colorful__saturation-pointer{z-index:3}.react-colorful__hue-pointer{z-index:2}", J.set(r, t);
			var n = $();
			n && t.setAttribute("nonce", n), r.head.appendChild(t);
		}
	}, []);
}, U = function(t) {
	var n = t.className, o = t.colorModel, a = t.color, l = void 0 === a ? o.defaultColor : a, i = t.onChange, s = c(t, [
		"className",
		"colorModel",
		"color",
		"onChange"
	]), f = (0, import_react.useRef)(null);
	Q(f);
	var v = Y(o, l, i), d = v[0], h = v[1], m = g(["react-colorful", n]);
	return import_react.createElement("div", u({}, s, {
		ref: f,
		className: m
	}), import_react.createElement(T, {
		hsva: d,
		onChange: h
	}), import_react.createElement(S, {
		hue: d.h,
		onChange: h,
		className: "react-colorful__last-control"
	}));
}, ee = function(r) {
	var t = r.className, n = r.hsva, o = r.onChange, a = { backgroundImage: "linear-gradient(90deg, " + k(Object.assign({}, n, { a: 0 })) + ", " + k(Object.assign({}, n, { a: 1 })) + ")" }, l = g(["react-colorful__alpha", t]), u = b(100 * n.a);
	return import_react.createElement("div", { className: l }, import_react.createElement("div", {
		className: "react-colorful__alpha-gradient",
		style: a
	}), import_react.createElement(m, {
		onMove: function(e) {
			o({ a: e.left });
		},
		onKey: function(e) {
			o({ a: s(n.a + e.left) });
		},
		"aria-label": "Alpha",
		"aria-valuetext": u + "%",
		"aria-valuenow": u,
		"aria-valuemin": "0",
		"aria-valuemax": "100"
	}, import_react.createElement(p, {
		className: "react-colorful__alpha-pointer",
		left: n.a,
		color: k(n)
	})));
}, re = function(t) {
	var n = t.className, o = t.colorModel, a = t.color, l = void 0 === a ? o.defaultColor : a, i = t.onChange, s = c(t, [
		"className",
		"colorModel",
		"color",
		"onChange"
	]), f = (0, import_react.useRef)(null);
	Q(f);
	var v = Y(o, l, i), d = v[0], h = v[1], m = g(["react-colorful", n]);
	return import_react.createElement("div", u({}, s, {
		ref: f,
		className: m
	}), import_react.createElement(T, {
		hsva: d,
		onChange: h
	}), import_react.createElement(S, {
		hue: d.h,
		onChange: h
	}), import_react.createElement(ee, {
		hsva: d,
		onChange: h,
		className: "react-colorful__last-control"
	}));
}, xe = {
	defaultColor: {
		r: 0,
		g: 0,
		b: 0,
		a: 1
	},
	toHsva: L,
	fromHsva: I,
	equal: F
}, Ce = function(r) {
	return import_react.createElement(re, u({}, r, { colorModel: xe }));
}, Me = {
	defaultColor: {
		r: 0,
		g: 0,
		b: 0
	},
	toHsva: function(e) {
		return L({
			r: e.r,
			g: e.g,
			b: e.b,
			a: 1
		});
	},
	fromHsva: function(e) {
		return {
			r: (r = I(e)).r,
			g: r.g,
			b: r.b
		};
		var r;
	},
	equal: F
}, Ne = function(r) {
	return import_react.createElement(U, u({}, r, { colorModel: Me }));
};
//#endregion
//#region ../../node_modules/prop-types/lib/ReactPropTypesSecret.js
/**
* Copyright (c) 2013-present, Facebook, Inc.
*
* This source code is licensed under the MIT license found in the
* LICENSE file in the root directory of this source tree.
*/
var require_ReactPropTypesSecret = /* @__PURE__ */ __commonJSMin(((exports, module) => {
	module.exports = "SECRET_DO_NOT_PASS_THIS_OR_YOU_WILL_BE_FIRED";
}));
//#endregion
//#region ../../node_modules/prop-types/factoryWithThrowingShims.js
/**
* Copyright (c) 2013-present, Facebook, Inc.
*
* This source code is licensed under the MIT license found in the
* LICENSE file in the root directory of this source tree.
*/
var require_factoryWithThrowingShims = /* @__PURE__ */ __commonJSMin(((exports, module) => {
	var ReactPropTypesSecret = require_ReactPropTypesSecret();
	function emptyFunction() {}
	function emptyFunctionWithReset() {}
	emptyFunctionWithReset.resetWarningCache = emptyFunction;
	module.exports = function() {
		function shim(props, propName, componentName, location, propFullName, secret) {
			if (secret === ReactPropTypesSecret) return;
			var err = /* @__PURE__ */ new Error("Calling PropTypes validators directly is not supported by the `prop-types` package. Use PropTypes.checkPropTypes() to call them. Read more at http://fb.me/use-check-prop-types");
			err.name = "Invariant Violation";
			throw err;
		}
		shim.isRequired = shim;
		function getShim() {
			return shim;
		}
		var ReactPropTypes = {
			array: shim,
			bigint: shim,
			bool: shim,
			func: shim,
			number: shim,
			object: shim,
			string: shim,
			symbol: shim,
			any: shim,
			arrayOf: getShim,
			element: shim,
			elementType: shim,
			instanceOf: getShim,
			node: shim,
			objectOf: getShim,
			oneOf: getShim,
			oneOfType: getShim,
			shape: getShim,
			exact: getShim,
			checkPropTypes: emptyFunctionWithReset,
			resetWarningCache: emptyFunction
		};
		ReactPropTypes.PropTypes = ReactPropTypes;
		return ReactPropTypes;
	};
}));
//#endregion
//#region ../../node_modules/prop-types/index.js
var require_prop_types = /* @__PURE__ */ __commonJSMin(((exports, module) => {
	module.exports = require_factoryWithThrowingShims()();
}));
//#endregion
//#region ../../node_modules/file-selector/dist/es5/file.js
var COMMON_MIME_TYPES = new Map([
	["aac", "audio/aac"],
	["abw", "application/x-abiword"],
	["arc", "application/x-freearc"],
	["avif", "image/avif"],
	["avi", "video/x-msvideo"],
	["azw", "application/vnd.amazon.ebook"],
	["bin", "application/octet-stream"],
	["bmp", "image/bmp"],
	["bz", "application/x-bzip"],
	["bz2", "application/x-bzip2"],
	["cda", "application/x-cdf"],
	["csh", "application/x-csh"],
	["css", "text/css"],
	["csv", "text/csv"],
	["doc", "application/msword"],
	["docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
	["eot", "application/vnd.ms-fontobject"],
	["epub", "application/epub+zip"],
	["gz", "application/gzip"],
	["gif", "image/gif"],
	["heic", "image/heic"],
	["heif", "image/heif"],
	["htm", "text/html"],
	["html", "text/html"],
	["ico", "image/vnd.microsoft.icon"],
	["ics", "text/calendar"],
	["jar", "application/java-archive"],
	["jpeg", "image/jpeg"],
	["jpg", "image/jpeg"],
	["js", "text/javascript"],
	["json", "application/json"],
	["jsonld", "application/ld+json"],
	["mid", "audio/midi"],
	["midi", "audio/midi"],
	["mjs", "text/javascript"],
	["mp3", "audio/mpeg"],
	["mp4", "video/mp4"],
	["mpeg", "video/mpeg"],
	["mpkg", "application/vnd.apple.installer+xml"],
	["odp", "application/vnd.oasis.opendocument.presentation"],
	["ods", "application/vnd.oasis.opendocument.spreadsheet"],
	["odt", "application/vnd.oasis.opendocument.text"],
	["oga", "audio/ogg"],
	["ogv", "video/ogg"],
	["ogx", "application/ogg"],
	["opus", "audio/opus"],
	["otf", "font/otf"],
	["png", "image/png"],
	["pdf", "application/pdf"],
	["php", "application/x-httpd-php"],
	["ppt", "application/vnd.ms-powerpoint"],
	["pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"],
	["rar", "application/vnd.rar"],
	["rtf", "application/rtf"],
	["sh", "application/x-sh"],
	["svg", "image/svg+xml"],
	["swf", "application/x-shockwave-flash"],
	["tar", "application/x-tar"],
	["tif", "image/tiff"],
	["tiff", "image/tiff"],
	["ts", "video/mp2t"],
	["ttf", "font/ttf"],
	["txt", "text/plain"],
	["vsd", "application/vnd.visio"],
	["wav", "audio/wav"],
	["weba", "audio/webm"],
	["webm", "video/webm"],
	["webp", "image/webp"],
	["woff", "font/woff"],
	["woff2", "font/woff2"],
	["xhtml", "application/xhtml+xml"],
	["xls", "application/vnd.ms-excel"],
	["xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
	["xml", "application/xml"],
	["xul", "application/vnd.mozilla.xul+xml"],
	["zip", "application/zip"],
	["7z", "application/x-7z-compressed"],
	["mkv", "video/x-matroska"],
	["mov", "video/quicktime"],
	["msg", "application/vnd.ms-outlook"]
]);
function toFileWithPath(file, path) {
	var f = withMimeType(file);
	if (typeof f.path !== "string") {
		var webkitRelativePath = file.webkitRelativePath;
		Object.defineProperty(f, "path", {
			value: typeof path === "string" ? path : typeof webkitRelativePath === "string" && webkitRelativePath.length > 0 ? webkitRelativePath : file.name,
			writable: false,
			configurable: false,
			enumerable: true
		});
	}
	return f;
}
function withMimeType(file) {
	var name = file.name;
	if (name && name.lastIndexOf(".") !== -1 && !file.type) {
		var ext = name.split(".").pop().toLowerCase();
		var type = COMMON_MIME_TYPES.get(ext);
		if (type) Object.defineProperty(file, "type", {
			value: type,
			writable: false,
			configurable: false,
			enumerable: true
		});
	}
	return file;
}
//#endregion
//#region ../../node_modules/file-selector/dist/es5/file-selector.js
var FILES_TO_IGNORE = [".DS_Store", "Thumbs.db"];
/**
* Convert a DragEvent's DataTrasfer object to a list of File objects
* NOTE: If some of the items are folders,
* everything will be flattened and placed in the same list but the paths will be kept as a {path} property.
*
* EXPERIMENTAL: A list of https://developer.mozilla.org/en-US/docs/Web/API/FileSystemHandle objects can also be passed as an arg
* and a list of File objects will be returned.
*
* @param evt
*/
function fromEvent(evt) {
	return __awaiter(this, void 0, void 0, function() {
		return __generator(this, function(_a) {
			if (isObject(evt) && isDataTransfer(evt)) return [2, getDataTransferFiles(evt.dataTransfer, evt.type)];
			else if (isChangeEvt(evt)) return [2, getInputFiles(evt)];
			else if (Array.isArray(evt) && evt.every(function(item) {
				return "getFile" in item && typeof item.getFile === "function";
			})) return [2, getFsHandleFiles(evt)];
			return [2, []];
		});
	});
}
function isDataTransfer(value) {
	return isObject(value.dataTransfer);
}
function isChangeEvt(value) {
	return isObject(value) && isObject(value.target);
}
function isObject(v) {
	return typeof v === "object" && v !== null;
}
function getInputFiles(evt) {
	return fromList(evt.target.files).map(function(file) {
		return toFileWithPath(file);
	});
}
function getFsHandleFiles(handles) {
	return __awaiter(this, void 0, void 0, function() {
		var files;
		return __generator(this, function(_a) {
			switch (_a.label) {
				case 0: return [4, Promise.all(handles.map(function(h) {
					return h.getFile();
				}))];
				case 1:
					files = _a.sent();
					return [2, files.map(function(file) {
						return toFileWithPath(file);
					})];
			}
		});
	});
}
function getDataTransferFiles(dt, type) {
	return __awaiter(this, void 0, void 0, function() {
		var items, files;
		return __generator(this, function(_a) {
			switch (_a.label) {
				case 0:
					if (dt === null) return [2, []];
					if (!dt.items) return [3, 2];
					items = fromList(dt.items).filter(function(item) {
						return item.kind === "file";
					});
					if (type !== "drop") return [2, items];
					return [4, Promise.all(items.map(toFilePromises))];
				case 1:
					files = _a.sent();
					return [2, noIgnoredFiles(flatten(files))];
				case 2: return [2, noIgnoredFiles(fromList(dt.files).map(function(file) {
					return toFileWithPath(file);
				}))];
			}
		});
	});
}
function noIgnoredFiles(files) {
	return files.filter(function(file) {
		return FILES_TO_IGNORE.indexOf(file.name) === -1;
	});
}
function fromList(items) {
	if (items === null) return [];
	var files = [];
	for (var i = 0; i < items.length; i++) {
		var file = items[i];
		files.push(file);
	}
	return files;
}
function toFilePromises(item) {
	if (typeof item.webkitGetAsEntry !== "function") return fromDataTransferItem(item);
	var entry = item.webkitGetAsEntry();
	if (entry && entry.isDirectory) return fromDirEntry(entry);
	return fromDataTransferItem(item);
}
function flatten(items) {
	return items.reduce(function(acc, files) {
		return __spread(acc, Array.isArray(files) ? flatten(files) : [files]);
	}, []);
}
function fromDataTransferItem(item) {
	var file = item.getAsFile();
	if (!file) return Promise.reject(item + " is not a File");
	var fwp = toFileWithPath(file);
	return Promise.resolve(fwp);
}
function fromEntry(entry) {
	return __awaiter(this, void 0, void 0, function() {
		return __generator(this, function(_a) {
			return [2, entry.isDirectory ? fromDirEntry(entry) : fromFileEntry(entry)];
		});
	});
}
function fromDirEntry(entry) {
	var reader = entry.createReader();
	return new Promise(function(resolve, reject) {
		var entries = [];
		function readEntries() {
			var _this = this;
			reader.readEntries(function(batch) {
				return __awaiter(_this, void 0, void 0, function() {
					var files, err_1, items;
					return __generator(this, function(_a) {
						switch (_a.label) {
							case 0:
								if (!!batch.length) return [3, 5];
								_a.label = 1;
							case 1:
								_a.trys.push([
									1,
									3,
									,
									4
								]);
								return [4, Promise.all(entries)];
							case 2:
								files = _a.sent();
								resolve(files);
								return [3, 4];
							case 3:
								err_1 = _a.sent();
								reject(err_1);
								return [3, 4];
							case 4: return [3, 6];
							case 5:
								items = Promise.all(batch.map(fromEntry));
								entries.push(items);
								readEntries();
								_a.label = 6;
							case 6: return [2];
						}
					});
				});
			}, function(err) {
				reject(err);
			});
		}
		readEntries();
	});
}
function fromFileEntry(entry) {
	return __awaiter(this, void 0, void 0, function() {
		return __generator(this, function(_a) {
			return [2, new Promise(function(resolve, reject) {
				entry.file(function(file) {
					resolve(toFileWithPath(file, entry.fullPath));
				}, function(err) {
					reject(err);
				});
			})];
		});
	});
}
//#endregion
//#region ../../node_modules/attr-accept/dist/es/index.js
var require_es = /* @__PURE__ */ __commonJSMin(((exports) => {
	exports.__esModule = true;
	exports.default = function(file, acceptedFiles) {
		if (file && acceptedFiles) {
			var acceptedFilesArray = Array.isArray(acceptedFiles) ? acceptedFiles : acceptedFiles.split(",");
			if (acceptedFilesArray.length === 0) return true;
			var fileName = file.name || "";
			var mimeType = (file.type || "").toLowerCase();
			var baseMimeType = mimeType.replace(/\/.*$/, "");
			return acceptedFilesArray.some(function(type) {
				var validType = type.trim().toLowerCase();
				if (validType.charAt(0) === ".") return fileName.toLowerCase().endsWith(validType);
				else if (validType.endsWith("/*")) return baseMimeType === validType.replace(/\/.*$/, "");
				return mimeType === validType;
			});
		}
		return true;
	};
}));
//#endregion
//#region ../../node_modules/react-dropzone/dist/es/utils/index.js
var import_prop_types = /* @__PURE__ */ __toESM(require_prop_types());
var import_es = /* @__PURE__ */ __toESM(require_es());
function ownKeys$1(object, enumerableOnly) {
	var keys = Object.keys(object);
	if (Object.getOwnPropertySymbols) {
		var symbols = Object.getOwnPropertySymbols(object);
		enumerableOnly && (symbols = symbols.filter(function(sym) {
			return Object.getOwnPropertyDescriptor(object, sym).enumerable;
		})), keys.push.apply(keys, symbols);
	}
	return keys;
}
function _objectSpread$1(target) {
	for (var i = 1; i < arguments.length; i++) {
		var source = null != arguments[i] ? arguments[i] : {};
		i % 2 ? ownKeys$1(Object(source), !0).forEach(function(key) {
			_defineProperty$1(target, key, source[key]);
		}) : Object.getOwnPropertyDescriptors ? Object.defineProperties(target, Object.getOwnPropertyDescriptors(source)) : ownKeys$1(Object(source)).forEach(function(key) {
			Object.defineProperty(target, key, Object.getOwnPropertyDescriptor(source, key));
		});
	}
	return target;
}
function _defineProperty$1(obj, key, value) {
	if (key in obj) Object.defineProperty(obj, key, {
		value,
		enumerable: true,
		configurable: true,
		writable: true
	});
	else obj[key] = value;
	return obj;
}
function _slicedToArray$1(arr, i) {
	return _arrayWithHoles$1(arr) || _iterableToArrayLimit$1(arr, i) || _unsupportedIterableToArray$1(arr, i) || _nonIterableRest$1();
}
function _nonIterableRest$1() {
	throw new TypeError("Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.");
}
function _unsupportedIterableToArray$1(o, minLen) {
	if (!o) return;
	if (typeof o === "string") return _arrayLikeToArray$1(o, minLen);
	var n = Object.prototype.toString.call(o).slice(8, -1);
	if (n === "Object" && o.constructor) n = o.constructor.name;
	if (n === "Map" || n === "Set") return Array.from(o);
	if (n === "Arguments" || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n)) return _arrayLikeToArray$1(o, minLen);
}
function _arrayLikeToArray$1(arr, len) {
	if (len == null || len > arr.length) len = arr.length;
	for (var i = 0, arr2 = new Array(len); i < len; i++) arr2[i] = arr[i];
	return arr2;
}
function _iterableToArrayLimit$1(arr, i) {
	var _i = arr == null ? null : typeof Symbol !== "undefined" && arr[Symbol.iterator] || arr["@@iterator"];
	if (_i == null) return;
	var _arr = [];
	var _n = true;
	var _d = false;
	var _s, _e;
	try {
		for (_i = _i.call(arr); !(_n = (_s = _i.next()).done); _n = true) {
			_arr.push(_s.value);
			if (i && _arr.length === i) break;
		}
	} catch (err) {
		_d = true;
		_e = err;
	} finally {
		try {
			if (!_n && _i["return"] != null) _i["return"]();
		} finally {
			if (_d) throw _e;
		}
	}
	return _arr;
}
function _arrayWithHoles$1(arr) {
	if (Array.isArray(arr)) return arr;
}
var FILE_INVALID_TYPE = "file-invalid-type";
var FILE_TOO_LARGE = "file-too-large";
var FILE_TOO_SMALL = "file-too-small";
var TOO_MANY_FILES = "too-many-files";
var getInvalidTypeRejectionErr = function getInvalidTypeRejectionErr(accept) {
	accept = Array.isArray(accept) && accept.length === 1 ? accept[0] : accept;
	var messageSuffix = Array.isArray(accept) ? "one of ".concat(accept.join(", ")) : accept;
	return {
		code: FILE_INVALID_TYPE,
		message: "File type must be ".concat(messageSuffix)
	};
};
var getTooLargeRejectionErr = function getTooLargeRejectionErr(maxSize) {
	return {
		code: FILE_TOO_LARGE,
		message: "File is larger than ".concat(maxSize, " ").concat(maxSize === 1 ? "byte" : "bytes")
	};
};
var getTooSmallRejectionErr = function getTooSmallRejectionErr(minSize) {
	return {
		code: FILE_TOO_SMALL,
		message: "File is smaller than ".concat(minSize, " ").concat(minSize === 1 ? "byte" : "bytes")
	};
};
var TOO_MANY_FILES_REJECTION = {
	code: TOO_MANY_FILES,
	message: "Too many files"
};
function fileAccepted(file, accept) {
	var isAcceptable = file.type === "application/x-moz-file" || (0, import_es.default)(file, accept);
	return [isAcceptable, isAcceptable ? null : getInvalidTypeRejectionErr(accept)];
}
function fileMatchSize(file, minSize, maxSize) {
	if (isDefined(file.size)) {
		if (isDefined(minSize) && isDefined(maxSize)) {
			if (file.size > maxSize) return [false, getTooLargeRejectionErr(maxSize)];
			if (file.size < minSize) return [false, getTooSmallRejectionErr(minSize)];
		} else if (isDefined(minSize) && file.size < minSize) return [false, getTooSmallRejectionErr(minSize)];
		else if (isDefined(maxSize) && file.size > maxSize) return [false, getTooLargeRejectionErr(maxSize)];
	}
	return [true, null];
}
function isDefined(value) {
	return value !== void 0 && value !== null;
}
function allFilesAccepted(_ref) {
	var files = _ref.files, accept = _ref.accept, minSize = _ref.minSize, maxSize = _ref.maxSize, multiple = _ref.multiple, maxFiles = _ref.maxFiles;
	if (!multiple && files.length > 1 || multiple && maxFiles >= 1 && files.length > maxFiles) return false;
	return files.every(function(file) {
		var accepted = _slicedToArray$1(fileAccepted(file, accept), 1)[0];
		var sizeMatch = _slicedToArray$1(fileMatchSize(file, minSize, maxSize), 1)[0];
		return accepted && sizeMatch;
	});
}
function isPropagationStopped(event) {
	if (typeof event.isPropagationStopped === "function") return event.isPropagationStopped();
	else if (typeof event.cancelBubble !== "undefined") return event.cancelBubble;
	return false;
}
function isEvtWithFiles(event) {
	if (!event.dataTransfer) return !!event.target && !!event.target.files;
	return Array.prototype.some.call(event.dataTransfer.types, function(type) {
		return type === "Files" || type === "application/x-moz-file";
	});
}
function onDocumentDragOver(event) {
	event.preventDefault();
}
function isIe(userAgent) {
	return userAgent.indexOf("MSIE") !== -1 || userAgent.indexOf("Trident/") !== -1;
}
function isEdge(userAgent) {
	return userAgent.indexOf("Edge/") !== -1;
}
function isIeOrEdge() {
	var userAgent = arguments.length > 0 && arguments[0] !== void 0 ? arguments[0] : window.navigator.userAgent;
	return isIe(userAgent) || isEdge(userAgent);
}
/**
* This is intended to be used to compose event handlers
* They are executed in order until one of them calls `event.isPropagationStopped()`.
* Note that the check is done on the first invoke too,
* meaning that if propagation was stopped before invoking the fns,
* no handlers will be executed.
*
* @param {Function} fns the event hanlder functions
* @return {Function} the event handler to add to an element
*/
function composeEventHandlers() {
	for (var _len = arguments.length, fns = new Array(_len), _key = 0; _key < _len; _key++) fns[_key] = arguments[_key];
	return function(event) {
		for (var _len2 = arguments.length, args = new Array(_len2 > 1 ? _len2 - 1 : 0), _key2 = 1; _key2 < _len2; _key2++) args[_key2 - 1] = arguments[_key2];
		return fns.some(function(fn) {
			if (!isPropagationStopped(event) && fn) fn.apply(void 0, [event].concat(args));
			return isPropagationStopped(event);
		});
	};
}
/**
* canUseFileSystemAccessAPI checks if the [File System Access API](https://developer.mozilla.org/en-US/docs/Web/API/File_System_Access_API)
* is supported by the browser.
* @returns {boolean}
*/
function canUseFileSystemAccessAPI() {
	return "showOpenFilePicker" in window;
}
/**
* filePickerOptionsTypes returns the {types} option for https://developer.mozilla.org/en-US/docs/Web/API/window/showOpenFilePicker
* based on the accept attr (see https://github.com/react-dropzone/attr-accept)
* E.g: converts ['image/*', 'text/*'] to {'image/*': [], 'text/*': []}
* @param {string|string[]} accept
*/
function filePickerOptionsTypes(accept) {
	accept = typeof accept === "string" ? accept.split(",") : accept;
	return [{
		description: "everything",
		accept: Array.isArray(accept) ? accept.filter(function(item) {
			return item === "audio/*" || item === "video/*" || item === "image/*" || item === "text/*" || /\w+\/[-+.\w]+/g.test(item);
		}).reduce(function(a, b) {
			return _objectSpread$1(_objectSpread$1({}, a), {}, _defineProperty$1({}, b, []));
		}, {}) : {}
	}];
}
/**
* Check if v is an exception caused by aborting a request (e.g window.showOpenFilePicker()).
*
* See https://developer.mozilla.org/en-US/docs/Web/API/DOMException.
* @param {any} v
* @returns {boolean} True if v is an abort exception.
*/
function isAbort(v) {
	return v instanceof DOMException && (v.name === "AbortError" || v.code === v.ABORT_ERR);
}
/**
* Check if v is a security error.
*
* See https://developer.mozilla.org/en-US/docs/Web/API/DOMException.
* @param {any} v
* @returns {boolean} True if v is a security error.
*/
function isSecurityError(v) {
	return v instanceof DOMException && (v.name === "SecurityError" || v.code === v.SECURITY_ERR);
}
//#endregion
//#region ../../node_modules/react-dropzone/dist/es/index.js
var _excluded = ["children"], _excluded2$2 = ["open"], _excluded3 = [
	"refKey",
	"role",
	"onKeyDown",
	"onFocus",
	"onBlur",
	"onClick",
	"onDragEnter",
	"onDragOver",
	"onDragLeave",
	"onDrop"
], _excluded4 = [
	"refKey",
	"onChange",
	"onClick"
];
function _toConsumableArray(arr) {
	return _arrayWithoutHoles(arr) || _iterableToArray(arr) || _unsupportedIterableToArray(arr) || _nonIterableSpread();
}
function _nonIterableSpread() {
	throw new TypeError("Invalid attempt to spread non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.");
}
function _iterableToArray(iter) {
	if (typeof Symbol !== "undefined" && iter[Symbol.iterator] != null || iter["@@iterator"] != null) return Array.from(iter);
}
function _arrayWithoutHoles(arr) {
	if (Array.isArray(arr)) return _arrayLikeToArray(arr);
}
function _slicedToArray(arr, i) {
	return _arrayWithHoles(arr) || _iterableToArrayLimit(arr, i) || _unsupportedIterableToArray(arr, i) || _nonIterableRest();
}
function _nonIterableRest() {
	throw new TypeError("Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.");
}
function _unsupportedIterableToArray(o, minLen) {
	if (!o) return;
	if (typeof o === "string") return _arrayLikeToArray(o, minLen);
	var n = Object.prototype.toString.call(o).slice(8, -1);
	if (n === "Object" && o.constructor) n = o.constructor.name;
	if (n === "Map" || n === "Set") return Array.from(o);
	if (n === "Arguments" || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n)) return _arrayLikeToArray(o, minLen);
}
function _arrayLikeToArray(arr, len) {
	if (len == null || len > arr.length) len = arr.length;
	for (var i = 0, arr2 = new Array(len); i < len; i++) arr2[i] = arr[i];
	return arr2;
}
function _iterableToArrayLimit(arr, i) {
	var _i = arr == null ? null : typeof Symbol !== "undefined" && arr[Symbol.iterator] || arr["@@iterator"];
	if (_i == null) return;
	var _arr = [];
	var _n = true;
	var _d = false;
	var _s, _e;
	try {
		for (_i = _i.call(arr); !(_n = (_s = _i.next()).done); _n = true) {
			_arr.push(_s.value);
			if (i && _arr.length === i) break;
		}
	} catch (err) {
		_d = true;
		_e = err;
	} finally {
		try {
			if (!_n && _i["return"] != null) _i["return"]();
		} finally {
			if (_d) throw _e;
		}
	}
	return _arr;
}
function _arrayWithHoles(arr) {
	if (Array.isArray(arr)) return arr;
}
function ownKeys(object, enumerableOnly) {
	var keys = Object.keys(object);
	if (Object.getOwnPropertySymbols) {
		var symbols = Object.getOwnPropertySymbols(object);
		enumerableOnly && (symbols = symbols.filter(function(sym) {
			return Object.getOwnPropertyDescriptor(object, sym).enumerable;
		})), keys.push.apply(keys, symbols);
	}
	return keys;
}
function _objectSpread(target) {
	for (var i = 1; i < arguments.length; i++) {
		var source = null != arguments[i] ? arguments[i] : {};
		i % 2 ? ownKeys(Object(source), !0).forEach(function(key) {
			_defineProperty(target, key, source[key]);
		}) : Object.getOwnPropertyDescriptors ? Object.defineProperties(target, Object.getOwnPropertyDescriptors(source)) : ownKeys(Object(source)).forEach(function(key) {
			Object.defineProperty(target, key, Object.getOwnPropertyDescriptor(source, key));
		});
	}
	return target;
}
function _defineProperty(obj, key, value) {
	if (key in obj) Object.defineProperty(obj, key, {
		value,
		enumerable: true,
		configurable: true,
		writable: true
	});
	else obj[key] = value;
	return obj;
}
function _objectWithoutProperties(source, excluded) {
	if (source == null) return {};
	var target = _objectWithoutPropertiesLoose(source, excluded);
	var key, i;
	if (Object.getOwnPropertySymbols) {
		var sourceSymbolKeys = Object.getOwnPropertySymbols(source);
		for (i = 0; i < sourceSymbolKeys.length; i++) {
			key = sourceSymbolKeys[i];
			if (excluded.indexOf(key) >= 0) continue;
			if (!Object.prototype.propertyIsEnumerable.call(source, key)) continue;
			target[key] = source[key];
		}
	}
	return target;
}
function _objectWithoutPropertiesLoose(source, excluded) {
	if (source == null) return {};
	var target = {};
	var sourceKeys = Object.keys(source);
	var key, i;
	for (i = 0; i < sourceKeys.length; i++) {
		key = sourceKeys[i];
		if (excluded.indexOf(key) >= 0) continue;
		target[key] = source[key];
	}
	return target;
}
/**
* Convenience wrapper component for the `useDropzone` hook
*
* ```jsx
* <Dropzone>
*   {({getRootProps, getInputProps}) => (
*     <div {...getRootProps()}>
*       <input {...getInputProps()} />
*       <p>Drag 'n' drop some files here, or click to select files</p>
*     </div>
*   )}
* </Dropzone>
* ```
*/
var Dropzone = /* @__PURE__ */ (0, import_react.forwardRef)(function(_ref, ref) {
	var children = _ref.children;
	var _useDropzone = useDropzone(_objectWithoutProperties(_ref, _excluded)), open = _useDropzone.open, props = _objectWithoutProperties(_useDropzone, _excluded2$2);
	(0, import_react.useImperativeHandle)(ref, function() {
		return { open };
	}, [open]);
	return /* @__PURE__ */ import_react.createElement(import_react.Fragment, null, children(_objectSpread(_objectSpread({}, props), {}, { open })));
});
Dropzone.displayName = "Dropzone";
var defaultProps = {
	disabled: false,
	getFilesFromEvent: fromEvent,
	maxSize: Infinity,
	minSize: 0,
	multiple: true,
	maxFiles: 0,
	preventDropOnDocument: true,
	noClick: false,
	noKeyboard: false,
	noDrag: false,
	noDragEventsBubbling: false,
	validator: null,
	useFsAccessApi: true
};
Dropzone.defaultProps = defaultProps;
Dropzone.propTypes = {
	/**
	* Render function that exposes the dropzone state and prop getter fns
	*
	* @param {object} params
	* @param {Function} params.getRootProps Returns the props you should apply to the root drop container you render
	* @param {Function} params.getInputProps Returns the props you should apply to hidden file input you render
	* @param {Function} params.open Open the native file selection dialog
	* @param {boolean} params.isFocused Dropzone area is in focus
	* @param {boolean} params.isFileDialogActive File dialog is opened
	* @param {boolean} params.isDragActive Active drag is in progress
	* @param {boolean} params.isDragAccept Dragged files are accepted
	* @param {boolean} params.isDragReject Some dragged files are rejected
	* @param {File[]} params.draggedFiles Files in active drag
	* @param {File[]} params.acceptedFiles Accepted files
	* @param {FileRejection[]} params.fileRejections Rejected files and why they were rejected
	*/
	children: import_prop_types.default.func,
	/**
	* Set accepted file types.
	* See https://github.com/okonet/attr-accept for more information.
	* Keep in mind that mime type determination is not reliable across platforms. CSV files,
	* for example, are reported as text/plain under macOS but as application/vnd.ms-excel under
	* Windows. In some cases there might not be a mime type set at all.
	* See: https://github.com/react-dropzone/react-dropzone/issues/276
	*/
	accept: import_prop_types.default.oneOfType([import_prop_types.default.string, import_prop_types.default.arrayOf(import_prop_types.default.string)]),
	/**
	* Allow drag 'n' drop (or selection from the file dialog) of multiple files
	*/
	multiple: import_prop_types.default.bool,
	/**
	* If false, allow dropped items to take over the current browser window
	*/
	preventDropOnDocument: import_prop_types.default.bool,
	/**
	* If true, disables click to open the native file selection dialog
	*/
	noClick: import_prop_types.default.bool,
	/**
	* If true, disables SPACE/ENTER to open the native file selection dialog.
	* Note that it also stops tracking the focus state.
	*/
	noKeyboard: import_prop_types.default.bool,
	/**
	* If true, disables drag 'n' drop
	*/
	noDrag: import_prop_types.default.bool,
	/**
	* If true, stops drag event propagation to parents
	*/
	noDragEventsBubbling: import_prop_types.default.bool,
	/**
	* Minimum file size (in bytes)
	*/
	minSize: import_prop_types.default.number,
	/**
	* Maximum file size (in bytes)
	*/
	maxSize: import_prop_types.default.number,
	/**
	* Maximum accepted number of files
	* The default value is 0 which means there is no limitation to how many files are accepted.
	*/
	maxFiles: import_prop_types.default.number,
	/**
	* Enable/disable the dropzone
	*/
	disabled: import_prop_types.default.bool,
	/**
	* Use this to provide a custom file aggregator
	*
	* @param {(DragEvent|Event)} event A drag event or input change event (if files were selected via the file dialog)
	*/
	getFilesFromEvent: import_prop_types.default.func,
	/**
	* Cb for when closing the file dialog with no selection
	*/
	onFileDialogCancel: import_prop_types.default.func,
	/**
	* Cb for when opening the file dialog
	*/
	onFileDialogOpen: import_prop_types.default.func,
	/**
	* Set to true to use the https://developer.mozilla.org/en-US/docs/Web/API/File_System_Access_API
	* to open the file picker instead of using an `<input type="file">` click event.
	*/
	useFsAccessApi: import_prop_types.default.bool,
	/**
	* Cb for when the `dragenter` event occurs.
	*
	* @param {DragEvent} event
	*/
	onDragEnter: import_prop_types.default.func,
	/**
	* Cb for when the `dragleave` event occurs
	*
	* @param {DragEvent} event
	*/
	onDragLeave: import_prop_types.default.func,
	/**
	* Cb for when the `dragover` event occurs
	*
	* @param {DragEvent} event
	*/
	onDragOver: import_prop_types.default.func,
	/**
	* Cb for when the `drop` event occurs.
	* Note that this callback is invoked after the `getFilesFromEvent` callback is done.
	*
	* Files are accepted or rejected based on the `accept`, `multiple`, `minSize` and `maxSize` props.
	* `accept` must be a valid [MIME type](http://www.iana.org/assignments/media-types/media-types.xhtml) according to [input element specification](https://www.w3.org/wiki/HTML/Elements/input/file) or a valid file extension.
	* If `multiple` is set to false and additional files are dropped,
	* all files besides the first will be rejected.
	* Any file which does not have a size in the [`minSize`, `maxSize`] range, will be rejected as well.
	*
	* Note that the `onDrop` callback will always be invoked regardless if the dropped files were accepted or rejected.
	* If you'd like to react to a specific scenario, use the `onDropAccepted`/`onDropRejected` props.
	*
	* `onDrop` will provide you with an array of [File](https://developer.mozilla.org/en-US/docs/Web/API/File) objects which you can then process and send to a server.
	* For example, with [SuperAgent](https://github.com/visionmedia/superagent) as a http/ajax library:
	*
	* ```js
	* function onDrop(acceptedFiles) {
	*   const req = request.post('/upload')
	*   acceptedFiles.forEach(file => {
	*     req.attach(file.name, file)
	*   })
	*   req.end(callback)
	* }
	* ```
	*
	* @param {File[]} acceptedFiles
	* @param {FileRejection[]} fileRejections
	* @param {(DragEvent|Event)} event A drag event or input change event (if files were selected via the file dialog)
	*/
	onDrop: import_prop_types.default.func,
	/**
	* Cb for when the `drop` event occurs.
	* Note that if no files are accepted, this callback is not invoked.
	*
	* @param {File[]} files
	* @param {(DragEvent|Event)} event
	*/
	onDropAccepted: import_prop_types.default.func,
	/**
	* Cb for when the `drop` event occurs.
	* Note that if no files are rejected, this callback is not invoked.
	*
	* @param {FileRejection[]} fileRejections
	* @param {(DragEvent|Event)} event
	*/
	onDropRejected: import_prop_types.default.func,
	/**
	* Custom validation function
	* @param {File} file
	* @returns {FileError|FileError[]}
	*/
	validator: import_prop_types.default.func
};
/**
* A function that is invoked for the `dragenter`,
* `dragover` and `dragleave` events.
* It is not invoked if the items are not files (such as link, text, etc.).
*
* @callback dragCb
* @param {DragEvent} event
*/
/**
* A function that is invoked for the `drop` or input change event.
* It is not invoked if the items are not files (such as link, text, etc.).
*
* @callback dropCb
* @param {File[]} acceptedFiles List of accepted files
* @param {FileRejection[]} fileRejections List of rejected files and why they were rejected
* @param {(DragEvent|Event)} event A drag event or input change event (if files were selected via the file dialog)
*/
/**
* A function that is invoked for the `drop` or input change event.
* It is not invoked if the items are files (such as link, text, etc.).
*
* @callback dropAcceptedCb
* @param {File[]} files List of accepted files that meet the given criteria
* (`accept`, `multiple`, `minSize`, `maxSize`)
* @param {(DragEvent|Event)} event A drag event or input change event (if files were selected via the file dialog)
*/
/**
* A function that is invoked for the `drop` or input change event.
*
* @callback dropRejectedCb
* @param {File[]} files List of rejected files that do not meet the given criteria
* (`accept`, `multiple`, `minSize`, `maxSize`)
* @param {(DragEvent|Event)} event A drag event or input change event (if files were selected via the file dialog)
*/
/**
* A function that is used aggregate files,
* in a asynchronous fashion, from drag or input change events.
*
* @callback getFilesFromEvent
* @param {(DragEvent|Event)} event A drag event or input change event (if files were selected via the file dialog)
* @returns {(File[]|Promise<File[]>)}
*/
/**
* An object with the current dropzone state and some helper functions.
*
* @typedef {object} DropzoneState
* @property {Function} getRootProps Returns the props you should apply to the root drop container you render
* @property {Function} getInputProps Returns the props you should apply to hidden file input you render
* @property {Function} open Open the native file selection dialog
* @property {boolean} isFocused Dropzone area is in focus
* @property {boolean} isFileDialogActive File dialog is opened
* @property {boolean} isDragActive Active drag is in progress
* @property {boolean} isDragAccept Dragged files are accepted
* @property {boolean} isDragReject Some dragged files are rejected
* @property {File[]} draggedFiles Files in active drag
* @property {File[]} acceptedFiles Accepted files
* @property {FileRejection[]} fileRejections Rejected files and why they were rejected
*/
var initialState = {
	isFocused: false,
	isFileDialogActive: false,
	isDragActive: false,
	isDragAccept: false,
	isDragReject: false,
	draggedFiles: [],
	acceptedFiles: [],
	fileRejections: []
};
/**
* A React hook that creates a drag 'n' drop area.
*
* ```jsx
* function MyDropzone(props) {
*   const {getRootProps, getInputProps} = useDropzone({
*     onDrop: acceptedFiles => {
*       // do something with the File objects, e.g. upload to some server
*     }
*   });
*   return (
*     <div {...getRootProps()}>
*       <input {...getInputProps()} />
*       <p>Drag and drop some files here, or click to select files</p>
*     </div>
*   )
* }
* ```
*
* @function useDropzone
*
* @param {object} props
* @param {string|string[]} [props.accept] Set accepted file types.
* See https://github.com/okonet/attr-accept for more information.
* Keep in mind that mime type determination is not reliable across platforms. CSV files,
* for example, are reported as text/plain under macOS but as application/vnd.ms-excel under
* Windows. In some cases there might not be a mime type set at all.
* See: https://github.com/react-dropzone/react-dropzone/issues/276
* @param {boolean} [props.multiple=true] Allow drag 'n' drop (or selection from the file dialog) of multiple files
* @param {boolean} [props.preventDropOnDocument=true] If false, allow dropped items to take over the current browser window
* @param {boolean} [props.noClick=false] If true, disables click to open the native file selection dialog
* @param {boolean} [props.noKeyboard=false] If true, disables SPACE/ENTER to open the native file selection dialog.
* Note that it also stops tracking the focus state.
* @param {boolean} [props.noDrag=false] If true, disables drag 'n' drop
* @param {boolean} [props.noDragEventsBubbling=false] If true, stops drag event propagation to parents
* @param {number} [props.minSize=0] Minimum file size (in bytes)
* @param {number} [props.maxSize=Infinity] Maximum file size (in bytes)
* @param {boolean} [props.disabled=false] Enable/disable the dropzone
* @param {getFilesFromEvent} [props.getFilesFromEvent] Use this to provide a custom file aggregator
* @param {Function} [props.onFileDialogCancel] Cb for when closing the file dialog with no selection
* @param {boolean} [props.useFsAccessApi] Set to true to use the https://developer.mozilla.org/en-US/docs/Web/API/File_System_Access_API
* to open the file picker instead of using an `<input type="file">` click event.
* @param {Function} [props.onFileDialogOpen] Cb for when opening the file dialog
* @param {dragCb} [props.onDragEnter] Cb for when the `dragenter` event occurs.
* @param {dragCb} [props.onDragLeave] Cb for when the `dragleave` event occurs
* @param {dragCb} [props.onDragOver] Cb for when the `dragover` event occurs
* @param {dropCb} [props.onDrop] Cb for when the `drop` event occurs.
* Note that this callback is invoked after the `getFilesFromEvent` callback is done.
*
* Files are accepted or rejected based on the `accept`, `multiple`, `minSize` and `maxSize` props.
* `accept` must be a valid [MIME type](http://www.iana.org/assignments/media-types/media-types.xhtml) according to [input element specification](https://www.w3.org/wiki/HTML/Elements/input/file) or a valid file extension.
* If `multiple` is set to false and additional files are dropped,
* all files besides the first will be rejected.
* Any file which does not have a size in the [`minSize`, `maxSize`] range, will be rejected as well.
*
* Note that the `onDrop` callback will always be invoked regardless if the dropped files were accepted or rejected.
* If you'd like to react to a specific scenario, use the `onDropAccepted`/`onDropRejected` props.
*
* `onDrop` will provide you with an array of [File](https://developer.mozilla.org/en-US/docs/Web/API/File) objects which you can then process and send to a server.
* For example, with [SuperAgent](https://github.com/visionmedia/superagent) as a http/ajax library:
*
* ```js
* function onDrop(acceptedFiles) {
*   const req = request.post('/upload')
*   acceptedFiles.forEach(file => {
*     req.attach(file.name, file)
*   })
*   req.end(callback)
* }
* ```
* @param {dropAcceptedCb} [props.onDropAccepted]
* @param {dropRejectedCb} [props.onDropRejected]
*
* @returns {DropzoneState}
*/
function useDropzone() {
	var options = arguments.length > 0 && arguments[0] !== void 0 ? arguments[0] : {};
	var _defaultProps$options = _objectSpread(_objectSpread({}, defaultProps), options), accept = _defaultProps$options.accept, disabled = _defaultProps$options.disabled, getFilesFromEvent = _defaultProps$options.getFilesFromEvent, maxSize = _defaultProps$options.maxSize, minSize = _defaultProps$options.minSize, multiple = _defaultProps$options.multiple, maxFiles = _defaultProps$options.maxFiles, onDragEnter = _defaultProps$options.onDragEnter, onDragLeave = _defaultProps$options.onDragLeave, onDragOver = _defaultProps$options.onDragOver, onDrop = _defaultProps$options.onDrop, onDropAccepted = _defaultProps$options.onDropAccepted, onDropRejected = _defaultProps$options.onDropRejected, onFileDialogCancel = _defaultProps$options.onFileDialogCancel, onFileDialogOpen = _defaultProps$options.onFileDialogOpen, useFsAccessApi = _defaultProps$options.useFsAccessApi, preventDropOnDocument = _defaultProps$options.preventDropOnDocument, noClick = _defaultProps$options.noClick, noKeyboard = _defaultProps$options.noKeyboard, noDrag = _defaultProps$options.noDrag, noDragEventsBubbling = _defaultProps$options.noDragEventsBubbling, validator = _defaultProps$options.validator;
	var onFileDialogOpenCb = (0, import_react.useMemo)(function() {
		return typeof onFileDialogOpen === "function" ? onFileDialogOpen : noop;
	}, [onFileDialogOpen]);
	var onFileDialogCancelCb = (0, import_react.useMemo)(function() {
		return typeof onFileDialogCancel === "function" ? onFileDialogCancel : noop;
	}, [onFileDialogCancel]);
	var rootRef = (0, import_react.useRef)(null);
	var inputRef = (0, import_react.useRef)(null);
	var _useReducer2 = _slicedToArray((0, import_react.useReducer)(reducer, initialState), 2), state = _useReducer2[0], dispatch = _useReducer2[1];
	var isFocused = state.isFocused, isFileDialogActive = state.isFileDialogActive, draggedFiles = state.draggedFiles;
	var fsAccessApiWorksRef = (0, import_react.useRef)(typeof window !== "undefined" && window.isSecureContext && useFsAccessApi && canUseFileSystemAccessAPI());
	var onWindowFocus = function onWindowFocus() {
		if (!fsAccessApiWorksRef.current && isFileDialogActive) setTimeout(function() {
			if (inputRef.current) {
				if (!inputRef.current.files.length) {
					dispatch({ type: "closeDialog" });
					onFileDialogCancelCb();
				}
			}
		}, 300);
	};
	(0, import_react.useEffect)(function() {
		window.addEventListener("focus", onWindowFocus, false);
		return function() {
			window.removeEventListener("focus", onWindowFocus, false);
		};
	}, [
		inputRef,
		isFileDialogActive,
		onFileDialogCancelCb,
		fsAccessApiWorksRef
	]);
	var dragTargetsRef = (0, import_react.useRef)([]);
	var onDocumentDrop = function onDocumentDrop(event) {
		if (rootRef.current && rootRef.current.contains(event.target)) return;
		event.preventDefault();
		dragTargetsRef.current = [];
	};
	(0, import_react.useEffect)(function() {
		if (preventDropOnDocument) {
			document.addEventListener("dragover", onDocumentDragOver, false);
			document.addEventListener("drop", onDocumentDrop, false);
		}
		return function() {
			if (preventDropOnDocument) {
				document.removeEventListener("dragover", onDocumentDragOver);
				document.removeEventListener("drop", onDocumentDrop);
			}
		};
	}, [rootRef, preventDropOnDocument]);
	var onDragEnterCb = (0, import_react.useCallback)(function(event) {
		event.preventDefault();
		event.persist();
		stopPropagation(event);
		dragTargetsRef.current = [].concat(_toConsumableArray(dragTargetsRef.current), [event.target]);
		if (isEvtWithFiles(event)) Promise.resolve(getFilesFromEvent(event)).then(function(draggedFiles) {
			if (isPropagationStopped(event) && !noDragEventsBubbling) return;
			dispatch({
				draggedFiles,
				isDragActive: true,
				type: "setDraggedFiles"
			});
			if (onDragEnter) onDragEnter(event);
		});
	}, [
		getFilesFromEvent,
		onDragEnter,
		noDragEventsBubbling
	]);
	var onDragOverCb = (0, import_react.useCallback)(function(event) {
		event.preventDefault();
		event.persist();
		stopPropagation(event);
		var hasFiles = isEvtWithFiles(event);
		if (hasFiles && event.dataTransfer) try {
			event.dataTransfer.dropEffect = "copy";
		} catch (_unused) {}
		if (hasFiles && onDragOver) onDragOver(event);
		return false;
	}, [onDragOver, noDragEventsBubbling]);
	var onDragLeaveCb = (0, import_react.useCallback)(function(event) {
		event.preventDefault();
		event.persist();
		stopPropagation(event);
		var targets = dragTargetsRef.current.filter(function(target) {
			return rootRef.current && rootRef.current.contains(target);
		});
		var targetIdx = targets.indexOf(event.target);
		if (targetIdx !== -1) targets.splice(targetIdx, 1);
		dragTargetsRef.current = targets;
		if (targets.length > 0) return;
		dispatch({
			isDragActive: false,
			type: "setDraggedFiles",
			draggedFiles: []
		});
		if (isEvtWithFiles(event) && onDragLeave) onDragLeave(event);
	}, [
		rootRef,
		onDragLeave,
		noDragEventsBubbling
	]);
	var setFiles = (0, import_react.useCallback)(function(files, event) {
		var acceptedFiles = [];
		var fileRejections = [];
		files.forEach(function(file) {
			var _fileAccepted2 = _slicedToArray(fileAccepted(file, accept), 2), accepted = _fileAccepted2[0], acceptError = _fileAccepted2[1];
			var _fileMatchSize2 = _slicedToArray(fileMatchSize(file, minSize, maxSize), 2), sizeMatch = _fileMatchSize2[0], sizeError = _fileMatchSize2[1];
			var customErrors = validator ? validator(file) : null;
			if (accepted && sizeMatch && !customErrors) acceptedFiles.push(file);
			else {
				var errors = [acceptError, sizeError];
				if (customErrors) errors = errors.concat(customErrors);
				fileRejections.push({
					file,
					errors: errors.filter(function(e) {
						return e;
					})
				});
			}
		});
		if (!multiple && acceptedFiles.length > 1 || multiple && maxFiles >= 1 && acceptedFiles.length > maxFiles) {
			acceptedFiles.forEach(function(file) {
				fileRejections.push({
					file,
					errors: [TOO_MANY_FILES_REJECTION]
				});
			});
			acceptedFiles.splice(0);
		}
		dispatch({
			acceptedFiles,
			fileRejections,
			type: "setFiles"
		});
		if (onDrop) onDrop(acceptedFiles, fileRejections, event);
		if (fileRejections.length > 0 && onDropRejected) onDropRejected(fileRejections, event);
		if (acceptedFiles.length > 0 && onDropAccepted) onDropAccepted(acceptedFiles, event);
	}, [
		dispatch,
		multiple,
		accept,
		minSize,
		maxSize,
		maxFiles,
		onDrop,
		onDropAccepted,
		onDropRejected,
		validator
	]);
	var onDropCb = (0, import_react.useCallback)(function(event) {
		event.preventDefault();
		event.persist();
		stopPropagation(event);
		dragTargetsRef.current = [];
		if (isEvtWithFiles(event)) Promise.resolve(getFilesFromEvent(event)).then(function(files) {
			if (isPropagationStopped(event) && !noDragEventsBubbling) return;
			setFiles(files, event);
		});
		dispatch({ type: "reset" });
	}, [
		getFilesFromEvent,
		setFiles,
		noDragEventsBubbling
	]);
	var openFileDialog = (0, import_react.useCallback)(function() {
		if (fsAccessApiWorksRef.current) {
			dispatch({ type: "openDialog" });
			onFileDialogOpenCb();
			var opts = {
				multiple,
				types: filePickerOptionsTypes(accept)
			};
			window.showOpenFilePicker(opts).then(function(handles) {
				return getFilesFromEvent(handles);
			}).then(function(files) {
				setFiles(files, null);
				dispatch({ type: "closeDialog" });
			}).catch(function(e) {
				if (isAbort(e)) {
					onFileDialogCancelCb(e);
					dispatch({ type: "closeDialog" });
				} else if (isSecurityError(e)) {
					fsAccessApiWorksRef.current = false;
					if (inputRef.current) {
						inputRef.current.value = null;
						inputRef.current.click();
					}
				}
			});
			return;
		}
		if (inputRef.current) {
			dispatch({ type: "openDialog" });
			onFileDialogOpenCb();
			inputRef.current.value = null;
			inputRef.current.click();
		}
	}, [
		dispatch,
		onFileDialogOpenCb,
		onFileDialogCancelCb,
		useFsAccessApi,
		setFiles,
		accept,
		multiple
	]);
	var onKeyDownCb = (0, import_react.useCallback)(function(event) {
		if (!rootRef.current || !rootRef.current.isEqualNode(event.target)) return;
		if (event.key === " " || event.key === "Enter" || event.keyCode === 32 || event.keyCode === 13) {
			event.preventDefault();
			openFileDialog();
		}
	}, [rootRef, openFileDialog]);
	var onFocusCb = (0, import_react.useCallback)(function() {
		dispatch({ type: "focus" });
	}, []);
	var onBlurCb = (0, import_react.useCallback)(function() {
		dispatch({ type: "blur" });
	}, []);
	var onClickCb = (0, import_react.useCallback)(function() {
		if (noClick) return;
		if (isIeOrEdge()) setTimeout(openFileDialog, 0);
		else openFileDialog();
	}, [noClick, openFileDialog]);
	var composeHandler = function composeHandler(fn) {
		return disabled ? null : fn;
	};
	var composeKeyboardHandler = function composeKeyboardHandler(fn) {
		return noKeyboard ? null : composeHandler(fn);
	};
	var composeDragHandler = function composeDragHandler(fn) {
		return noDrag ? null : composeHandler(fn);
	};
	var stopPropagation = function stopPropagation(event) {
		if (noDragEventsBubbling) event.stopPropagation();
	};
	var getRootProps = (0, import_react.useMemo)(function() {
		return function() {
			var _ref2 = arguments.length > 0 && arguments[0] !== void 0 ? arguments[0] : {}, _ref2$refKey = _ref2.refKey, refKey = _ref2$refKey === void 0 ? "ref" : _ref2$refKey, role = _ref2.role, onKeyDown = _ref2.onKeyDown, onFocus = _ref2.onFocus, onBlur = _ref2.onBlur, onClick = _ref2.onClick, onDragEnter = _ref2.onDragEnter, onDragOver = _ref2.onDragOver, onDragLeave = _ref2.onDragLeave, onDrop = _ref2.onDrop, rest = _objectWithoutProperties(_ref2, _excluded3);
			return _objectSpread(_objectSpread(_defineProperty({
				onKeyDown: composeKeyboardHandler(composeEventHandlers(onKeyDown, onKeyDownCb)),
				onFocus: composeKeyboardHandler(composeEventHandlers(onFocus, onFocusCb)),
				onBlur: composeKeyboardHandler(composeEventHandlers(onBlur, onBlurCb)),
				onClick: composeHandler(composeEventHandlers(onClick, onClickCb)),
				onDragEnter: composeDragHandler(composeEventHandlers(onDragEnter, onDragEnterCb)),
				onDragOver: composeDragHandler(composeEventHandlers(onDragOver, onDragOverCb)),
				onDragLeave: composeDragHandler(composeEventHandlers(onDragLeave, onDragLeaveCb)),
				onDrop: composeDragHandler(composeEventHandlers(onDrop, onDropCb)),
				role: typeof role === "string" && role !== "" ? role : "button"
			}, refKey, rootRef), !disabled && !noKeyboard ? { tabIndex: 0 } : {}), rest);
		};
	}, [
		rootRef,
		onKeyDownCb,
		onFocusCb,
		onBlurCb,
		onClickCb,
		onDragEnterCb,
		onDragOverCb,
		onDragLeaveCb,
		onDropCb,
		noKeyboard,
		noDrag,
		disabled
	]);
	var onInputElementClick = (0, import_react.useCallback)(function(event) {
		event.stopPropagation();
	}, []);
	var getInputProps = (0, import_react.useMemo)(function() {
		return function() {
			var _ref3 = arguments.length > 0 && arguments[0] !== void 0 ? arguments[0] : {}, _ref3$refKey = _ref3.refKey, refKey = _ref3$refKey === void 0 ? "ref" : _ref3$refKey, onChange = _ref3.onChange, onClick = _ref3.onClick, rest = _objectWithoutProperties(_ref3, _excluded4);
			return _objectSpread(_objectSpread({}, _defineProperty({
				accept,
				multiple,
				type: "file",
				style: { display: "none" },
				onChange: composeHandler(composeEventHandlers(onChange, onDropCb)),
				onClick: composeHandler(composeEventHandlers(onClick, onInputElementClick)),
				tabIndex: -1
			}, refKey, inputRef)), rest);
		};
	}, [
		inputRef,
		accept,
		multiple,
		onDropCb,
		disabled
	]);
	var fileCount = draggedFiles.length;
	var isDragAccept = fileCount > 0 && allFilesAccepted({
		files: draggedFiles,
		accept,
		minSize,
		maxSize,
		multiple,
		maxFiles
	});
	var isDragReject = fileCount > 0 && !isDragAccept;
	return _objectSpread(_objectSpread({}, state), {}, {
		isDragAccept,
		isDragReject,
		isFocused: isFocused && !disabled,
		getRootProps,
		getInputProps,
		rootRef,
		inputRef,
		open: composeHandler(openFileDialog)
	});
}
function reducer(state, action) {
	/* istanbul ignore next */
	switch (action.type) {
		case "focus": return _objectSpread(_objectSpread({}, state), {}, { isFocused: true });
		case "blur": return _objectSpread(_objectSpread({}, state), {}, { isFocused: false });
		case "openDialog": return _objectSpread(_objectSpread({}, initialState), {}, { isFileDialogActive: true });
		case "closeDialog": return _objectSpread(_objectSpread({}, state), {}, { isFileDialogActive: false });
		case "setDraggedFiles":
			var isDragActive = action.isDragActive, draggedFiles = action.draggedFiles;
			return _objectSpread(_objectSpread({}, state), {}, {
				draggedFiles,
				isDragActive
			});
		case "setFiles": return _objectSpread(_objectSpread({}, state), {}, {
			acceptedFiles: action.acceptedFiles,
			fileRejections: action.fileRejections
		});
		case "reset": return _objectSpread({}, initialState);
		default: return state;
	}
}
function noop() {}
//#endregion
//#region ../../node_modules/leva/node_modules/zustand/esm/index.js
function createStore(createState) {
	let state;
	const listeners = /* @__PURE__ */ new Set();
	const setState = (partial, replace) => {
		const nextState = typeof partial === "function" ? partial(state) : partial;
		if (nextState !== state) {
			const previousState = state;
			state = replace ? nextState : Object.assign({}, state, nextState);
			listeners.forEach((listener) => listener(state, previousState));
		}
	};
	const getState = () => state;
	const subscribeWithSelector = (listener, selector = getState, equalityFn = Object.is) => {
		console.warn("[DEPRECATED] Please use `subscribeWithSelector` middleware");
		let currentSlice = selector(state);
		function listenerToAdd() {
			const nextSlice = selector(state);
			if (!equalityFn(currentSlice, nextSlice)) {
				const previousSlice = currentSlice;
				listener(currentSlice = nextSlice, previousSlice);
			}
		}
		listeners.add(listenerToAdd);
		return () => listeners.delete(listenerToAdd);
	};
	const subscribe = (listener, selector, equalityFn) => {
		if (selector || equalityFn) return subscribeWithSelector(listener, selector, equalityFn);
		listeners.add(listener);
		return () => listeners.delete(listener);
	};
	const destroy = () => listeners.clear();
	const api = {
		setState,
		getState,
		subscribe,
		destroy
	};
	state = createState(setState, getState, api);
	return api;
}
var useIsomorphicLayoutEffect = typeof window === "undefined" || !window.navigator || /ServerSideRendering|^Deno\//.test(window.navigator.userAgent) ? import_react.useEffect : import_react.useLayoutEffect;
function create(createState) {
	const api = typeof createState === "function" ? createStore(createState) : createState;
	const useStore = (selector = api.getState, equalityFn = Object.is) => {
		const [, forceUpdate] = (0, import_react.useReducer)((c) => c + 1, 0);
		const state = api.getState();
		const stateRef = (0, import_react.useRef)(state);
		const selectorRef = (0, import_react.useRef)(selector);
		const equalityFnRef = (0, import_react.useRef)(equalityFn);
		const erroredRef = (0, import_react.useRef)(false);
		const currentSliceRef = (0, import_react.useRef)();
		if (currentSliceRef.current === void 0) currentSliceRef.current = selector(state);
		let newStateSlice;
		let hasNewStateSlice = false;
		if (stateRef.current !== state || selectorRef.current !== selector || equalityFnRef.current !== equalityFn || erroredRef.current) {
			newStateSlice = selector(state);
			hasNewStateSlice = !equalityFn(currentSliceRef.current, newStateSlice);
		}
		useIsomorphicLayoutEffect(() => {
			if (hasNewStateSlice) currentSliceRef.current = newStateSlice;
			stateRef.current = state;
			selectorRef.current = selector;
			equalityFnRef.current = equalityFn;
			erroredRef.current = false;
		});
		const stateBeforeSubscriptionRef = (0, import_react.useRef)(state);
		useIsomorphicLayoutEffect(() => {
			const listener = () => {
				try {
					const nextState = api.getState();
					const nextStateSlice = selectorRef.current(nextState);
					if (!equalityFnRef.current(currentSliceRef.current, nextStateSlice)) {
						stateRef.current = nextState;
						currentSliceRef.current = nextStateSlice;
						forceUpdate();
					}
				} catch (error) {
					erroredRef.current = true;
					forceUpdate();
				}
			};
			const unsubscribe = api.subscribe(listener);
			if (api.getState() !== stateBeforeSubscriptionRef.current) listener();
			return unsubscribe;
		}, []);
		const sliceToReturn = hasNewStateSlice ? newStateSlice : currentSliceRef.current;
		(0, import_react.useDebugValue)(sliceToReturn);
		return sliceToReturn;
	};
	Object.assign(useStore, api);
	useStore[Symbol.iterator] = function() {
		console.warn("[useStore, api] = create() is deprecated and will be removed in v4");
		const items = [useStore, api];
		return { next() {
			const done = items.length <= 0;
			return {
				value: items.shift(),
				done
			};
		} };
	};
	return useStore;
}
//#endregion
//#region ../../node_modules/leva/node_modules/zustand/esm/middleware.js
var subscribeWithSelector = (fn) => (set, get, api) => {
	const origSubscribe = api.subscribe;
	api.subscribe = (selector, optListener, options) => {
		let listener = selector;
		if (optListener) {
			const equalityFn = (options == null ? void 0 : options.equalityFn) || Object.is;
			let currentSlice = selector(api.getState());
			listener = (state) => {
				const nextSlice = selector(state);
				if (!equalityFn(currentSlice, nextSlice)) {
					const previousSlice = currentSlice;
					optListener(currentSlice = nextSlice, previousSlice);
				}
			};
			if (options == null ? void 0 : options.fireImmediately) optListener(currentSlice, currentSlice);
		}
		return origSubscribe(listener);
	};
	return fn(set, get, api);
};
//#endregion
//#region ../../node_modules/isobject/index.js
/*!
* isobject <https://github.com/jonschlinkert/isobject>
*
* Copyright (c) 2014-2017, Jon Schlinkert.
* Released under the MIT License.
*/
var require_isobject = /* @__PURE__ */ __commonJSMin(((exports, module) => {
	module.exports = function isObject(val) {
		return val != null && typeof val === "object" && Array.isArray(val) === false;
	};
}));
//#endregion
//#region ../../node_modules/is-plain-object/index.js
/*!
* is-plain-object <https://github.com/jonschlinkert/is-plain-object>
*
* Copyright (c) 2014-2017, Jon Schlinkert.
* Released under the MIT License.
*/
var require_is_plain_object = /* @__PURE__ */ __commonJSMin(((exports, module) => {
	var isObject = require_isobject();
	function isObjectObject(o) {
		return isObject(o) === true && Object.prototype.toString.call(o) === "[object Object]";
	}
	module.exports = function isPlainObject(o) {
		var ctor, prot;
		if (isObjectObject(o) === false) return false;
		ctor = o.constructor;
		if (typeof ctor !== "function") return false;
		prot = ctor.prototype;
		if (isObjectObject(prot) === false) return false;
		if (prot.hasOwnProperty("isPrototypeOf") === false) return false;
		return true;
	};
}));
//#endregion
//#region ../../node_modules/merge-value/node_modules/is-extendable/index.js
/*!
* is-extendable <https://github.com/jonschlinkert/is-extendable>
*
* Copyright (c) 2015-2017, Jon Schlinkert.
* Released under the MIT License.
*/
var require_is_extendable$3 = /* @__PURE__ */ __commonJSMin(((exports, module) => {
	var isPlainObject = require_is_plain_object();
	module.exports = function isExtendable(val) {
		return isPlainObject(val) || typeof val === "function" || Array.isArray(val);
	};
}));
//#endregion
//#region ../../node_modules/mixin-deep/node_modules/is-extendable/index.js
/*!
* is-extendable <https://github.com/jonschlinkert/is-extendable>
*
* Copyright (c) 2015-2017, Jon Schlinkert.
* Released under the MIT License.
*/
var require_is_extendable$2 = /* @__PURE__ */ __commonJSMin(((exports, module) => {
	var isPlainObject = require_is_plain_object();
	module.exports = function isExtendable(val) {
		return isPlainObject(val) || typeof val === "function" || Array.isArray(val);
	};
}));
//#endregion
//#region ../../node_modules/for-in/index.js
/*!
* for-in <https://github.com/jonschlinkert/for-in>
*
* Copyright (c) 2014-2017, Jon Schlinkert.
* Released under the MIT License.
*/
var require_for_in = /* @__PURE__ */ __commonJSMin(((exports, module) => {
	module.exports = function forIn(obj, fn, thisArg) {
		for (var key in obj) if (fn.call(thisArg, obj[key], key, obj) === false) break;
	};
}));
//#endregion
//#region ../../node_modules/mixin-deep/index.js
var require_mixin_deep = /* @__PURE__ */ __commonJSMin(((exports, module) => {
	var isExtendable = require_is_extendable$2();
	var forIn = require_for_in();
	function mixinDeep(target, objects) {
		var len = arguments.length, i = 0;
		while (++i < len) {
			var obj = arguments[i];
			if (isObject(obj)) forIn(obj, copy, target);
		}
		return target;
	}
	/**
	* Copy properties from the source object to the
	* target object.
	*
	* @param  {*} `val`
	* @param  {String} `key`
	*/
	function copy(val, key) {
		if (!isValidKey(key)) return;
		var obj = this[key];
		if (isObject(val) && isObject(obj)) mixinDeep(obj, val);
		else this[key] = val;
	}
	/**
	* Returns true if `val` is an object or function.
	*
	* @param  {any} val
	* @return {Boolean}
	*/
	function isObject(val) {
		return isExtendable(val) && !Array.isArray(val);
	}
	/**
	* Returns true if `key` is a valid key to use when extending objects.
	*
	* @param  {String} `key`
	* @return {Boolean}
	*/
	function isValidKey(key) {
		return key !== "__proto__" && key !== "constructor" && key !== "prototype";
	}
	/**
	* Expose `mixinDeep`
	*/
	module.exports = mixinDeep;
}));
//#endregion
//#region ../../node_modules/get-value/index.js
var require_get_value = /* @__PURE__ */ __commonJSMin(((exports, module) => {
	/*!
	* get-value <https://github.com/jonschlinkert/get-value>
	*
	* Copyright (c) 2014-2015, Jon Schlinkert.
	* Licensed under the MIT License.
	*/
	module.exports = function(obj, prop, a, b, c) {
		if (!isObject(obj) || !prop) return obj;
		prop = toString(prop);
		if (a) prop += "." + toString(a);
		if (b) prop += "." + toString(b);
		if (c) prop += "." + toString(c);
		if (prop in obj) return obj[prop];
		var segs = prop.split(".");
		var len = segs.length;
		var i = -1;
		while (obj && ++i < len) {
			var key = segs[i];
			while (key[key.length - 1] === "\\") key = key.slice(0, -1) + "." + segs[++i];
			obj = obj[key];
		}
		return obj;
	};
	function isObject(val) {
		return val !== null && (typeof val === "object" || typeof val === "function");
	}
	function toString(val) {
		if (!val) return "";
		if (Array.isArray(val)) return val.join(".");
		return val;
	}
}));
//#endregion
//#region ../../node_modules/split-string/node_modules/is-extendable/index.js
/*!
* is-extendable <https://github.com/jonschlinkert/is-extendable>
*
* Copyright (c) 2015-2017, Jon Schlinkert.
* Released under the MIT License.
*/
var require_is_extendable$1 = /* @__PURE__ */ __commonJSMin(((exports, module) => {
	var isPlainObject = require_is_plain_object();
	module.exports = function isExtendable(val) {
		return isPlainObject(val) || typeof val === "function" || Array.isArray(val);
	};
}));
//#endregion
//#region ../../node_modules/assign-symbols/index.js
/*!
* assign-symbols <https://github.com/jonschlinkert/assign-symbols>
*
* Copyright (c) 2015, Jon Schlinkert.
* Licensed under the MIT License.
*/
var require_assign_symbols = /* @__PURE__ */ __commonJSMin(((exports, module) => {
	module.exports = function(receiver, objects) {
		if (receiver === null || typeof receiver === "undefined") throw new TypeError("expected first argument to be an object.");
		if (typeof objects === "undefined" || typeof Symbol === "undefined") return receiver;
		if (typeof Object.getOwnPropertySymbols !== "function") return receiver;
		var isEnumerable = Object.prototype.propertyIsEnumerable;
		var target = Object(receiver);
		var len = arguments.length, i = 0;
		while (++i < len) {
			var provider = Object(arguments[i]);
			var names = Object.getOwnPropertySymbols(provider);
			for (var j = 0; j < names.length; j++) {
				var key = names[j];
				if (isEnumerable.call(provider, key)) target[key] = provider[key];
			}
		}
		return target;
	};
}));
//#endregion
//#region ../../node_modules/split-string/node_modules/extend-shallow/index.js
var require_extend_shallow$1 = /* @__PURE__ */ __commonJSMin(((exports, module) => {
	var isExtendable = require_is_extendable$1();
	var assignSymbols = require_assign_symbols();
	module.exports = Object.assign || function(obj) {
		if (obj === null || typeof obj === "undefined") throw new TypeError("Cannot convert undefined or null to object");
		if (!isObject(obj)) obj = {};
		for (var i = 1; i < arguments.length; i++) {
			var val = arguments[i];
			if (isString(val)) val = toObject(val);
			if (isObject(val)) {
				assign(obj, val);
				assignSymbols(obj, val);
			}
		}
		return obj;
	};
	function assign(a, b) {
		for (var key in b) if (hasOwn(b, key)) a[key] = b[key];
	}
	function isString(val) {
		return val && typeof val === "string";
	}
	function toObject(str) {
		var obj = {};
		for (var i in str) obj[i] = str[i];
		return obj;
	}
	function isObject(val) {
		return val && typeof val === "object" || isExtendable(val);
	}
	/**
	* Returns true if the given `key` is an own property of `obj`.
	*/
	function hasOwn(obj, key) {
		return Object.prototype.hasOwnProperty.call(obj, key);
	}
}));
//#endregion
//#region ../../node_modules/split-string/index.js
/*!
* split-string <https://github.com/jonschlinkert/split-string>
*
* Copyright (c) 2015-2017, Jon Schlinkert.
* Released under the MIT License.
*/
var require_split_string = /* @__PURE__ */ __commonJSMin(((exports, module) => {
	var extend = require_extend_shallow$1();
	module.exports = function(str, options, fn) {
		if (typeof str !== "string") throw new TypeError("expected a string");
		if (typeof options === "function") {
			fn = options;
			options = null;
		}
		if (typeof options === "string") options = { sep: options };
		var opts = extend({ sep: "." }, options);
		var quotes = opts.quotes || [
			"\"",
			"'",
			"`"
		];
		var brackets;
		if (opts.brackets === true) brackets = {
			"<": ">",
			"(": ")",
			"[": "]",
			"{": "}"
		};
		else if (opts.brackets) brackets = opts.brackets;
		var tokens = [];
		var stack = [];
		var arr = [""];
		var sep = opts.sep;
		var len = str.length;
		var idx = -1;
		var closeIdx;
		function expected() {
			if (brackets && stack.length) return brackets[stack[stack.length - 1]];
		}
		while (++idx < len) {
			var ch = str[idx];
			var next = str[idx + 1];
			var tok = {
				val: ch,
				idx,
				arr,
				str
			};
			tokens.push(tok);
			if (ch === "\\") {
				tok.val = keepEscaping(opts, str, idx) === true ? ch + next : next;
				tok.escaped = true;
				if (typeof fn === "function") fn(tok);
				arr[arr.length - 1] += tok.val;
				idx++;
				continue;
			}
			if (brackets && brackets[ch]) {
				stack.push(ch);
				var e = expected();
				var i = idx + 1;
				if (str.indexOf(e, i + 1) !== -1) while (stack.length && i < len) {
					var s = str[++i];
					if (s === "\\") {
						s++;
						continue;
					}
					if (quotes.indexOf(s) !== -1) {
						i = getClosingQuote(str, s, i + 1);
						continue;
					}
					e = expected();
					if (stack.length && str.indexOf(e, i + 1) === -1) break;
					if (brackets[s]) {
						stack.push(s);
						continue;
					}
					if (e === s) stack.pop();
				}
				closeIdx = i;
				if (closeIdx === -1) {
					arr[arr.length - 1] += ch;
					continue;
				}
				ch = str.slice(idx, closeIdx + 1);
				tok.val = ch;
				tok.idx = idx = closeIdx;
			}
			if (quotes.indexOf(ch) !== -1) {
				closeIdx = getClosingQuote(str, ch, idx + 1);
				if (closeIdx === -1) {
					arr[arr.length - 1] += ch;
					continue;
				}
				if (keepQuotes(ch, opts) === true) ch = str.slice(idx, closeIdx + 1);
				else ch = str.slice(idx + 1, closeIdx);
				tok.val = ch;
				tok.idx = idx = closeIdx;
			}
			if (typeof fn === "function") {
				fn(tok, tokens);
				ch = tok.val;
				idx = tok.idx;
			}
			if (tok.val === sep && tok.split !== false) {
				arr.push("");
				continue;
			}
			arr[arr.length - 1] += tok.val;
		}
		return arr;
	};
	function getClosingQuote(str, ch, i, brackets) {
		var idx = str.indexOf(ch, i);
		if (str.charAt(idx - 1) === "\\") return getClosingQuote(str, ch, idx + 1);
		return idx;
	}
	function keepQuotes(ch, opts) {
		if (opts.keepDoubleQuotes === true && ch === "\"") return true;
		if (opts.keepSingleQuotes === true && ch === "'") return true;
		return opts.keepQuotes;
	}
	function keepEscaping(opts, str, idx) {
		if (typeof opts.keepEscaping === "function") return opts.keepEscaping(str, idx);
		return opts.keepEscaping === true || str[idx + 1] === "\\";
	}
}));
//#endregion
//#region ../../node_modules/is-extendable/index.js
/*!
* is-extendable <https://github.com/jonschlinkert/is-extendable>
*
* Copyright (c) 2015, Jon Schlinkert.
* Licensed under the MIT License.
*/
var require_is_extendable = /* @__PURE__ */ __commonJSMin(((exports, module) => {
	module.exports = function isExtendable(val) {
		return typeof val !== "undefined" && val !== null && (typeof val === "object" || typeof val === "function");
	};
}));
//#endregion
//#region ../../node_modules/extend-shallow/index.js
var require_extend_shallow = /* @__PURE__ */ __commonJSMin(((exports, module) => {
	var isObject = require_is_extendable();
	module.exports = function extend(o) {
		if (!isObject(o)) o = {};
		var len = arguments.length;
		for (var i = 1; i < len; i++) {
			var obj = arguments[i];
			if (isObject(obj)) assign(o, obj);
		}
		return o;
	};
	function assign(a, b) {
		for (var key in b) if (hasOwn(b, key)) a[key] = b[key];
	}
	/**
	* Returns true if the given `key` is an own property of `obj`.
	*/
	function hasOwn(obj, key) {
		return Object.prototype.hasOwnProperty.call(obj, key);
	}
}));
//#endregion
//#region ../../node_modules/set-value/index.js
/*!
* set-value <https://github.com/jonschlinkert/set-value>
*
* Copyright (c) 2014-2015, 2017, Jon Schlinkert.
* Released under the MIT License.
*/
var require_set_value = /* @__PURE__ */ __commonJSMin(((exports, module) => {
	var split = require_split_string();
	var extend = require_extend_shallow();
	var isPlainObject = require_is_plain_object();
	var isObject = require_is_extendable();
	module.exports = function(obj, prop, val) {
		if (!isObject(obj)) return obj;
		if (Array.isArray(prop)) prop = [].concat.apply([], prop).join(".");
		if (typeof prop !== "string") return obj;
		var keys = split(prop, {
			sep: ".",
			brackets: true
		}).filter(isValidKey);
		var len = keys.length;
		var idx = -1;
		var current = obj;
		while (++idx < len) {
			var key = keys[idx];
			if (idx !== len - 1) {
				if (!isObject(current[key])) current[key] = {};
				current = current[key];
				continue;
			}
			if (isPlainObject(current[key]) && isPlainObject(val)) current[key] = extend({}, current[key], val);
			else current[key] = val;
		}
		return obj;
	};
	function isValidKey(key) {
		return key !== "__proto__" && key !== "constructor" && key !== "prototype";
	}
}));
//#endregion
//#region ../../node_modules/merge-value/index.js
var require_merge_value = /* @__PURE__ */ __commonJSMin(((exports, module) => {
	var isObject = require_is_extendable$3();
	var merge = require_mixin_deep();
	var get = require_get_value();
	var set = require_set_value();
	module.exports = function mergeValue(obj, prop, value) {
		if (!isObject(obj)) throw new TypeError("expected an object");
		if (typeof prop !== "string" || value == null) return merge.apply(null, arguments);
		if (typeof value === "string") {
			set(obj, prop, value);
			return obj;
		}
		var current = get(obj, prop);
		if (isObject(value) && isObject(current)) value = merge({}, current, value);
		set(obj, prop, value);
		return obj;
	};
}));
//#endregion
//#region ../../node_modules/leva/dist/leva.esm.js
var import_client = require_client();
var import_merge_value = /* @__PURE__ */ __toESM(require_merge_value());
var join = (...args) => args.filter(Boolean).join(".");
function getKeyPath(path) {
	const dir = path.split(".");
	return [dir.pop(), dir.join(".") || void 0];
}
function getValuesForPaths(data, paths) {
	return Object.entries(pick(data, paths)).reduce((acc, [, { value, disabled, key }]) => {
		acc[key] = disabled ? void 0 : value;
		return acc;
	}, {});
}
function useCompareMemoize(value, deep) {
	const ref = (0, import_react.useRef)();
	if (!(deep ? dequal : shallow)(value, ref.current)) ref.current = value;
	return ref.current;
}
function useDeepMemo(fn, deps) {
	var _useCompareMemoize;
	return (0, import_react.useMemo)(fn, (_useCompareMemoize = useCompareMemoize(deps, true)) !== null && _useCompareMemoize !== void 0 ? _useCompareMemoize : []);
}
function useToggle(toggled) {
	const wrapperRef = (0, import_react.useRef)(null);
	const contentRef = (0, import_react.useRef)(null);
	const firstRender = (0, import_react.useRef)(true);
	(0, import_react.useLayoutEffect)(() => {
		if (!toggled) {
			wrapperRef.current.style.height = "0px";
			wrapperRef.current.style.overflow = "hidden";
		}
	}, []);
	(0, import_react.useEffect)(() => {
		if (firstRender.current) {
			firstRender.current = false;
			return;
		}
		let timeout;
		const ref = wrapperRef.current;
		const fixHeight = () => {
			if (toggled) {
				ref.style.removeProperty("height");
				ref.style.removeProperty("overflow");
				contentRef.current.scrollIntoView({
					behavior: "smooth",
					block: "nearest"
				});
			}
		};
		ref.addEventListener("transitionend", fixHeight, { once: true });
		const { height } = contentRef.current.getBoundingClientRect();
		ref.style.height = height + "px";
		if (!toggled) {
			ref.style.overflow = "hidden";
			timeout = window.setTimeout(() => ref.style.height = "0px", 50);
		}
		return () => {
			ref.removeEventListener("transitionend", fixHeight);
			clearTimeout(timeout);
		};
	}, [toggled]);
	return {
		wrapperRef,
		contentRef
	};
}
var useVisiblePaths = (store) => {
	const [paths, setPaths] = (0, import_react.useState)(store.getVisiblePaths());
	(0, import_react.useEffect)(() => {
		setPaths(store.getVisiblePaths());
		const unsub = store.useStore.subscribe(store.getVisiblePaths, setPaths, { equalityFn: shallow });
		return () => unsub();
	}, [store]);
	return paths;
};
function useValuesForPath(store, paths, initialData) {
	return store.useStore((s) => {
		return getValuesForPaths(_objectSpread2(_objectSpread2({}, initialData), s.data), paths);
	}, shallow);
}
function usePopin(margin = 3) {
	const popinRef = (0, import_react.useRef)(null);
	const wrapperRef = (0, import_react.useRef)(null);
	const [shown, setShow] = (0, import_react.useState)(false);
	const show = (0, import_react.useCallback)(() => setShow(true), []);
	const hide = (0, import_react.useCallback)(() => setShow(false), []);
	(0, import_react.useLayoutEffect)(() => {
		if (shown) {
			const { bottom, top, left } = popinRef.current.getBoundingClientRect();
			const { height } = wrapperRef.current.getBoundingClientRect();
			const direction = bottom + height > window.innerHeight - 40 ? "up" : "down";
			wrapperRef.current.style.position = "fixed";
			wrapperRef.current.style.zIndex = "10000";
			wrapperRef.current.style.left = left + "px";
			if (direction === "down") wrapperRef.current.style.top = bottom + margin + "px";
			else wrapperRef.current.style.bottom = window.innerHeight - top + margin + "px";
		}
	}, [margin, shown]);
	return {
		popinRef,
		wrapperRef,
		shown,
		show,
		hide
	};
}
k$1([names_default]);
var convertMap = {
	rgb: "toRgb",
	hsl: "toHsl",
	hsv: "toHsv",
	hex: "toHex"
};
v8n.extend({ color: () => (value) => w$1(value).isValid() });
var schema$2 = (o) => v8n().color().test(o);
function convert(color, { format, hasAlpha, isString }) {
	const result = color[convertMap[format] + (isString && format !== "hex" ? "String" : "")]();
	return typeof result === "object" && !hasAlpha ? omit(result, ["a"]) : result;
}
var sanitize$2 = (v, settings) => {
	const color = w$1(v);
	if (!color.isValid()) throw Error("Invalid color");
	return convert(color, settings);
};
var format$1 = (v, settings) => {
	return convert(w$1(v), _objectSpread2(_objectSpread2({}, settings), {}, {
		isString: true,
		format: "hex"
	}));
};
var normalize$3 = ({ value }) => {
	const _f = I$1(value);
	const settings = {
		format: _f === "name" ? "hex" : _f,
		hasAlpha: typeof value === "object" ? "a" in value : _f === "hex" && value.length === 8 || /^(rgba)|(hsla)|(hsva)/.test(value),
		isString: typeof value === "string"
	};
	return {
		value: sanitize$2(value, settings),
		settings
	};
};
var props$2 = /* @__PURE__ */ Object.freeze({
	__proto__: null,
	schema: schema$2,
	sanitize: sanitize$2,
	format: format$1,
	normalize: normalize$3
});
var ColorPreview = styled("div", {
	position: "relative",
	boxSizing: "border-box",
	borderRadius: "$sm",
	overflow: "hidden",
	cursor: "pointer",
	height: "$rowHeight",
	width: "$rowHeight",
	backgroundColor: "#fff",
	backgroundImage: `url('data:image/svg+xml;charset=utf-8,<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill-opacity=".05"><path d="M8 0h8v8H8zM0 8h8v8H0z"/></svg>')`,
	$inputStyle: "",
	$hover: "",
	zIndex: 1,
	variants: { active: { true: { $inputStyle: "$accent1" } } },
	"&::before": {
		content: "\"\"",
		position: "absolute",
		top: 0,
		bottom: 0,
		right: 0,
		left: 0,
		backgroundColor: "currentColor",
		zIndex: 1
	}
});
var PickerContainer = styled("div", {
	position: "relative",
	display: "grid",
	gridTemplateColumns: "$sizes$rowHeight auto",
	columnGap: "$colGap",
	alignItems: "center"
});
var PickerWrapper = styled("div", {
	width: "$colorPickerWidth",
	height: "$colorPickerHeight",
	".react-colorful": {
		width: "100%",
		height: "100%",
		boxShadow: "$level2",
		cursor: "crosshair"
	},
	".react-colorful__saturation": { borderRadius: "$sm $sm 0 0" },
	".react-colorful__alpha, .react-colorful__hue": { height: 10 },
	".react-colorful__last-control": { borderRadius: "0 0 $sm $sm" },
	".react-colorful__pointer": {
		height: 12,
		width: 12
	}
});
function convertToRgb(value, format) {
	return format !== "rgb" ? w$1(value).toRgb() : value;
}
function Color({ value, displayValue, settings, onUpdate }) {
	const { emitOnEditStart, emitOnEditEnd } = useInputContext();
	const { format, hasAlpha } = settings;
	const { popinRef, wrapperRef, shown, show, hide } = usePopin();
	const timer = (0, import_react.useRef)(0);
	const [initialRgb, setInitialRgb] = (0, import_react.useState)(() => convertToRgb(value, format));
	const ColorPicker = hasAlpha ? Ce : Ne;
	const showPicker = () => {
		setInitialRgb(convertToRgb(value, format));
		show();
		emitOnEditStart();
	};
	const hidePicker = () => {
		hide();
		emitOnEditEnd();
		window.clearTimeout(timer.current);
	};
	const hideAfterDelay = () => {
		timer.current = window.setTimeout(hidePicker, 500);
	};
	(0, import_react.useEffect)(() => {
		return () => window.clearTimeout(timer.current);
	}, []);
	return import_react.createElement(import_react.Fragment, null, import_react.createElement(ColorPreview, {
		ref: popinRef,
		active: shown,
		onClick: () => showPicker(),
		style: { color: displayValue }
	}), shown && import_react.createElement(Portal, null, import_react.createElement(Overlay, { onPointerUp: hidePicker }), import_react.createElement(PickerWrapper, {
		ref: wrapperRef,
		onMouseEnter: () => window.clearTimeout(timer.current),
		onMouseLeave: (e) => e.buttons === 0 && hideAfterDelay()
	}, import_react.createElement(ColorPicker, {
		color: initialRgb,
		onChange: onUpdate
	}))));
}
function ColorComponent() {
	const { value, displayValue, label, onChange, onUpdate, settings } = useInputContext();
	return import_react.createElement(Row, { input: true }, import_react.createElement(Label, null, label), import_react.createElement(PickerContainer, null, import_react.createElement(Color, {
		value,
		displayValue,
		onChange,
		onUpdate,
		settings
	}), import_react.createElement(ValueInput, {
		value: displayValue,
		onChange,
		onUpdate
	})));
}
var color = createInternalPlugin(_objectSpread2({ component: ColorComponent }, props$2));
function Vector3dComponent() {
	const { label, displayValue, onUpdate, settings } = useInputContext();
	return import_react.createElement(Row, { input: true }, import_react.createElement(Label, null, label), import_react.createElement(Vector, {
		value: displayValue,
		settings,
		onUpdate
	}));
}
var vector3d = createInternalPlugin(_objectSpread2({ component: Vector3dComponent }, getVectorPlugin([
	"x",
	"y",
	"z"
])));
var JoystickTrigger = styled("div", {
	$flexCenter: "",
	position: "relative",
	backgroundColor: "$elevation3",
	borderRadius: "$sm",
	cursor: "pointer",
	height: "$rowHeight",
	width: "$rowHeight",
	touchAction: "none",
	$draggable: "",
	$hover: "",
	"&:active": { cursor: "none" },
	"&::after": {
		content: "\"\"",
		backgroundColor: "$accent2",
		height: 4,
		width: 4,
		borderRadius: 2
	}
});
var JoystickPlayground = styled("div", {
	$flexCenter: "",
	width: "$joystickWidth",
	height: "$joystickHeight",
	borderRadius: "$sm",
	boxShadow: "$level2",
	position: "fixed",
	zIndex: 1e4,
	overflow: "hidden",
	$draggable: "",
	transform: "translate(-50%, -50%)",
	variants: { isOutOfBounds: {
		true: { backgroundColor: "$elevation1" },
		false: { backgroundColor: "$elevation3" }
	} },
	"> div": {
		position: "absolute",
		$flexCenter: "",
		borderStyle: "solid",
		borderWidth: 1,
		borderColor: "$highlight1",
		backgroundColor: "$elevation3",
		width: "80%",
		height: "80%",
		"&::after,&::before": {
			content: "\"\"",
			position: "absolute",
			zindex: 10,
			backgroundColor: "$highlight1"
		},
		"&::before": {
			width: "100%",
			height: 1
		},
		"&::after": {
			height: "100%",
			width: 1
		}
	},
	"> span": {
		position: "relative",
		zindex: 100,
		width: 10,
		height: 10,
		backgroundColor: "$accent2",
		borderRadius: "50%"
	}
});
function Joystick({ value, settings, onUpdate }) {
	const timeout = (0, import_react.useRef)();
	const outOfBoundsX = (0, import_react.useRef)(0);
	const outOfBoundsY = (0, import_react.useRef)(0);
	const stepMultiplier = (0, import_react.useRef)(1);
	const [joystickShown, setShowJoystick] = (0, import_react.useState)(false);
	const [isOutOfBounds, setIsOutOfBounds] = (0, import_react.useState)(false);
	const [spanRef, set] = useTransform();
	const joystickeRef = (0, import_react.useRef)(null);
	const playgroundRef = (0, import_react.useRef)(null);
	(0, import_react.useLayoutEffect)(() => {
		if (joystickShown) {
			const { top, left, width, height } = joystickeRef.current.getBoundingClientRect();
			playgroundRef.current.style.left = left + width / 2 + "px";
			playgroundRef.current.style.top = top + height / 2 + "px";
		}
	}, [joystickShown]);
	const { keys: [v1, v2], joystick } = settings;
	const yFactor = joystick === "invertY" ? 1 : -1;
	const { [v1]: { step: stepV1 }, [v2]: { step: stepV2 } } = settings;
	const wpx = useTh("sizes", "joystickWidth");
	const hpx = useTh("sizes", "joystickHeight");
	const w = parseFloat(wpx) * .8 / 2;
	const h = parseFloat(hpx) * .8 / 2;
	const startOutOfBounds = (0, import_react.useCallback)(() => {
		if (timeout.current) return;
		setIsOutOfBounds(true);
		if (outOfBoundsX.current) set({ x: outOfBoundsX.current * w });
		if (outOfBoundsY.current) set({ y: outOfBoundsY.current * -h });
		timeout.current = window.setInterval(() => {
			onUpdate((v) => {
				const incX = stepV1 * outOfBoundsX.current * stepMultiplier.current;
				const incY = yFactor * stepV2 * outOfBoundsY.current * stepMultiplier.current;
				return Array.isArray(v) ? {
					[v1]: v[0] + incX,
					[v2]: v[1] + incY
				} : {
					[v1]: v[v1] + incX,
					[v2]: v[v2] + incY
				};
			});
		}, 16);
	}, [
		w,
		h,
		onUpdate,
		set,
		stepV1,
		stepV2,
		v1,
		v2,
		yFactor
	]);
	const endOutOfBounds = (0, import_react.useCallback)(() => {
		window.clearTimeout(timeout.current);
		timeout.current = void 0;
		setIsOutOfBounds(false);
	}, []);
	(0, import_react.useEffect)(() => {
		function setStepMultiplier(event) {
			stepMultiplier.current = multiplyStep(event);
		}
		window.addEventListener("keydown", setStepMultiplier);
		window.addEventListener("keyup", setStepMultiplier);
		return () => {
			window.clearTimeout(timeout.current);
			window.removeEventListener("keydown", setStepMultiplier);
			window.removeEventListener("keyup", setStepMultiplier);
		};
	}, []);
	const bind = useDrag(({ first, active, delta: [dx, dy], movement: [mx, my] }) => {
		if (first) setShowJoystick(true);
		const _x = clamp(mx, -w, w);
		const _y = clamp(my, -h, h);
		outOfBoundsX.current = Math.abs(mx) > Math.abs(_x) ? Math.sign(mx - _x) : 0;
		outOfBoundsY.current = Math.abs(my) > Math.abs(_y) ? Math.sign(_y - my) : 0;
		let newX = value[v1];
		let newY = value[v2];
		if (active) {
			if (!outOfBoundsX.current) {
				newX += dx * stepV1 * stepMultiplier.current;
				set({ x: _x });
			}
			if (!outOfBoundsY.current) {
				newY -= yFactor * dy * stepV2 * stepMultiplier.current;
				set({ y: _y });
			}
			if (outOfBoundsX.current || outOfBoundsY.current) startOutOfBounds();
			else endOutOfBounds();
			onUpdate({
				[v1]: newX,
				[v2]: newY
			});
		} else {
			setShowJoystick(false);
			outOfBoundsX.current = 0;
			outOfBoundsY.current = 0;
			set({
				x: 0,
				y: 0
			});
			endOutOfBounds();
		}
	});
	return import_react.createElement(JoystickTrigger, _extends({ ref: joystickeRef }, bind()), joystickShown && import_react.createElement(Portal, null, import_react.createElement(JoystickPlayground, {
		ref: playgroundRef,
		isOutOfBounds
	}, import_react.createElement("div", null), import_react.createElement("span", { ref: spanRef }))));
}
var Container$1 = styled("div", {
	display: "grid",
	columnGap: "$colGap",
	variants: { withJoystick: {
		true: { gridTemplateColumns: "$sizes$rowHeight auto" },
		false: { gridTemplateColumns: "auto" }
	} }
});
function Vector2dComponent() {
	const { label, displayValue, onUpdate, settings } = useInputContext();
	return import_react.createElement(Row, { input: true }, import_react.createElement(Label, null, label), import_react.createElement(Container$1, { withJoystick: !!settings.joystick }, settings.joystick && import_react.createElement(Joystick, {
		value: displayValue,
		settings,
		onUpdate
	}), import_react.createElement(Vector, {
		value: displayValue,
		settings,
		onUpdate
	})));
}
var _excluded$7 = ["joystick"];
var plugin = getVectorPlugin(["x", "y"]);
var normalize$2 = (_ref) => {
	let { joystick = true } = _ref, input = _objectWithoutProperties$1(_ref, _excluded$7);
	const { value, settings } = plugin.normalize(input);
	return {
		value,
		settings: _objectSpread2(_objectSpread2({}, settings), {}, { joystick })
	};
};
var vector2d = createInternalPlugin(_objectSpread2(_objectSpread2({ component: Vector2dComponent }, plugin), {}, { normalize: normalize$2 }));
var sanitize$1 = (v) => {
	if (v === void 0) return void 0;
	if (v instanceof File) try {
		return URL.createObjectURL(v);
	} catch (e) {
		return;
	}
	if (typeof v === "string" && v.indexOf("blob:") === 0) return v;
	throw Error(`Invalid image format [undefined | blob | File].`);
};
var schema$1 = (_o, s) => typeof s === "object" && "image" in s;
var normalize$1 = ({ image }) => {
	return { value: image };
};
var props$1 = /* @__PURE__ */ Object.freeze({
	__proto__: null,
	sanitize: sanitize$1,
	schema: schema$1,
	normalize: normalize$1
});
var ImageContainer = styled("div", {
	position: "relative",
	display: "grid",
	gridTemplateColumns: "$sizes$rowHeight auto 20px",
	columnGap: "$colGap",
	alignItems: "center"
});
var DropZone = styled("div", {
	$flexCenter: "",
	overflow: "hidden",
	height: "$rowHeight",
	background: "$elevation3",
	textAlign: "center",
	color: "inherit",
	borderRadius: "$sm",
	outline: "none",
	userSelect: "none",
	cursor: "pointer",
	$inputStyle: "",
	$hover: "",
	$focusWithin: "",
	$active: "$accent1 $elevation1",
	variants: { isDragAccept: { true: {
		$inputStyle: "$accent1",
		backgroundColor: "$elevation1"
	} } }
});
var ImagePreview = styled("div", {
	boxSizing: "border-box",
	borderRadius: "$sm",
	height: "$rowHeight",
	width: "$rowHeight",
	$inputStyle: "",
	backgroundSize: "cover",
	backgroundPosition: "center",
	variants: { hasImage: { true: {
		cursor: "pointer",
		$hover: "",
		$active: ""
	} } }
});
var ImageLargePreview = styled("div", {
	$flexCenter: "",
	width: "$imagePreviewWidth",
	height: "$imagePreviewHeight",
	borderRadius: "$sm",
	boxShadow: "$level2",
	pointerEvents: "none",
	$inputStyle: "",
	backgroundSize: "cover",
	backgroundPosition: "center"
});
var Instructions = styled("div", {
	fontSize: "0.8em",
	height: "100%",
	padding: "$rowGap $md"
});
var Remove = styled("div", {
	$flexCenter: "",
	top: "0",
	right: "0",
	marginRight: "$sm",
	height: "100%",
	cursor: "pointer",
	variants: { disabled: { true: {
		color: "$elevation3",
		cursor: "default"
	} } },
	"&::after,&::before": {
		content: "\"\"",
		position: "absolute",
		height: 2,
		width: 10,
		borderRadius: 1,
		backgroundColor: "currentColor"
	},
	"&::after": { transform: "rotate(45deg)" },
	"&::before": { transform: "rotate(-45deg)" }
});
function ImageComponent() {
	const { label, value, onUpdate, disabled } = useInputContext();
	const { popinRef, wrapperRef, shown, show, hide } = usePopin();
	const onDrop = (0, import_react.useCallback)((acceptedFiles) => {
		if (acceptedFiles.length) onUpdate(acceptedFiles[0]);
	}, [onUpdate]);
	const clear = (0, import_react.useCallback)((e) => {
		e.stopPropagation();
		onUpdate(void 0);
	}, [onUpdate]);
	const { getRootProps, getInputProps, isDragAccept } = useDropzone({
		maxFiles: 1,
		accept: "image/*",
		onDrop,
		disabled
	});
	return import_react.createElement(Row, { input: true }, import_react.createElement(Label, null, label), import_react.createElement(ImageContainer, null, import_react.createElement(ImagePreview, {
		ref: popinRef,
		hasImage: !!value,
		onPointerDown: () => !!value && show(),
		onPointerUp: hide,
		style: { backgroundImage: value ? `url(${value})` : "none" }
	}), shown && !!value && import_react.createElement(Portal, null, import_react.createElement(Overlay, {
		onPointerUp: hide,
		style: { cursor: "pointer" }
	}), import_react.createElement(ImageLargePreview, {
		ref: wrapperRef,
		style: { backgroundImage: `url(${value})` }
	})), import_react.createElement(DropZone, getRootProps({ isDragAccept }), import_react.createElement("input", getInputProps()), import_react.createElement(Instructions, null, isDragAccept ? "drop image" : "click or drop")), import_react.createElement(Remove, {
		onClick: clear,
		disabled: !value
	})));
}
var image = createInternalPlugin(_objectSpread2({ component: ImageComponent }, props$1));
var number = v8n().number();
var schema = (o, s) => v8n().array().length(2).every.number().test(o) && v8n().schema({
	min: number,
	max: number
}).test(s);
var format = (v) => ({
	min: v[0],
	max: v[1]
});
var sanitize = (value, { bounds: [MIN, MAX] }, prevValue) => {
	const _value = Array.isArray(value) ? format(value) : value;
	const { min, max } = _objectSpread2(_objectSpread2({}, {
		min: prevValue[0],
		max: prevValue[1]
	}), _value);
	return [clamp(Number(min), MIN, Math.max(MIN, max)), clamp(Number(max), Math.min(MAX, min), MAX)];
};
var normalize = ({ value, min, max }) => {
	const boundsSettings = {
		min,
		max
	};
	const _settings = normalizeKeyedNumberSettings(format(value), {
		min: boundsSettings,
		max: boundsSettings
	});
	const bounds = [min, max];
	const settings = _objectSpread2(_objectSpread2({}, _settings), {}, { bounds });
	return {
		value: sanitize(format(value), settings, value),
		settings
	};
};
var props = /* @__PURE__ */ Object.freeze({
	__proto__: null,
	schema,
	format,
	sanitize,
	normalize
});
var _excluded$6 = [
	"value",
	"bounds",
	"onDrag"
], _excluded2$1 = ["bounds"];
var Container = styled("div", {
	display: "grid",
	columnGap: "$colGap",
	gridTemplateColumns: "auto calc($sizes$numberInputMinWidth * 2 + $space$rowGap)"
});
function IntervalSlider(_ref) {
	let { value, bounds: [min, max], onDrag } = _ref, settings = _objectWithoutProperties$1(_ref, _excluded$6);
	const ref = (0, import_react.useRef)(null);
	const minScrubberRef = (0, import_react.useRef)(null);
	const maxScrubberRef = (0, import_react.useRef)(null);
	const rangeWidth = (0, import_react.useRef)(0);
	const scrubberWidth = useTh("sizes", "scrubberWidth");
	const bind = useDrag(({ event, first, xy: [x], movement: [mx], memo: _memo = {} }) => {
		if (first) {
			const { width, left } = ref.current.getBoundingClientRect();
			rangeWidth.current = width - parseFloat(scrubberWidth);
			const targetIsScrub = (event === null || event === void 0 ? void 0 : event.target) === minScrubberRef.current || (event === null || event === void 0 ? void 0 : event.target) === maxScrubberRef.current;
			_memo.pos = invertedRange((x - left) / width, min, max);
			const delta = Math.abs(_memo.pos - value.min) - Math.abs(_memo.pos - value.max);
			_memo.key = delta < 0 || delta === 0 && _memo.pos <= value.min ? "min" : "max";
			if (targetIsScrub) _memo.pos = value[_memo.key];
		}
		const newValue = _memo.pos + invertedRange(mx / rangeWidth.current, 0, max - min);
		onDrag({ [_memo.key]: sanitizeStep(newValue, settings[_memo.key]) });
		return _memo;
	});
	const minStyle = `calc(${range(value.min, min, max)} * (100% - ${scrubberWidth} - 8px) + 4px)`;
	const maxStyle = `calc(${1 - range(value.max, min, max)} * (100% - ${scrubberWidth} - 8px) + 4px)`;
	return import_react.createElement(RangeWrapper, _extends({ ref }, bind()), import_react.createElement(Range, null, import_react.createElement(Indicator, { style: {
		left: minStyle,
		right: maxStyle
	} })), import_react.createElement(Scrubber, {
		position: "left",
		ref: minScrubberRef,
		style: { left: minStyle }
	}), import_react.createElement(Scrubber, {
		position: "right",
		ref: maxScrubberRef,
		style: { right: maxStyle }
	}));
}
function IntervalComponent() {
	const { label, displayValue, onUpdate, settings } = useInputContext();
	const _settings = _objectWithoutProperties$1(settings, _excluded2$1);
	return import_react.createElement(import_react.Fragment, null, import_react.createElement(Row, { input: true }, import_react.createElement(Label, null, label), import_react.createElement(Container, null, import_react.createElement(IntervalSlider, _extends({ value: displayValue }, settings, { onDrag: onUpdate })), import_react.createElement(Vector, {
		value: displayValue,
		settings: _settings,
		onUpdate,
		innerLabelTrim: 0
	}))));
}
var interval = createInternalPlugin(_objectSpread2({ component: IntervalComponent }, props));
var createEventEmitter = () => {
	const listenerMapping = /* @__PURE__ */ new Map();
	return {
		on: (topic, listener) => {
			let listeners = listenerMapping.get(topic);
			if (listeners === void 0) {
				listeners = /* @__PURE__ */ new Set();
				listenerMapping.set(topic, listeners);
			}
			listeners.add(listener);
		},
		off: (topic, listener) => {
			const listeners = listenerMapping.get(topic);
			if (listeners === void 0) return;
			listeners.delete(listener);
			if (listeners.size === 0) listenerMapping.delete(topic);
		},
		emit: (topic, ...args) => {
			const listeners = listenerMapping.get(topic);
			if (listeners === void 0) return;
			for (const listener of listeners) listener(...args);
		}
	};
};
var _excluded$5 = ["type", "value"], _excluded2 = [
	"onChange",
	"transient",
	"onEditStart",
	"onEditEnd"
];
var levaStore = new function Store() {
	const store = create(subscribeWithSelector(() => ({ data: {} })));
	const eventEmitter = createEventEmitter();
	this.storeId = getUid();
	this.useStore = store;
	const folders = {};
	const orderedPaths = /* @__PURE__ */ new Set();
	this.getVisiblePaths = () => {
		const data = this.getData();
		const paths = Object.keys(data);
		const hiddenFolders = [];
		Object.entries(folders).forEach(([path, settings]) => {
			if (settings.render && paths.some((p) => p.indexOf(path) === 0) && !settings.render(this.get)) hiddenFolders.push(path + ".");
		});
		const visiblePaths = [];
		orderedPaths.forEach((path) => {
			if (path in data && data[path].__refCount > 0 && hiddenFolders.every((p) => path.indexOf(p) === -1) && (!data[path].render || data[path].render(this.get))) visiblePaths.push(path);
		});
		return visiblePaths;
	};
	this.setOrderedPaths = (newPaths) => {
		newPaths.forEach((p) => orderedPaths.add(p));
	};
	this.orderPaths = (paths) => {
		this.setOrderedPaths(paths);
		return paths;
	};
	this.disposePaths = (paths) => {
		store.setState((s) => {
			const data = s.data;
			paths.forEach((path) => {
				if (path in data) {
					const input = data[path];
					input.__refCount--;
					if (input.__refCount === 0 && input.type in SpecialInputs) delete data[path];
				}
			});
			return { data };
		});
	};
	this.dispose = () => {
		store.setState(() => {
			return { data: {} };
		});
	};
	this.getFolderSettings = (path) => {
		return folders[path] || {};
	};
	this.getData = () => {
		return store.getState().data;
	};
	this.addData = (newData, override) => {
		store.setState((s) => {
			const data = s.data;
			Object.entries(newData).forEach(([path, newInputData]) => {
				let input = data[path];
				if (!!input) {
					const { type, value } = newInputData, rest = _objectWithoutProperties$1(newInputData, _excluded$5);
					if (type !== input.type) warn(LevaErrors.INPUT_TYPE_OVERRIDE, path, input.type, type);
					else {
						if (input.__refCount === 0 || override) Object.assign(input, rest);
						input.__refCount++;
					}
				} else data[path] = _objectSpread2(_objectSpread2({}, newInputData), {}, { __refCount: 1 });
			});
			return { data };
		});
	};
	this.setValueAtPath = (path, value, fromPanel) => {
		store.setState((s) => {
			const data = s.data;
			updateInput(data[path], value, path, this, fromPanel);
			return { data };
		});
	};
	this.setSettingsAtPath = (path, settings) => {
		store.setState((s) => {
			const data = s.data;
			data[path].settings = _objectSpread2(_objectSpread2({}, data[path].settings), settings);
			return { data };
		});
	};
	this.disableInputAtPath = (path, flag) => {
		store.setState((s) => {
			const data = s.data;
			data[path].disabled = flag;
			return { data };
		});
	};
	this.set = (values, fromPanel) => {
		store.setState((s) => {
			const data = s.data;
			Object.entries(values).forEach(([path, value]) => {
				try {
					updateInput(data[path], value, void 0, void 0, fromPanel);
				} catch (e) {}
			});
			return { data };
		});
	};
	this.getInput = (path) => {
		try {
			return this.getData()[path];
		} catch (e) {
			warn(LevaErrors.PATH_DOESNT_EXIST, path);
		}
	};
	this.get = (path) => {
		var _this$getInput;
		return (_this$getInput = this.getInput(path)) === null || _this$getInput === void 0 ? void 0 : _this$getInput.value;
	};
	this.emitOnEditStart = (path) => {
		eventEmitter.emit(`onEditStart:${path}`, this.get(path), path, _objectSpread2(_objectSpread2({}, this.getInput(path)), {}, { get: this.get }));
	};
	this.emitOnEditEnd = (path) => {
		eventEmitter.emit(`onEditEnd:${path}`, this.get(path), path, _objectSpread2(_objectSpread2({}, this.getInput(path)), {}, { get: this.get }));
	};
	this.subscribeToEditStart = (path, listener) => {
		const _path = `onEditStart:${path}`;
		eventEmitter.on(_path, listener);
		return () => eventEmitter.off(_path, listener);
	};
	this.subscribeToEditEnd = (path, listener) => {
		const _path = `onEditEnd:${path}`;
		eventEmitter.on(_path, listener);
		return () => eventEmitter.off(_path, listener);
	};
	const _getDataFromSchema = (schema, rootPath, mappedPaths) => {
		const data = {};
		Object.entries(schema).forEach(([key, rawInput]) => {
			if (key === "") return warn(LevaErrors.EMPTY_KEY);
			let newPath = join(rootPath, key);
			if (rawInput.type === SpecialInputs.FOLDER) {
				const newData = _getDataFromSchema(rawInput.schema, newPath, mappedPaths);
				Object.assign(data, newData);
				if (!(newPath in folders)) folders[newPath] = rawInput.settings;
			} else if (key in mappedPaths) warn(LevaErrors.DUPLICATE_KEYS, key, newPath, mappedPaths[key].path);
			else {
				const normalizedInput = normalizeInput(rawInput, key, newPath, data);
				if (normalizedInput) {
					const { type, options, input } = normalizedInput;
					const { onChange, transient, onEditStart, onEditEnd } = options, _options = _objectWithoutProperties$1(options, _excluded2);
					data[newPath] = _objectSpread2(_objectSpread2(_objectSpread2({ type }, _options), input), {}, { fromPanel: true });
					mappedPaths[key] = {
						path: newPath,
						onChange,
						transient,
						onEditStart,
						onEditEnd
					};
				} else warn(LevaErrors.UNKNOWN_INPUT, newPath, rawInput);
			}
		});
		return data;
	};
	this.getDataFromSchema = (schema) => {
		const mappedPaths = {};
		return [_getDataFromSchema(schema, "", mappedPaths), mappedPaths];
	};
}();
var defaultSettings$2 = { collapsed: false };
function folder(schema, settings) {
	return {
		type: SpecialInputs.FOLDER,
		schema,
		settings: _objectSpread2(_objectSpread2({}, defaultSettings$2), settings)
	};
}
var isInput = (v) => "__levaInput" in v;
var buildTree = (paths, filter) => {
	const tree = {};
	const _filter = filter ? filter.toLowerCase() : null;
	paths.forEach((path) => {
		const [valueKey, folderPath] = getKeyPath(path);
		if (!_filter || valueKey.toLowerCase().indexOf(_filter) > -1) (0, import_merge_value.default)(tree, folderPath, { [valueKey]: {
			__levaInput: true,
			path
		} });
	});
	return tree;
};
var _excluded$4 = [
	"type",
	"label",
	"path",
	"valueKey",
	"value",
	"settings",
	"setValue",
	"disabled"
];
function ControlInput(_ref) {
	let { type, label, path, valueKey, value, settings, setValue, disabled } = _ref, rest = _objectWithoutProperties$1(_ref, _excluded$4);
	const { displayValue, onChange, onUpdate } = useInputSetters({
		type,
		value,
		settings,
		setValue
	});
	const Input = Plugins[type].component;
	if (!Input) {
		warn(LevaErrors.NO_COMPONENT_FOR_TYPE, type, path);
		return null;
	}
	return import_react.createElement(InputContext.Provider, { value: _objectSpread2({
		key: valueKey,
		path,
		id: "" + path,
		label,
		displayValue,
		value,
		onChange,
		onUpdate,
		settings,
		setValue,
		disabled
	}, rest) }, import_react.createElement(StyledInputWrapper$1, { disabled }, import_react.createElement(Input, null)));
}
var StyledButton = styled("button", {
	display: "block",
	$reset: "",
	fontWeight: "$button",
	height: "$rowHeight",
	borderStyle: "none",
	borderRadius: "$sm",
	backgroundColor: "$elevation1",
	color: "$highlight1",
	"&:not(:disabled)": {
		color: "$highlight3",
		backgroundColor: "$accent2",
		cursor: "pointer",
		$hover: "$accent3",
		$active: "$accent3 $accent1",
		$focus: ""
	}
});
function Button({ onClick, settings, label }) {
	const store = useStoreContext();
	return import_react.createElement(Row, null, import_react.createElement(StyledButton, {
		disabled: settings.disabled,
		onClick: () => onClick(store.get)
	}, label));
}
var StyledButtonGroup = styled("div", {
	$flex: "",
	justifyContent: "flex-end",
	gap: "$colGap"
});
var StyledButtonGroupButton = styled("button", {
	$reset: "",
	cursor: "pointer",
	borderRadius: "$xs",
	"&:hover": { backgroundColor: "$elevation3" }
});
var getOpts = ({ label: _label, opts: _opts }) => {
	let label = typeof _label === "string" ? _label.trim() === "" ? null : _label : _label;
	let opts = _opts;
	if (typeof _opts.opts === "object") {
		if (opts.label !== void 0) label = _opts.label;
		opts = _opts.opts;
	}
	return {
		label,
		opts
	};
};
function ButtonGroup(props) {
	const { label, opts } = getOpts(props);
	const store = useStoreContext();
	return import_react.createElement(Row, { input: !!label }, label && import_react.createElement(Label, null, label), import_react.createElement(StyledButtonGroup, null, Object.entries(opts).map(([label, onClick]) => import_react.createElement(StyledButtonGroupButton, {
		key: label,
		onClick: () => onClick(store.get)
	}, label))));
}
var Canvas = styled("canvas", {
	height: "$monitorHeight",
	width: "100%",
	display: "block",
	borderRadius: "$sm"
});
var POINTS = 100;
function push(arr, val) {
	arr.push(val);
	if (arr.length > POINTS) arr.shift();
}
var MonitorCanvas = (0, import_react.forwardRef)(function({ initialValue }, ref) {
	const accentColor = useTh("colors", "highlight3");
	const backgroundColor = useTh("colors", "elevation2");
	const fillColor = useTh("colors", "highlight1");
	const [gradientTop, gradientBottom] = (0, import_react.useMemo)(() => {
		return [w$1(fillColor).alpha(.4).toRgbString(), w$1(fillColor).alpha(.1).toRgbString()];
	}, [fillColor]);
	const points = (0, import_react.useRef)([initialValue]);
	const min = (0, import_react.useRef)(initialValue);
	const max = (0, import_react.useRef)(initialValue);
	const raf = (0, import_react.useRef)();
	const drawPlot = (0, import_react.useCallback)((_canvas, _ctx) => {
		if (!_canvas) return;
		const { width, height } = _canvas;
		const path = new Path2D();
		const interval = width / POINTS;
		const verticalPadding = height * .05;
		for (let i = 0; i < points.current.length; i++) {
			const p = range(points.current[i], min.current, max.current);
			const x = interval * i;
			const y = height - p * (height - verticalPadding * 2) - verticalPadding;
			path.lineTo(x, y);
		}
		_ctx.clearRect(0, 0, width, height);
		const gradientPath = new Path2D(path);
		gradientPath.lineTo(interval * (points.current.length + 1), height);
		gradientPath.lineTo(0, height);
		gradientPath.lineTo(0, 0);
		const gradient = _ctx.createLinearGradient(0, 0, 0, height);
		gradient.addColorStop(0, gradientTop);
		gradient.addColorStop(1, gradientBottom);
		_ctx.fillStyle = gradient;
		_ctx.fill(gradientPath);
		_ctx.strokeStyle = backgroundColor;
		_ctx.lineJoin = "round";
		_ctx.lineWidth = 14;
		_ctx.stroke(path);
		_ctx.strokeStyle = accentColor;
		_ctx.lineWidth = 2;
		_ctx.stroke(path);
	}, [
		accentColor,
		backgroundColor,
		gradientTop,
		gradientBottom
	]);
	const [canvas, ctx] = useCanvas2d(drawPlot);
	(0, import_react.useImperativeHandle)(ref, () => ({ frame: (val) => {
		if (min.current === void 0 || val < min.current) min.current = val;
		if (max.current === void 0 || val > max.current) max.current = val;
		push(points.current, val);
		raf.current = requestAnimationFrame(() => drawPlot(canvas.current, ctx.current));
	} }), [
		canvas,
		ctx,
		drawPlot
	]);
	(0, import_react.useEffect)(() => () => cancelAnimationFrame(raf.current), []);
	return import_react.createElement(Canvas, { ref: canvas });
});
var parse = (val) => Number.isFinite(val) ? val.toPrecision(2) : val.toString();
var MonitorLog = (0, import_react.forwardRef)(function({ initialValue }, ref) {
	const [val, set] = (0, import_react.useState)(parse(initialValue));
	(0, import_react.useImperativeHandle)(ref, () => ({ frame: (v) => set(parse(v)) }), []);
	return import_react.createElement("div", null, val);
});
function getValue(o) {
	return typeof o === "function" ? o() : o.current;
}
function Monitor({ label, objectOrFn, settings }) {
	const ref = (0, import_react.useRef)();
	const initialValue = (0, import_react.useRef)(getValue(objectOrFn));
	(0, import_react.useEffect)(() => {
		const timeout = window.setInterval(() => {
			var _ref$current;
			if (document.hidden) return;
			(_ref$current = ref.current) === null || _ref$current === void 0 || _ref$current.frame(getValue(objectOrFn));
		}, settings.interval);
		return () => window.clearInterval(timeout);
	}, [objectOrFn, settings.interval]);
	return import_react.createElement(Row, { input: true }, import_react.createElement(Label, { align: "top" }, label), settings.graph ? import_react.createElement(MonitorCanvas, {
		ref,
		initialValue: initialValue.current
	}) : import_react.createElement(MonitorLog, {
		ref,
		initialValue: initialValue.current
	}));
}
var _excluded$3 = [
	"type",
	"label",
	"key"
];
var specialComponents = {
	[SpecialInputs.BUTTON]: Button,
	[SpecialInputs.BUTTON_GROUP]: ButtonGroup,
	[SpecialInputs.MONITOR]: Monitor
};
var Control = import_react.memo(({ path }) => {
	const [input, { set, setSettings, disable, storeId, emitOnEditStart, emitOnEditEnd }] = useInput(path);
	if (!input) return null;
	const { type, label, key } = input, inputProps = _objectWithoutProperties$1(input, _excluded$3);
	if (type in SpecialInputs) {
		const SpecialInputForType = specialComponents[type];
		return import_react.createElement(SpecialInputForType, _extends({
			label,
			path
		}, inputProps));
	}
	if (!(type in Plugins)) {
		log(LevaErrors.UNSUPPORTED_INPUT, type, path);
		return null;
	}
	return import_react.createElement(ControlInput, _extends({
		key: storeId + path,
		type,
		label,
		storeId,
		path,
		valueKey: key,
		setValue: set,
		setSettings,
		disable,
		emitOnEditStart,
		emitOnEditEnd
	}, inputProps));
});
function FolderTitle({ toggle, toggled, name }) {
	return import_react.createElement(StyledTitle, { onClick: () => toggle() }, import_react.createElement(Chevron, { toggled }), import_react.createElement("div", null, name));
}
var Folder = ({ name, path, tree }) => {
	const store = useStoreContext();
	const newPath = join(path, name);
	const { collapsed, color } = store.getFolderSettings(newPath);
	const [toggled, setToggle] = (0, import_react.useState)(!collapsed);
	const folderRef = (0, import_react.useRef)(null);
	const widgetColor = useTh("colors", "folderWidgetColor");
	const textColor = useTh("colors", "folderTextColor");
	(0, import_react.useLayoutEffect)(() => {
		folderRef.current.style.setProperty("--leva-colors-folderWidgetColor", color || widgetColor);
		folderRef.current.style.setProperty("--leva-colors-folderTextColor", color || textColor);
	}, [
		color,
		widgetColor,
		textColor
	]);
	return import_react.createElement(StyledFolder, { ref: folderRef }, import_react.createElement(FolderTitle, {
		name,
		toggled,
		toggle: () => setToggle((t) => !t)
	}), import_react.createElement(TreeWrapper, {
		parent: newPath,
		tree,
		toggled
	}));
};
var TreeWrapper = import_react.memo(({ isRoot: _isRoot = false, fill: _fill = false, flat: _flat = false, parent, tree, toggled }) => {
	const { wrapperRef, contentRef } = useToggle(toggled);
	const store = useStoreContext();
	const getOrder = ([key, o]) => {
		var _store$getInput;
		return (isInput(o) ? (_store$getInput = store.getInput(o.path)) === null || _store$getInput === void 0 ? void 0 : _store$getInput.order : store.getFolderSettings(join(parent, key)).order) || 0;
	};
	const entries = Object.entries(tree).sort((a, b) => getOrder(a) - getOrder(b));
	return import_react.createElement(StyledWrapper, {
		ref: wrapperRef,
		isRoot: _isRoot,
		fill: _fill,
		flat: _flat
	}, import_react.createElement(StyledContent, {
		ref: contentRef,
		isRoot: _isRoot,
		toggled
	}, entries.map(([key, value]) => isInput(value) ? import_react.createElement(Control, {
		key: value.path,
		valueKey: value.valueKey,
		path: value.path
	}) : import_react.createElement(Folder, {
		key,
		name: key,
		path: parent,
		tree: value
	}))));
});
var StyledRoot = styled("div", {
	position: "relative",
	fontFamily: "$mono",
	fontSize: "$root",
	color: "$rootText",
	backgroundColor: "$elevation1",
	variants: {
		fill: {
			false: {
				position: "fixed",
				top: "10px",
				right: "10px",
				zIndex: 1e3,
				width: "$rootWidth"
			},
			true: {
				position: "relative",
				width: "100%"
			}
		},
		flat: { false: {
			borderRadius: "$lg",
			boxShadow: "$level1"
		} },
		oneLineLabels: { true: { [`${StyledInputRow}`]: {
			gridTemplateColumns: "auto",
			gridAutoColumns: "minmax(max-content, 1fr)",
			gridAutoRows: "minmax($sizes$rowHeight), auto)",
			rowGap: 0,
			columnGap: 0,
			marginTop: "$rowGap"
		} } },
		hideTitleBar: {
			true: { $$titleBarHeight: "0px" },
			false: { $$titleBarHeight: "$sizes$titleBarHeight" }
		}
	},
	"&,*,*:after,*:before": { boxSizing: "border-box" },
	"*::selection": { backgroundColor: "$accent2" }
});
var iconWidth = 40;
var Icon = styled("i", {
	$flexCenter: "",
	width: iconWidth,
	userSelect: "none",
	cursor: "pointer",
	"> svg": {
		fill: "$highlight1",
		transition: "transform 350ms ease, fill 250ms ease"
	},
	"&:hover > svg": { fill: "$highlight3" },
	variants: { active: { true: { "> svg": { fill: "$highlight2" } } } }
});
var StyledTitleWithFilter = styled("div", {
	display: "flex",
	alignItems: "stretch",
	justifyContent: "space-between",
	height: "$titleBarHeight",
	variants: { mode: { drag: { cursor: "grab" } } }
});
var FilterWrapper = styled("div", {
	$flex: "",
	position: "relative",
	width: "100%",
	overflow: "hidden",
	transition: "height 250ms ease",
	color: "$highlight3",
	paddingLeft: "$md",
	[`> ${Icon}`]: { height: 30 },
	variants: { toggled: {
		true: { height: 30 },
		false: { height: 0 }
	} }
});
var StyledFilterInput = styled("input", {
	$reset: "",
	flex: 1,
	position: "relative",
	height: 30,
	width: "100%",
	backgroundColor: "transparent",
	fontSize: "10px",
	borderRadius: "$root",
	"&:focus": {},
	"&::placeholder": { color: "$highlight2" }
});
var TitleContainer = styled("div", {
	touchAction: "none",
	$flexCenter: "",
	flex: 1,
	"> svg": { fill: "$highlight1" },
	color: "$highlight1",
	variants: {
		drag: { true: {
			$draggable: "",
			"> svg": { transition: "fill 250ms ease" },
			"&:hover": { color: "$highlight3" },
			"&:hover > svg": { fill: "$highlight3" }
		} },
		filterEnabled: { false: { paddingRight: iconWidth } }
	}
});
var FilterInput = import_react.forwardRef(({ setFilter, toggle }, ref) => {
	const [value, set] = (0, import_react.useState)("");
	const debouncedOnChange = (0, import_react.useMemo)(() => debounce(setFilter, 250), [setFilter]);
	const clear = () => {
		setFilter("");
		set("");
	};
	const _onChange = (e) => {
		const v = e.currentTarget.value;
		toggle(true);
		set(v);
	};
	(0, import_react.useEffect)(() => {
		debouncedOnChange(value);
	}, [value, debouncedOnChange]);
	return import_react.createElement(import_react.Fragment, null, import_react.createElement(StyledFilterInput, {
		ref,
		value,
		placeholder: "[Open filter with CMD+SHIFT+L]",
		onPointerDown: (e) => e.stopPropagation(),
		onChange: _onChange
	}), import_react.createElement(Icon, {
		onClick: () => clear(),
		style: { visibility: value ? "visible" : "hidden" }
	}, import_react.createElement("svg", {
		xmlns: "http://www.w3.org/2000/svg",
		height: "14",
		width: "14",
		viewBox: "0 0 20 20",
		fill: "currentColor"
	}, import_react.createElement("path", {
		fillRule: "evenodd",
		d: "M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z",
		clipRule: "evenodd"
	}))));
});
function TitleWithFilter({ setFilter, onDrag, onDragStart, onDragEnd, toggle, toggled, title, drag, filterEnabled, from }) {
	const [filterShown, setShowFilter] = (0, import_react.useState)(false);
	const inputRef = (0, import_react.useRef)(null);
	(0, import_react.useEffect)(() => {
		var _inputRef$current, _inputRef$current2;
		if (filterShown) (_inputRef$current = inputRef.current) === null || _inputRef$current === void 0 || _inputRef$current.focus();
		else (_inputRef$current2 = inputRef.current) === null || _inputRef$current2 === void 0 || _inputRef$current2.blur();
	}, [filterShown]);
	const bind = useDrag(({ offset: [x, y], first, last }) => {
		onDrag({
			x,
			y
		});
		if (first) onDragStart({
			x,
			y
		});
		if (last) onDragEnd({
			x,
			y
		});
	}, {
		filterTaps: true,
		from: ({ offset: [x, y] }) => [(from === null || from === void 0 ? void 0 : from.x) || x, (from === null || from === void 0 ? void 0 : from.y) || y]
	});
	(0, import_react.useEffect)(() => {
		const handleShortcut = (event) => {
			if (event.key === "L" && event.shiftKey && event.metaKey) setShowFilter((f) => !f);
		};
		window.addEventListener("keydown", handleShortcut);
		return () => window.removeEventListener("keydown", handleShortcut);
	}, []);
	return import_react.createElement(import_react.Fragment, null, import_react.createElement(StyledTitleWithFilter, { mode: drag ? "drag" : void 0 }, import_react.createElement(Icon, {
		active: !toggled,
		onClick: () => toggle()
	}, import_react.createElement(Chevron, {
		toggled,
		width: 12,
		height: 8
	})), import_react.createElement(TitleContainer, _extends({}, drag ? bind() : {}, {
		drag,
		filterEnabled
	}), title === void 0 && drag ? import_react.createElement("svg", {
		width: "20",
		height: "10",
		viewBox: "0 0 28 14",
		xmlns: "http://www.w3.org/2000/svg"
	}, import_react.createElement("circle", {
		cx: "2",
		cy: "2",
		r: "2"
	}), import_react.createElement("circle", {
		cx: "14",
		cy: "2",
		r: "2"
	}), import_react.createElement("circle", {
		cx: "26",
		cy: "2",
		r: "2"
	}), import_react.createElement("circle", {
		cx: "2",
		cy: "12",
		r: "2"
	}), import_react.createElement("circle", {
		cx: "14",
		cy: "12",
		r: "2"
	}), import_react.createElement("circle", {
		cx: "26",
		cy: "12",
		r: "2"
	})) : title), filterEnabled && import_react.createElement(Icon, {
		active: filterShown,
		onClick: () => setShowFilter((f) => !f)
	}, import_react.createElement("svg", {
		xmlns: "http://www.w3.org/2000/svg",
		height: "20",
		viewBox: "0 0 20 20"
	}, import_react.createElement("path", { d: "M9 9a2 2 0 114 0 2 2 0 01-4 0z" }), import_react.createElement("path", {
		fillRule: "evenodd",
		d: "M10 18a8 8 0 100-16 8 8 0 000 16zm1-13a4 4 0 00-3.446 6.032l-2.261 2.26a1 1 0 101.414 1.415l2.261-2.261A4 4 0 1011 5z",
		clipRule: "evenodd"
	})))), import_react.createElement(FilterWrapper, { toggled: filterShown }, import_react.createElement(FilterInput, {
		ref: inputRef,
		setFilter,
		toggle
	})));
}
var _excluded$2 = [
	"store",
	"hidden",
	"theme",
	"collapsed"
];
function LevaRoot(_ref) {
	let { store, hidden = false, theme, collapsed = false } = _ref, props = _objectWithoutProperties$1(_ref, _excluded$2);
	const themeContext = useDeepMemo(() => mergeTheme(theme), [theme]);
	const [toggled, setToggle] = (0, import_react.useState)(!collapsed);
	const computedToggled = typeof collapsed === "object" ? !collapsed.collapsed : toggled;
	const computedSetToggle = (0, import_react.useMemo)(() => {
		if (typeof collapsed === "object") return (value) => {
			if (typeof value === "function") collapsed.onChange(!value(!collapsed.collapsed));
			else collapsed.onChange(!value);
		};
		return setToggle;
	}, [collapsed]);
	if (!store || hidden) return null;
	return import_react.createElement(ThemeContext.Provider, { value: themeContext }, import_react.createElement(LevaCore, _extends({ store }, props, {
		toggled: computedToggled,
		setToggle: computedSetToggle,
		rootClass: themeContext.className
	})));
}
var LevaCore = import_react.memo(({ store, rootClass, fill: _fill = false, flat: _flat = false, neverHide: _neverHide = false, oneLineLabels: _oneLineLabels = false, titleBar: _titleBar = {
	title: void 0,
	drag: true,
	filter: true,
	position: void 0,
	onDrag: void 0,
	onDragStart: void 0,
	onDragEnd: void 0
}, hideCopyButton: _hideCopyButton = false, toggled, setToggle }) => {
	var _titleBar$drag, _titleBar$filter;
	const paths = useVisiblePaths(store);
	const [filter, setFilter] = (0, import_react.useState)("");
	const tree = (0, import_react.useMemo)(() => buildTree(paths, filter), [paths, filter]);
	const [rootRef, set] = useTransform();
	const shouldShow = _neverHide || paths.length > 0;
	const title = typeof _titleBar === "object" ? _titleBar.title || void 0 : void 0;
	const drag = typeof _titleBar === "object" ? (_titleBar$drag = _titleBar.drag) !== null && _titleBar$drag !== void 0 ? _titleBar$drag : true : true;
	const filterEnabled = typeof _titleBar === "object" ? (_titleBar$filter = _titleBar.filter) !== null && _titleBar$filter !== void 0 ? _titleBar$filter : true : true;
	const position = typeof _titleBar === "object" ? _titleBar.position || void 0 : void 0;
	const onDrag = typeof _titleBar === "object" ? _titleBar.onDrag || void 0 : void 0;
	const onDragStart = typeof _titleBar === "object" ? _titleBar.onDragStart || void 0 : void 0;
	const onDragEnd = typeof _titleBar === "object" ? _titleBar.onDragEnd || void 0 : void 0;
	import_react.useEffect(() => {
		set({
			x: position === null || position === void 0 ? void 0 : position.x,
			y: position === null || position === void 0 ? void 0 : position.y
		});
	}, [position, set]);
	globalStyles();
	return import_react.createElement(Provider, null, import_react.createElement(PanelSettingsContext.Provider, { value: { hideCopyButton: _hideCopyButton } }, import_react.createElement(StyledRoot, {
		ref: rootRef,
		className: rootClass,
		fill: _fill,
		flat: _flat,
		oneLineLabels: _oneLineLabels,
		hideTitleBar: !_titleBar,
		style: { display: shouldShow ? "block" : "none" }
	}, _titleBar && import_react.createElement(TitleWithFilter, {
		onDrag: (point) => {
			set(point);
			onDrag === null || onDrag === void 0 || onDrag(point);
		},
		onDragStart: (point) => onDragStart === null || onDragStart === void 0 ? void 0 : onDragStart(point),
		onDragEnd: (point) => onDragEnd === null || onDragEnd === void 0 ? void 0 : onDragEnd(point),
		setFilter,
		toggle: (flag) => setToggle((t) => flag !== null && flag !== void 0 ? flag : !t),
		toggled,
		title,
		drag,
		filterEnabled,
		from: position
	}), shouldShow && import_react.createElement(StoreContext.Provider, { value: store }, import_react.createElement(TreeWrapper, {
		isRoot: true,
		fill: _fill,
		flat: _flat,
		tree,
		toggled
	})))));
});
var _excluded$1 = ["isRoot"];
var rootInitialized = false;
var rootEl = null;
function Leva(_ref) {
	let { isRoot = false } = _ref, props = _objectWithoutProperties$1(_ref, _excluded$1);
	(0, import_react.useEffect)(() => {
		rootInitialized = true;
		if (!isRoot && rootEl) {
			rootEl.remove();
			rootEl = null;
		}
		return () => {
			if (!isRoot) rootInitialized = false;
		};
	}, [isRoot]);
	return import_react.createElement(LevaRoot, _extends({ store: levaStore }, props));
}
function useRenderRoot(isGlobalPanel) {
	(0, import_react.useEffect)(() => {
		if (isGlobalPanel && !rootInitialized) {
			if (!rootEl) {
				rootEl = document.getElementById("leva__root") || Object.assign(document.createElement("div"), { id: "leva__root" });
				if (document.body) {
					document.body.appendChild(rootEl);
					(0, import_client.createRoot)(rootEl).render(import_react.createElement(Leva, { isRoot: true }));
				}
			}
			rootInitialized = true;
		}
	}, [isGlobalPanel]);
}
function parseArgs(schemaOrFolderName, settingsOrDepsOrSchema, depsOrSettingsOrFolderSettings, depsOrSettings, depsOrUndefined) {
	let schema;
	let folderName = void 0;
	let folderSettings;
	let hookSettings;
	let deps;
	if (typeof schemaOrFolderName === "string") {
		folderName = schemaOrFolderName;
		schema = settingsOrDepsOrSchema;
		if (Array.isArray(depsOrSettingsOrFolderSettings)) deps = depsOrSettingsOrFolderSettings;
		else if (depsOrSettingsOrFolderSettings) if ("store" in depsOrSettingsOrFolderSettings) {
			hookSettings = depsOrSettingsOrFolderSettings;
			deps = depsOrSettings;
		} else {
			folderSettings = depsOrSettingsOrFolderSettings;
			if (Array.isArray(depsOrSettings)) deps = depsOrSettings;
			else {
				hookSettings = depsOrSettings;
				deps = depsOrUndefined;
			}
		}
	} else {
		schema = schemaOrFolderName;
		if (Array.isArray(settingsOrDepsOrSchema)) deps = settingsOrDepsOrSchema;
		else {
			hookSettings = settingsOrDepsOrSchema;
			deps = depsOrSettingsOrFolderSettings;
		}
	}
	return {
		schema,
		folderName,
		folderSettings,
		hookSettings,
		deps: deps || []
	};
}
function useControls(schemaOrFolderName, settingsOrDepsOrSchema, depsOrSettingsOrFolderSettings, depsOrSettings, depsOrUndefined) {
	const { folderName, schema, folderSettings, hookSettings, deps } = parseArgs(schemaOrFolderName, settingsOrDepsOrSchema, depsOrSettingsOrFolderSettings, depsOrSettings, depsOrUndefined);
	const schemaIsFunction = typeof schema === "function";
	const depsChanged = (0, import_react.useRef)(false);
	const firstRender = (0, import_react.useRef)(true);
	const _schema = useDeepMemo(() => {
		depsChanged.current = true;
		const s = typeof schema === "function" ? schema() : schema;
		return folderName ? { [folderName]: folder(s, folderSettings) } : s;
	}, deps);
	useRenderRoot(!(hookSettings !== null && hookSettings !== void 0 && hookSettings.store));
	const [store] = (0, import_react.useState)(() => (hookSettings === null || hookSettings === void 0 ? void 0 : hookSettings.store) || levaStore);
	const [initialData, mappedPaths] = (0, import_react.useMemo)(() => store.getDataFromSchema(_schema), [store, _schema]);
	const [allPaths, renderPaths, onChangePaths, onEditStartPaths, onEditEndPaths] = (0, import_react.useMemo)(() => {
		const allPaths = [];
		const renderPaths = [];
		const onChangePaths = {};
		const onEditStartPaths = {};
		const onEditEndPaths = {};
		Object.values(mappedPaths).forEach(({ path, onChange, onEditStart, onEditEnd, transient }) => {
			allPaths.push(path);
			if (!!onChange) {
				onChangePaths[path] = onChange;
				if (!transient) renderPaths.push(path);
			} else renderPaths.push(path);
			if (onEditStart) onEditStartPaths[path] = onEditStart;
			if (onEditEnd) onEditEndPaths[path] = onEditEnd;
		});
		return [
			allPaths,
			renderPaths,
			onChangePaths,
			onEditStartPaths,
			onEditEndPaths
		];
	}, [mappedPaths]);
	const paths = (0, import_react.useMemo)(() => store.orderPaths(allPaths), [allPaths, store]);
	const values = useValuesForPath(store, renderPaths, initialData);
	const set = (0, import_react.useCallback)((values) => {
		const _values = Object.entries(values).reduce((acc, [p, v]) => Object.assign(acc, { [mappedPaths[p].path]: v }), {});
		store.set(_values, false);
	}, [store, mappedPaths]);
	const get = (0, import_react.useCallback)((path) => store.get(mappedPaths[path].path), [store, mappedPaths]);
	(0, import_react.useEffect)(() => {
		const shouldOverrideSettings = !firstRender.current && depsChanged.current;
		store.addData(initialData, shouldOverrideSettings);
		firstRender.current = false;
		depsChanged.current = false;
		return () => store.disposePaths(paths);
	}, [
		store,
		paths,
		initialData
	]);
	(0, import_react.useEffect)(() => {
		const unsubscriptions = [];
		Object.entries(onChangePaths).forEach(([path, onChange]) => {
			onChange(store.get(path), path, _objectSpread2({
				initial: true,
				get: store.get
			}, store.getInput(path)));
			const unsub = store.useStore.subscribe((s) => {
				const input = s.data[path];
				return [input.disabled ? void 0 : input.value, input];
			}, ([value, input]) => onChange(value, path, _objectSpread2({
				initial: false,
				get: store.get
			}, input)), { equalityFn: shallow });
			unsubscriptions.push(unsub);
		});
		return () => unsubscriptions.forEach((unsub) => unsub());
	}, [store, onChangePaths]);
	(0, import_react.useEffect)(() => {
		const unsubscriptions = [];
		Object.entries(onEditStartPaths).forEach(([path, onEditStart]) => unsubscriptions.push(store.subscribeToEditStart(path, onEditStart)));
		Object.entries(onEditEndPaths).forEach(([path, onEditEnd]) => unsubscriptions.push(store.subscribeToEditEnd(path, onEditEnd)));
		return () => unsubscriptions.forEach((unsub) => unsub());
	}, [
		onEditStartPaths,
		onEditEndPaths,
		store
	]);
	if (schemaIsFunction) return [
		values,
		set,
		get
	];
	return values;
}
register(LevaInputs.SELECT, select);
register(LevaInputs.IMAGE, image);
register(LevaInputs.NUMBER, number$1);
register(LevaInputs.COLOR, color);
register(LevaInputs.STRING, string);
register(LevaInputs.BOOLEAN, boolean);
register(LevaInputs.INTERVAL, interval);
register(LevaInputs.VECTOR3D, vector3d);
register(LevaInputs.VECTOR2D, vector2d);
//#endregion
//#region src/components/BackdropLeva.tsx
var import_jsx_runtime = require_jsx_runtime();
var BLEND_MODES = [
	"normal",
	"multiply",
	"screen",
	"overlay",
	"darken",
	"lighten",
	"color-dodge",
	"color-burn",
	"hard-light",
	"soft-light",
	"difference",
	"exclusion",
	"hue",
	"saturation",
	"color",
	"luminosity"
];
function BackdropLeva() {
	const shape = useControls("UI / Shape", { radiusScalar: {
		value: .2,
		min: 0,
		max: 2,
		step: .1,
		label: "radius scalar"
	} }, { collapsed: true });
	const statue = useControls("Backdrop / Statue", {
		enabled: {
			value: true,
			label: "on"
		},
		opacity: {
			value: .025,
			min: 0,
			max: 1,
			step: .005
		},
		blendMode: {
			value: "difference",
			options: [...BLEND_MODES],
			label: "blend"
		},
		invert: {
			value: true,
			label: "invert color"
		},
		saturate: {
			value: 1,
			min: 0,
			max: 3,
			step: .05,
			label: "saturate"
		},
		brightness: {
			value: 1,
			min: 0,
			max: 2,
			step: .05,
			label: "brightness"
		},
		objectPosition: {
			value: "top left",
			options: [
				"top left",
				"top right",
				"bottom left",
				"bottom right",
				"center",
				"top",
				"bottom",
				"left",
				"right"
			],
			label: "position"
		},
		scale: {
			value: 160,
			min: 100,
			max: 300,
			step: 5,
			label: "height (dvh)"
		}
	}, { collapsed: true });
	(0, import_react.useEffect)(() => {
		$radiusScalar.set(shape.radiusScalar);
	}, [shape.radiusScalar]);
	(0, import_react.useEffect)(() => {
		$backdropSettings.set({
			enabled: statue.enabled,
			opacity: statue.opacity,
			blendMode: statue.blendMode,
			invert: statue.invert,
			saturate: statue.saturate,
			brightness: statue.brightness,
			objectPosition: statue.objectPosition,
			scale: statue.scale
		});
	}, [statue]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Leva, {
		collapsed: true,
		hidden: true,
		titleBar: {
			title: "backdrop",
			drag: true
		}
	});
}
//#endregion
export { BackdropLeva as default };
