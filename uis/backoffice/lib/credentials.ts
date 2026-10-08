const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export const LOGIN_PATH = "/auth/login";
export const USERS_PATH = "/users";

export const EMAIL_ERROR = "Enter a valid email (example: name@email.com)";
export const PASSWORD_ERROR = "Enter your password";

export function emailFieldError(value: string): string {
  return EMAIL_PATTERN.test(value.trim()) ? "" : EMAIL_ERROR;
}

export function passwordFieldError(value: string): string {
  return value.length > 0 ? "" : PASSWORD_ERROR;
}

export function authCredentials(
  email: string,
  password: string,
): { email: string; password: string } | null {
  if (emailFieldError(email) || passwordFieldError(password)) {
    return null;
  }
  return { email: email.trim(), password };
}

export function withoutSecret(message: string, secret: string): string {
  if (secret.length > 0 && message.includes(secret)) {
    return "That request failed. Check the details and try again.";
  }
  return message;
}
