import { C as Select, D as SelectValue, E as SelectTrigger, P as Switch, Qa as atom, T as SelectItem, Xa as init_nanostores, Ya as useStore, ao as require_jsx_runtime, w as SelectContent } from "./index-B_yd1pEX.js";
//#region src/store/accessibility-store.ts
init_nanostores();
var $accessibility = /* @__PURE__ */ atom({
	screenReaderEnabled: false,
	keyboardNavigationEnabled: true,
	highContrastEnabled: false,
	contrastMode: "normal",
	fontSize: "normal",
	customFontSize: 16,
	largeFontsEnabled: false,
	captionsEnabled: false,
	captionStyle: "default",
	voiceNavigationEnabled: false,
	reduceMotion: false,
	reduceTransparency: false,
	focusIndicatorEnabled: true,
	focusIndicatorWidth: 2,
	announcementVolume: .7,
	stickyKeys: false,
	slowKeys: false,
	bounceKeys: false,
	toggleKeys: false,
	typingFeedback: "off"
});
var patch = (u) => $accessibility.set({
	...$accessibility.get(),
	...u
});
function setScreenReaderEnabled(e) {
	patch({ screenReaderEnabled: e });
}
function setKeyboardNavigationEnabled(e) {
	patch({ keyboardNavigationEnabled: e });
}
function setHighContrastEnabled(e) {
	patch({ highContrastEnabled: e });
}
function setContrastMode(m) {
	patch({ contrastMode: m });
}
function setFontSize(s) {
	patch({ fontSize: s });
}
function setCustomFontSize(s) {
	patch({ customFontSize: s });
}
function setLargeFontsEnabled(e) {
	patch({ largeFontsEnabled: e });
}
function setCaptionsEnabled(e) {
	patch({ captionsEnabled: e });
}
function setCaptionStyle(s) {
	patch({ captionStyle: s });
}
function setVoiceNavigationEnabled(e) {
	patch({ voiceNavigationEnabled: e });
}
function setReduceMotion(r) {
	patch({ reduceMotion: r });
}
function setReduceTransparency(r) {
	patch({ reduceTransparency: r });
}
function setFocusIndicatorEnabled(e) {
	patch({ focusIndicatorEnabled: e });
}
function setFocusIndicatorWidth(w) {
	patch({ focusIndicatorWidth: w });
}
function setAnnouncementVolume(v) {
	patch({ announcementVolume: v });
}
//#endregion
//#region src/app/settings/accessibility-settings.tsx
var import_jsx_runtime = require_jsx_runtime();
function RangeSlider({ value, min, max, step, onChange, label }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex items-center gap-3",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
			className: "h-1.5 w-full cursor-pointer appearance-none rounded-full bg-(--ui-bg-tertiary) accent-[#00D4FF]",
			max,
			min,
			onChange: (e) => onChange(Number(e.target.value)),
			step,
			type: "range",
			value
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
			className: "min-w-8 text-right text-xs text-(--ui-text-secondary)",
			children: [value, label]
		})]
	});
}
function AccessibilitySettings() {
	const state = useStore($accessibility);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-col gap-6",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "text-lg font-semibold",
				children: "Accessibility"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-sm text-(--ui-text-tertiary)",
				children: "Configure accessibility features for screen readers, vision, hearing, and mobility"
			})] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
				className: "flex flex-col gap-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
						className: "text-sm font-medium text-(--ui-text-secondary)",
						children: "Vision"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "Screen Reader"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)",
							children: "Enable screen reader support"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: state.screenReaderEnabled,
							onCheckedChange: setScreenReaderEnabled
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "High Contrast"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)",
							children: "Increase visual contrast"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: state.highContrastEnabled,
							onCheckedChange: setHighContrastEnabled
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "Contrast Mode"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)",
							children: "Color contrast preset"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
							onValueChange: (v) => setContrastMode(v),
							value: state.contrastMode,
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
								className: "w-36",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SelectContent, { children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "normal",
									children: "Normal"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "high",
									children: "High Contrast"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "dark",
									children: "Dark Mode"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "light",
									children: "Light Mode"
								})
							] })]
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "Font Size"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)",
							children: "UI text size"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
							onValueChange: (v) => setFontSize(v),
							value: state.fontSize,
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
								className: "w-28",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SelectContent, { children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "small",
									children: "Small"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "normal",
									children: "Normal"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "large",
									children: "Large"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "xlarge",
									children: "X-Large"
								})
							] })]
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "Large Fonts"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)",
							children: "Use larger text everywhere"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: state.largeFontsEnabled,
							onCheckedChange: setLargeFontsEnabled
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "Custom Font Size"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)}",
							children: "Base font size in pixels"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "w-32",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(RangeSlider, {
								label: "px",
								max: 24,
								min: 12,
								onChange: setCustomFontSize,
								step: 1,
								value: state.customFontSize
							})
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "Reduce Motion"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)",
							children: "Minimize animations"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: state.reduceMotion,
							onCheckedChange: setReduceMotion
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "Reduce Transparency"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)",
							children: "Reduce transparent elements"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: state.reduceTransparency,
							onCheckedChange: setReduceTransparency
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "Focus Indicator"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)",
							children: "Show keyboard focus ring"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: state.focusIndicatorEnabled,
							onCheckedChange: setFocusIndicatorEnabled
						})]
					}),
					state.focusIndicatorEnabled && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "Focus Width"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)}",
							children: "Focus indicator thickness"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "w-32",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(RangeSlider, {
								label: "px",
								max: 6,
								min: 1,
								onChange: setFocusIndicatorWidth,
								step: 1,
								value: state.focusIndicatorWidth
							})
						})]
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
				className: "flex flex-col gap-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
						className: "text-sm font-medium text-(--ui-text-secondary)",
						children: "Hearing"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "Captions"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)",
							children: "Show captions for audio content"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: state.captionsEnabled,
							onCheckedChange: setCaptionsEnabled
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "Caption Style"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)",
							children: "Caption appearance"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
							onValueChange: (v) => setCaptionStyle(v),
							value: state.captionStyle,
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
								className: "w-36",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SelectContent, { children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "default",
									children: "Default"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "large",
									children: "Large"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "high_contrast",
									children: "High Contrast"
								})
							] })]
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "Announcement Volume"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)}",
							children: "Volume for screen reader"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "w-32",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(RangeSlider, {
								label: "",
								max: 1,
								min: 0,
								onChange: setAnnouncementVolume,
								step: .1,
								value: state.announcementVolume
							})
						})]
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
				className: "flex flex-col gap-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
						className: "text-sm font-medium text-(--ui-text-secondary)",
						children: "Mobility & Navigation"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "Keyboard Navigation"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)",
							children: "Full keyboard navigation support"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: state.keyboardNavigationEnabled,
							onCheckedChange: setKeyboardNavigationEnabled
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "Voice Navigation"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)",
							children: "Navigate using voice commands"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: state.voiceNavigationEnabled,
							onCheckedChange: setVoiceNavigationEnabled
						})]
					})
				]
			})
		]
	});
}
//#endregion
export { AccessibilitySettings };
