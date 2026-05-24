# Design: Group Creation in Batch Modal, Export Format, Default Pagination

**Date:** 2026-05-24

## Overview

Three independent enhancements to the mailbox management UI:

1. Allow creating new groups directly from the batch group assignment modal
2. Change export format from CSV to txt with the same delimiter format as import
3. Default pagination to 100 items per page

---

## 1. Batch Group Select - Inline Group Creation

### Current Behavior

`GroupSelect.tsx` shows a modal with a Select dropdown listing existing groups. No way to create a new group without leaving the flow.

### Target Behavior

The Select dropdown renders a footer area (via `dropdownRender`) containing:
- A text input for the new group name
- A "+" or "添加" button to confirm creation

Flow:
1. User opens batch group modal
2. Opens the Select dropdown, sees existing groups
3. At the bottom, sees an input row: `[  输入新分组名  ] [添加]`
4. Types a name, clicks "添加"
5. Calls `groupsApi.create({ name })` (existing `POST /api/groups` endpoint)
6. On success: refreshes group list, auto-selects the newly created group
7. On 409 conflict (name exists): shows error message

### Files Changed

- `frontend/src/components/GroupSelect.tsx` — add `dropdownRender` with inline input/button, state for new group name, create handler

### No Backend Changes Required

`POST /api/groups` already handles creation with duplicate detection (409).

---

## 2. Export Backup as TXT

### Current Behavior

Backend `export_mailboxes` generates CSV with headers (`邮箱地址,密码,Client_ID,刷新令牌,分组,令牌状态`). Frontend downloads as `mailboxes.csv`.

### Target Behavior

Export produces a plain text file where each line uses the same format as import:

```
邮箱地址----密码----Client_ID----刷新令牌
```

- Separator: `----` (four hyphens)
- No header row
- No extra fields (no group, no token status)
- Content-Type: `text/plain; charset=utf-8`
- Filename: `mailboxes.txt`

### Files Changed

- `backend/app/api/mailboxes.py` (`export_mailboxes`):
  - Remove CSV writer logic
  - Build lines as `f"{email}----{password}----{client_id}----{refresh_token}"`
  - Return with `media_type="text/plain"` and `filename=mailboxes.txt`
- `frontend/src/pages/MailboxList.tsx` (`handleExport`):
  - Change `format: 'csv'` to `format: 'txt'` (or remove format param since backend now only produces one format)
  - Change download filename to `mailboxes.txt`

---

## 3. Default 100 Items Per Page

### Current Behavior

- Frontend: `pageRef` defaults to `page_size: 10`, options are `['10', '20', '50']`
- Backend: `page_size` parameter has `le=100` constraint

### Target Behavior

- Frontend: `pageRef` defaults to `page_size: 100`, options are `['50', '100', '200']`
- Backend: `page_size` constraint changes to `le=200`

### Files Changed

- `frontend/src/pages/MailboxList.tsx`:
  - `pageRef` default: `{ page: 1, page_size: 100 }`
  - `pageSizeOptions`: `['50', '100', '200']`
- `backend/app/api/mailboxes.py`:
  - `page_size: int = Query(100, ge=1, le=200)` (default and max both updated)

---

## Testing

- Group creation: open batch modal, create new group, verify it appears in list and is auto-selected; try duplicate name and verify error message
- Export: export with and without selection, open downloaded `.txt`, verify format matches import parser expectations (paste back into import to round-trip)
- Pagination: load page, verify 100 rows shown by default; switch page size to 200, verify it works
