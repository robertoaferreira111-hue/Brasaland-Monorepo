import type { Location, MenuItem } from "../types/models";

/**
 * Duplicate-key policy:
 * - Linear search returns the first matching element (lowest index).
 * - Binary search returns the leftmost matching index when duplicates exist.
 * Callers that need every match should filter, not search.
 */

export type KeySelector<T, K> = (item: T) => K;
export type Comparator<K> = (left: K, right: K) => number;

/**
 * Linear search over an unsorted array.
 * Returns the first element whose selected key equals target, or null.
 */
export function linearSearch<T, K>(
  items: readonly T[],
  target: K,
  selectKey: KeySelector<T, K>,
  equals: (left: K, right: K) => boolean = Object.is
): T | null {
  for (let index = 0; index < items.length; index += 1) {
    const item = items[index];
    if (equals(selectKey(item), target)) {
      return item;
    }
  }
  return null;
}

/**
 * Binary search over an array already sorted ascending by the selected key.
 * Precondition is explicit in the parameter name `sortedAscending`.
 * Returns the leftmost matching index, or -1 when not found.
 * Does not sort or mutate the input.
 */
export function binarySearchIndex<T, K>(
  sortedAscending: readonly T[],
  target: K,
  selectKey: KeySelector<T, K>,
  compare: Comparator<K>
): number {
  let low = 0;
  let high = sortedAscending.length - 1;
  let foundIndex = -1;

  while (low <= high) {
    const mid = low + Math.floor((high - low) / 2);
    const midKey = selectKey(sortedAscending[mid]);
    const ordering = compare(midKey, target);

    if (ordering === 0) {
      foundIndex = mid;
      high = mid - 1;
    } else if (ordering < 0) {
      low = mid + 1;
    } else {
      high = mid - 1;
    }
  }

  return foundIndex;
}

/**
 * Linear search for a location by id.
 * Returns the location if found, otherwise null.
 */
export function findLocationById(
  locations: readonly Location[],
  id: string
): Location | null {
  return linearSearch(locations, id, (location) => location.id);
}

/**
 * Linear search for a menu item by name (case-insensitive).
 * Returns the first matching item, otherwise null.
 */
export function findMenuItemByName(
  items: readonly MenuItem[],
  name: string
): MenuItem | null {
  const target = name.toLowerCase();
  return linearSearch(
    items,
    target,
    (item) => item.name.toLowerCase(),
    (left, right) => left === right
  );
}

/**
 * Binary search on locations already sorted by seatingCapacity ascending.
 * Returns the leftmost index with the target capacity, or -1.
 * Does not sort the caller's array.
 */
export function binarySearchLocationByCapacity(
  sortedLocations: readonly Location[],
  targetCapacity: number
): number {
  return binarySearchIndex(
    sortedLocations,
    targetCapacity,
    (location) => location.seatingCapacity,
    (left, right) => left - right
  );
}
