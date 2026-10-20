// OpenSSH syslog lines carry no year ("Dec 10 07:13:31"), so the frozen SSH detector parses them
// with the placeholder year 2000. Show the log time as written, never as a real date in 2000 and
// never shifted into the browser's time zone (the log's time zone is unknown). The stored
// detector timestamp is unchanged; this is display only.
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export const PLACEHOLDER_YEAR = "2000";

export function sshLogTime(value?: string | null): string {
  const m = value?.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/);
  if (!m) return value || "Unknown";
  const [, year, month, day, hour, minute] = m;
  const text = `${Number(day)} ${MONTHS[Number(month) - 1]} ${hour}:${minute}`;
  return year === PLACEHOLDER_YEAR ? `${text} (year not in log)` : `${text} ${year}`;
}
