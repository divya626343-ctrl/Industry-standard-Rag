import { useState, useRef, useEffect } from "react";
import type { ChunkingStrategy } from "../types";
import { DropdownChevronIcon, LockIcon } from "./icons/icons";

const STRATEGIES: { value: ChunkingStrategy; label: string }[] = [
  { value: "recursive_token", label: "Recursive token" },
  { value: "semantic", label: "Semantics" },
  { value: "fixed", label: "Fixed" },
];

interface Props {
  value: ChunkingStrategy | null;
  locked: boolean;
  onChange: (s: ChunkingStrategy) => void;
}

export function StrategyDropdown({ value, locked, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const label = value ? STRATEGIES.find((s) => s.value === value)?.label : "chunking strategy";

  return (
    <div className="strategy-dropdown" ref={ref}>
      <button
        className={`strategy-dropdown-trigger${locked ? " locked" : ""}`}
        onClick={() => !locked && setOpen((o) => !o)}
        disabled={locked}
      >
        {locked && <LockIcon size={12} style={{ marginRight: 6, color: "var(--text-secondary)" }} />}
        <span>{label}</span>
        {!locked && <DropdownChevronIcon size={16} style={{ marginLeft: 6 }} />}
      </button>

      {open && !locked && (
        <div className="strategy-dropdown-menu">
          {STRATEGIES.map((s) => (
            <div
              key={s.value}
              className={`strategy-dropdown-option${s.value === value ? " selected" : ""}`}
              onClick={() => {
                onChange(s.value);
                setOpen(false);
              }}
            >
              {s.label}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
