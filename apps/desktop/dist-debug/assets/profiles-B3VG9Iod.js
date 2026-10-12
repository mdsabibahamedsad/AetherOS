import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { t as IconDeviceFloppy } from "./IconDeviceFloppy-DF2vDv8v.js";
import { C as getProfileSetupCommand, I as renameProfile, T as getProfiles, i as createProfile, s as deleteProfile, st as updateProfileSoul, w as getProfileSoul } from "./aetheros-DF_uJq_t.js";
import { Aa as IconAlertTriangle, An as Dialog, Di as notify, Fn as DialogTitle, Hi as IconTrash, La as Button, Mn as DialogDescription, Nn as DialogFooter, Oi as notifyError, Pn as DialogHeader, Ra as cn, Vi as IconUsers, Wi as IconTerminal2, ao as require_jsx_runtime, bt as PageLoader, ea as IconPencil, jn as DialogContent, jt as Textarea, ki as useI18n, ni as Input, oo as require_react } from "./index-B_yd1pEX.js";
import { t as OverlayView } from "./overlay-view-DLw12qQQ.js";
import { t as useRefreshHotkey } from "./use-refresh-hotkey-CjSQqOti.js";
import { a as OverlaySplitLayout, i as OverlaySidebar, r as OverlayNewButton, t as OverlayMain } from "./overlay-split-layout-DUaHa8tB.js";
//#region src/app/profiles/index.tsx
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
var PROFILE_NAME_RE = /^[a-z0-9][a-z0-9_-]{0,63}$/;
function isValidProfileName(name) {
	return PROFILE_NAME_RE.test(name.trim());
}
function ProfilesView({ onClose }) {
	const { t } = useI18n();
	const p = t.profiles;
	const [profiles, setProfiles] = (0, import_react.useState)(null);
	const [selectedName, setSelectedName] = (0, import_react.useState)(null);
	const [createOpen, setCreateOpen] = (0, import_react.useState)(false);
	const [pendingDelete, setPendingDelete] = (0, import_react.useState)(null);
	const [deleting, setDeleting] = (0, import_react.useState)(false);
	const refresh = (0, import_react.useCallback)(async () => {
		try {
			const { profiles: list } = await getProfiles();
			setProfiles(list);
			setSelectedName((current) => {
				if (current && list.some((p) => p.name === current)) return current;
				return list.find((p) => p.is_default)?.name ?? list[0]?.name ?? null;
			});
		} catch (err) {
			notifyError(err, p.failedLoad);
		}
	}, [p]);
	useRefreshHotkey(refresh);
	(0, import_react.useEffect)(() => {
		refresh();
	}, [refresh]);
	const selected = (0, import_react.useMemo)(() => {
		if (!profiles) return null;
		return profiles.find((p) => p.name === selectedName) ?? profiles[0] ?? null;
	}, [profiles, selectedName]);
	const handleCreate = (0, import_react.useCallback)(async (name, cloneFromDefault) => {
		const trimmed = name.trim();
		if (!isValidProfileName(trimmed)) throw new Error(p.nameHint);
		await createProfile({
			name: trimmed,
			clone_from_default: cloneFromDefault
		});
		notify({
			kind: "success",
			title: p.created,
			message: trimmed
		});
		setSelectedName(trimmed);
		await refresh();
	}, [p, refresh]);
	const handleRename = (0, import_react.useCallback)(async (from, to) => {
		const target = to.trim();
		if (target === from) return;
		if (!isValidProfileName(target)) throw new Error(p.nameHint);
		await renameProfile(from, target);
		notify({
			kind: "success",
			title: p.renamed,
			message: `${from} → ${target}`
		});
		setSelectedName(target);
		await refresh();
	}, [p, refresh]);
	const handleConfirmDelete = (0, import_react.useCallback)(async () => {
		if (!pendingDelete) return;
		setDeleting(true);
		try {
			await deleteProfile(pendingDelete.name);
			notify({
				kind: "success",
				title: p.deleted,
				message: pendingDelete.name
			});
			setPendingDelete(null);
			setSelectedName(null);
			await refresh();
		} catch (err) {
			notifyError(err, p.failedDelete);
		} finally {
			setDeleting(false);
		}
	}, [
		p,
		pendingDelete,
		refresh
	]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(OverlayView, {
		closeLabel: p.close,
		onClose,
		children: [
			!profiles ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageLoader, { label: p.loading }) : /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(OverlaySplitLayout, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(OverlaySidebar, { children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(OverlayNewButton, {
					label: p.newProfile,
					onClick: () => setCreateOpen(true)
				}),
				profiles.map((profile) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ProfileRow, {
					active: selected?.name === profile.name,
					onSelect: () => setSelectedName(profile.name),
					profile
				}, profile.name)),
				profiles.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "px-2 py-4 text-center text-xs text-muted-foreground",
					children: p.noProfiles
				})
			] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(OverlayMain, {
				className: "px-0",
				children: selected ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ProfileDetail, {
					onDelete: () => setPendingDelete(selected),
					onRename: (newName) => handleRename(selected.name, newName),
					profile: selected
				}, selected.name) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "grid h-full place-items-center px-6 py-12 text-center text-sm text-muted-foreground",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconUsers, { className: "mx-auto size-6 text-muted-foreground/60" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-3",
						children: p.selectPrompt
					})] })
				})
			})] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CreateProfileDialog, {
				onClose: () => setCreateOpen(false),
				onCreate: async (name, cloneFromDefault) => handleCreate(name, cloneFromDefault),
				open: createOpen
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Dialog, {
				onOpenChange: (open) => !open && !deleting && setPendingDelete(null),
				open: pendingDelete !== null,
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogContent, {
					className: "max-w-md",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogHeader, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogTitle, { children: p.deleteTitle }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogDescription, { children: pendingDelete ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
						p.deleteDescPrefix,
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "font-medium text-foreground",
							children: pendingDelete.name
						}),
						p.deleteDescMid,
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "font-mono text-xs",
							children: pendingDelete.path
						}),
						p.deleteDescSuffix
					] }) : null })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogFooter, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						disabled: deleting,
						onClick: () => setPendingDelete(null),
						variant: "outline",
						children: t.common.cancel
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						disabled: deleting,
						onClick: () => void handleConfirmDelete(),
						variant: "destructive",
						children: deleting ? p.deleting : t.common.delete
					})] })]
				})
			})
		]
	});
}
function ProfileRow({ active, onSelect, profile }) {
	const { t } = useI18n();
	const p = t.profiles;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
		className: cn("flex w-full flex-col items-start gap-0.5 rounded-md px-2 py-1.5 text-left transition-colors", active ? "bg-accent text-foreground" : "text-foreground/85 hover:bg-accent/60"),
		onClick: onSelect,
		type: "button",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
			className: "flex w-full items-center justify-between gap-2",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "truncate text-sm font-medium",
				children: profile.name
			}), profile.is_default && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "text-[0.6rem] text-primary",
				children: p.default
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
			className: "text-[0.66rem] text-muted-foreground",
			children: [p.skills(profile.skill_count), profile.has_env ? ` · ${p.env}` : ""]
		})]
	});
}
function ProfileDetail({ onDelete, onRename, profile }) {
	const { t } = useI18n();
	const p = t.profiles;
	const [renameOpen, setRenameOpen] = (0, import_react.useState)(false);
	const [copying, setCopying] = (0, import_react.useState)(false);
	const handleCopySetup = (0, import_react.useCallback)(async () => {
		setCopying(true);
		try {
			const { command } = await getProfileSetupCommand(profile.name);
			await navigator.clipboard.writeText(command);
			notify({
				kind: "success",
				title: p.setupCopied,
				message: command
			});
		} catch (err) {
			notifyError(err, p.failedCopy);
		} finally {
			setCopying(false);
		}
	}, [p, profile.name]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full min-h-0 flex-col",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "min-h-0 flex-1 overflow-y-auto",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mx-auto max-w-2xl space-y-6 px-6 py-6",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", {
					className: "space-y-3",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex flex-wrap items-start justify-between gap-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "min-w-0",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex flex-wrap items-center gap-2",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
										className: "text-xl font-semibold tracking-tight",
										children: profile.name
									}),
									profile.is_default && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "rounded-full bg-primary/10 px-2 py-0.5 text-[0.65rem] font-medium text-primary",
										children: p.defaultBadge
									}),
									profile.has_env && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "rounded-full bg-muted px-2 py-0.5 text-[0.65rem] font-medium text-muted-foreground",
										children: ".env"
									})
								]
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "mt-1 font-mono text-[0.7rem] text-muted-foreground",
								title: profile.path,
								children: profile.path
							})]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex shrink-0 items-center gap-1",
							children: [
								!profile.is_default && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
									onClick: () => setRenameOpen(true),
									size: "sm",
									variant: "outline",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconPencil, {}), p.rename]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
									disabled: copying,
									onClick: () => void handleCopySetup(),
									size: "sm",
									variant: "outline",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconTerminal2, {}), copying ? p.copying : p.copySetup]
								}),
								!profile.is_default && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
									className: "text-muted-foreground hover:bg-destructive/10 hover:text-destructive",
									onClick: onDelete,
									size: "sm",
									variant: "ghost",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconTrash, {}), t.common.delete]
								})
							]
						})]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("dl", {
						className: "grid gap-2 text-xs sm:grid-cols-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DetailRow, {
							label: p.modelLabel,
							children: profile.model ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "font-mono",
								children: profile.model
							}), profile.provider && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
								className: "text-muted-foreground",
								children: [" · ", profile.provider]
							})] }) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "text-muted-foreground",
								children: p.notSet
							})
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DetailRow, {
							label: p.skillsLabel,
							children: profile.skill_count
						})]
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SoulEditor, { profileName: profile.name })]
			})
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(RenameProfileDialog, {
			currentName: profile.name,
			onClose: () => setRenameOpen(false),
			onRename: async (newName) => {
				await onRename(newName);
				setRenameOpen(false);
			},
			open: renameOpen
		})]
	});
}
function DetailRow({ children, label }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-wrap items-baseline gap-2",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("dt", {
			className: "text-[0.65rem] font-semibold uppercase tracking-[0.12em] text-muted-foreground",
			children: label
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("dd", {
			className: "text-sm text-foreground",
			children
		})]
	});
}
function SoulEditor({ profileName }) {
	const { t } = useI18n();
	const p = t.profiles;
	const [content, setContent] = (0, import_react.useState)("");
	const [original, setOriginal] = (0, import_react.useState)("");
	const [loading, setLoading] = (0, import_react.useState)(true);
	const [saving, setSaving] = (0, import_react.useState)(false);
	const [error, setError] = (0, import_react.useState)(null);
	const requestRef = (0, import_react.useRef)(profileName);
	(0, import_react.useEffect)(() => {
		requestRef.current = profileName;
		setLoading(true);
		setError(null);
		setContent("");
		setOriginal("");
		(async () => {
			try {
				const soul = await getProfileSoul(profileName);
				if (requestRef.current === profileName) {
					setContent(soul.content);
					setOriginal(soul.content);
				}
			} catch (err) {
				if (requestRef.current === profileName) setError(err instanceof Error ? err.message : p.failedLoadSoul);
			} finally {
				if (requestRef.current === profileName) setLoading(false);
			}
		})();
	}, [p, profileName]);
	const dirty = content !== original;
	const isEmpty = !content.trim();
	async function handleSave() {
		setSaving(true);
		setError(null);
		try {
			await updateProfileSoul(profileName, content);
			setOriginal(content);
			notify({
				kind: "success",
				title: p.soulSaved,
				message: profileName
			});
		} catch (err) {
			setError(err instanceof Error ? err.message : p.failedSaveSoul);
		} finally {
			setSaving(false);
		}
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
		className: "space-y-2",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-wrap items-baseline justify-between gap-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h4", {
					className: "text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-muted-foreground",
					children: "SOUL.md"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-xs text-muted-foreground",
					children: p.soulDesc
				})] }), dirty && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "text-[0.65rem] text-muted-foreground",
					children: p.unsavedChanges
				})]
			}),
			loading ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageLoader, {
				className: "min-h-44",
				label: p.loadingSoul
			}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Textarea, {
				className: "min-h-72 font-mono text-xs leading-5",
				onChange: (event) => setContent(event.target.value),
				placeholder: isEmpty ? p.emptySoul : void 0,
				value: content
			}),
			error && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconAlertTriangle, { className: "mt-0.5 size-3.5 shrink-0" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: error })]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex justify-end",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
					disabled: !dirty || saving || loading,
					onClick: () => void handleSave(),
					size: "sm",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconDeviceFloppy, {}), saving ? p.saving : p.saveSoul]
				})
			})
		]
	});
}
function CreateProfileDialog({ onClose, onCreate, open }) {
	const { t } = useI18n();
	const p = t.profiles;
	const [name, setName] = (0, import_react.useState)("");
	const [cloneFromDefault, setCloneFromDefault] = (0, import_react.useState)(true);
	const [saving, setSaving] = (0, import_react.useState)(false);
	const [error, setError] = (0, import_react.useState)(null);
	(0, import_react.useEffect)(() => {
		if (!open) return;
		setName("");
		setCloneFromDefault(true);
		setError(null);
		setSaving(false);
	}, [open]);
	const trimmed = name.trim();
	const invalid = trimmed !== "" && !isValidProfileName(trimmed);
	async function handleSubmit(event) {
		event.preventDefault();
		if (!trimmed || invalid) {
			setError(invalid ? p.invalidName(p.nameHint) : p.nameRequired);
			return;
		}
		setSaving(true);
		setError(null);
		try {
			await onCreate(trimmed, cloneFromDefault);
			onClose();
		} catch (err) {
			setError(err instanceof Error ? err.message : p.failedCreate);
		} finally {
			setSaving(false);
		}
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Dialog, {
		onOpenChange: (value) => !value && !saving && onClose(),
		open,
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogContent, {
			className: "max-w-md",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogHeader, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogTitle, { children: p.newProfile }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogDescription, { children: p.createDesc })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("form", {
				className: "grid gap-4",
				onSubmit: handleSubmit,
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "grid gap-1.5",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
								className: "text-xs font-medium",
								htmlFor: "new-profile-name",
								children: p.nameLabel
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
								"aria-invalid": invalid,
								autoFocus: true,
								id: "new-profile-name",
								onChange: (event) => setName(event.target.value),
								placeholder: "my-profile",
								value: name
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: cn("text-[0.66rem] leading-4", invalid ? "text-destructive" : "text-muted-foreground"),
								children: p.nameHint
							})
						]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
						className: "flex cursor-pointer items-center gap-2 rounded-md border border-border/40 bg-background/50 px-3 py-2 text-sm",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
							checked: cloneFromDefault,
							className: "size-4 accent-primary",
							onChange: (event) => setCloneFromDefault(event.target.checked),
							type: "checkbox"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "font-medium",
							children: p.cloneFromDefault
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "ml-2 text-xs text-muted-foreground",
							children: p.cloneFromDefaultDesc
						})] })]
					}),
					error && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconAlertTriangle, { className: "mt-0.5 size-3.5 shrink-0" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: error })]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogFooter, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						disabled: saving,
						onClick: onClose,
						type: "button",
						variant: "outline",
						children: t.common.cancel
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						disabled: saving || !trimmed || invalid,
						type: "submit",
						children: saving ? p.creating : p.createAction
					})] })
				]
			})]
		})
	});
}
function RenameProfileDialog({ currentName, onClose, onRename, open }) {
	const { t } = useI18n();
	const p = t.profiles;
	const [name, setName] = (0, import_react.useState)(currentName);
	const [saving, setSaving] = (0, import_react.useState)(false);
	const [error, setError] = (0, import_react.useState)(null);
	(0, import_react.useEffect)(() => {
		if (!open) return;
		setName(currentName);
		setError(null);
		setSaving(false);
	}, [currentName, open]);
	const trimmed = name.trim();
	const unchanged = trimmed === currentName;
	const invalid = trimmed !== "" && !unchanged && !isValidProfileName(trimmed);
	async function handleSubmit(event) {
		event.preventDefault();
		if (unchanged) {
			onClose();
			return;
		}
		if (!trimmed || invalid) {
			setError(invalid ? p.invalidName(p.nameHint) : p.nameRequired);
			return;
		}
		setSaving(true);
		setError(null);
		try {
			await onRename(trimmed);
		} catch (err) {
			setError(err instanceof Error ? err.message : p.failedRename);
		} finally {
			setSaving(false);
		}
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Dialog, {
		onOpenChange: (value) => !value && !saving && onClose(),
		open,
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogContent, {
			className: "max-w-md",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogHeader, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogTitle, { children: p.renameTitle }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogDescription, { children: [
				p.renameDescPrefix,
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "font-mono",
					children: "~/.local/bin"
				}),
				p.renameDescSuffix
			] })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("form", {
				className: "grid gap-3",
				onSubmit: handleSubmit,
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "grid gap-1.5",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
								className: "text-xs font-medium",
								htmlFor: "rename-profile-name",
								children: p.newNameLabel
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
								"aria-invalid": invalid,
								autoFocus: true,
								id: "rename-profile-name",
								onChange: (event) => setName(event.target.value),
								value: name
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: cn("text-[0.66rem] leading-4", invalid ? "text-destructive" : "text-muted-foreground"),
								children: p.nameHint
							})
						]
					}),
					error && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconAlertTriangle, { className: "mt-0.5 size-3.5 shrink-0" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: error })]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogFooter, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						disabled: saving,
						onClick: onClose,
						type: "button",
						variant: "outline",
						children: t.common.cancel
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						disabled: saving || invalid || unchanged,
						type: "submit",
						children: saving ? p.renaming : p.rename
					})] })
				]
			})]
		})
	});
}
//#endregion
export { ProfilesView };
