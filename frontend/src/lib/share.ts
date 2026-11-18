/**
 * Handing a file on: the phone's share sheet (Viber, WhatsApp, mail) where the browser can share
 * files, otherwise a plain download.
 */

/** Save a file the way a download link does. */
export function saveFile(file: File): void {
  const url = URL.createObjectURL(file);
  const link = document.createElement("a");
  link.href = url;
  link.download = file.name;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30_000);
}

/**
 * - ``shared``: the share sheet sent it;
 * - ``saved``: this browser cannot share files, so it was downloaded;
 * - ``cancelled``: he closed the share sheet;
 * - ``blocked``: the browser wants a fresh tap first (making the file took too long).
 */
export type ShareResult = "shared" | "saved" | "cancelled" | "blocked";

export async function shareFile(file: File, text: string): Promise<ShareResult> {
  if (typeof navigator.canShare === "function" && navigator.canShare({ files: [file] })) {
    try {
      await navigator.share({ files: [file], title: file.name, text });
      return "shared";
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return "cancelled";
      if (error instanceof DOMException && error.name === "NotAllowedError") return "blocked";
      throw error;
    }
  }
  saveFile(file);
  return "saved";
}

/** Text only, for when no PDF can be made: the share sheet, or the clipboard. */
export async function shareText(title: string, text: string): Promise<ShareResult> {
  if (typeof navigator.share === "function") {
    try {
      await navigator.share({ title, text });
      return "shared";
    } catch {
      return "cancelled";
    }
  }
  await navigator.clipboard?.writeText(text);
  return "saved";
}
