import { apiClient } from '@/lib/api';

export type PdfOptions = {
  includeMedia?: boolean;
};

export function pdfApiPath(path: string, options?: PdfOptions): string {
  if (!options?.includeMedia) {
    return path;
  }
  const separator = path.includes('?') ? '&' : '?';
  return `${path}${separator}include_media=true`;
}

/**
 * Fetch an authenticated PDF and open it in a new tab.
 *
 * Opens a blank window synchronously (user gesture), then navigates it once the
 * blob is ready. Do not pass `noopener` on that first window.open — it prevents
 * the opener from setting `popup.location`.
 */
export async function openProtectedPdf(path: string, options?: PdfOptions): Promise<void> {
  const popup = window.open('', '_blank');
  if (popup) {
    popup.document.title = 'Loading PDF…';
    popup.document.body.innerHTML =
      '<p style="font-family:system-ui,sans-serif;padding:2rem;color:#334155">Generating PDF…</p>';
  }

  try {
    const blob = await apiClient.getBlob(pdfApiPath(path, options));
    const pdfBlob =
      blob.type === 'application/pdf' ? blob : new Blob([blob], { type: 'application/pdf' });
    const url = URL.createObjectURL(pdfBlob);

    if (popup && !popup.closed) {
      popup.location.replace(url);
    } else {
      const opened = window.open(url, '_blank');
      if (!opened) {
        const link = document.createElement('a');
        link.href = url;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.click();
      }
    }

    window.setTimeout(() => URL.revokeObjectURL(url), 120_000);
  } catch (err) {
    if (popup && !popup.closed) {
      popup.close();
    }
    throw err;
  }
}
