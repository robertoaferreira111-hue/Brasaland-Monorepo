import type {
  Location,
  LocationStatus,
  MenuCategory,
  MenuItem,
  MenuItemStatus,
  SaleTransaction,
} from "../types/models";

export type SortOrder = "asc" | "desc";
export type CurrencyCode = "USD" | "COP";

/** Optional sale filters; provided fields are ANDed. */
export interface SaleFilterCriteria {
  locationId?: string;
  startDate?: Date;
  endDate?: Date;
}

/** Optional menu filters; provided fields are ANDed. */
export interface MenuItemFilterCriteria {
  category?: MenuCategory;
  status?: MenuItemStatus;
  isAvailableInColombia?: boolean;
  isAvailableInUSA?: boolean;
}

function isValidDate(value: Date): boolean {
  return value instanceof Date && !Number.isNaN(value.getTime());
}

/**
 * Returns sales for a location.
 * Empty input or no matches → [].
 */
export function filterSalesByLocation(
  sales: SaleTransaction[],
  locationId: string
): SaleTransaction[] {
  return sales.filter((sale) => sale.locationId === locationId);
}

/**
 * Returns sales with timestamp in [startDate, endDate] (inclusive, by ms).
 * Invalid timestamps are excluded. Reversed range → [].
 */
export function filterSalesByDateRange(
  sales: SaleTransaction[],
  startDate: Date,
  endDate: Date
): SaleTransaction[] {
  if (!isValidDate(startDate) || !isValidDate(endDate)) {
    return [];
  }

  const startMs = startDate.getTime();
  const endMs = endDate.getTime();
  if (startMs > endMs) {
    return [];
  }

  return sales.filter((sale) => {
    if (!isValidDate(sale.timestamp)) {
      return false;
    }
    const timeMs = sale.timestamp.getTime();
    return timeMs >= startMs && timeMs <= endMs;
  });
}

/**
 * Filters sales by any combination of location and/or date range.
 * Omitted criteria are ignored.
 */
export function filterSales(
  sales: SaleTransaction[],
  criteria: SaleFilterCriteria
): SaleTransaction[] {
  let result = sales;

  if (criteria.locationId !== undefined) {
    result = filterSalesByLocation(result, criteria.locationId);
  }

  if (criteria.startDate !== undefined && criteria.endDate !== undefined) {
    result = filterSalesByDateRange(result, criteria.startDate, criteria.endDate);
  } else if (criteria.startDate !== undefined) {
    result = filterSalesByDateRange(result, criteria.startDate, new Date(8640000000000000));
  } else if (criteria.endDate !== undefined) {
    result = filterSalesByDateRange(result, new Date(-8640000000000000), criteria.endDate);
  }

  return result;
}

/**
 * Returns menu items in the given category.
 */
export function filterMenuItemsByCategory(
  items: MenuItem[],
  category: MenuCategory
): MenuItem[] {
  return items.filter((item) => item.category === category);
}

/**
 * Filters menu items by any combination of category, status, and availability.
 * Omitted criteria are ignored.
 */
export function filterMenuItems(
  items: MenuItem[],
  criteria: MenuItemFilterCriteria
): MenuItem[] {
  return items.filter((item) => {
    if (criteria.category !== undefined && item.category !== criteria.category) {
      return false;
    }
    if (criteria.status !== undefined && item.status !== criteria.status) {
      return false;
    }
    if (
      criteria.isAvailableInColombia !== undefined &&
      item.isAvailableInColombia !== criteria.isAvailableInColombia
    ) {
      return false;
    }
    if (
      criteria.isAvailableInUSA !== undefined &&
      item.isAvailableInUSA !== criteria.isAvailableInUSA
    ) {
      return false;
    }
    return true;
  });
}

/**
 * Returns locations whose status is "Active".
 */
export function filterActiveLocations(locations: Location[]): Location[] {
  return locations.filter((location) => location.status === "Active");
}

/**
 * Returns a new array sorted by seatingCapacity.
 * Tie-break: location.id ascending (stable, deterministic).
 */
export function sortLocationsByCapacity(
  locations: Location[],
  order: SortOrder
): Location[] {
  const direction = order === "asc" ? 1 : -1;

  return [...locations].sort((left, right) => {
    const byCapacity =
      (left.seatingCapacity - right.seatingCapacity) * direction;
    if (byCapacity !== 0) {
      return byCapacity;
    }
    return left.id.localeCompare(right.id);
  });
}

/**
 * Returns a new array sorted by basePrice in the given currency.
 * Tie-break: item.id ascending.
 */
export function sortMenuItemsByPrice(
  items: MenuItem[],
  currency: CurrencyCode,
  order: SortOrder
): MenuItem[] {
  const direction = order === "asc" ? 1 : -1;

  return [...items].sort((left, right) => {
    const byPrice =
      (left.basePrice[currency] - right.basePrice[currency]) * direction;
    if (byPrice !== 0) {
      return byPrice;
    }
    return left.id.localeCompare(right.id);
  });
}

/**
 * Sorts locations by seatingCapacity, then staffCount, then id.
 * All fields use the same order direction; id always asc on final tie.
 */
export function sortLocationsByCapacityAndStaff(
  locations: Location[],
  order: SortOrder
): Location[] {
  const direction = order === "asc" ? 1 : -1;

  return [...locations].sort((left, right) => {
    const byCapacity =
      (left.seatingCapacity - right.seatingCapacity) * direction;
    if (byCapacity !== 0) {
      return byCapacity;
    }
    const byStaff = (left.staffCount - right.staffCount) * direction;
    if (byStaff !== 0) {
      return byStaff;
    }
    return left.id.localeCompare(right.id);
  });
}

/**
 * Groups menu items by category. Every MenuCategory key is present.
 */
export function groupMenuItemsByCategory(
  items: MenuItem[]
): Record<MenuCategory, MenuItem[]> {
  const initial: Record<MenuCategory, MenuItem[]> = {
    Meat: [],
    Side: [],
    Beverage: [],
    Dessert: [],
    Combo: [],
  };

  return items.reduce<Record<MenuCategory, MenuItem[]>>((groups, item) => {
    groups[item.category] = [...groups[item.category], item];
    return groups;
  }, initial);
}

/**
 * Groups menu items by status. Every MenuItemStatus key is present.
 */
export function groupMenuItemsByStatus(
  items: MenuItem[]
): Record<MenuItemStatus, MenuItem[]> {
  const initial: Record<MenuItemStatus, MenuItem[]> = {
    Active: [],
    Seasonal: [],
    Discontinued: [],
  };

  return items.reduce<Record<MenuItemStatus, MenuItem[]>>((groups, item) => {
    groups[item.status] = [...groups[item.status], item];
    return groups;
  }, initial);
}

/**
 * Groups locations by status. Every LocationStatus key is present.
 */
export function groupLocationsByStatus(
  locations: Location[]
): Record<LocationStatus, Location[]> {
  const initial: Record<LocationStatus, Location[]> = {
    Active: [],
    "Temporarily closed": [],
    "Under renovation": [],
  };

  return locations.reduce<Record<LocationStatus, Location[]>>(
    (groups, location) => {
      groups[location.status] = [...groups[location.status], location];
      return groups;
    },
    initial
  );
}
