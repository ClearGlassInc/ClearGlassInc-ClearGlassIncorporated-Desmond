type RequestLog = {
  event: string;
  fingerprint: string;
  path: string;
  referrer: string | null;
  timestamp: string;
  burstCount?: number;
};

export function emitSecurityLog(record: RequestLog) {
  console.info(JSON.stringify({ source: "clearglass-storefront", ...record }));
}
