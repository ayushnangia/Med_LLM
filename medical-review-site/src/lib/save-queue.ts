// Global save queue - serializes save operations to prevent concurrent writes
// that cause lost updates on Netlify Blobs (no server-side locking)
let saveQueue: Promise<void> = Promise.resolve();

export function enqueueSave<T>(saveFn: () => Promise<T>): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    saveQueue = saveQueue.then(
      () => saveFn().then(resolve, reject),
      () => saveFn().then(resolve, reject)
    );
  });
}
