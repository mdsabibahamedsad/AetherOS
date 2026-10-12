/**
 * Semantic Version Parser and Comparator
 * Implements strict semver parsing as per specification
 */

import type { SemanticVersion } from './types';

export function parseSemanticVersion(version: string): SemanticVersion {
  const semverRegex = /^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+([0-9A-Za-z.-]+))?$/;
  const match = version.trim().match(semverRegex);

  if (!match) {
    throw new Error(`Invalid semantic version: ${version}`);
  }

  const [, major, minor, patch, prerelease, build] = match;

  return {
    major: parseInt(major, 10),
    minor: parseInt(minor, 10),
    patch: parseInt(patch, 10),
    prerelease: prerelease || undefined,
    build: build || undefined,
    raw: version.trim(),
  };
}

export function compareVersions(a: string, b: string): number {
  const va = parseSemanticVersion(a);
  const vb = parseSemanticVersion(b);

  // Compare major.minor.patch
  if (va.major !== vb.major) {return va.major < vb.major ? -1 : 1;}

  if (va.minor !== vb.minor) {return va.minor < vb.minor ? -1 : 1;}

  if (va.patch !== vb.patch) {return va.patch < vb.patch ? -1 : 1;}

  // Handle prerelease versions (per semver spec: prerelease < release)
  const aPre = va.prerelease;
  const bPre = vb.prerelease;

  if (!aPre && !bPre) {return 0;}

  if (!aPre) {return 1;} // Release > prerelease

  if (!bPre) {return -1;}

  // Compare prerelease identifiers
  const aParts = aPre.split('.');
  const bParts = bPre.split('.');

  for (let i = 0; i < Math.max(aParts.length, bParts.length); i++) {
    const aPart = aParts[i];
    const bPart = bParts[i];

    if (aPart === undefined) {return -1;}

    if (bPart === undefined) {return 1;}

    const aNum = parseInt(aPart, 10);
    const bNum = parseInt(bPart, 10);

    const aIsNum = !isNaN(aNum);
    const bIsNum = !isNaN(bNum);

    if (aIsNum && bIsNum) {
      if (aNum !== bNum) {return aNum < bNum ? -1 : 1;}
    } else if (aIsNum) {
      return -1; // Numeric identifiers < alpha identifiers
    } else if (bIsNum) {
      return 1;
    } else {
      if (aPart !== bPart) {return aPart < bPart ? -1 : 1;}
    }
  }

  return 0;
}

export function isVersionNewer(current: string, target: string): boolean {
  return compareVersions(current, target) < 0;
}

export function isVersionOlder(current: string, target: string): boolean {
  return compareVersions(current, target) > 0;
}

export function satisfiesVersion(version: string, range: string): boolean {
  // Simple range support: ^1.2.3, ~1.2.3, >=1.2.3, <=1.2.3, >1.2.3, <1.2.3
  if (range.startsWith('^')) {
    const base = parseSemanticVersion(range.slice(1));
    const target = parseSemanticVersion(version);

    return target.major === base.major && compareVersions(version, range.slice(1)) >= 0;
  }

  if (range.startsWith('~')) {
    const base = parseSemanticVersion(range.slice(1));
    const target = parseSemanticVersion(version);

    return target.major === base.major && target.minor === base.minor && compareVersions(version, range.slice(1)) >= 0;
  }

  if (range.startsWith('>=')) {
    return compareVersions(version, range.slice(2)) >= 0;
  }

  if (range.startsWith('<=')) {
    return compareVersions(version, range.slice(2)) <= 0;
  }

  if (range.startsWith('>')) {
    return compareVersions(version, range.slice(1)) > 0;
  }

  if (range.startsWith('<')) {
    return compareVersions(version, range.slice(1)) < 0;
  }

  if (range.startsWith('=')) {
    return compareVersions(version, range.slice(1)) === 0;
  }

  // Exact match
  return compareVersions(version, range) === 0;
}

export function formatVersion(version: SemanticVersion): string {
  let result = `${version.major}.${version.minor}.${version.patch}`;

  if (version.prerelease) {result += `-${version.prerelease}`;}

  if (version.build) {result += `+${version.build}`;}

  return result;
}

export function getVersionKey(version: string): string {
  const v = parseSemanticVersion(version);

  return `${v.major}.${v.minor}.${v.patch}`;
}

export function incrementVersion(version: string, type: 'major' | 'minor' | 'patch' | 'prerelease', prereleaseId?: string): string {
  const v = parseSemanticVersion(version);

  switch (type) {
    case 'major':
      return formatVersion({ ...v, major: v.major + 1, minor: 0, patch: 0, prerelease: undefined, build: undefined });

    case 'minor':
      return formatVersion({ ...v, minor: v.minor + 1, patch: 0, prerelease: undefined, build: undefined });

    case 'patch':
      return formatVersion({ ...v, patch: v.patch + 1, prerelease: undefined, build: undefined });

    case 'prerelease':
      if (v.prerelease) {
        const parts = v.prerelease.split('.');
        const last = parts[parts.length - 1];
        const num = parseInt(last, 10);

        if (!isNaN(num)) {
          parts[parts.length - 1] = String(num + 1);

          return formatVersion({ ...v, prerelease: parts.join('.') });
        }

        return formatVersion({ ...v, prerelease: `${v.prerelease}.1` });
      }

      return formatVersion({ ...v, prerelease: `${prereleaseId || 'beta'}.1` });

    default:
      return version;
  }
}