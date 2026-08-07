# PSA Live Validation Sprint - Execution Guide

**Objective:** Validate PSA Public API against readiness assessment v1.1 using real API calls and official documentation.

**Status:** Test suite created. Ready for execution on your local system.

---

## Why You Need to Run This Locally

The validation suite requires direct HTTPS access to `psacard.com`. The build/CI environment has network restrictions that prevent external API calls. You'll need to run this on your local machine where you have:

1. ✅ Network access to `api.psacard.com`
2. ✅ The PSA API key from `.env`
3. ✅ Python 3.8+

---

## How to Run the Validation Suite

### Step 1: Prepare Your Local Environment

```bash
# Clone/navigate to your Project Atlas repository
cd /path/to/sports-card-arbitrage

# Verify .env exists with PSA_API_KEY
grep PSA_API_KEY .env
# Should output: PSA_API_KEY=VsQFxLZFPRr...

# Install dependencies if needed
pip install requests python-dotenv
```

### Step 2: Run the Test Suite

```bash
python3 PSA_LIVE_VALIDATION_TEST_SUITE.py
```

### Step 3: Observe Test Output

The script will run 7 tests in sequence:

1. **Authentication** - Validates bearer token works
2. **Cert Lookups** - Tests real cert numbers
3. **Population Fields** - Checks TotalPopulation/PopulationHigher availability
4. **Invalid Cert Handling** - Tests error responses
5. **Rate Limit Evidence** - Gathers rate-limit data from responses and docs
6. **Image URL Behavior** - Validates image URL responses
7. **End User Agreement** - Documents ToS items needing review (manual)

---

## What Each Test Does

### Test 1: Authentication

**Purpose:** Validate that PSA API bearer token auth works

**What it checks:**
- PSA_API_KEY environment variable is loaded
- Bearer token is accepted by API
- Response headers are examined for rate-limit info
- Response is valid JSON

**Expected result:**
```
✓ Authentication TEST PASSED
  Conclusion: Bearer token auth works, API is reachable
  HTTP 200
  Response is valid JSON
```

**If it fails:**
- Check that PSA_API_KEY is correct in .env
- Confirm network access to api.psacard.com
- If proxy error: You may need VPN or different network

---

### Test 2 & 3: Cert Lookups & Population Fields

**Purpose:** Test real cert lookups and determine if population data is available

**What it tests:**
- Calls PSA API for 3 test cert numbers
- Extracts all fields from response
- Specifically checks TotalPopulation and PopulationHigher values

**Expected results:**
```
✓ Cert found
  Subject: Patrick Mahomes
  Grade: 10
  TotalPopulation: null  ← or a number if data exists
  PopulationHigher: null  ← or a number if data exists
```

**Key finding:**
- If TotalPopulation is `null` across all certs → Confirms assessment (population not available)
- If TotalPopulation has values → Updates assessment (population IS available)

---

### Test 4: Invalid Cert Handling

**Purpose:** Verify PSA handles invalid certs gracefully

**Tests:**
- Non-numeric cert: `INVALID`
- Too many digits: `999999999`
- Valid format but non-existent: `00000001`

**Expected responses:**
```
IsValidRequest: false
ServerMessage: Invalid CertNo
HTTP Status: 200  ← Still 200, not 4xx
```

---

### Test 5: Rate Limit Evidence

**Purpose:** Gather actual rate-limit data

**What it checks:**
1. Response headers for rate-limit info (from Test 1)
2. Official PSA documentation
3. Community reports (GitHub, Reddit)

**Expected findings:**
```
- No rate-limit headers in responses
- Official docs don't state rate limit
- Community reports: 100/day (unverified)
- Recommendation: Contact PSA for official limit
```

**Classification:**
- `CONFIRMED` - If official documentation states rate limit
- `NOT CONFIRMED` - If only community sources mention it
- `CONTRADICTED` - If different limits are reported

---

### Test 6: Image URL Behavior

**Purpose:** Validate image URLs are accessible

