import { describe, it, expect, beforeEach } from 'vitest';

// We need to reset the module between tests to get a fresh queue
// Use dynamic import to get around module caching
describe('enqueueSave', () => {
  let enqueueSave: typeof import('@/lib/save-queue').enqueueSave;

  beforeEach(async () => {
    // Reset module to get a fresh save queue
    const mod = await import('@/lib/save-queue');
    enqueueSave = mod.enqueueSave;
  });

  it('resolves with the return value of the save function', async () => {
    const result = await enqueueSave(async () => 42);
    expect(result).toBe(42);
  });

  it('resolves with complex objects', async () => {
    const review = { id: 'test', case_id: 'ncc_1', model_id: 'model_a' };
    const result = await enqueueSave(async () => review);
    expect(result).toEqual(review);
  });

  it('serializes concurrent saves - executes in order', async () => {
    const executionOrder: number[] = [];

    const save1 = enqueueSave(async () => {
      await new Promise(r => setTimeout(r, 50));
      executionOrder.push(1);
      return 'first';
    });

    const save2 = enqueueSave(async () => {
      await new Promise(r => setTimeout(r, 10));
      executionOrder.push(2);
      return 'second';
    });

    const save3 = enqueueSave(async () => {
      executionOrder.push(3);
      return 'third';
    });

    const [r1, r2, r3] = await Promise.all([save1, save2, save3]);

    expect(r1).toBe('first');
    expect(r2).toBe('second');
    expect(r3).toBe('third');
    // Even though save2 and save3 are faster, they wait for save1
    expect(executionOrder).toEqual([1, 2, 3]);
  });

  it('prevents concurrent writes that would cause lost updates', async () => {
    // Simulate the actual race condition: multiple saves reading/writing a shared store
    let sharedStore: string[] = [];

    const saveFn = (modelId: string) => async () => {
      // Simulate read-modify-write cycle
      const current = [...sharedStore]; // "read"
      await new Promise(r => setTimeout(r, Math.random() * 20)); // network delay
      current.push(modelId); // "modify"
      sharedStore = current; // "write"
      return modelId;
    };

    // Queue 5 saves - with serialization, all should persist
    const saves = [
      enqueueSave(saveFn('model_a')),
      enqueueSave(saveFn('model_b')),
      enqueueSave(saveFn('model_c')),
      enqueueSave(saveFn('model_d')),
      enqueueSave(saveFn('model_e')),
    ];

    await Promise.all(saves);

    expect(sharedStore).toHaveLength(5);
    expect(sharedStore).toEqual(['model_a', 'model_b', 'model_c', 'model_d', 'model_e']);
  });

  it('continues processing queue after an error', async () => {
    const results: string[] = [];

    const save1 = enqueueSave(async () => {
      results.push('ok1');
      return 'ok1';
    });

    const save2 = enqueueSave(async () => {
      throw new Error('save failed');
    });

    const save3 = enqueueSave(async () => {
      results.push('ok3');
      return 'ok3';
    });

    await expect(save1).resolves.toBe('ok1');
    await expect(save2).rejects.toThrow('save failed');
    await expect(save3).resolves.toBe('ok3');

    // save3 should still execute even though save2 failed
    expect(results).toEqual(['ok1', 'ok3']);
  });

  it('handles rapid sequential saves without data loss', async () => {
    let counter = 0;

    const saves = Array.from({ length: 20 }, (_, i) =>
      enqueueSave(async () => {
        const current = counter;
        await new Promise(r => setTimeout(r, 1));
        counter = current + 1;
        return i;
      })
    );

    await Promise.all(saves);

    // Without serialization, counter would be much less than 20
    // due to read-modify-write races
    expect(counter).toBe(20);
  });
});
