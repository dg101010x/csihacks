/** Section 21.1 — no auth yet (Section 80 lands with the real backend); a static identity placeholder. */
export function UserMenu({ name = "Sarah" }: { name?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-foreground">
      <span
        aria-hidden="true"
        className="flex size-7 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground"
      >
        {name.charAt(0)}
      </span>
      <span>{name}</span>
    </div>
  );
}
