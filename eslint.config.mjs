export default [
  {
    files: ["web/static/js/**/*.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "script",
      globals: {
        window: "readonly",
        document: "readonly",
        fetch: "readonly",
        console: "readonly",
        setInterval: "readonly",
        encodeURIComponent: "readonly",
        Date: "readonly",
        String: "readonly",
        Node: "readonly",
        EventTarget: "readonly",
        lucide: "readonly",
      },
    },
    rules: {
      "no-unused-vars": ["warn", { "argsIgnorePattern": "^_", "caughtErrorsIgnorePattern": "^_" }],
      "no-console": "off",
      "no-undef": "error",
      "semi": ["error", "always"],
    },
  },
];
