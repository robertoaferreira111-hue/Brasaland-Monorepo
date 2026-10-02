import type {
  Location,
  MenuItem,
  Price,
  SaleTransaction,
} from "../types/models";

/** CONTEXT return shape for entity validators. */
export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

function isPresent<T>(value: T | null | undefined): value is T {
  return value !== null && value !== undefined;
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

/** Required non-empty string (whitespace-only counts as empty). */
export function validateRequiredString(
  value: unknown,
  fieldName: string
): string | null {
  if (!isPresent(value)) {
    return `${fieldName} is required`;
  }
  if (typeof value !== "string") {
    return `${fieldName} must be a string`;
  }
  if (value.trim() === "") {
    return `${fieldName} must not be empty`;
  }
  return null;
}

/**
 * Both USD and COP on a Price must be > 0 (CONTEXT).
 * Missing/null price or non-finite numbers produce field-specific errors.
 */
export function validatePositivePrice(
  price: Price | null | undefined,
  fieldName: string
): string[] {
  if (!isPresent(price)) {
    return [`${fieldName} is required`];
  }

  const errors: string[] = [];

  if (!isFiniteNumber(price.USD) || !(price.USD > 0)) {
    errors.push(`${fieldName}.USD must be greater than 0`);
  }
  if (!isFiniteNumber(price.COP) || !(price.COP > 0)) {
    errors.push(`${fieldName}.COP must be greater than 0`);
  }

  return errors;
}

/** MenuItem: name must not be empty. */
export function validateMenuItemName(item: MenuItem | null | undefined): string | null {
  if (!isPresent(item)) {
    return "menu item is required";
  }
  return validateRequiredString(item.name, "name");
}

/** MenuItem: prepTimeMinutes must be > 0 and <= 60. */
export function validateMenuItemPrepTime(
  item: MenuItem | null | undefined
): string | null {
  if (!isPresent(item)) {
    return "menu item is required";
  }
  if (!isFiniteNumber(item.prepTimeMinutes)) {
    return "prepTimeMinutes must be a finite number";
  }
  if (!(item.prepTimeMinutes > 0 && item.prepTimeMinutes <= 60)) {
    return "prepTimeMinutes must be greater than 0 and less than or equal to 60";
  }
  return null;
}

/** MenuItem: available in Colombia and/or USA. */
export function validateMenuItemAvailability(
  item: MenuItem | null | undefined
): string | null {
  if (!isPresent(item)) {
    return "menu item is required";
  }
  if (item.isAvailableInColombia !== true && item.isAvailableInUSA !== true) {
    return "item must be available in at least one country";
  }
  return null;
}

/** SaleTransaction: quantity must be > 0. */
export function validateSaleQuantity(
  sale: SaleTransaction | null | undefined
): string | null {
  if (!isPresent(sale)) {
    return "sale is required";
  }
  if (!isFiniteNumber(sale.quantity)) {
    return "quantity must be a finite number";
  }
  if (!(sale.quantity > 0)) {
    return "quantity must be greater than 0";
  }
  return null;
}

/** SaleTransaction: waiterName must not be empty. */
export function validateSaleWaiterName(
  sale: SaleTransaction | null | undefined
): string | null {
  if (!isPresent(sale)) {
    return "sale is required";
  }
  return validateRequiredString(sale.waiterName, "waiterName");
}

/** Location: openingYear >= 2008 and <= current year. */
export function validateLocationOpeningYear(
  location: Location | null | undefined,
  currentYear: number = new Date().getFullYear()
): string | null {
  if (!isPresent(location)) {
    return "location is required";
  }
  if (!isFiniteNumber(location.openingYear)) {
    return "openingYear must be a finite number";
  }
  if (!(location.openingYear >= 2008 && location.openingYear <= currentYear)) {
    return `openingYear must be greater than or equal to 2008 and less than or equal to ${currentYear}`;
  }
  return null;
}

/** Location: seatingCapacity must be > 0. */
export function validateLocationSeatingCapacity(
  location: Location | null | undefined
): string | null {
  if (!isPresent(location)) {
    return "location is required";
  }
  if (!isFiniteNumber(location.seatingCapacity)) {
    return "seatingCapacity must be a finite number";
  }
  if (!(location.seatingCapacity > 0)) {
    return "seatingCapacity must be greater than 0";
  }
  return null;
}

/** Location: staffCount must be > 0. */
export function validateLocationStaffCount(
  location: Location | null | undefined
): string | null {
  if (!isPresent(location)) {
    return "location is required";
  }
  if (!isFiniteNumber(location.staffCount)) {
    return "staffCount must be a finite number";
  }
  if (!(location.staffCount > 0)) {
    return "staffCount must be greater than 0";
  }
  return null;
}

function collectErrors(messages: Array<string | null | string[]>): string[] {
  return messages.flatMap((message) => {
    if (message === null) {
      return [];
    }
    return Array.isArray(message) ? message : [message];
  });
}

function toResult(errors: string[]): ValidationResult {
  return {
    valid: errors.length === 0,
    errors,
  };
}

/**
 * Validates all CONTEXT MenuItem rules.
 * Price rule ("Both USD and COP prices must be > 0") applies only to
 * basePrice — the field the brief names as a price. ingredientCost is a
 * cost field and is not checked under that rule.
 * Does not mutate the input.
 */
export function validateMenuItem(
  item: MenuItem | null | undefined
): ValidationResult {
  if (!isPresent(item)) {
    return toResult(["menu item is required"]);
  }

  return toResult(
    collectErrors([
      validateMenuItemName(item),
      validatePositivePrice(item.basePrice, "basePrice"),
      validateMenuItemPrepTime(item),
      validateMenuItemAvailability(item),
    ])
  );
}

/**
 * Validates all CONTEXT SaleTransaction rules.
 * Does not mutate the input.
 */
export function validateSaleTransaction(
  sale: SaleTransaction | null | undefined
): ValidationResult {
  if (!isPresent(sale)) {
    return toResult(["sale is required"]);
  }

  return toResult(
    collectErrors([
      validateSaleQuantity(sale),
      validatePositivePrice(sale.totalPrice, "totalPrice"),
      validateSaleWaiterName(sale),
    ])
  );
}

/**
 * Validates all CONTEXT Location rules.
 * Does not mutate the input.
 */
export function validateLocation(
  location: Location | null | undefined
): ValidationResult {
  if (!isPresent(location)) {
    return toResult(["location is required"]);
  }

  return toResult(
    collectErrors([
      validateLocationOpeningYear(location),
      validateLocationSeatingCapacity(location),
      validateLocationStaffCount(location),
      validatePositivePrice(location.monthlyRentCost, "monthlyRentCost"),
      validatePositivePrice(
        location.averageMonthlyUtilities,
        "averageMonthlyUtilities"
      ),
    ])
  );
}
