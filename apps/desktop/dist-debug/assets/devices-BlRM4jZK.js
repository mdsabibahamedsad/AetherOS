import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { An as Dialog, C as Select, D as SelectValue, Di as notify, E as SelectTrigger, Fn as DialogTitle, Ia as Codicon, La as Button, Mn as DialogDescription, Nn as DialogFooter, O as Badge, Pn as DialogHeader, Qa as atom, Ra as cn, T as SelectItem, Xa as init_nanostores, Ya as useStore, ao as require_jsx_runtime, jn as DialogContent, ni as Input, oo as require_react, vt as SearchField, w as SelectContent } from "./index-B_yd1pEX.js";
import { i as PageTitle, n as PageHeader, r as PageShell, t as PageDescription } from "./page-shell-DlpGsnrD.js";
//#region src/store/devices.ts
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
init_nanostores();
function detectOS() {
	const platform = typeof navigator !== "undefined" ? navigator.platform.toLowerCase() : "";
	if (platform.includes("mac")) return "macos";
	if (platform.includes("linux")) return "linux";
	return "windows";
}
var CURRENT_DEVICE = {
	id: "device-current",
	name: "This Device",
	os: detectOS(),
	osVersion: "",
	appVersion: "",
	lastActive: (/* @__PURE__ */ new Date()).toISOString(),
	online: true,
	syncStatus: "offline",
	isCurrent: true,
	ipAddress: "",
	registeredAt: (/* @__PURE__ */ new Date()).toISOString()
};
var $devices = /* @__PURE__ */ atom([CURRENT_DEVICE]);
var $currentDevice = /* @__PURE__ */ atom(CURRENT_DEVICE);
var $deviceLoading = /* @__PURE__ */ atom(false);
var $deviceSearch = /* @__PURE__ */ atom("");
var $deviceFilterOS = /* @__PURE__ */ atom(null);
function revokeDevice(deviceId) {
	if ($currentDevice.get().id === deviceId) return;
	$devices.set($devices.get().filter((d) => d.id !== deviceId));
}
function renameDevice(deviceId, name) {
	$devices.set($devices.get().map((d) => d.id === deviceId ? {
		...d,
		name
	} : d));
}
function setDeviceSearch(search) {
	$deviceSearch.set(search);
}
function setDeviceFilterOS(os) {
	$deviceFilterOS.set(os);
}
//#endregion
//#region src/app/devices/index.tsx
var import_jsx_runtime = require_jsx_runtime();
var OS_OPTIONS = [
	{
		value: "all",
		label: "All OS",
		icon: "symbol-misc"
	},
	{
		value: "windows",
		label: "Windows",
		icon: "symbol-misc"
	},
	{
		value: "macos",
		label: "macOS",
		icon: "symbol-misc"
	},
	{
		value: "linux",
		label: "Linux",
		icon: "symbol-misc"
	},
	{
		value: "ios",
		label: "iOS",
		icon: "symbol-misc"
	},
	{
		value: "android",
		label: "Android",
		icon: "symbol-misc"
	},
	{
		value: "web",
		label: "Web",
		icon: "symbol-misc"
	}
];
function DevicesView() {
	const devices = useStore($devices);
	const loading = useStore($deviceLoading);
	const search = useStore($deviceSearch);
	const filterOS = useStore($deviceFilterOS);
	const [renameDialog, setRenameDialog] = (0, import_react.useState)(null);
	const [renameName, setRenameName] = (0, import_react.useState)("");
	const [revokeConfirm, setRevokeConfirm] = (0, import_react.useState)(null);
	const filteredDevices = (0, import_react.useMemo)(() => {
		const q = search.trim().toLowerCase();
		return devices.filter((d) => {
			if (filterOS && d.os !== filterOS) return false;
			if (q && !d.name.toLowerCase().includes(q) && !d.os.toLowerCase().includes(q)) return false;
			return true;
		});
	}, [
		devices,
		search,
		filterOS
	]);
	const handleRename = (0, import_react.useCallback)((device) => {
		setRenameDialog(device);
		setRenameName(device.name);
	}, []);
	const handleRenameConfirm = (0, import_react.useCallback)(() => {
		if (!renameDialog || !renameName.trim()) return;
		renameDevice(renameDialog.id, renameName.trim());
		setRenameDialog(null);
		notify({
			kind: "success",
			title: "Device Renamed",
			message: `Device renamed to "${renameName.trim()}"`
		});
	}, [renameDialog, renameName]);
	const handleRevoke = (0, import_react.useCallback)((device) => {
		setRevokeConfirm(device);
	}, []);
	const handleRevokeConfirm = (0, import_react.useCallback)(() => {
		if (!revokeConfirm) return;
		revokeDevice(revokeConfirm.id);
		setRevokeConfirm(null);
		notify({
			kind: "success",
			title: "Device Revoked",
			message: `${revokeConfirm.name} has been revoked`
		});
	}, [revokeConfirm]);
	const handleRevokeCancel = (0, import_react.useCallback)(() => {
		setRevokeConfirm(null);
	}, []);
	const syncStatusColor = (status) => {
		switch (status) {
			case "synced": return "text-emerald-500";
			case "syncing": return "text-primary";
			case "pending": return "text-amber-500";
			case "error": return "text-destructive";
			case "offline": return "text-muted-foreground";
		}
	};
	if (loading) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageShell, {
		header: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageHeader, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, { children: "Devices" }) }),
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "grid min-h-52 place-items-center",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
				className: "animate-spin text-muted-foreground",
				name: "sync",
				size: "1.5rem"
			})
		})
	});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(PageShell, {
		header: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageHeader, {
			className: "w-full",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageTitle, { children: "Devices" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageDescription, { children: "Local device registry — rename and revoke manage this machine's entries" })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
						className: "text-muted-foreground",
						name: "device-desktop",
						size: "1rem"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
						className: "text-xs text-muted-foreground",
						children: [
							devices.length,
							" device",
							devices.length !== 1 ? "s" : ""
						]
					})]
				})]
			})
		}),
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SearchField, {
					containerClassName: "flex-1 max-w-xs",
					onChange: (v) => setDeviceSearch(v),
					placeholder: "Search devices...",
					value: search
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
					onValueChange: (v) => setDeviceFilterOS(v === "all" ? null : v),
					value: filterOS ?? "all",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
						className: "h-8 w-32 text-xs",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectContent, { children: OS_OPTIONS.map((opt) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
						value: opt.value,
						children: opt.label
					}, opt.value)) })]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3",
				children: filteredDevices.map((device) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: cn("group relative flex flex-col rounded-xl border bg-(--ui-chat-surface-background) p-4 transition-all hover:shadow-sm", device.isCurrent ? "border-primary/40 ring-1 ring-primary/20" : "border-(--ui-stroke-tertiary) hover:border-(--ui-stroke-secondary)"),
					children: [
						device.isCurrent && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
							className: "absolute right-2.5 top-2.5 text-[0.55rem]",
							variant: "default",
							children: "Current"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "flex items-start justify-between",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center gap-3",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary",
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
										name: "device-desktop",
										size: "1.1rem"
									})
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
									className: "text-sm font-medium",
									children: device.name
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
									className: "mt-0.5 flex items-center gap-1.5 text-[0.6rem] text-muted-foreground",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: "capitalize",
										children: [device.os, device.osVersion ? ` ${device.osVersion}` : ""]
									}), device.appVersion ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: "·" }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: ["v", device.appVersion] })] }) : null]
								})] })]
							})
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "mt-3 flex items-center gap-3 text-[0.65rem] text-muted-foreground",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
								className: cn("flex items-center gap-1", device.online ? "text-emerald-500" : "text-muted-foreground"),
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									name: "circle-filled",
									size: "0.5rem"
								}), device.online ? "Online" : "Offline"]
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
								className: cn("flex items-center gap-1", syncStatusColor(device.syncStatus)),
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
									name: "sync",
									size: "0.65rem"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "capitalize",
									children: device.syncStatus
								})]
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
							className: "mt-1.5 text-[0.6rem] text-muted-foreground",
							children: ["Last active: ", new Date(device.lastActive).toLocaleString()]
						}),
						!device.isCurrent && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "mt-3 flex items-center gap-2 border-t border-(--ui-stroke-tertiary) pt-3",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								className: "flex-1 text-xs",
								onClick: () => handleRename(device),
								size: "sm",
								variant: "outline",
								children: "Rename"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								className: "flex-1 text-xs text-muted-foreground hover:text-destructive",
								onClick: () => handleRevoke(device),
								size: "sm",
								variant: "ghost",
								children: "Revoke"
							})]
						})
					]
				}, device.id))
			}),
			filteredDevices.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "mt-8 grid min-h-40 place-items-center",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "text-center",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
							className: "text-muted-foreground/40",
							name: "search",
							size: "2rem"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-2 text-sm text-muted-foreground",
							children: "No devices found"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-xs text-muted-foreground/60",
							children: "Try a different search or filter"
						})
					]
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Dialog, {
				onOpenChange: (v) => {
					if (!v) setRenameDialog(null);
				},
				open: renameDialog !== null,
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogContent, { children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogHeader, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogTitle, { children: "Rename Device" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogDescription, { children: "Enter a new name for this device" })] }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						onChange: (e) => setRenameName(e.target.value),
						onKeyDown: (e) => {
							if (e.key === "Enter") handleRenameConfirm();
						},
						placeholder: "Device name",
						value: renameName
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogFooter, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						onClick: () => setRenameDialog(null),
						size: "sm",
						variant: "outline",
						children: "Cancel"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						disabled: !renameName.trim(),
						onClick: handleRenameConfirm,
						size: "sm",
						children: "Rename"
					})] })
				] })
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Dialog, {
				onOpenChange: (v) => {
					if (!v) setRevokeConfirm(null);
				},
				open: revokeConfirm !== null,
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogContent, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogHeader, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogTitle, { children: "Revoke Device" }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogDescription, { children: [
					"Are you sure you want to revoke ",
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("strong", { children: revokeConfirm?.name }),
					"? This will remove its access to your AetherOS instance."
				] })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogFooter, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: handleRevokeCancel,
					size: "sm",
					variant: "outline",
					children: "Cancel"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					onClick: handleRevokeConfirm,
					size: "sm",
					variant: "destructive",
					children: "Revoke"
				})] })] })
			})
		]
	});
}
//#endregion
export { DevicesView };
