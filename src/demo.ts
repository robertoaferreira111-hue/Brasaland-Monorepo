/**
 * Brasaland operations demo walker.
 * Run: npm run demo
 */

import {
  filterActiveLocations,
  filterMenuItems,
  filterMenuItemsByCategory,
  filterSales,
  filterSalesByDateRange,
  filterSalesByLocation,
  groupLocationsByStatus,
  groupMenuItemsByCategory,
  groupMenuItemsByStatus,
  sortLocationsByCapacity,
  sortLocationsByCapacityAndStaff,
  sortMenuItemsByPrice,
} from "./utils/collections";
import {
  binarySearchLocationByCapacity,
  findLocationById,
  findMenuItemByName,
} from "./utils/search";
import {
  calculateAverageTicket,
  calculateCountryComparison,
  calculateDailyRevenue,
  calculateLocationMargin,
  calculateWasteCost,
  convertCurrency,
  countMenuItemsByCategory,
  countSalesByPaymentMethod,
  findMenuItemWithMaxPrice,
  findMenuItemWithMinPrice,
  findTopSellingItems,
  groupWasteByReason,
  rankLocationsByPerformance,
  scoreLocationPerformance,
  sumSaleTotals,
} from "./utils/transformations";
import {
  validateLocation,
  validateMenuItem,
  validateSaleTransaction,
} from "./utils/validations";
import {
  invalidLocation,
  invalidMenuItem,
  invalidSaleTransaction,
  sampleLocations,
  sampleMenuItems,
  sampleSales,
  sampleWasteRecords,
} from "./types/sampleData";

function section(title: string): void {
  console.log("\n" + "=".repeat(64));
  console.log(title);
  console.log("=".repeat(64));
}

function label(name: string, value: unknown): void {
  console.log(`\n${name}`);
  console.log(value);
}

section("Brasaland operations demo");
console.log("Sample sizes:", {
  menuItems: sampleMenuItems.length,
  locations: sampleLocations.length,
  sales: sampleSales.length,
  wasteRecords: sampleWasteRecords.length,
});

section("1. Collections — filter");
label(
  "filterSalesByLocation(LOC-MEDELLIN-01)",
  filterSalesByLocation(sampleSales, "LOC-MEDELLIN-01").map((sale) => sale.id)
);
label(
  "filterSalesByDateRange(2024-03-15)",
  filterSalesByDateRange(
    sampleSales,
    new Date("2024-03-15T00:00:00"),
    new Date("2024-03-15T23:59:59")
  ).map((sale) => sale.id)
);
label(
  "filterSales({ locationId: LOC-MIAMI-01, date range Mar 15–16 })",
  filterSales(sampleSales, {
    locationId: "LOC-MIAMI-01",
    startDate: new Date("2024-03-15T00:00:00"),
    endDate: new Date("2024-03-16T23:59:59"),
  }).map((sale) => sale.id)
);
label(
  "filterMenuItemsByCategory(Meat)",
  filterMenuItemsByCategory(sampleMenuItems, "Meat").map((item) => item.id)
);
label(
  "filterMenuItems({ category: Side, status: Active, Colombia })",
  filterMenuItems(sampleMenuItems, {
    category: "Side",
    status: "Active",
    isAvailableInColombia: true,
  }).map((item) => item.id)
);
label(
  "filterActiveLocations()",
  filterActiveLocations(sampleLocations).map((location) => location.id)
);

section("2. Collections — sort");
label(
  "sortLocationsByCapacity(asc)",
  sortLocationsByCapacity(sampleLocations, "asc").map((location) => ({
    id: location.id,
    seatingCapacity: location.seatingCapacity,
  }))
);
label(
  "sortLocationsByCapacityAndStaff(desc)",
  sortLocationsByCapacityAndStaff(sampleLocations, "desc").map((location) => ({
    id: location.id,
    seatingCapacity: location.seatingCapacity,
    staffCount: location.staffCount,
  }))
);
label(
  "sortMenuItemsByPrice(USD, asc)",
  sortMenuItemsByPrice(sampleMenuItems, "USD", "asc").map((item) => ({
    id: item.id,
    USD: item.basePrice.USD,
  }))
);

