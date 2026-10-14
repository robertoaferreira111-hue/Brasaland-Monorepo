/** @type {import('ts-jest').JestConfigWithTsJest} */
module.exports = {
  preset: "ts-jest",
  testEnvironment: "node",
  testMatch: [
    "<rootDir>/lib/**/*.jest.test.ts",
    "<rootDir>/__tests__/**/*.test.ts",
  ],
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/$1",
  },
  transform: {
    "^.+\\.tsx?$": [
      "ts-jest",
      {
        tsconfig: {
          target: "ES2022",
          module: "commonjs",
          moduleResolution: "node",
          strict: true,
          esModuleInterop: true,
          isolatedModules: true,
          jsx: "react-jsx",
          baseUrl: ".",
          paths: {
            "@/*": ["./*"],
          },
        },
      },
    ],
  },
  collectCoverageFrom: [
    "lib/**/*.ts",
    "!lib/**/*.test.ts",
    "!lib/**/*.jest.test.ts",
  ],
};
