import { Qa as atom, Xa as init_nanostores } from "./index-B_yd1pEX.js";
//#region src/store/privacy-store.ts
init_nanostores();
var $privacy = /* @__PURE__ */ atom({
	processingMode: "hybrid",
	askBeforeUpload: true,
	offlineMode: false,
	microphone: {
		state: "not_determined",
		lastAccess: null
	},
	camera: {
		state: "not_determined",
		lastAccess: null
	},
	screen: {
		state: "not_determined",
		lastAccess: null
	},
	clipboard: {
		state: "not_determined",
		lastAccess: null
	},
	files: {
		state: "not_determined",
		lastAccess: null
	},
	dataCollectionEnabled: false,
	anonymizeData: true,
	retainHistory: true,
	historyRetentionDays: 30,
	autoClearHistory: false,
	showPrivacyIndicator: true,
	requireConsentForVoice: true,
	requireConsentForScreen: true,
	requireConsentForCamera: true,
	requireConsentForClipboard: true,
	consentTimeoutMs: 3e4,
	allowedDomains: [],
	blockedDomains: [],
	encryptedStorage: true
});
var patch = (u) => $privacy.set({
	...$privacy.get(),
	...u
});
function setProcessingMode(m) {
	patch({ processingMode: m });
}
function setAskBeforeUpload(a) {
	patch({ askBeforeUpload: a });
}
function setOfflineMode(o) {
	patch({ offlineMode: o });
}
function setMicrophonePermission(p) {
	patch({ microphone: {
		...$privacy.get().microphone,
		...p
	} });
}
function setCameraPermission(p) {
	patch({ camera: {
		...$privacy.get().camera,
		...p
	} });
}
function setScreenPermission(p) {
	patch({ screen: {
		...$privacy.get().screen,
		...p
	} });
}
function setClipboardPermission(p) {
	patch({ clipboard: {
		...$privacy.get().clipboard,
		...p
	} });
}
function setFilePermission(p) {
	patch({ files: {
		...$privacy.get().files,
		...p
	} });
}
function setShowPrivacyIndicator(s) {
	patch({ showPrivacyIndicator: s });
}
function setEncryptedStorage(e) {
	patch({ encryptedStorage: e });
}
async function requestPermission(kind) {
	try {
		if (kind === "microphone") {
			(await navigator.mediaDevices.getUserMedia({ audio: true })).getTracks().forEach((t) => t.stop());
			setMicrophonePermission({
				state: "granted",
				lastAccess: Date.now()
			});
			return true;
		}
		if (kind === "camera") {
			(await navigator.mediaDevices.getUserMedia({ video: true })).getTracks().forEach((t) => t.stop());
			setCameraPermission({
				state: "granted",
				lastAccess: Date.now()
			});
			return true;
		}
		if (kind === "screen") {
			(await navigator.mediaDevices.getDisplayMedia({ video: true })).getTracks().forEach((t) => t.stop());
			setScreenPermission({
				state: "granted",
				lastAccess: Date.now()
			});
			return true;
		}
		return false;
	} catch {
		if (kind === "microphone") setMicrophonePermission({ state: "denied" });
		else if (kind === "camera") setCameraPermission({ state: "denied" });
		else if (kind === "screen") setScreenPermission({ state: "denied" });
		return false;
	}
}
//#endregion
export { setClipboardPermission as a, setMicrophonePermission as c, setScreenPermission as d, setShowPrivacyIndicator as f, setCameraPermission as i, setOfflineMode as l, requestPermission as n, setEncryptedStorage as o, setAskBeforeUpload as r, setFilePermission as s, $privacy as t, setProcessingMode as u };
