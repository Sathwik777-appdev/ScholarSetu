import { apiClient, errorMessage } from './client';

/** Open a wallet document (the request carries the officer's token, so it is fetched, not linked). */
export async function openDocument(id: string): Promise<void> {
  const win = window.open('', '_blank');
  try {
    const res = await apiClient.get(`/wallet/documents/${id}/content`, { responseType: 'blob' });
    const url = URL.createObjectURL(res.data as Blob);
    if (win) win.location.href = url; else window.location.href = url;
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  } catch (err) {
    win?.close();
    alert(errorMessage(err));
  }
}
