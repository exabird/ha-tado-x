# Roadmap Proposal - New Issues Review

**Date:** 2026-01-14
**Status:** Pending Validation

---

## Issue #4 - API Usage Monitoring Sensor

**Type:** Feature Request
**Author:** @TexTown
**Category:** 🎯 **ROADMAP** - High value feature
**Complexity:** ⚠️ Moderate
**Priority:** 🔴 HIGH

### Description
Create sensors to monitor API call usage and quota limits. Critical for users without Tado Auto-Assist subscription (100 requests/day limit).

### User Need
> "Without a Tado subscription I suspect it will only work for a very short period each day. To see if it stops working because the integration has hit the limit, sensors to monitor that would be great."

### Proposed Implementation

**New Sensors:**
1. **API Calls Today** - Count of API requests made since midnight
2. **API Quota Remaining** - Requests remaining (100 or 20,000 depending on subscription)
3. **API Usage Percentage** - Visual percentage (0-100%)
4. **API Reset Time** - When the quota resets (midnight)

**Technical Approach:**
- Add counter in coordinator to track API calls
- Store daily count in memory (reset at midnight)
- Create sensor entities in new sensor platform
- Add configuration option for quota limit (100 vs 20,000)

**Estimated Version:** v1.2.0

**Files to Modify:**
- `api.py` - Add call counter decorator
- `coordinator.py` - Track and reset daily counts
- `sensor.py` - Add new API usage sensors
- `const.py` - Add quota constants
- `config_flow.py` - Add quota limit option (optional)

**Estimated Development Time:** 2-3 hours

### Benefits
✅ Users can see if they're approaching quota limit
✅ Helps users decide if they need Auto-Assist
✅ Prevents unexpected service interruption
✅ Matches functionality in other Tado integrations

### Drawbacks
⚠️ Adds complexity to coordinator
⚠️ Counter accuracy depends on HA not restarting

---

## Issue #5 - Add Meter Reading Action

**Type:** Feature Request
**Author:** @kalua85
**Category:** ✅ **QUICK WIN** - Simple implementation
**Complexity:** ✅ Simple
**Priority:** 🟡 MEDIUM

### Description
Implement `tado_x.add_meter_reading` service to upload meter readings to Tado, matching the official Tado integration functionality.

### User Need
> "To automatically upload meter readings to tado"

Reference: https://www.home-assistant.io/integrations/tado#action-tadoadd_meter_reading

### Proposed Implementation

**New Service:**
- **Service Name:** `tado_x.add_meter_reading`
- **Parameters:**
  - `reading` (required): Integer value of meter reading
  - `date` (optional): Date of reading (defaults to today)

**Technical Approach:**
- API endpoint already exists in Tado API: `POST /homes/{id}/eiqMeterReadings`
- Add service definition in `services.yaml`
- Add service handler in `__init__.py`
- Update `strings.json` with translations

**Estimated Version:** v1.2.0 (can be bundled with API monitoring)

**Files to Modify:**
- `api.py` - Add `add_meter_reading()` method (might already exist!)
- `__init__.py` - Register new service
- `services.yaml` - Define service
- `strings.json` - Add translations

**Estimated Development Time:** 30 minutes

### Benefits
✅ Feature parity with official Tado integration
✅ Useful for users with Tado Energy IQ
✅ Very simple to implement

### Drawbacks
❌ Only useful for users with Energy IQ subscription
❌ Not all users have compatible meters

---

## Recommendation Summary

| Issue | Priority | Complexity | Recommend | Version |
|-------|----------|------------|-----------|---------|
| #4 - API Usage Sensor | 🔴 HIGH | ⚠️ Moderate | ✅ **YES** | v1.2.0 |
| #5 - Meter Reading | 🟡 MEDIUM | ✅ Simple | ✅ **YES** | v1.2.0 |

---

## Proposed Implementation Plan

### Version 1.2.0 - Monitoring & Energy Features

**Bundle both features together for a themed release:**

**Theme:** "Monitoring & Energy Management"

**Features:**
1. API Usage Monitoring (Issue #4)
   - 4 new sensors for API tracking
   - Visual quota management
   - Configurable limits

2. Meter Reading Service (Issue #5)
   - Upload meter readings to Tado
   - Feature parity with official integration

**Development Order:**
1. ✅ Implement meter reading service (30 min) - Quick win first
2. ⚙️ Implement API usage monitoring (2-3 hours)
3. 📝 Update documentation
4. 🧪 Test both features
5. 🚀 Release v1.2.0

**Estimated Total Time:** 3-4 hours

---

## Alternative: Phased Approach

If you prefer to release faster:

### Version 1.2.0 - Meter Reading (Quick Win)
- Implement Issue #5 only
- Release in 1 hour
- Easy win for users

### Version 1.3.0 - API Monitoring
- Implement Issue #4
- More substantial feature
- Release when ready

---

## Questions for Validation

1. **Approve both features for v1.2.0?**
   - [ ] Yes - Bundle together (recommended)
   - [ ] No - Do meter reading first (v1.2.0), API monitoring later (v1.3.0)
   - [ ] No - Reject one or both

2. **API Usage Sensor - Configuration:**
   - [ ] Add config option for quota limit
   - [ ] Auto-detect based on API behavior
   - [ ] Hardcode 100 (can adjust manually if needed)

3. **Priority Level:**
   - [ ] High - Implement ASAP
   - [ ] Medium - Implement when available
   - [ ] Low - Nice to have

---

## Notes

- Both features are valuable and requested by active users
- Issue #4 is more critical for users without Auto-Assist
- Issue #5 is simpler and provides feature parity
- Bundling both creates a strong "monitoring" themed release
- Both users seem engaged and will likely test/provide feedback
