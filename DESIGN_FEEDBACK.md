# InsightAgent Design Feedback - Revision Request

**Date:** 2026-01-29
**Reviewer:** Engineering Team
**Overall Status:** Approved with revisions

---

## Summary

The designs are high-quality and capture the intended tone well. The reasoning trace panel is excellent. We need a revision pass to remove out-of-scope features and fix a few alignment issues before we begin React implementation.

---

## Required Changes

### Priority 1: Remove Out-of-Scope Features (v1)

These features are planned for future versions but should not appear in v1:

| Screen | Element to Remove | Location |
|--------|-------------------|----------|
| Welcome | Attach file button | Input field (left icon) |
| Welcome | Microphone button | Input field (right of text) |
| Welcome | Notifications bell | Header (right side) |
| Welcome | "Dashboard" nav link | Header navigation |
| Welcome | "Reports" nav link | Header navigation |
| Welcome | "Analytics" nav link | Header navigation |
| Active Chat | Left sidebar entirely | Left panel |
| Active Chat | "Share" button | Header (right side) |
| Active Chat | "Export" button | Header (right side) |
| Active Chat | Attach file button | Input field |

**Simplified Header for v1:**
```
[Logo] InsightAgent                    [3 saved findings] [User Avatar]
```

### Priority 2: Layout Corrections

#### 2.1 User Message Alignment
**Current:** User message bubble is left-aligned with avatar on left
**Required:** User message should be right-aligned

```
CURRENT (incorrect):
[Avatar] [User message bubble.............]

REQUIRED:
              [............User message bubble] [Avatar]
                                            OR
              [............User message bubble]
              (no avatar needed, just right-align)
```

#### 2.2 Simplify to 2-Panel Layout
**Current:** 3 panels (sidebar + chat + reasoning trace)
**Required:** 2 panels (chat + reasoning trace)

For v1, remove the left sidebar entirely. The layout should be:
```
┌─────────────────────────────────────────────────────┐
│  [Logo] InsightAgent        [Memory] [Avatar]       │
├────────────────────────────────┬────────────────────┤
│                                │                    │
│     Chat Messages              │  Reasoning Trace   │
│                                │                    │
├────────────────────────────────┴────────────────────┤
│  [Input field...                           ] [Send] │
└─────────────────────────────────────────────────────┘
```

### Priority 3: Content Corrections

#### 3.1 Model Name
**Current:** "InsightGPT-4.5"
**Required:** "Gemini 2.5 Flash"

This appears in the "Current Context" panel at the bottom of the reasoning trace.

#### 3.2 Session Title
**Current:** "West Region Performance" with "LIVE QUERY" badge
**Required:** Simpler approach - either:
- No title bar (chat speaks for itself), OR
- "New Session" / timestamp format like "Session - Jan 29, 2:30 PM"

The current design makes it look like a report rather than a chat interface.

---

## Optional Enhancements (Nice to Have)

These are not blockers but would improve the design:

1. **Character count indicator** on input field showing "0 / 4,000"
2. **"Learn more" button** in reasoning panel empty state - clarify where this links (or remove if no destination)
3. **History icon** in header - keep this one (useful for session history)

---

## What's Perfect - Don't Change

These elements are excellent and should be preserved exactly:

1. **Reasoning trace step design** - checkmarks, spinners, grayed upcoming steps
2. **SQL query display** with monospace font
3. **Row count badges** ("42 rows returned")
4. **Step timing** (0.2s, 1.4s)
5. **Progress bar** on active step
6. **Data table styling** with color-coded percentages
7. **Follow-up suggestion chips** design
8. **"Save this insight" button** styling
9. **Current context panel** (model, latency, tokens)
10. **Color palette** (#137fec primary blue)
11. **Typography** (Manrope font)
12. **Dark mode implementation**
13. **Welcome screen question cards**
14. **"3 saved findings" memory indicator**

---

## Deliverable Request

Please provide updated versions of both screens with the changes above:

1. **Welcome Screen v2** - Simplified header, no attach/mic buttons
2. **Active Chat v2** - 2-panel layout, right-aligned user messages, correct model name

Format: Same as before (screen.png + code.html)

---

## Questions for Designer

1. For mobile (<768px), should the reasoning trace become a collapsible bottom sheet or a slide-out drawer?
2. Any preference on the streaming text animation (cursor blink vs. fade-in)?

---

*Please reach out if any of these changes are unclear. We're excited to move to implementation!*