**What it checks:**
- ImageURL field is populated in responses
- URL format and domain
- Whether authentication is needed
- Whether front/back images are separate

**Expected findings:**
```
- URLs point to images.psacard.com
- URLs appear public (no auth on URL itself)
- Images are full slab front image
- Check ToS for storage/caching rights
```

---

### Test 7: End User Agreement Review

**Purpose:** Extract PSA ToS provisions relevant to Atlas

**This is a MANUAL step.** The script documents what to review:

1. Visit: https://www.psacard.com/publicapi
2. Find the "PSA API End User Agreement" section
3. Extract provisions for:
   - Caching API responses
   - Storing cert metadata
   - Storing/displaying PSA images
   - Commercial use
   - Derived analytics/models
   - Redistribution restrictions
   - Attribution requirements
   - Rate-limit enforcement
   - Prohibited automation/scraping

4. For each provision, classify as:
   - **ALLOWED** - No restrictions
   - **RESTRICTED** - Conditions apply (document them)
   - **PROHIBITED** - Cannot do this
   - **NOT CLEAR** - Ambiguous wording

---

## Interpreting the Report

After running the test suite, the script generates:

**File:** `PSA_LIVE_VALIDATION_REPORT.md`

### Report Sections

1. **Test Results** - What each test found
2. **Findings** - Key discoveries organized by category
3. **Errors & Issues** - Any problems encountered
4. **Recommendations** - Phase 1 go/no-go decision

---

## Critical Questions the Report Must Answer

These are the questions Atlas leadership needs answered:

### A. Can PSA Public API safely be used in Atlas Phase 1 for cert verification?

**What to look for in report:**
- ✅ Authentication test PASSED
- ✅ Cert lookups returning valid data
- ✅ No legal blockers in ToS
- ✅ Rate limit sufficient for MVP volume

**Decision criteria:**
- GREEN (Yes) - All tests pass, no ToS blockers
- YELLOW (Conditional) - Tests pass but ToS has restrictions (document them)
- RED (No) - Tests fail or ToS prohibits usage

---

### B. Which fields are reliable enough to map into CardIdentity?

**Look for in report:**
- CertNumber, CardNumber, YearIssued, Brand, Variety, Subject, Category
- CardGrade, LabelType, CardAttributes, ImageURL, IsFlagship

**These should be consistently populated across test certs.**

**Mark as UNRELIABLE if:**
- Frequently null
- Inconsistent format
- Missing from responses

---

### C. Can responses be cached/stored?

**Check End User Agreement findings for:**
- Caching restrictions
- Storage duration limits
- Data retention requirements

**Possible answers:**
- ✅ YES - No restrictions mentioned
- ⚠️ RESTRICTED - Can cache with conditions (document them)
- ❌ NO - Prohibited by ToS

---

### D. Can PSA images be displayed or stored?

**Check:**
- Image URL accessibility (Test 6)
- ToS provisions for image display/storage
- Attribution requirements

**Possible answers:**
- ✅ YES - Display with attribution
- ⚠️ RESTRICTED - Can display but not store
- ❌ NO - ToS prohibits display/caching

---

### E. Are population fields actually available?

**Check Test 2 & 3 results:**
- If TotalPopulation contains values → YES (contradicts assessment)
- If TotalPopulation is null across all certs → NO (confirms assessment)

**Conclusion determines:**
- Whether to use PSA for population (unlikely but verify)
- Whether GemRate integration is essential (likely)

---

### F. Is the documented/free rate limit sufficient for Phase 1?

**Check Test 5 findings:**
- Confirmed rate limit value
- Atlas Phase 1 volume requirements (20-50 certs/day estimate)

**Decision:**
- If limit ≥ 100/day AND Phase 1 volume ≤ 50/day → SUFFICIENT
- If limit < 100/day OR Phase 1 volume projected > limit → INSUFFICIENT (upgrade needed)

---

### G. Is there a legal or technical blocker before implementation?

