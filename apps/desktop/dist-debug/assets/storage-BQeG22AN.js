//#region src/lib/storage.ts
function storedBoolean(key, fallback) {
	try {
		const value = window.localStorage.getItem(key);
		return value === null ? fallback : value === "true";
	} catch {
		return fallback;
	}
}
function persistBoolean(key, value) {
	try {
		window.localStorage.setItem(key, String(value));
	} catch {}
}
function storedString(key) {
	try {
		return window.localStorage.getItem(key);
	} catch {
		return null;
	}
}
function persistString(key, value) {
	try {
		if (value === null) window.localStorage.removeItem(key);
		else window.localStorage.setItem(key, value);
	} catch {}
}
function storedStringArray(key) {
	try {
		const value = window.localStorage.getItem(key);
		if (!value) return [];
		const parsed = JSON.parse(value);
		if (!Array.isArray(parsed)) return [];
		return parsed.filter((item) => typeof item === "string" && item.length > 0);
	} catch {
		return [];
	}
}
function persistStringArray(key, value) {
	try {
		window.localStorage.setItem(key, JSON.stringify(value));
	} catch {}
}
function storedStringRecord(key) {
	try {
		const value = window.localStorage.getItem(key);
		if (!value) return {};
		const parsed = JSON.parse(value);
		if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
		return Object.fromEntries(Object.entries(parsed).filter((entry) => typeof entry[1] === "string"));
	} catch {
		return {};
	}
}
function persistStringRecord(key, value) {
	try {
		window.localStorage.setItem(key, JSON.stringify(value));
	} catch {}
}
function arraysEqual(left, right) {
	return left.length === right.length && left.every((item, index) => item === right[index]);
}
function insertUniqueId(ids, id, index) {
	const next = ids.filter((item) => item !== id);
	const boundedIndex = Math.min(Math.max(index, 0), next.length);
	next.splice(boundedIndex, 0, id);
	return next;
}
//#endregion
export { persistStringArray as a, storedString as c, persistString as i, storedStringArray as l, insertUniqueId as n, persistStringRecord as o, persistBoolean as r, storedBoolean as s, arraysEqual as t, storedStringRecord as u };