section("3. Collections — group");
label(
  "groupMenuItemsByCategory() sizes",
  Object.fromEntries(
    Object.entries(groupMenuItemsByCategory(sampleMenuItems)).map(
      ([category, items]) => [category, items.length]
    )
  )
);
label(
  "groupMenuItemsByStatus() sizes",
  Object.fromEntries(
    Object.entries(groupMenuItemsByStatus(sampleMenuItems)).map(
      ([status, items]) => [status, items.length]
    )
  )
);
label(
  "groupLocationsByStatus() sizes",
  Object.fromEntries(
    Object.entries(groupLocationsByStatus(sampleLocations)).map(
      ([status, locations]) => [status, locations.length]
    )
  )
);

section("4. Search — linear and binary");
label(
  "findLocationById(LOC-MEDELLIN-01)",
  findLocationById(sampleLocations, "LOC-MEDELLIN-01")?.name ?? null
);
label(
  "findLocationById(LOC-MISSING) — not found",
  findLocationById(sampleLocations, "LOC-MISSING")
);
label(
  "findMenuItemByName('coca-cola') — case-insensitive",
  findMenuItemByName(sampleMenuItems, "coca-cola")?.id ?? null
);
label(
  "findMenuItemByName('Missing Dish') — not found",
  findMenuItemByName(sampleMenuItems, "Missing Dish")
);

const sortedByCapacity = sortLocationsByCapacity(sampleLocations, "asc");
label(
  "binarySearchLocationByCapacity(sorted, 100)",
  {
    index: binarySearchLocationByCapacity(sortedByCapacity, 100),
    locationId: sortedByCapacity[binarySearchLocationByCapacity(sortedByCapacity, 100)]?.id,
  }
);
label(
  "binarySearchLocationByCapacity(sorted, 50) — not found",
  binarySearchLocationByCapacity(sortedByCapacity, 50)
);

section("5. Transformations — reports");
label(
  "calculateDailyRevenue(2024-03-15, USD)",
  calculateDailyRevenue(sampleSales, new Date("2024-03-15T12:00:00"), "USD")
);
label(
  "calculateLocationMargin(LOC-MEDELLIN-01, USD)",
  calculateLocationMargin(
    sampleSales,
    sampleMenuItems,
    "LOC-MEDELLIN-01",
    "USD"
  )
);
label(
  "calculateWasteCost(LOC-MEDELLIN-01, USD)",
  calculateWasteCost(sampleWasteRecords, "LOC-MEDELLIN-01", "USD")
);
label("convertCurrency(1, USD → COP)", convertCurrency(1, "USD", "COP"));
label("convertCurrency(18.5, USD → USD)", convertCurrency(18.5, "USD", "USD"));
label("sumSaleTotals(USD)", sumSaleTotals(sampleSales, "USD"));
label("calculateAverageTicket(USD)", calculateAverageTicket(sampleSales, "USD"));
label(
  "findMenuItemWithMaxPrice(USD)",
  findMenuItemWithMaxPrice(sampleMenuItems, "USD")?.id ?? null
);
label(
  "findMenuItemWithMinPrice(USD)",
  findMenuItemWithMinPrice(sampleMenuItems, "USD")?.id ?? null
);
label(
  "countMenuItemsByCategory()",
  countMenuItemsByCategory(sampleMenuItems)
);
label(
  "countSalesByPaymentMethod()",
  countSalesByPaymentMethod(sampleSales)
);
label(
  "findTopSellingItems(top 3)",
  findTopSellingItems(sampleSales, sampleMenuItems, 3).map((entry) => ({
    id: entry.item.id,
    totalSold: entry.totalSold,
  }))
);
label(
  "groupWasteByReason() sizes",
  Object.fromEntries(
    Object.entries(groupWasteByReason(sampleWasteRecords)).map(
      ([reason, records]) => [reason, records.length]
    )
  )
);
label(
  "calculateCountryComparison()",
  calculateCountryComparison(sampleSales, sampleLocations, sampleMenuItems)
);
label(
  "scoreLocationPerformance(LOC-MIAMI-01)",
  scoreLocationPerformance(
    sampleLocations[1],
    sampleSales,
    sampleWasteRecords,
    sampleMenuItems
  )
);
label(
  "rankLocationsByPerformance()",
  rankLocationsByPerformance(
    sampleLocations,
    sampleSales,
    sampleWasteRecords,
    sampleMenuItems
  ).map((entry) => ({
    id: entry.location.id,
    score: entry.score,
  }))
);

