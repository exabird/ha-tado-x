# Issue Management Workflow

This document defines the automated workflow for managing issues and feature requests in the Tado X integration.

## Workflow Steps

### 1. Detection & Collection
**Frequency:** On demand or when notified
**Action:** Collect all new issues and comments since last check

```bash
gh issue list --repo exabird/ha-tado-x --state open --limit 20
gh issue view {number} --comments
```

### 2. Analysis & Categorization

For each new issue or comment:

**Extract:**
- Issue number
- Title
- Author
- Description
- Type (bug / feature / question / enhancement)
- Priority (critical / high / medium / low)
- Complexity (simple / moderate / complex)

**Categorize:**
- ✅ **Quick Win** - Simple, high value (implement immediately)
- 🎯 **Roadmap** - Valuable, needs planning
- 🤔 **Discussion** - Needs clarification or design decision
- ❌ **Won't Fix** - Out of scope, duplicate, or not aligned
- 🐛 **Bug** - Requires immediate attention

### 3. Create Validation Summary

Generate a markdown summary for user approval:

```markdown
## New Issues Summary

### Issue #X - Title
**Type:** Feature Request
**Author:** @username
**Category:** 🎯 Roadmap
**Complexity:** Moderate
**Priority:** Medium

**Description:**
[Brief description]

**Proposed Implementation:**
[Technical approach]

**Estimated Version:** v1.X.0

**Decision:** [ ] Approve [ ] Reject [ ] Discuss
```

### 4. User Validation

Present summary to user for approval. Possible responses:
- ✅ Approve - Add to roadmap and implement
- ❌ Reject - Close with explanation
- 🤔 Discuss - Ask for clarification

### 5. Implementation

For approved items:

**A. Development**
1. Create feature branch (optional for small features)
2. Implement the feature
3. Update relevant files (api.py, coordinator.py, etc.)
4. Update strings.json with new translations
5. Test syntax and compatibility

**B. Documentation**
1. Update README.md if needed
2. Update CONTRIBUTING.md with new patterns
3. Document service in services.yaml

**C. Versioning**
- Bug fix: Patch version (1.1.X)
- New feature (minor): Minor version (1.X.0)
- Breaking change: Major version (X.0.0)

### 6. Commit & Release

**Commit Message Format:**
```
[Type] Brief description (vX.X.X)

[Detailed description]

[Technical changes]

Closes #X
```

**Release Notes Format:**
```markdown
# vX.X.X - [Title]

## What's New / Fixed
- Description

## Technical Details
- Changes made

## Update Instructions
[HACS / Manual]

Thanks to @author for [requesting/reporting]
```

### 7. Issue Response

**For Implemented Features:**
```markdown
✅ **Implemented in vX.X.X!**

[Feature description]

## How to Use
[Usage instructions]

## Update Instructions
[Update steps]

Thanks for the feature request! 🎉
```

**For Rejected Features:**
```markdown
Thank you for the suggestion!

After review, we've decided not to implement this because:
[Reason]

[Alternative suggestion if applicable]
```

**For Bugs:**
```markdown
🐛 **Bug confirmed and fixed in vX.X.X**

## Root Cause
[Explanation]

## Fix
[What was changed]

## Update Instructions
[Update steps]

Thanks for reporting! 🙏
```

### 8. Roadmap Update

Update README.md roadmap section:
- Move implemented items to "Implemented" with version
- Add new approved items to "Planned"
- Remove rejected items

## Automation Checklist

For each issue processing session:

- [ ] Collect new issues and comments
- [ ] Analyze and categorize
- [ ] Create validation summary
- [ ] Get user approval
- [ ] Implement approved items
- [ ] Update version number
- [ ] Commit with proper message
- [ ] Create release
- [ ] Respond to all issues
- [ ] Update roadmap
- [ ] Close completed issues

## Issue Categories Reference

### Quick Wins
- Simple bug fixes
- Minor UI improvements
- Documentation updates
- Translation additions

### Roadmap Features
- New entity types
- New services
- Integration with other systems
- Performance improvements

### Discussion Needed
- Architectural changes
- Breaking changes
- Features requiring design decisions
- Unclear requirements

### Won't Fix
- Duplicate issues
- Hardware limitations
- Tado API limitations
- Out of scope requests

## Version Strategy

- **Patch (1.1.X)**: Bug fixes, minor improvements
- **Minor (1.X.0)**: New features, backward compatible
- **Major (X.0.0)**: Breaking changes, major refactoring

## Response Time Goals

- **Critical bugs**: Same day
- **Non-critical bugs**: Within 3 days
- **Feature requests**: Acknowledge within 2 days, implement based on priority
- **Questions**: Within 24 hours
