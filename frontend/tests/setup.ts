import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: query.includes("prefers-reduced-motion"),
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

class MockIntersectionObserver implements IntersectionObserver {
  readonly root = null;
  readonly rootMargin = "0px";
  readonly thresholds = [0];
  constructor(private readonly callback: IntersectionObserverCallback) {}
  observe(target: Element) {
    this.callback([{ boundingClientRect: target.getBoundingClientRect(), intersectionRatio: 1, intersectionRect: target.getBoundingClientRect(), isIntersecting: true, rootBounds: null, target, time: 0 } as IntersectionObserverEntry], this);
  }
  unobserve() {}
  disconnect() {}
  takeRecords(): IntersectionObserverEntry[] { return []; }
}

Object.defineProperty(globalThis, "IntersectionObserver", { writable: true, value: MockIntersectionObserver });
Object.defineProperty(globalThis, "requestAnimationFrame", { writable: true, value: (callback: FrameRequestCallback) => setTimeout(() => callback(performance.now()), 0) as unknown as number });
Object.defineProperty(globalThis, "cancelAnimationFrame", { writable: true, value: (id: number) => clearTimeout(id) });
Object.defineProperty(window, "scrollTo", { writable: true, value: vi.fn() });
