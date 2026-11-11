/** Local UI preferences. Desktop keeps its existing keys; each web surface can isolate its own. */
let namespace = '';

export function setStorageNamespace(next: string): () => void {
  const previous = namespace;
  namespace = next;
  return () => { if (namespace === next) namespace = previous; };
}

export const appStorage = {
  getItem(key: string): string | null { return localStorage.getItem(namespace + key); },
  setItem(key: string, value: string): void { localStorage.setItem(namespace + key, value); },
  removeItem(key: string): void { localStorage.removeItem(namespace + key); },
  removePrefix(prefix: string): void {
    if (!prefix) throw new Error('A non-empty UI preference prefix is required');
    const target = namespace + prefix;
    for (let index = localStorage.length - 1; index >= 0; index--) {
      const key = localStorage.key(index);
      if (key?.startsWith(target)) localStorage.removeItem(key);
    }
  },
};