**Check for:**
- Technical blockers:
  - Authentication fails → BLOCKER
  - API unreachable → BLOCKER
  - Responses malformed → BLOCKER
  - Rate-limited immediately → BLOCKER

- Legal blockers:
  - ToS prohibits commercial use → BLOCKER
  - ToS prohibits caching → BLOCKER (depends on use case)
  - ToS prohibits storage → BLOCKER (depends on use case)

**If any BLOCKER found:** Contact PSA before proceeding

---

## Next Steps After Validation

### If All Tests Pass (GREEN)

1. ✅ Accept PSA API for Phase 1 cert verification
2. ✅ Begin PSA adapter implementation
3. ✅ Implement cert caching per ToS terms
4. ✅ Confirm GemRate integration for population data

### If Some Tests Fail (YELLOW)

1. ⚠️ Document specific restrictions found
2. ⚠️ Adjust Phase 1 scope based on findings
3. ⚠️ Contact PSA for clarification on ambiguous ToS items
4. ⚠️ Plan workarounds (caching strategies, rate-limit handling)

### If Critical Tests Fail (RED)

1. ❌ Do NOT proceed with PSA integration
2. ❌ Contact PSA to resolve blockers
3. ❌ Evaluate alternative cert sources (BGS, SGC)
4. ❌ Update readiness assessment with findings

---

## What to Do If Tests Fail

### "Unable to connect to proxy" Error

**Cause:** Network restriction in your environment

**Solution:**
- Ensure you're running from a machine with direct internet access
- Not from behind a corporate proxy without proper configuration
- Try from home network if corporate network blocks API calls

### "HTTP 401 Unauthorized"

**Cause:** PSA_API_KEY is invalid or expired

**Solution:**
- Verify key in .env matches what PSA dashboard shows
- Regenerate key at https://www.psacard.com/publicapi
- Update .env with new key

### "HTTP 429 Too Many Requests"

**Cause:** Rate limit exceeded (even in validation)

**Solution:**
- Wait until next day (if daily reset)
- Contact PSA about rate limits
- Document this finding in report

### Certificate Lookup Returns Null for All Certs

**Cause:** Test certs don't exist, or you're using example numbers

**Solution:**
- Use real PSA cert numbers you know exist
- Find examples in:
  - Your own PSA graded collection
  - eBay listings with PSA numbers
  - PSA's own website/documentation
- Update `TEST_CERT_NUMBERS` in the script with valid numbers

---

## Sharing Results with Project Atlas Team

After running the validation and generating the report:

1. **Save the report:** `PSA_LIVE_VALIDATION_REPORT.md`
2. **Share findings:** Email or share the markdown report
3. **Highlight answers to the 7 critical questions** (see sections above)
4. **Flag any blockers:** Note if GREEN/YELLOW/RED
5. **Include recommendations:** What's next for Phase 1

---

## Timeline

- **Time to run:** 5-10 minutes (depending on API response times)
- **Manual review:** 15-20 minutes (for End User Agreement review)
- **Total:** ~30 minutes per validation run

---

## File Locations

- **Test Suite:** `PSA_LIVE_VALIDATION_TEST_SUITE.py`
- **Output Report:** `PSA_LIVE_VALIDATION_REPORT.md` (generated)
- **Readiness Assessment:** `PSA_API_READINESS_ASSESSMENT.md` (reference)
- **This Guide:** `PSA_VALIDATION_SPRINT_GUIDE.md`

---

## Questions?

If validation fails or produces unexpected results:

1. Check this guide for troubleshooting
2. Review the generated report for detailed findings
3. Contact PSA support: [api-support@psacard.com](mailto:api-support@psacard.com)
4. Update Project Atlas documentation with findings

---

**Status:** Ready for execution  
**Next Step:** Run `python3 PSA_LIVE_VALIDATION_TEST_SUITE.py` on your local system  
**Deliverable:** `PSA_LIVE_VALIDATION_REPORT.md` with final recommendation (GREEN/YELLOW/RED)
