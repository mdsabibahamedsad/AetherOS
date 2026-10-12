/**
 * AetherOS Design System — Accessibility Utilities
 * Helpers for WCAG 2.1 AA compliance.
 */

import React, { type HTMLAttributes, type ReactNode } from 'react';

/**
 * Generate unique IDs for aria relationships
 */
let idCounter = 0;

export function generateId(prefix = 'aetheros'): string {
  return `${prefix}-${++idCounter}-${Math.random().toString(36).slice(2, 9)}`;
}

/**
 * Focus management utilities
 */
export function trapFocus(element: HTMLElement): () => void {
  const focusableElements = element.querySelectorAll<HTMLElement>(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );

  const firstElement = focusableElements[0];
  const lastElement = focusableElements[focusableElements.length - 1];

  function handleTab(e: KeyboardEvent) {
    if (e.key !== 'Tab') {return;}

    if (e.shiftKey) {
      if (document.activeElement === firstElement) {
        e.preventDefault();
        lastElement?.focus();
      }
    } else {
      if (document.activeElement === lastElement) {
        e.preventDefault();
        firstElement?.focus();
      }
    }
  }

  element.addEventListener('keydown', handleTab);
  firstElement?.focus();

  return () => {
    element.removeEventListener('keydown', handleTab);
  };
}

/**
 * Announce to screen readers
 */
export function announce(message: string, priority: 'polite' | 'assertive' = 'polite'): void {
  const announcer = document.getElementById('aetheros-announcer') || createAnnouncer();
  announcer.setAttribute('aria-live', priority);
  announcer.textContent = message;
}

function createAnnouncer(): HTMLDivElement {
  const announcer = document.createElement('div');
  announcer.id = 'aetheros-announcer';
  announcer.setAttribute('role', 'status');
  announcer.setAttribute('aria-live', 'polite');
  announcer.setAttribute('aria-atomic', 'true');
  announcer.style.position = 'absolute';
  announcer.style.width = '1px';
  announcer.style.height = '1px';
  announcer.style.padding = '0';
  announcer.style.margin = '-1px';
  announcer.style.overflow = 'hidden';
  announcer.style.clip = 'rect(0, 0, 0, 0)';
  announcer.style.whiteSpace = 'nowrap';
  announcer.style.border = '0';
  document.body.appendChild(announcer);

  return announcer;
}

/**
 * Skip link component for keyboard navigation
 */
export function SkipLink({ href = '#main-content', children = 'Skip to main content' }: { href?: string; children?: string }) {
  return (
    <a
      className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-md focus:shadow-lg focus:font-medium"
      href={href}
    >
      {children}
    </a>
  );
}

/**
 * Visually hidden but accessible to screen readers
 */
export const srOnly = 'absolute w-px h-px p-0 -m-px overflow-hidden whitespace-nowrap border-0';
export const srOnlyFocusable = 'sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50';

/**
 * Merge refs utility
 */
export function mergeRefs<T>(...refs: Array<React.Ref<T> | undefined>): React.RefCallback<T> {
  return (value: T | null) => {
    refs.forEach((ref) => {
      if (typeof ref === 'function') {
        ref(value);
      } else if (ref != null) {
        (ref as React.MutableRefObject<T | null>).current = value;
      }
    });
  };
}

/**
 * Keyboard event helpers
 */
export const Keys = {
  Enter: 'Enter',
  Space: ' ',
  Escape: 'Escape',
  Tab: 'Tab',
  ArrowUp: 'ArrowUp',
  ArrowDown: 'ArrowDown',
  ArrowLeft: 'ArrowLeft',
  ArrowRight: 'ArrowRight',
  Home: 'Home',
  End: 'End',
  PageUp: 'PageUp',
  PageDown: 'PageDown',
  Backspace: 'Backspace',
  Delete: 'Delete',
} as const;

export function isActivationKey(key: string): boolean {
  return key === Keys.Enter || key === Keys.Space;
}

export function isNavigationKey(key: string): boolean {
  const navigationKeys: readonly string[] = [Keys.ArrowUp, Keys.ArrowDown, Keys.ArrowLeft, Keys.ArrowRight, Keys.Home, Keys.End, Keys.PageUp, Keys.PageDown];

  return navigationKeys.includes(key);
}

/**
 * ARIA attribute helpers
 */
export function getAriaProps(
  props: {
    label?: string;
    labelledBy?: string;
    describedBy?: string;
    expanded?: boolean;
    selected?: boolean;
    checked?: boolean | 'mixed';
    disabled?: boolean;
    required?: boolean;
    invalid?: boolean;
    controls?: string;
    owns?: string;
    live?: 'off' | 'polite' | 'assertive';
    atomic?: boolean;
    busy?: boolean;
    hidden?: boolean;
  }
): HTMLAttributes<HTMLElement> {
  const {
    label,
    labelledBy,
    describedBy,
    expanded,
    selected,
    checked,
    disabled,
    required,
    invalid,
    controls,
    owns,
    live,
    atomic,
    busy,
    hidden,
  } = props;

  const aria: HTMLAttributes<HTMLElement> = {};

  if (label) {aria['aria-label'] = label;}

  if (labelledBy) {aria['aria-labelledby'] = labelledBy;}

  if (describedBy) {aria['aria-describedby'] = describedBy;}

  if (expanded !== undefined) {aria['aria-expanded'] = expanded;}

  if (selected !== undefined) {aria['aria-selected'] = selected;}

  if (checked !== undefined) {aria['aria-checked'] = checked;}

  if (disabled !== undefined) {aria['aria-disabled'] = disabled;}

  if (required !== undefined) {aria['aria-required'] = required;}

  if (invalid !== undefined) {aria['aria-invalid'] = invalid;}

  if (controls) {aria['aria-controls'] = controls;}

  if (owns) {aria['aria-owns'] = owns;}

  if (live) {aria['aria-live'] = live;}

  if (atomic !== undefined) {aria['aria-atomic'] = atomic;}

  if (busy !== undefined) {aria['aria-busy'] = busy;}

  if (hidden !== undefined) {aria['aria-hidden'] = hidden;}

  return aria;
}

/**
 * Reduced motion detection
 */
export function useReducedMotion(): boolean {
  if (typeof window === 'undefined') {return false;}
  const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');

  return mediaQuery.matches;
}

/**
 * Focus visible polyfill class
 */
export const focusVisibleClass = 'focus-visible:focus-ring focus-visible:outline-none';

/**
 * Live region component
 */
export function LiveRegion({ priority = 'polite', children }: { priority?: 'polite' | 'assertive'; children: ReactNode }) {
  return (
    <div
      aria-atomic="true"
      aria-live={priority}
      className="sr-only"
      role={priority === 'assertive' ? 'alert' : 'status'}
    >
      {children}
    </div>
  );
}

export default {
  generateId,
  trapFocus,
  announce,
  SkipLink,
  srOnly,
  srOnlyFocusable,
  mergeRefs,
  Keys,
  isActivationKey,
  isNavigationKey,
  getAriaProps,
  useReducedMotion,
  focusVisibleClass,
  LiveRegion,
};