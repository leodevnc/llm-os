const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const data = process.env.LLM_OS_TEST_DATA ||= fs.mkdtempSync(path.join(os.tmpdir(), 'llm-os-e2e-'));
module.exports = {
  testDir: './tests/browser', workers: 1, timeout: 30000,
  use: { baseURL: 'http://127.0.0.1:8898', viewport: { width: 1440, height: 1100 } },
  webServer: { command: `python3 -m llm_os --data '${data}' --port 8898`, url: 'http://127.0.0.1:8898', reuseExistingServer: false }
};
