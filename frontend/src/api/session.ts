/**
 * Operator belirteci deposu (F-19).
 *
 * NEREDE DURUYOR: `sessionStorage`. Bilincli bir secim ve iki gerekcesi var:
 *   1. Sekme kapaninca silinir — kontrol odasindaki paylasilan bir makinede belirtec
 *      kalici olmamali.
 *   2. localStorage'dan farkli olarak sekmeler arasi paylasilmaz.
 *
 * NE DEGIL: bu bir oturum yonetimi degildir. Belirtec YAPILANDIRMADA duran paylasilan
 * bir sirdir (bkz. backend/app/auth.py); son kullanma suresi, yenileme ve iptal yoktur.
 * Tarayici deposundaki her sey XSS'e aciktir — sahada bunun karsiligi HTTPS + kurumsal
 * SSO'dur ve docs/15 §5'te uretim farki olarak yazilidir.
 */

const KEY = "gridup.operator.token";

type Listener = () => void;
const listeners = new Set<Listener>();

function emit(): void {
  for (const listener of listeners) listener();
}

export function getToken(): string | null {
  try {
    return sessionStorage.getItem(KEY);
  } catch {
    // Gizli sekme veya depolama kapali: belirtecsiz devam edilir. Kimlik dogrulama
    // kapaliysa yigin yine calisir; aciksa kullanici 401 gorur ve giris ekrani cikar.
    return null;
  }
}

export function setToken(token: string): void {
  try {
    sessionStorage.setItem(KEY, token);
  } catch {
    // yoksayilir: asagidaki emit() yine de arayuzu tazeler
  }
  emit();
}

export function clearToken(): void {
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    // yoksayilir
  }
  emit();
}

export function onTokenChange(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Belirtec varsa Authorization basligi, yoksa bos nesne. */
export function authHeader(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}
