import nextCoreVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

const config = [
  {
    ignores: [".next/**", "test-results/**", "playwright-report/**"],
  },
  ...nextCoreVitals,
  ...nextTypescript,
];

export default config;
