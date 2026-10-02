import { filterSalesByLocation } from "./collections";
import type { CurrencyCode } from "./collections";
import type {
  Country,
  CountryMetrics,
  Location,
  MenuCategory,
  MenuItem,
  PaymentMethod,
  Price,
  SaleTransaction,
  WasteReason,
  WasteRecord,
} from "../types/models";

export type { CurrencyCode };

const USD_TO_COP = 4000;

export interface LocationPerformance {
  location: Location;
  score: number;
}

export interface TopSellingItem {
  item: MenuItem;
  totalSold: number;
}

export interface CountryComparison {
  Colombia: CountryMetrics;
  USA: CountryMetrics;
}

function roundToCents(value: number): number {
  return Math.round(value * 100) / 100;
}

function sameCalendarDay(left: Date, right: Date): boolean {
  return (
    left instanceof Date &&
    right instanceof Date &&
    !Number.isNaN(left.getTime()) &&
    !Number.isNaN(right.getTime()) &&
    left.getFullYear() === right.getFullYear() &&
    left.getMonth() === right.getMonth() &&
    left.getDate() === right.getDate()
  );
}

function emptyPrice(): Price {
  return { USD: 0, COP: 0 };
}

function emptyPaymentCounts(): Record<PaymentMethod, number> {
  return {
    Cash: 0,
    "Credit card": 0,
    "Debit card": 0,
    "Digital wallet": 0,
  };
}

function emptyWasteGroups(): Record<WasteReason, WasteRecord[]> {
  return {
    Expired: [],
    "Cooking error": [],
    "Customer return": [],
    Damage: [],
    Other: [],
  };
}

function emptyCategoryCounts(): Record<MenuCategory, number> {
  return {
    Meat: 0,
    Side: 0,
    Beverage: 0,
    Dessert: 0,
    Combo: 0,
  };
}

function menuItemMap(menuItems: readonly MenuItem[]): Map<string, MenuItem> {
  return new Map(menuItems.map((item) => [item.id, item]));
}

/**
 * Converts between USD and COP at 1 USD = 4000 COP.
 * Same currency returns the original amount (not re-rounded).
 */
export function convertCurrency(
  amount: number,
  fromCurrency: CurrencyCode,
  toCurrency: CurrencyCode
): number {
  if (fromCurrency === toCurrency) {
    return amount;
  }

  if (fromCurrency === "USD" && toCurrency === "COP") {
    return roundToCents(amount * USD_TO_COP);
  }

  return roundToCents(amount / USD_TO_COP);
}

/**
 * Total revenue for sales on a calendar day in the given currency.
 * Empty / no matches → 0.
 */
export function calculateDailyRevenue(
  sales: readonly SaleTransaction[],
  date: Date,
  currency: CurrencyCode
): number {
  const total = sales
    .filter((sale) => sameCalendarDay(sale.timestamp, date))
    .reduce((sum, sale) => sum + sale.totalPrice[currency], 0);

  return roundToCents(total);
}

/**
 * Profit margin % for a location:
 * ((revenue - ingredientCost * quantity) / revenue) * 100.
 * Sales without a matching menu item are omitted from both sums.
 * Zero revenue → 0.
 */
export function calculateLocationMargin(
  sales: readonly SaleTransaction[],
  menuItems: readonly MenuItem[],
  locationId: string,
  currency: CurrencyCode
): number {
  const itemsById = menuItemMap(menuItems);
  const locationSales = filterSalesByLocation([...sales], locationId);

  const { revenue, cost } = locationSales.reduce(
    (totals, sale) => {
      const item = itemsById.get(sale.itemId);
      if (!item) {
        return totals;
      }
      return {
        revenue: totals.revenue + sale.totalPrice[currency],
        cost: totals.cost + item.ingredientCost[currency] * sale.quantity,
      };
    },
    { revenue: 0, cost: 0 }
  );

  if (revenue === 0) {
    return 0;
  }

  return roundToCents(((revenue - cost) / revenue) * 100);
}

/**
 * Total waste cost for a location in the given currency.
 * Empty / no matches → 0.
 */
