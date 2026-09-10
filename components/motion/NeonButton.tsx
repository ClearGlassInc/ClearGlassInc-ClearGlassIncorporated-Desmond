"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";

export type NeonButtonState = "idle" | "loading" | "success" | "error";

export interface NeonButtonProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> {
  children: ReactNode;
  variant?: "primary" | "secondary";
  state?: NeonButtonState;
  /** Rendered after the label; shifts on hover. */
  withArrow?: boolean;
}

const BUSY_LABEL: Record<NeonButtonState, string | undefined> = {
  idle: undefined,
  loading: "Working…",
  success: "Done",
  error: "Something went wrong",
};

/**
 * Primary CTA. Every state is announced in text as well as colour, and the
 * button is genuinely disabled while loading so a double submit is impossible.
 */
export function NeonButton({
  children,
  variant = "primary",
  state = "idle",
  withArrow = false,
  className,
  disabled,
  ...rest
}: NeonButtonProps): React.JSX.Element {
  const busy = state === "loading";
  return (
    <button
      type="button"
      data-state={state}
      data-no-future-glass
      aria-busy={busy}
      disabled={disabled === true || busy}
      className={["cgm-btn", variant === "secondary" ? "cgm-btn--secondary" : "", className ?? ""]
        .filter(Boolean)
        .join(" ")}
      {...rest}
    >
      <span>{children}</span>
      {withArrow ? (
        <span className="cgm-btn__arrow" aria-hidden="true">
          &rarr;
        </span>
      ) : null}
      {/* Screen readers get the state as words, not just a colour change. */}
      <span className="cgm-sr">{BUSY_LABEL[state] ?? ""}</span>
    </button>
  );
}
