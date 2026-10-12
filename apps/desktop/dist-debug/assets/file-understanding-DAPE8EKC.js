import { a as __toESM } from "./chunk-DKxDMwdo.js";
import { C as Select, D as SelectValue, E as SelectTrigger, P as Switch, Qa as atom, T as SelectItem, Xa as init_nanostores, Ya as useStore, ao as require_jsx_runtime, oo as require_react, w as SelectContent } from "./index-B_yd1pEX.js";
//#region src/store/file-understanding.ts
var import_react = /* @__PURE__ */ __toESM(require_react(), 1);
init_nanostores();
var $fileUnderstanding = /* @__PURE__ */ atom({
	recentAnalyses: [],
	activeAnalysis: null,
	pdfExtractionMethod: "ocr",
	officeHandling: "convert",
	autoAnalyzeOnDrop: true,
	analyzeClipboardImages: true,
	supportedTypes: [
		"pdf",
		"docx",
		"xlsx",
		"pptx",
		"md",
		"csv",
		"json",
		"xml",
		"zip",
		"image",
		"video",
		"audio"
	],
	maxFileSizeMB: 50
});
var patch = (u) => $fileUnderstanding.set({
	...$fileUnderstanding.get(),
	...u
});
function setActiveAnalysis(a) {
	patch({ activeAnalysis: a });
}
function addRecentAnalysis(a) {
	patch({ recentAnalyses: [a, ...$fileUnderstanding.get().recentAnalyses].slice(0, 25) });
}
function setPdfExtractionMethod(m) {
	patch({ pdfExtractionMethod: m });
}
function setOfficeHandling(h) {
	patch({ officeHandling: h });
}
function setAutoAnalyzeOnDrop(a) {
	patch({ autoAnalyzeOnDrop: a });
}
function setAnalyzeClipboardImages(a) {
	patch({ analyzeClipboardImages: a });
}
function setMaxFileSizeMB(s) {
	patch({ maxFileSizeMB: s });
}
//#endregion
//#region src/app/file-understanding/file-analyzer.tsx
var import_jsx_runtime = require_jsx_runtime();
var DOCUMENT_TYPES = [
	{
		value: "pdf",
		label: "PDF"
	},
	{
		value: "docx",
		label: "Word"
	},
	{
		value: "xlsx",
		label: "Excel"
	},
	{
		value: "pptx",
		label: "PowerPoint"
	},
	{
		value: "md",
		label: "Markdown"
	},
	{
		value: "csv",
		label: "CSV"
	},
	{
		value: "json",
		label: "JSON"
	},
	{
		value: "xml",
		label: "XML"
	},
	{
		value: "zip",
		label: "ZIP"
	},
	{
		value: "image",
		label: "Images"
	},
	{
		value: "video",
		label: "Videos"
	},
	{
		value: "audio",
		label: "Audio"
	}
];
function formatFileSize(bytes) {
	if (bytes < 1024) return `${bytes} B`;
	if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
	return `${(bytes / 1048576).toFixed(1)} MB`;
}
function getTypeLabel(type) {
	return DOCUMENT_TYPES.find((d) => d.value === type)?.label ?? type;
}
function FileAnalyzer() {
	const state = useStore($fileUnderstanding);
	const fileInputRef = (0, import_react.useRef)(null);
	const [analyzing, setAnalyzing] = (0, import_react.useState)(false);
	const [dragOver, setDragOver] = (0, import_react.useState)(false);
	const handleFileSelected = (0, import_react.useCallback)(async (files) => {
		if (!files || files.length === 0) return;
		const file = files[0];
		if (file.size > state.maxFileSizeMB * 1048576) return;
		setAnalyzing(true);
		const startTime = Date.now();
		const result = {
			fileName: file.name,
			filePath: file.name,
			documentType: inferDocumentType(file.name, file.type),
			fileSizeBytes: file.size,
			textContent: await file.text().catch(() => `[Binary file: ${file.name}]`),
			metadata: {
				mimeType: file.type,
				lastModified: new Date(file.lastModified).toISOString()
			},
			processingTimeMs: Date.now() - startTime,
			status: "done"
		};
		addRecentAnalysis(result);
		setActiveAnalysis(result);
		setAnalyzing(false);
	}, [state.maxFileSizeMB]);
	const handleDrop = (0, import_react.useCallback)((e) => {
		e.preventDefault();
		setDragOver(false);
		handleFileSelected(e.dataTransfer.files);
	}, [handleFileSelected]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-col gap-5",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "text-lg font-semibold",
				children: "File Understanding"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-sm text-(--ui-text-tertiary)",
				children: "Analyze documents, spreadsheets, presentations, and media files"
			})] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
				className: "flex flex-col gap-4",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
					className: "text-sm font-medium text-(--ui-text-secondary)",
					children: "Upload File"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: `flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors ${dragOver ? "border-primary bg-primary/5" : "border-(--ui-stroke-tertiary) hover:border-(--ui-stroke-secondary)"}`,
					onClick: () => fileInputRef.current?.click(),
					onDragLeave: () => setDragOver(false),
					onDragOver: (e) => {
						e.preventDefault();
						setDragOver(true);
					},
					onDrop: handleDrop,
					onKeyDown: (e) => {
						if (e.key === "Enter") fileInputRef.current?.click();
					},
					role: "button",
					tabIndex: 0,
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("svg", {
							className: "mb-2 size-8 text-(--ui-text-tertiary)",
							fill: "none",
							stroke: "currentColor",
							viewBox: "0 0 24 24",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
								d: "M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12",
								strokeLinecap: "round",
								strokeLinejoin: "round",
								strokeWidth: 1.5
							})
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-sm text-(--ui-text-secondary)",
							children: "Drop a file here or click to browse"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-1 text-xs text-(--ui-text-tertiary)",
							children: "Supports PDF, Word, Excel, PowerPoint, Markdown, CSV, JSON, XML, images, video, audio"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
							className: "hidden",
							onChange: (e) => handleFileSelected(e.target.files),
							ref: fileInputRef,
							type: "file"
						})
					]
				})]
			}),
			analyzing && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-2 rounded-lg bg-(--ui-bg-quaternary) px-3 py-2 text-sm text-(--ui-text-secondary)",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("svg", {
					className: "size-4 animate-spin",
					fill: "none",
					viewBox: "0 0 24 24",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("circle", {
						className: "opacity-25",
						cx: "12",
						cy: "12",
						r: "10",
						stroke: "currentColor",
						strokeWidth: "4"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
						className: "opacity-75",
						d: "M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z",
						fill: "currentColor"
					})]
				}), "Analyzing file..."]
			}),
			state.activeAnalysis && !analyzing && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
				className: "flex flex-col gap-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
					className: "text-sm font-medium text-(--ui-text-secondary)",
					children: "Analysis Result"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) p-4",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "mb-3 flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-sm font-medium",
							children: state.activeAnalysis.fileName
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
							className: "text-xs text-(--ui-text-tertiary)",
							children: [
								getTypeLabel(state.activeAnalysis.documentType),
								" · ",
								formatFileSize(state.activeAnalysis.fileSizeBytes)
							]
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
							className: "rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary",
							children: [state.activeAnalysis.processingTimeMs, "ms"]
						})]
					}), state.activeAnalysis.textContent && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("pre", {
						className: "max-h-48 overflow-y-auto whitespace-pre-wrap rounded bg-(--ui-bg-quinary) p-2 text-xs text-(--ui-text-secondary)",
						children: [state.activeAnalysis.textContent.slice(0, 5e3), state.activeAnalysis.textContent.length > 5e3 && "..."]
					})]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
				className: "flex flex-col gap-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
						className: "text-sm font-medium text-(--ui-text-secondary)",
						children: "Processing"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "PDF Extraction"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)}",
							children: "Method for PDF text extraction"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
							onValueChange: (v) => setPdfExtractionMethod(v),
							value: state.pdfExtractionMethod,
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
								className: "w-32",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SelectContent, { children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "text",
									children: "Text"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "ocr",
									children: "OCR"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "vision",
									children: "Vision"
								})
							] })]
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "Office Documents"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)}",
							children: "How .docx/.xlsx/.pptx are handled"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
							onValueChange: (v) => setOfficeHandling(v),
							value: state.officeHandling,
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
								className: "w-32",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SelectContent, { children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "convert",
									children: "Convert"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "ocr",
									children: "OCR"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "vision",
									children: "Vision"
								})
							] })]
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "Auto-Analyze on Drop"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)}",
							children: "Analyze files when dropped"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: state.autoAnalyzeOnDrop,
							onCheckedChange: setAutoAnalyzeOnDrop
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "Clipboard Images"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)}",
							children: "Analyze images from clipboard"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Switch, {
							checked: state.analyzeClipboardImages,
							onCheckedChange: setAnalyzeClipboardImages
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-sm font-medium",
							children: "Max File Size"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "text-xs text-(--ui-text-tertiary)}",
							children: "Maximum file size for analysis"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Select, {
							onValueChange: (v) => setMaxFileSizeMB(Number(v)),
							value: String(state.maxFileSizeMB),
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectTrigger, {
								className: "w-20",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectValue, {})
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(SelectContent, { children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "5",
									children: "5 MB"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "10",
									children: "10 MB"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "25",
									children: "25 MB"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "50",
									children: "50 MB"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SelectItem, {
									value: "100",
									children: "100 MB"
								})
							] })]
						})]
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
				className: "flex flex-col gap-4",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
					className: "text-sm font-medium text-(--ui-text-secondary)",
					children: "Supported Formats"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex flex-wrap gap-1.5",
					children: DOCUMENT_TYPES.map((dt) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "rounded-full bg-(--ui-background-tertiary) px-2 py-0.5 text-xs text-(--ui-text-secondary)",
						children: dt.label
					}, dt.value))
				})]
			}),
			state.recentAnalyses.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
				className: "flex flex-col gap-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
					className: "text-sm font-medium text-(--ui-text-secondary)",
					children: "Recent Analyses"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex flex-col gap-2",
					children: state.recentAnalyses.slice(0, 5).map((analysis, i) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
						className: "flex items-center gap-3 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2 text-left transition-colors hover:bg-(--ui-bg-quaternary)",
						onClick: () => setActiveAnalysis(analysis),
						type: "button",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "flex h-8 w-8 items-center justify-center rounded-md bg-(--ui-bg-tertiary)",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("svg", {
								className: "size-4 text-(--ui-text-secondary)",
								fill: "none",
								stroke: "currentColor",
								viewBox: "0 0 24 24",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
									d: "M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z",
									strokeLinecap: "round",
									strokeLinejoin: "round",
									strokeWidth: 1.5
								})
							})
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex-1 min-w-0",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "truncate text-sm font-medium",
								children: analysis.fileName
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
								className: "text-xs text-(--ui-text-tertiary)",
								children: [
									getTypeLabel(analysis.documentType),
									" · ",
									formatFileSize(analysis.fileSizeBytes)
								]
							})]
						})]
					}, i))
				})]
			})
		]
	});
}
function inferDocumentType(fileName, mimeType) {
	const ext = fileName.split(".").pop()?.toLowerCase();
	if (ext === "pdf") return "pdf";
	if (["doc", "docx"].includes(ext ?? "")) return "docx";
	if (["xls", "xlsx"].includes(ext ?? "")) return "xlsx";
	if (["ppt", "pptx"].includes(ext ?? "")) return "pptx";
	if (ext === "md") return "md";
	if (ext === "csv") return "csv";
	if (ext === "json") return "json";
	if ([
		"xml",
		"html",
		"svg"
	].includes(ext ?? "")) return "xml";
	if ([
		"zip",
		"rar",
		"7z",
		"tar",
		"gz"
	].includes(ext ?? "")) return "zip";
	if (mimeType.startsWith("image/") || [
		"png",
		"jpg",
		"jpeg",
		"gif",
		"webp",
		"bmp"
	].includes(ext ?? "")) return "image";
	if (mimeType.startsWith("video/") || [
		"mp4",
		"avi",
		"mkv",
		"mov",
		"wmv"
	].includes(ext ?? "")) return "video";
	if (mimeType.startsWith("audio/") || [
		"mp3",
		"wav",
		"ogg",
		"flac",
		"aac"
	].includes(ext ?? "")) return "audio";
	return "unknown";
}
//#endregion
export { FileAnalyzer };