export function calculateWasteCost(
  wasteRecords: readonly WasteRecord[],
  locationId: string,
  currency: CurrencyCode
): number {
  const total = wasteRecords
    .filter((record) => record.locationId === locationId)
    .reduce((sum, record) => sum + record.cost[currency], 0);

  return roundToCents(total);
}

/**
 * Sum of sale totals in the given currency. Empty → 0.
 */
export function sumSaleTotals(
  sales: readonly SaleTransaction[],
  currency: CurrencyCode
): number {
  const total = sales.reduce(
    (sum, sale) => sum + sale.totalPrice[currency],
    0
  );
  return roundToCents(total);
}

/**
 * Average sale total (ticket) in the given currency. Empty → 0 (never NaN).
 */
export function calculateAverageTicket(
  sales: readonly SaleTransaction[],
  currency: CurrencyCode
): number {
  if (sales.length === 0) {
    return 0;
  }

  return roundToCents(sumSaleTotals(sales, currency) / sales.length);
}

/**
 * Menu item with the highest basePrice in currency, or null if empty.
 * Ties break by id ascending.
 */
export function findMenuItemWithMaxPrice(
  items: readonly MenuItem[],
  currency: CurrencyCode
): MenuItem | null {
  if (items.length === 0) {
    return null;
  }

  return items.reduce<MenuItem>((best, item) => {
    const bestPrice = best.basePrice[currency];
    const itemPrice = item.basePrice[currency];
    if (itemPrice > bestPrice) {
      return item;
    }
    if (itemPrice === bestPrice && item.id.localeCompare(best.id) < 0) {
      return item;
    }
    return best;
  }, items[0]);
}

/**
 * Menu item with the lowest basePrice in currency, or null if empty.
 * Ties break by id ascending.
 */
export function findMenuItemWithMinPrice(
  items: readonly MenuItem[],
  currency: CurrencyCode
): MenuItem | null {
  if (items.length === 0) {
    return null;
  }

  return items.reduce<MenuItem>((best, item) => {
    const bestPrice = best.basePrice[currency];
    const itemPrice = item.basePrice[currency];
    if (itemPrice < bestPrice) {
      return item;
    }
    if (itemPrice === bestPrice && item.id.localeCompare(best.id) < 0) {
      return item;
    }
    return best;
  }, items[0]);
}

/**
 * Count of menu items per category. Every MenuCategory key is present.
 */
export function countMenuItemsByCategory(
  items: readonly MenuItem[]
): Record<MenuCategory, number> {
  return items.reduce<Record<MenuCategory, number>>((counts, item) => {
    counts[item.category] += 1;
    return counts;
  }, emptyCategoryCounts());
}

/**
 * Count of sales per payment method. Every PaymentMethod key is present.
 */
export function countSalesByPaymentMethod(
  sales: readonly SaleTransaction[]
): Record<PaymentMethod, number> {
  return sales.reduce<Record<PaymentMethod, number>>((counts, sale) => {
    counts[sale.paymentMethod] += 1;
    return counts;
  }, emptyPaymentCounts());
}

/**
 * Top N menu items by total quantity sold (desc), then item.id asc.
 * Unknown itemIds are skipped. topN <= 0 or empty → [].
 */
export function findTopSellingItems(
  sales: readonly SaleTransaction[],
  menuItems: readonly MenuItem[],
  topN: number
): TopSellingItem[] {
  if (topN <= 0 || sales.length === 0 || menuItems.length === 0) {
    return [];
  }

  const itemsById = menuItemMap(menuItems);
  const soldByItemId = sales.reduce<Map<string, number>>((totals, sale) => {
    if (!itemsById.has(sale.itemId)) {
      return totals;
    }
    totals.set(sale.itemId, (totals.get(sale.itemId) ?? 0) + sale.quantity);
    return totals;
  }, new Map());

  return [...soldByItemId.entries()]
    .map(([itemId, totalSold]) => ({
      item: itemsById.get(itemId) as MenuItem,
      totalSold,
    }))
    .sort((left, right) => {
      if (right.totalSold !== left.totalSold) {
        return right.totalSold - left.totalSold;
      }
      return left.item.id.localeCompare(right.item.id);
    })
    .slice(0, topN);
}

/**
 * Groups waste records by reason. Every WasteReason key is present.
 */
