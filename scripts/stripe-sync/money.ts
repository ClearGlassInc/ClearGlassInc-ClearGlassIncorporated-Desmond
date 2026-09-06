// Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
// Proprietary and confidential. See LICENSE for terms.
/**
 * Currency and amount handling.
 *
 * Every amount that reaches Stripe is an integer in the currency's minor unit,
 * because that is the only representation `unit_amount` accepts. Source data is
 * not so disciplined — `side-store.html` lists `6.99` CAD, the store catalog
 * lists `24900` cents — so conversion happens here, once, with the rounding
 * done on the decimal *string* rather than the float. `6.99 * 100` is
 * 698.9999999999999 in IEEE-754; a catalogue that silently undercharges by a
 * cent is worse than one that refuses to sync.
 */

/** Currencies Stripe bills with no decimal places at all. */
const ZERO_DECIMAL = new Set([
  "bif", "clp", "djf", "gnf", "jpy", "kmf", "krw", "mga", "pyg",
  "rwf", "ugx", "vnd", "vuv", "xaf", "xof", "xpf",
]);

/**
 * Currencies with three decimal places. Stripe requires the minor amount to be
 * an even multiple of 10 for these, which `toMinorUnits` enforces.
 */
const THREE_DECIMAL = new Set(["bhd", "jod", "kwd", "omr", "tnd"]);

/** Stripe rejects `unit_amount` above this in every currency. */
export const MAX_UNIT_AMOUNT = 99_999_999;

export class AmountError extends Error {}

/** Number of decimal places the currency is billed with. */
export function minorUnitExponent(currency: string): number {
  const code = currency.trim().toLowerCase();
  if (ZERO_DECIMAL.has(code)) return 0;
  if (THREE_DECIMAL.has(code)) return 3;
  return 2;
}

/** Normalise and validate an ISO-4217 code into the lowercase form Stripe uses. */
export function normalizeCurrency(currency: unknown): string {
  if (typeof currency !== "string" || !/^[A-Za-z]{3}$/.test(currency.trim())) {
    throw new AmountError(`currency must be a 3-letter ISO-4217 code, got ${JSON.stringify(currency)}`);
  }
  return currency.trim().toLowerCase();
}

/**
 * Assert an amount is a Stripe-legal integer in minor units.
 *
 * Zero and negative are rejected rather than clamped: a $0 product is either a
 * data-entry mistake or a deliberate freebie, and the two need different
 * handling by a human.
 */
export function assertMinorAmount(amount: unknown, currency: string): number {
  if (typeof amount !== "number" || !Number.isFinite(amount)) {
    throw new AmountError(`amount must be a finite number of minor units, got ${JSON.stringify(amount)}`);
  }
  if (!Number.isInteger(amount)) {
    throw new AmountError(`amount must be an integer number of minor units, got ${amount}`);
  }
  if (amount <= 0) {
    throw new AmountError(`amount must be greater than zero, got ${amount}`);
  }
  if (amount > MAX_UNIT_AMOUNT) {
    throw new AmountError(`amount ${amount} exceeds Stripe's maximum unit_amount of ${MAX_UNIT_AMOUNT}`);
  }
  if (minorUnitExponent(currency) === 3 && amount % 10 !== 0) {
    throw new AmountError(
      `${currency.toUpperCase()} is a three-decimal currency; Stripe requires unit_amount to be a multiple of 10, got ${amount}`,
    );
  }
  return amount;
}

/**
 * Convert a major-unit price (`6.99`, `"2,500.00"`) to minor units.
 *
 * Works on the decimal representation so no float rounding is involved, and
 * refuses inputs with more precision than the currency can express — `1.005`
 * CAD is ambiguous, and picking a rounding direction on someone's revenue is
 * not this script's call.
 */
export function toMinorUnits(value: unknown, currency: string): number {
  const code = normalizeCurrency(currency);
  const exponent = minorUnitExponent(code);

  let text: string;
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new AmountError(`price must be a finite number, got ${value}`);
    }
    text = String(value);
  } else if (typeof value === "string") {
    text = value.trim().replace(/,/g, "");
  } else {
    throw new AmountError(`price must be a number or numeric string, got ${JSON.stringify(value)}`);
  }

  if (/e/i.test(text)) {
    // Exponential notation hides the decimal place count this check depends on.
    text = Number(text).toFixed(exponent + 1);
  }

  const match = /^(-?)(\d+)(?:\.(\d*))?$/.exec(text);
  if (!match) {
    throw new AmountError(`price is not a plain decimal number: ${JSON.stringify(value)}`);
  }
  const [, sign, whole, fraction = ""] = match;
  if (sign === "-") {
    throw new AmountError(`price must not be negative: ${JSON.stringify(value)}`);
  }
  if (fraction.length > exponent) {
    throw new AmountError(
      `price ${JSON.stringify(value)} has ${fraction.length} decimal places but ${code.toUpperCase()} bills with ${exponent}`,
    );
  }

  const padded = (whole ?? "0") + fraction.padEnd(exponent, "0");
  const minor = Number(padded);
  if (!Number.isSafeInteger(minor)) {
    throw new AmountError(`price ${JSON.stringify(value)} does not fit in a safe integer of minor units`);
  }
  return assertMinorAmount(minor, code);
}

/** Render minor units back to a human-readable major-unit string for the report. */
export function formatMinor(amount: number, currency: string): string {
  const exponent = minorUnitExponent(currency);
  if (exponent === 0) return String(amount);
  const negative = amount < 0;
  const digits = String(Math.abs(amount)).padStart(exponent + 1, "0");
  const whole = digits.slice(0, digits.length - exponent);
  const fraction = digits.slice(digits.length - exponent);
  return `${negative ? "-" : ""}${whole}.${fraction}`;
}
