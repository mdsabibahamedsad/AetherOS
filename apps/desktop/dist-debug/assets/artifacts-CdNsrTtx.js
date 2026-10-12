import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { D as getSessionMessages, N as listAllProfileSessions } from "./aetheros-DF_uJq_t.js";
import { $i as IconPhoto, $t as urlSlugTitleLabel, Dt as sessionRoute, I as PAGE_INSET_X, Ia as Codicon, La as Button, Oi as notifyError, Qt as hostPathLabel, Ra as cn, Rt as CopyButton, Xt as ExternalLink, Zt as ExternalLinkIcon, ao as require_jsx_runtime, bt as PageLoader, en as useLinkTitle, eo as useNavigate, ga as IconFileText, ha as IconFolderOpen, ki as useI18n, kn as ZoomableImage, la as IconLink, oo as require_react, un as sessionTitle, zt as Tip } from "./index-B_yd1pEX.js";
import { n as TextTabMeta, t as TextTab } from "./text-tab-zHHaCEaQ.js";
import { t as useRefreshHotkey } from "./use-refresh-hotkey-CjSQqOti.js";
import { t as useRouteEnumParam } from "./use-route-enum-param-BgGOGZCn.js";
import { t as PageSearchShell } from "./page-search-shell-CWZgYH3F.js";
//#region src/components/ui/pagination.tsx
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
var import_jsx_runtime = require_jsx_runtime();
function Pagination({ className, ...props }) {
	const { t } = useI18n();
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("nav", {
		"aria-label": t.ui.pagination.label,
		className: cn("mx-auto flex w-full justify-center", className),
		"data-slot": "pagination",
		...props
	});
}
function PaginationContent({ className, ...props }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
		className: cn("flex h-5 flex-row items-center gap-0.5", className),
		"data-slot": "pagination-content",
		...props
	});
}
function PaginationItem({ className, ...props }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", {
		className: cn("flex h-5 items-center", className),
		"data-slot": "pagination-item",
		...props
	});
}
function PaginationButton({ className, isActive, ...props }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
		"aria-current": isActive ? "page" : void 0,
		className: cn("inline-flex h-5 min-w-5 items-center justify-center rounded border border-transparent px-1 text-[0.6875rem] leading-none tabular-nums transition-colors disabled:pointer-events-none disabled:opacity-45", isActive ? "border-border bg-background text-foreground shadow-xs" : "text-muted-foreground hover:bg-accent hover:text-foreground", className),
		"data-active": isActive,
		"data-slot": "pagination-button",
		type: "button",
		...props
	});
}
function PaginationPrevious({ className, ...props }) {
	const { t } = useI18n();
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
		"aria-label": t.ui.pagination.previousAria,
		className: cn("inline-flex h-5 items-center justify-center gap-0.5 rounded border border-transparent px-1 text-[0.6875rem] leading-none text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:pointer-events-none disabled:opacity-45", className),
		"data-slot": "pagination-previous",
		type: "button",
		...props,
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
			name: "chevron-left",
			size: "0.75rem"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: t.ui.pagination.previous })]
	});
}
function PaginationNext({ className, ...props }) {
	const { t } = useI18n();
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
		"aria-label": t.ui.pagination.nextAria,
		className: cn("inline-flex h-5 items-center justify-center gap-0.5 rounded border border-transparent px-1 text-[0.6875rem] leading-none text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:pointer-events-none disabled:opacity-45", className),
		"data-slot": "pagination-next",
		type: "button",
		...props,
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: t.ui.pagination.next }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
			name: "chevron-right",
			size: "0.75rem"
		})]
	});
}
function PaginationEllipsis({ className, ...props }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
		"aria-hidden": true,
		className: cn("flex size-5 items-center justify-center", className),
		"data-slot": "pagination-ellipsis",
		...props,
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
			name: "ellipsis",
			size: "0.75rem"
		})
	});
}
//#endregion
//#region src/app/artifacts/index.tsx
var ARTIFACT_FILTERS = [
	"all",
	"image",
	"file",
	"link"
];
var MARKDOWN_IMAGE_RE = /!\[([^\]]*)\]\(([^)\s]+)\)/g;
var MARKDOWN_LINK_RE = /\[([^\]]+)\]\(([^)\s]+)\)/g;
var URL_RE = /https?:\/\/[^\s<>"')]+/g;
var PATH_RE = /(^|[\s("'`])((?:\/|~\/|\.\.?\/)[^\s"'`<>]+(?:\.[a-z0-9]{1,8})?)/gi;
var IMAGE_EXT_RE = /\.(?:png|jpe?g|gif|webp|svg|bmp)(?:\?.*)?$/i;
var FILE_EXT_RE = /\.(?:png|jpe?g|gif|webp|svg|bmp|pdf|txt|json|md|csv|zip|tar|gz|mp3|wav|mp4|mov)(?:\?.*)?$/i;
var KEY_HINT_RE = /(path|file|url|image|artifact|output|download|result|target)/i;
var ARTIFACT_TIME_FMT = new Intl.DateTimeFormat(void 0, {
	day: "numeric",
	hour: "numeric",
	minute: "2-digit",
	month: "short"
});
function normalizeValue(value) {
	return value.trim().replace(/[),.;]+$/, "");
}
function parseMaybeJson(value) {
	if (!value.trim()) return null;
	try {
		return JSON.parse(value);
	} catch {
		return null;
	}
}
function looksLikePathOrUrl(value) {
	return value.startsWith("http://") || value.startsWith("https://") || value.startsWith("file://") || value.startsWith("data:image/") || value.startsWith("/") || value.startsWith("./") || value.startsWith("../") || value.startsWith("~/");
}
function looksLikeArtifact(value) {
	if (/^(?:https?:\/\/|data:image\/)/.test(value)) return true;
	if (looksLikePathOrUrl(value) && (IMAGE_EXT_RE.test(value) || FILE_EXT_RE.test(value))) return true;
	return value.startsWith("/") && value.includes(".");
}
function artifactKind(value) {
	if (value.startsWith("data:image/") || IMAGE_EXT_RE.test(value)) return "image";
	if (value.startsWith("/") || value.startsWith("./") || value.startsWith("../") || value.startsWith("~/") || value.startsWith("file://")) return "file";
	return "link";
}
function artifactHref(value) {
	if (value.startsWith("http://") || value.startsWith("https://") || value.startsWith("file://") || value.startsWith("data:")) return value;
	if (value.startsWith("/")) return `file://${encodeURI(value)}`;
	return value;
}
function artifactLabel(value) {
	try {
		return new URL(value).pathname.split("/").filter(Boolean).pop() || value;
	} catch {
		return value.split(/[\\/]/).filter(Boolean).pop() || value;
	}
}
function messageText(message) {
	if (typeof message.content === "string" && message.content.trim()) return message.content;
	if (typeof message.text === "string" && message.text.trim()) return message.text;
	if (typeof message.context === "string" && message.context.trim()) return message.context;
	return "";
}
function collectStringValues(value, keyPath, collector) {
	if (typeof value === "string") {
		collector(value, keyPath);
		return;
	}
	if (Array.isArray(value)) {
		value.forEach((entry, index) => collectStringValues(entry, `${keyPath}.${index}`, collector));
		return;
	}
	if (!value || typeof value !== "object") return;
	for (const [key, child] of Object.entries(value)) collectStringValues(child, keyPath ? `${keyPath}.${key}` : key, collector);
}
function collectArtifactsFromText(text, pushValue) {
	for (const match of text.matchAll(MARKDOWN_IMAGE_RE)) pushValue(match[2] || "");
	for (const match of text.matchAll(MARKDOWN_LINK_RE)) {
		const start = match.index ?? 0;
		if (start > 0 && text[start - 1] === "!") continue;
		const value = match[2] || "";
		if (looksLikeArtifact(value)) pushValue(value);
	}
	for (const match of text.matchAll(URL_RE)) {
		const value = match[0] || "";
		if (looksLikeArtifact(value)) pushValue(value);
	}
	for (const match of text.matchAll(PATH_RE)) pushValue(match[2] || "");
}
function collectArtifactsFromMessage(message, pushValue) {
	const text = messageText(message);
	if (text) collectArtifactsFromText(text, pushValue);
	if (message.role !== "tool" && !Array.isArray(message.tool_calls)) return;
	if (Array.isArray(message.tool_calls)) for (const call of message.tool_calls) collectStringValues(call, "tool_call", (value, keyPath) => {
		const normalized = normalizeValue(value);
		if (!normalized) return;
		if (KEY_HINT_RE.test(keyPath) && (looksLikePathOrUrl(normalized) || FILE_EXT_RE.test(normalized))) pushValue(normalized);
	});
	const parsed = parseMaybeJson(text);
	if (parsed !== null) collectStringValues(parsed, "tool_result", (value, keyPath) => {
		const normalized = normalizeValue(value);
		if (!normalized) return;
		if ((KEY_HINT_RE.test(keyPath) || looksLikePathOrUrl(normalized)) && looksLikeArtifact(normalized)) pushValue(normalized);
	});
}
function collectArtifactsForSession(session, messages) {
	const found = /* @__PURE__ */ new Map();
	const title = sessionTitle(session);
	for (const message of messages) {
		if (message.role !== "assistant" && message.role !== "tool") continue;
		collectArtifactsFromMessage(message, (candidate) => {
			const value = normalizeValue(candidate);
			if (!value || !looksLikeArtifact(value)) return;
			const key = `${session.id}:${value}`;
			if (found.has(key)) return;
			found.set(key, {
				id: key,
				kind: artifactKind(value),
				value,
				href: artifactHref(value),
				label: artifactLabel(value),
				sessionId: session.id,
				sessionTitle: title,
				timestamp: message.timestamp || session.last_active || session.started_at || Date.now()
			});
		});
	}
	return Array.from(found.values());
}
function formatArtifactTime(timestamp) {
	return ARTIFACT_TIME_FMT.format(new Date(timestamp));
}
function pageRangeLabel(total, page, pageSize, a) {
	if (total === 0) return a.zero;
	const start = (page - 1) * pageSize + 1;
	const end = Math.min(total, page * pageSize);
	return a.rangeOf(start, end, total);
}
function paginationItems(page, pageCount) {
	if (pageCount <= 7) return Array.from({ length: pageCount }, (_, index) => index + 1);
	const pages = [1];
	const start = Math.max(2, page - 1);
	const end = Math.min(pageCount - 1, page + 1);
	if (start > 2) pages.push("ellipsis");
	for (let nextPage = start; nextPage <= end; nextPage += 1) pages.push(nextPage);
	if (end < pageCount - 1) pages.push("ellipsis");
	pages.push(pageCount);
	return pages;
}
var itemsLabel = (f, a) => f === "link" ? a.itemsLink : f === "file" ? a.itemsFile : a.itemsGeneric;
function ArtifactsView({ setStatusbarItemGroup: _setStatusbarItemGroup, ...props }) {
	const { t } = useI18n();
	const a = t.artifacts;
	const navigate = useNavigate();
	const [artifacts, setArtifacts] = (0, import_react.useState)(null);
	const [query, setQuery] = (0, import_react.useState)("");
	const [refreshing, setRefreshing] = (0, import_react.useState)(false);
	const [kindFilter, setKindFilter] = useRouteEnumParam("tab", ARTIFACT_FILTERS, "all");
	const [failedImageIds, setFailedImageIds] = (0, import_react.useState)(() => /* @__PURE__ */ new Set());
	const [imagePage, setImagePage] = (0, import_react.useState)(1);
	const [filePage, setFilePage] = (0, import_react.useState)(1);
	const refreshArtifacts = (0, import_react.useCallback)(async () => {
		setRefreshing(true);
		try {
			const sessions = (await listAllProfileSessions(30, 1)).sessions;
			const results = await Promise.allSettled(sessions.map((session) => getSessionMessages(session.id, session.profile)));
			const nextArtifacts = [];
			results.forEach((result, index) => {
				if (result.status !== "fulfilled") return;
				const session = sessions[index];
				nextArtifacts.push(...collectArtifactsForSession(session, result.value.messages));
			});
			setArtifacts(nextArtifacts.sort((left, right) => right.timestamp - left.timestamp));
		} catch (err) {
			notifyError(err, a.failedLoad);
			setArtifacts([]);
		} finally {
			setRefreshing(false);
		}
	}, [a]);
	useRefreshHotkey(refreshArtifacts);
	(0, import_react.useEffect)(() => {
		refreshArtifacts();
	}, [refreshArtifacts]);
	(0, import_react.useEffect)(() => {
		setImagePage(1);
		setFilePage(1);
	}, [
		artifacts,
		kindFilter,
		query
	]);
	const visibleArtifacts = (0, import_react.useMemo)(() => {
		if (!artifacts) return [];
		const q = query.trim().toLowerCase();
		return artifacts.filter((artifact) => {
			if (kindFilter !== "all" && artifact.kind !== kindFilter) return false;
			if (!q) return true;
			return artifact.label.toLowerCase().includes(q) || artifact.value.toLowerCase().includes(q) || artifact.sessionTitle.toLowerCase().includes(q);
		});
	}, [
		artifacts,
		kindFilter,
		query
	]);
	const visibleImageArtifacts = (0, import_react.useMemo)(() => visibleArtifacts.filter((artifact) => artifact.kind === "image"), [visibleArtifacts]);
	const visibleFileArtifacts = (0, import_react.useMemo)(() => visibleArtifacts.filter((artifact) => artifact.kind !== "image"), [visibleArtifacts]);
	const imagePageCount = Math.max(1, Math.ceil(visibleImageArtifacts.length / 24));
	const filePageCount = Math.max(1, Math.ceil(visibleFileArtifacts.length / 100));
	const currentImagePage = Math.min(imagePage, imagePageCount);
	const currentFilePage = Math.min(filePage, filePageCount);
	const pagedImageArtifacts = (0, import_react.useMemo)(() => visibleImageArtifacts.slice((currentImagePage - 1) * 24, currentImagePage * 24), [currentImagePage, visibleImageArtifacts]);
	const pagedFileArtifacts = (0, import_react.useMemo)(() => visibleFileArtifacts.slice((currentFilePage - 1) * 100, currentFilePage * 100), [currentFilePage, visibleFileArtifacts]);
	const counts = (0, import_react.useMemo)(() => {
		const all = artifacts || [];
		return {
			all: all.length,
			image: all.filter((artifact) => artifact.kind === "image").length,
			file: all.filter((artifact) => artifact.kind === "file").length,
			link: all.filter((artifact) => artifact.kind === "link").length
		};
	}, [artifacts]);
	const openArtifact = (0, import_react.useCallback)(async (href) => {
		try {
			if (window.aetherosDesktop?.openExternal) await window.aetherosDesktop.openExternal(href);
			else window.open(href, "_blank", "noopener,noreferrer");
		} catch (err) {
			notifyError(err, a.openFailed);
		}
	}, [a]);
	const markImageFailed = (0, import_react.useCallback)((id) => {
		setFailedImageIds((current) => {
			if (current.has(id)) return current;
			return new Set(current).add(id);
		});
	}, []);
	const cellCtx = {
		onOpen: openArtifact,
		onOpenChat: (sessionId) => navigate(sessionRoute(sessionId))
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageSearchShell, {
		...props,
		onSearchChange: setQuery,
		searchHidden: counts.all === 0,
		searchPlaceholder: a.search,
		searchTrailingAction: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
			"aria-label": refreshing ? a.refreshing : a.refresh,
			className: "text-(--ui-text-tertiary) hover:bg-transparent hover:text-foreground",
			disabled: refreshing,
			onClick: () => void refreshArtifacts(),
			size: "icon-xs",
			title: refreshing ? a.refreshing : a.refresh,
			type: "button",
			variant: "ghost",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Codicon, {
				name: "refresh",
				size: "0.875rem",
				spinning: refreshing
			})
		}),
		searchValue: query,
		tabs: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(TextTab, {
				active: kindFilter === "all",
				onClick: () => setKindFilter("all"),
				children: [
					a.tabAll,
					" ",
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(TextTabMeta, { children: [
						"(",
						counts.all,
						")"
					] })
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(TextTab, {
				active: kindFilter === "image",
				onClick: () => setKindFilter("image"),
				children: [
					a.tabImages,
					" ",
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(TextTabMeta, { children: [
						"(",
						counts.image,
						")"
					] })
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(TextTab, {
				active: kindFilter === "file",
				onClick: () => setKindFilter("file"),
				children: [
					a.tabFiles,
					" ",
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(TextTabMeta, { children: [
						"(",
						counts.file,
						")"
					] })
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(TextTab, {
				active: kindFilter === "link",
				onClick: () => setKindFilter("link"),
				children: [
					a.tabLinks,
					" ",
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(TextTabMeta, { children: [
						"(",
						counts.link,
						")"
					] })
				]
			})
		] }),
		children: !artifacts ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PageLoader, { label: a.indexing }) : visibleArtifacts.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "grid h-full place-items-center px-6 text-center",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "text-sm font-medium",
				children: a.noArtifactsTitle
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "mt-1 text-xs text-muted-foreground",
				children: a.noArtifactsDesc
			})] })
		}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "h-full overflow-y-auto",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: cn("flex flex-col gap-3 pb-2", PAGE_INSET_X),
				children: [visibleImageArtifacts.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
					className: "flex flex-col",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: cn("sticky top-0 z-10 flex h-7 items-center gap-3 overflow-x-auto bg-background", "-mx-[clamp(1.25rem,4vw,4rem)]", "px-[clamp(1.25rem,4vw,4rem)]"),
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ArtifactsPagination, {
							className: "ml-auto justify-end px-0",
							itemLabel: a.itemsImage,
							onPageChange: setImagePage,
							page: currentImagePage,
							pageSize: 24,
							total: visibleImageArtifacts.length
						})
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "grid grid-cols-[repeat(auto-fill,minmax(11rem,1fr))] items-start gap-2 pt-1.5",
						children: pagedImageArtifacts.map((artifact) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ArtifactImageCard, {
							artifact,
							failedImage: failedImageIds.has(artifact.id),
							onImageError: markImageFailed,
							onOpenChat: (sessionId) => navigate(sessionRoute(sessionId))
						}, artifact.id))
					})]
				}), visibleFileArtifacts.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
					className: "flex flex-col",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: cn("sticky top-0 z-10 flex h-7 items-center gap-3 overflow-x-auto bg-background", "-mx-[clamp(1.25rem,4vw,4rem)]", "px-[clamp(1.25rem,4vw,4rem)]"),
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ArtifactsPagination, {
							className: "ml-auto justify-end px-0",
							itemLabel: itemsLabel(kindFilter, a),
							onPageChange: setFilePage,
							page: currentFilePage,
							pageSize: 100,
							total: visibleFileArtifacts.length
						})
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "overflow-x-auto rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-chat-bubble-background)",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ArtifactTable, {
							artifacts: pagedFileArtifacts,
							ctx: cellCtx,
							filter: kindFilter
						})
					})]
				})]
			})
		})
	});
}
function ArtifactsPagination({ className, itemLabel, onPageChange, page, pageSize, total }) {
	const { t } = useI18n();
	const a = t.artifacts;
	const pageCount = Math.max(1, Math.ceil(total / pageSize));
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: cn("flex h-6 items-center justify-between gap-2 px-1", className),
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "shrink-0 text-[0.62rem] text-muted-foreground",
			children: [
				pageRangeLabel(total, page, pageSize, a),
				" ",
				itemLabel
			]
		}), pageCount > 1 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Pagination, {
			className: "mx-0 w-auto min-w-0 justify-end",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(PaginationContent, {
				className: "gap-0.5",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PaginationItem, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PaginationPrevious, {
						disabled: page <= 1,
						onClick: () => onPageChange(Math.max(1, page - 1))
					}) }),
					paginationItems(page, pageCount).map((item, index) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PaginationItem, { children: item === "ellipsis" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PaginationEllipsis, {}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PaginationButton, {
						"aria-label": a.goToPage(itemLabel, item),
						isActive: page === item,
						onClick: () => onPageChange(item),
						children: item
					}) }, `${item}-${index}`)),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(PaginationItem, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PaginationNext, {
						disabled: page >= pageCount,
						onClick: () => onPageChange(Math.min(pageCount, page + 1))
					}) })
				]
			})
		})]
	});
}
function ArtifactImageCard({ artifact, failedImage, onImageError, onOpenChat }) {
	const { t } = useI18n();
	const a = t.artifacts;
	const kindLabel = artifact.kind === "image" ? a.kindImage : artifact.kind === "file" ? a.kindFile : a.kindLink;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("article", {
		className: "group/artifact overflow-hidden rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-chat-bubble-background)",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: cn("relative flex h-40 w-full items-center justify-center overflow-hidden border-b border-(--ui-stroke-tertiary) bg-(--ui-bg-quinary) p-1.5", failedImage && "cursor-default"),
			children: !failedImage && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ZoomableImage, {
				alt: artifact.label,
				className: "max-h-40 max-w-full cursor-zoom-in rounded-md object-contain",
				containerClassName: "max-h-full",
				decoding: "async",
				loading: "lazy",
				onError: () => onImageError(artifact.id),
				slot: "artifact-media",
				src: artifact.href
			})
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "space-y-1.5 p-2",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "min-w-0",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "mb-0.5 flex items-center gap-1 text-[0.625rem] uppercase tracking-[0.08em] text-(--ui-text-tertiary)",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconPhoto, { className: "size-3" }), kindLabel]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "truncate text-[length:var(--conversation-caption-font-size)] font-medium",
							children: artifact.label
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "mt-0.5 truncate text-[0.625rem] text-(--ui-text-tertiary)",
							children: artifact.value
						})
					]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "truncate text-[0.625rem] text-(--ui-text-tertiary)",
					children: [
						artifact.sessionTitle,
						" · ",
						formatArtifactTime(artifact.timestamp)
					]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex flex-wrap gap-1.5",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
						onClick: () => onOpenChat(artifact.sessionId),
						size: "xs",
						type: "button",
						variant: "textStrong",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(IconFolderOpen, { className: "size-3" }), a.chat]
					})
				})
			]
		})]
	});
}
function ArtifactCellAction({ children, href, onClick, title }) {
	if (href) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ExternalLink, {
		className: "flex h-full w-full min-w-0 items-center gap-2 px-2.5 py-1.5 text-left text-[length:var(--conversation-caption-font-size)] leading-(--conversation-caption-line-height) font-normal text-(--ui-text-secondary) no-underline underline-offset-4 decoration-current/20 transition-colors hover:text-foreground hover:underline",
		href,
		showExternalIcon: false,
		title,
		children
	});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
		className: "flex h-full w-full min-w-0 items-center gap-2 px-2.5 py-1.5 text-left text-[length:var(--conversation-caption-font-size)] leading-(--conversation-caption-line-height) font-normal text-(--ui-text-secondary) no-underline underline-offset-4 decoration-current/20 transition-colors hover:text-foreground hover:underline",
		onClick,
		type: "button",
		children
	});
}
function PrimaryCell({ artifact, ctx }) {
	const isLink = artifact.kind === "link";
	const Icon = isLink ? IconLink : IconFileText;
	const fetchedTitle = useLinkTitle(isLink ? artifact.href : null);
	const label = isLink ? fetchedTitle || urlSlugTitleLabel(artifact.href) : artifact.label;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(ArtifactCellAction, {
		href: isLink ? artifact.href : void 0,
		onClick: isLink ? void 0 : () => void ctx.onOpen(artifact.href),
		title: label,
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
			className: "mt-0.5 grid size-6 shrink-0 place-items-center self-start rounded-md bg-(--ui-bg-tertiary) text-(--ui-text-tertiary)",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Icon, { className: "size-3.5" })
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
			className: cn("min-w-0 flex-1", isLink ? "wrap-anywhere" : "truncate"),
			children: [label, isLink && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ExternalLinkIcon, {})]
		})]
	});
}
function LocationCell({ artifact }) {
	const { t } = useI18n();
	const isLink = artifact.kind === "link";
	const value = isLink ? hostPathLabel(artifact.value) : artifact.value;
	const copyLabel = isLink ? t.artifacts.copyUrl : t.artifacts.copyPath;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "group/location flex min-w-0 items-center gap-1.5",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Tip, {
			label: artifact.value,
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: cn("min-w-0 flex-1 truncate text-[length:var(--conversation-caption-font-size)] text-(--ui-text-tertiary)", isLink ? "font-normal" : "font-mono"),
				children: value
			})
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CopyButton, {
			appearance: "icon",
			buttonSize: "icon-xs",
			className: "shrink-0 text-muted-foreground opacity-0 transition-opacity hover:text-foreground focus-visible:opacity-100 group-hover/location:opacity-100",
			iconClassName: "size-3.5",
			label: copyLabel,
			text: artifact.value,
			title: copyLabel
		})]
	});
}
function SessionCell({ artifact, ctx }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ArtifactCellAction, {
		onClick: () => ctx.onOpenChat(artifact.sessionId),
		title: artifact.sessionTitle,
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
			className: "flex min-w-0 flex-col",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "truncate",
				children: artifact.sessionTitle
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "truncate text-[0.6875rem] font-normal text-(--ui-text-tertiary)",
				children: formatArtifactTime(artifact.timestamp)
			})]
		})
	});
}
var ARTIFACT_COLUMNS = [
	{
		Cell: PrimaryCell,
		bodyClassName: "p-0",
		header: (filter, a) => filter === "link" ? a.colTitleLink : filter === "file" ? a.colTitleFile : a.colTitleDefault,
		id: "primary",
		width: (filter) => filter === "link" ? "w-[50%]" : "w-[35%]"
	},
	{
		Cell: LocationCell,
		bodyClassName: "px-2.5 py-1.5",
		header: (filter, a) => filter === "link" ? a.colLocationLink : filter === "file" ? a.colLocationFile : a.colLocationDefault,
		id: "location",
		width: (filter) => filter === "link" ? "w-[30%]" : "w-[41%]"
	},
	{
		Cell: SessionCell,
		bodyClassName: "p-0",
		header: (_filter, a) => a.colSession,
		id: "session",
		width: (filter) => filter === "link" ? "w-[20%]" : "w-[24%]"
	}
];
function ArtifactTable({ artifacts, ctx, filter }) {
	const { t } = useI18n();
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("table", {
		className: "w-full min-w-176 table-fixed text-left text-[length:var(--conversation-caption-font-size)]",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("thead", {
			className: "border-b border-(--ui-stroke-tertiary) bg-(--ui-bg-quinary) text-[0.625rem] uppercase tracking-[0.08em] text-(--ui-text-tertiary)",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("tr", { children: ARTIFACT_COLUMNS.map((col) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("th", {
				className: cn(col.width(filter), "px-2.5 py-1.5 font-medium"),
				children: col.header(filter, t.artifacts)
			}, col.id)) })
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("tbody", { children: artifacts.map((artifact) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("tr", {
			className: "group/artifact",
			children: ARTIFACT_COLUMNS.map((col) => {
				const Cell = col.Cell;
				return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("td", {
					className: cn("align-middle", col.bodyClassName),
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Cell, {
						artifact,
						ctx
					})
				}, col.id);
			})
		}, artifact.id)) })]
	});
}
//#endregion
export { ArtifactsView };