export function groupWasteByReason(
  wasteRecords: readonly WasteRecord[]
): Record<WasteReason, WasteRecord[]> {
  return wasteRecords.reduce<Record<WasteReason, WasteRecord[]>>(
    (groups, record) => {
      groups[record.reason] = [...groups[record.reason], record];
      return groups;
    },
    emptyWasteGroups()
  );
}

/**
 * Country-level metrics for Colombia and USA.
 * Revenue uses sale.totalPrice as-is (no FX conversion).
 * menuItems is accepted per CONTEXT signature; metrics use sales + locations.
 */
export function calculateCountryComparison(
  sales: readonly SaleTransaction[],
  locations: readonly Location[],
  _menuItems: readonly MenuItem[]
): CountryComparison {
  const locationCountry = new Map(
    locations.map((location) => [location.id, location.country])
  );

  const metricsFor = (country: Country): CountryMetrics => {
    const countryLocations = locations.filter(
      (location) => location.country === country
    );
    const countrySales = sales.filter(
      (sale) => locationCountry.get(sale.locationId) === country
    );

    const totalRevenue: Price = {
      USD: roundToCents(sumSaleTotals(countrySales, "USD")),
      COP: roundToCents(sumSaleTotals(countrySales, "COP")),
    };

    const totalLocations = countryLocations.length;
    const averageRevenuePerLocation: Price =
      totalLocations === 0
        ? emptyPrice()
        : {
            USD: roundToCents(totalRevenue.USD / totalLocations),
            COP: roundToCents(totalRevenue.COP / totalLocations),
          };

    return {
      totalLocations,
      totalRevenue,
      averageRevenuePerLocation,
      totalSales: countrySales.length,
    };
  };

  return {
    Colombia: metricsFor("Colombia"),
    USA: metricsFor("USA"),
  };
}

function estimateOperatingDays(openingYear: number, now: Date = new Date()): number {
  const yearsOpen = now.getFullYear() - openingYear;
  return Math.max(1, yearsOpen * 365);
}

/**
 * Location performance score 0–100 (CONTEXT weighted formula).
 * Revenue / waste / margin components use USD.
 */
export function scoreLocationPerformance(
  location: Location,
  sales: readonly SaleTransaction[],
  wasteRecords: readonly WasteRecord[],
  menuItems: readonly MenuItem[]
): number {
  const locationSales = filterSalesByLocation([...sales], location.id);
  const totalRevenueUsd = sumSaleTotals(locationSales, "USD");
  const totalWasteUsd = calculateWasteCost(wasteRecords, location.id, "USD");

  const operatingDays = estimateOperatingDays(location.openingYear);
  const avgDailyRevenueUsd = totalRevenueUsd / operatingDays;
  const revenueScore = Math.min(40, Math.max(0, (avgDailyRevenueUsd / 1000) * 40));

  const efficiencyScore =
    location.seatingCapacity > 0
      ? Math.min(30, Math.max(0, (locationSales.length / location.seatingCapacity) * 30))
      : 0;

  let wasteScore = 0;
  if (totalRevenueUsd === 0) {
    wasteScore = totalWasteUsd === 0 ? 20 : 0;
  } else {
    const wastePercent = (totalWasteUsd / totalRevenueUsd) * 100;
    wasteScore = Math.max(0, 20 - wastePercent * 2);
  }

  const margin = calculateLocationMargin(
    sales,
    menuItems,
    location.id,
    "USD"
  );
  const marginScore = Math.min(10, Math.max(0, margin / 10));

  return roundToCents(revenueScore + efficiencyScore + wasteScore + marginScore);
}

/**
 * Scores all locations and returns them highest score first (then id asc).
 */
export function rankLocationsByPerformance(
  locations: readonly Location[],
  sales: readonly SaleTransaction[],
  wasteRecords: readonly WasteRecord[],
  menuItems: readonly MenuItem[]
): LocationPerformance[] {
  return locations
    .map((location) => ({
      location,
      score: scoreLocationPerformance(
        location,
        sales,
        wasteRecords,
        menuItems
      ),
    }))
    .sort((left, right) => {
      if (right.score !== left.score) {
        return right.score - left.score;
      }
      return left.location.id.localeCompare(right.location.id);
    });
}
