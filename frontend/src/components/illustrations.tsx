"use client";

import { useRef, useState } from "react";

export function EvidenceNetwork() {
  const ref = useRef<HTMLDivElement>(null);
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  function move(event: React.PointerEvent<HTMLDivElement>) {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width - 0.5) * 8;
    const y = ((event.clientY - rect.top) / rect.height - 0.5) * 8;
    setOffset({ x, y });
  }

  return (
    <div
      ref={ref}
      onPointerMove={move}
      onPointerLeave={() => setOffset({ x: 0, y: 0 })}
      className="hero-network"
      aria-label="Visualisasi sumber, evidence, verifikasi, dan trust yang saling terhubung"
      role="img"
    >
      <svg viewBox="0 0 620 520" className="h-full w-full" aria-hidden="true">
        <defs>
          <linearGradient id="flow" x1="0" x2="1">
            <stop offset="0%" stopColor="#7DD3C7" />
            <stop offset="100%" stopColor="#0F766E" />
          </linearGradient>
          <filter id="softShadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="14" stdDeviation="18" floodColor="#0f172a" floodOpacity="0.08" />
          </filter>
        </defs>
        <path d="M126 165 C210 88 306 120 350 210" className="network-line" />
        <path d="M505 135 C438 119 405 159 350 210" className="network-line network-line-delay" />
        <path d="M142 376 C213 397 285 339 350 268" className="network-line network-line-delay-2" />
        <path d="M510 365 C438 384 407 331 350 268" className="network-line" />
        <g transform={`translate(${offset.x * 0.5} ${offset.y * 0.5})`}>
          <circle cx="350" cy="242" r="92" fill="#ffffff" stroke="#BFE9E2" strokeWidth="2" filter="url(#softShadow)" />
          <circle cx="350" cy="242" r="67" fill="#E7F7F4" />
          <text x="350" y="231" textAnchor="middle" className="network-kicker">TRUST</text>
          <text x="350" y="258" textAnchor="middle" className="network-title">Verified</text>
        </g>
        <Node x={96 + offset.x * -0.8} y={132 + offset.y * -0.6} label="Source" number="01" />
        <Node x={475 + offset.x * 0.7} y={103 + offset.y * -0.5} label="Evidence" number="02" />
        <Node x={108 + offset.x * -0.5} y={344 + offset.y * 0.6} label="Check" number="03" />
        <Node x={479 + offset.x * 0.6} y={334 + offset.y * 0.7} label="Explain" number="04" />
      </svg>
      <div className="pointer-events-none absolute bottom-5 left-5 right-5 flex items-center justify-between gap-4 text-[11px] font-semibold uppercase tracking-[0.16em] text-secondary">
        <span>Source → Evidence</span><span>Verification → Trust</span>
      </div>
    </div>
  );
}

function Node({ x, y, label, number }: { x: number; y: number; label: string; number: string }) {
  return (
    <g transform={`translate(${x} ${y})`} className="network-node">
      <circle r="50" fill="#ffffff" stroke="#D8E6E3" strokeWidth="1.5" />
      <text y="-6" textAnchor="middle" className="network-node-number">{number}</text>
      <text y="16" textAnchor="middle" className="network-node-label">{label}</text>
    </g>
  );
}

export function NutritionVisual() {
  return (
    <svg viewBox="0 0 420 320" className="h-full w-full" role="img" aria-label="Ilustrasi piring dan kelompok makanan">
      <circle cx="210" cy="160" r="115" fill="#F7FBFA" stroke="#BFE9E2" strokeWidth="2" />
      <path d="M210 47 A113 113 0 0 1 323 160 L210 160Z" fill="#D8F3ED" />
      <path d="M323 160 A113 113 0 0 1 210 273 L210 160Z" fill="#FDEBD2" />
      <path d="M210 273 A113 113 0 0 1 97 160 L210 160Z" fill="#E8EEF9" />
      <path d="M97 160 A113 113 0 0 1 210 47 L210 160Z" fill="#F2E9D8" />
      <circle cx="210" cy="160" r="42" fill="#fff" stroke="#D8E6E3" />
      <text x="210" y="155" textAnchor="middle" className="svg-kicker">BALANCE</text>
      <text x="210" y="174" textAnchor="middle" className="svg-label">Nutrition</text>
      <circle cx="120" cy="85" r="12" fill="#0F766E" opacity=".9" />
      <circle cx="304" cy="88" r="9" fill="#E39A35" opacity=".8" />
      <circle cx="318" cy="235" r="13" fill="#2563EB" opacity=".55" />
      <circle cx="103" cy="235" r="10" fill="#B88D4B" opacity=".55" />
    </svg>
  );
}

export function BloodVisual() {
  return (
    <svg viewBox="0 0 420 320" className="h-full w-full" role="img" aria-label="Ilustrasi koneksi fasilitas dan ketersediaan darah">
      <path d="M68 236 C130 142 179 193 230 121 C274 60 334 101 360 63" fill="none" stroke="#D9E8E5" strokeWidth="2" strokeDasharray="5 8" />
      <circle cx="86" cy="217" r="34" fill="#fff" stroke="#D8E6E3" />
      <circle cx="226" cy="125" r="42" fill="#FCE8E8" stroke="#F1BFC0" />
      <circle cx="344" cy="79" r="30" fill="#fff" stroke="#D8E6E3" />
      <path d="M226 94 C244 117 250 127 250 143 C250 160 239 172 226 172 C212 172 201 161 201 144 C201 128 208 116 226 94Z" fill="#C9474C" />
      <text x="226" y="224" textAnchor="middle" className="svg-kicker">LOCATION + AVAILABILITY</text>
      <text x="226" y="247" textAnchor="middle" className="svg-label">Find blood faster</text>
    </svg>
  );
}

export function ClaimVisual() {
  return (
    <svg viewBox="0 0 420 320" className="h-full w-full" role="img" aria-label="Ilustrasi klaim yang dibandingkan dengan sumber dan evidence">
      <rect x="45" y="75" width="120" height="84" rx="16" fill="#fff" stroke="#D8E6E3" />
      <rect x="255" y="54" width="118" height="70" rx="16" fill="#E7F7F4" stroke="#BFE9E2" />
      <rect x="255" y="194" width="118" height="70" rx="16" fill="#fff" stroke="#D8E6E3" />
      <path d="M165 117 C209 117 211 89 255 89" fill="none" stroke="#0F766E" strokeWidth="2" />
      <path d="M165 117 C214 117 208 229 255 229" fill="none" stroke="#0F766E" strokeWidth="2" />
      <circle cx="207" cy="118" r="31" fill="#0F766E" />
      <path d="M195 118 l8 8 17 -18" fill="none" stroke="#fff" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
      <text x="105" y="109" textAnchor="middle" className="svg-kicker">CLAIM</text>
      <text x="105" y="132" textAnchor="middle" className="svg-label">Question</text>
      <text x="314" y="84" textAnchor="middle" className="svg-kicker">SOURCE</text>
      <text x="314" y="107" textAnchor="middle" className="svg-label">Evidence</text>
      <text x="314" y="224" textAnchor="middle" className="svg-kicker">SOURCE</text>
      <text x="314" y="247" textAnchor="middle" className="svg-label">Evidence</text>
    </svg>
  );
}
