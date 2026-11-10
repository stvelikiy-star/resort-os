const expo = require('eslint-config-expo/flat');
module.exports = [...expo, { files: ['jest.setup.js','__tests__/**'], languageOptions: { globals: { jest: 'readonly', describe: 'readonly', it: 'readonly', test: 'readonly', expect: 'readonly', beforeEach: 'readonly', afterEach: 'readonly' } } },
  { ignores: ['node_modules/**', 'dist/**', '.expo/**', 'coverage/**'] }];
