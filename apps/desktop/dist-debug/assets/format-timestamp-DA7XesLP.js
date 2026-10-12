//#region src/lib/format-timestamp.ts
function formatTimestamp(value) {
	if (value === null || value === void 0 || value === "") return "—";
	const date = value instanceof Date ? value : new Date(value);
	if (Number.isNaN(date.getTime())) return "—";
	return new Intl.DateTimeFormat(void 0, {
		dateStyle: "medium",
		timeStyle: "short"
	}).format(date);
}
//#endregion
export { formatTimestamp as t };
