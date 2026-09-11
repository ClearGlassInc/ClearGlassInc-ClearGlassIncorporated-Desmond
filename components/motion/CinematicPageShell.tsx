import type { ReactNode } from "react";
import { AtmosphericBackground } from "./AtmosphericBackground";
import { CustomCursor } from "./CustomCursor";
import { MotionPreferenceControl } from "./MotionPreferenceControl";
import { PerformanceModeController } from "./PerformanceModeController";
import { RouteTransition } from "./RouteTransition";

/**
 * The one wrapper a route needs. Server Component: it composes the shell and
 * lets each interactive piece opt into the client boundary on its own, so the
 * page's own content stays server-rendered.
 */
export function CinematicPageShell({ children }: { children: ReactNode }): React.JSX.Element {
  return (
    <PerformanceModeController>
      <AtmosphericBackground />
      <CustomCursor />
      <RouteTransition>{children}</RouteTransition>
      <MotionPreferenceControl />
    </PerformanceModeController>
  );
}