section("6. Validations — valid samples");
label(
  "validateMenuItem(Picanha)",
  validateMenuItem(sampleMenuItems[0])
);
label(
  "validateSaleTransaction(TXN-2024-15482)",
  validateSaleTransaction(sampleSales[0])
);
label(
  "validateLocation(Medellín)",
  validateLocation(sampleLocations[0])
);

section("7. Validations — invalid samples");
label("validateMenuItem(invalidMenuItem)", validateMenuItem(invalidMenuItem));
label(
  "validateSaleTransaction(invalidSaleTransaction)",
  validateSaleTransaction(invalidSaleTransaction)
);
label("validateLocation(invalidLocation)", validateLocation(invalidLocation));

section("8. MenuItem validation boundary cases");
const menuBase = sampleMenuItems[0];

const menuBoundaryCases: Array<{
  name: string;
  expected: "pass" | "fail";
  actual: "pass" | "fail";
}> = [
  {
    name: "prepTimeMinutes 0",
    expected: "fail",
    actual: validateMenuItem({ ...menuBase, prepTimeMinutes: 0 }).valid
      ? "pass"
      : "fail",
  },
  {
    name: "prepTimeMinutes 1",
    expected: "pass",
    actual: validateMenuItem({ ...menuBase, prepTimeMinutes: 1 }).valid
      ? "pass"
      : "fail",
  },
  {
    name: "prepTimeMinutes 60",
    expected: "pass",
    actual: validateMenuItem({ ...menuBase, prepTimeMinutes: 60 }).valid
      ? "pass"
      : "fail",
  },
  {
    name: "prepTimeMinutes 61",
    expected: "fail",
    actual: validateMenuItem({ ...menuBase, prepTimeMinutes: 61 }).valid
      ? "pass"
      : "fail",
  },
  {
    name: "empty name",
    expected: "fail",
    actual: validateMenuItem({ ...menuBase, name: "" }).valid ? "pass" : "fail",
  },
  {
    name: "whitespace-only name",
    expected: "fail",
    actual: validateMenuItem({ ...menuBase, name: "   " }).valid
      ? "pass"
      : "fail",
  },
  {
    name: "available nowhere",
    expected: "fail",
    actual: validateMenuItem({
      ...menuBase,
      isAvailableInColombia: false,
      isAvailableInUSA: false,
    }).valid
      ? "pass"
      : "fail",
  },
  {
    name: "basePrice.USD 0",
    expected: "fail",
    actual: validateMenuItem({
      ...menuBase,
      basePrice: { USD: 0, COP: 74000 },
    }).valid
      ? "pass"
      : "fail",
  },
  {
    name: "basePrice.COP negative",
    expected: "fail",
    actual: validateMenuItem({
      ...menuBase,
      basePrice: { USD: 18.5, COP: -1 },
    }).valid
      ? "pass"
      : "fail",
  },
  {
    name: "ingredientCost 0 (not a brief price field — still pass)",
    expected: "pass",
    actual: validateMenuItem({
      ...menuBase,
      ingredientCost: { USD: 0, COP: 0 },
    }).valid
      ? "pass"
      : "fail",
  },
];

const boundaryFailures = menuBoundaryCases.filter(
  (testCase) => testCase.actual !== testCase.expected
);
console.table(menuBoundaryCases);
if (boundaryFailures.length > 0) {
  throw new Error(
    `MenuItem boundary mismatches: ${boundaryFailures
      .map((testCase) => testCase.name)
      .join(", ")}`
  );
}
console.log("MenuItem boundary cases: all matched expected pass/fail.");

section("Demo complete");
console.log("All function groups exercised. Exit cleanly.");
