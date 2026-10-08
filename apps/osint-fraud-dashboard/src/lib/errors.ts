export class AuthenticationRequiredError extends Error {
  readonly status = 401;
  constructor() {
    super("Sign in required");
  }
}

export class ForbiddenError extends Error {
  readonly status = 403;
  constructor(message = "You do not have permission for this action") {
    super(message);
  }
}

export class NotFoundError extends Error {
  readonly status = 404;
}

export class ValidationError extends Error {
  readonly status = 422;
  constructor(
    message: string,
    readonly issues: string[] = [],
  ) {
    super(message);
  }
}

export function errorMessage(err: unknown): string {
  if (err instanceof ValidationError && err.issues.length) return `${err.message}: ${err.issues.join("; ")}`;
  if (err instanceof Error) return err.message;
  return "Unexpected error";
}
