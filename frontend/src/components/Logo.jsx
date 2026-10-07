import { useId } from "react";

export default function Logo({ size = 32 }) {
  const gradientId = useId();
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      role="img"
      aria-label="RecomAI logo"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#8b93ff" />
          <stop offset="1" stopColor="#46d3c4" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx="16" fill="#10131a" />
      <rect
        x="2"
        y="2"
        width="60"
        height="60"
        rx="14"
        fill="none"
        stroke={`url(#${gradientId})`}
        strokeWidth="2"
        opacity="0.7"
      />
      <path
        d="M32 14l4.6 11.4L48 30l-11.4 4.6L32 46l-4.6-11.4L16 30l11.4-4.6z"
        fill={`url(#${gradientId})`}
      />
      <circle cx="47" cy="17" r="3.2" fill="#46d3c4" />
    </svg>
  );
}
