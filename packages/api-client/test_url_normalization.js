import { AarogyaApiClient, ApiError } from "./index";

function assert(condition, message) {
  if (!condition) {
    console.error(`FAIL: ${message}`);
    process.exit(1);
  }
  console.log(`PASS: ${message}`);
}

async function testUrlNormalization() {
  console.log("--- Testing API Client URL Normalization & Health Origin ---");

  // 1. Default constructor without env (Node / SSR)
  const clientDefault = new AarogyaApiClient();
  assert(
    clientDefault.getBaseUrl().endsWith("/api"),
    `Default baseUrl should end with /api, got: ${clientDefault.getBaseUrl()}`
  );

  // 2. Trailing slash trimming
  const clientTrailing = new AarogyaApiClient("https://aarogya-sahayak-backend.onrender.com/api/");
  assert(
    clientTrailing.getBaseUrl() === "https://aarogya-sahayak-backend.onrender.com/api",
    `Trailing slash should be stripped, got: ${clientTrailing.getBaseUrl()}`
  );

  // 3. Origin derivation without /api
  const clientOriginOnly = new AarogyaApiClient("https://aarogya-sahayak-backend.onrender.com");
  assert(
    clientOriginOnly.getBaseUrl() === "https://aarogya-sahayak-backend.onrender.com/api",
    `Origin-only URL should automatically get /api appended, got: ${clientOriginOnly.getBaseUrl()}`
  );
  assert(
    clientOriginOnly.getOrigin() === "https://aarogya-sahayak-backend.onrender.com",
    `Origin should be root origin, got: ${clientOriginOnly.getOrigin()}`
  );

  // 4. Test ApiError instantiation
  const err = new ApiError("Invalid credentials", "INVALID_CREDENTIALS", { field: "password" }, "req-123", 401);
  assert(err.code === "INVALID_CREDENTIALS", `ApiError code should be INVALID_CREDENTIALS, got: ${err.code}`);
  assert(err.status === 401, `ApiError status should be 401, got: ${err.status}`);
  assert(err.requestId === "req-123", `ApiError requestId should match, got: ${err.requestId}`);

  console.log("All API Client URL & error classification unit assertions PASSED.");
}

testUrlNormalization().catch((e) => {
  console.error("Test failed with unhandled error:", e);
  process.exit(1);
});
