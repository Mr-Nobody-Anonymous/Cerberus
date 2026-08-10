// Fake vulnerable JS fixture for scanner tests — values are NOT real secrets.
const GITHUB_TOKEN = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";

// High-entropy string so the entropy detector fires (test/secret-scanner.test.ts:44-49)
const SESSION_KEY = "Zx9Kq2Lp7Wm4Rt6Yn3Bv8Cf1Dg5Hj0Ns2Qw4Er6Ty8Ui0";

module.exports = { GITHUB_TOKEN, SESSION_KEY };
