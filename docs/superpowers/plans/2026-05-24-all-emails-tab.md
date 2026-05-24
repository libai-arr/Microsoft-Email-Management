# "All Emails" Tab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "全部" tab to the email viewer that merges Inbox and JunkEmail into one sorted list, with junk-source tagging.

**Architecture:** The API layer (`emails.py`) gains a `folder="all"` code path that fires two concurrent calls to `GraphClient.list_emails` (one for inbox, one for junk), merges and sorts the results, and tags each message with its source folder. `GraphClient` is unchanged. Frontend adds the tab and renders a `<Tag>` for junk-sourced items.

**Tech Stack:** Python/FastAPI, Microsoft Graph API, React/TypeScript, Ant Design

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `backend/app/schemas/email.py:6-13` | Add `folder` field to `EmailSummary` |
| Modify | `backend/app/api/emails.py:27-67` | Handle `folder=all` with two concurrent GraphClient calls, merge, tag |
| Modify | `backend/tests/test_api_emails.py` | Add tests for `folder=all` and `folder` field |
| Modify | `frontend/src/types/index.ts:34-42` | Add `folder` field to `EmailSummary` |
| Modify | `frontend/src/components/EmailViewer.tsx` | Add "全部" tab, junk tag rendering |

**Not modified:** `backend/app/services/graph_client.py` (stays as-is, called twice for "all"), `frontend/src/hooks/useEmails.ts`, `frontend/src/services/api.ts`

---

### Task 1: Backend Schema — Add `folder` field to `EmailSummary`

**Files:**
- Modify: `backend/app/schemas/email.py:6-13`

- [ ] **Step 1: Add `folder` field**

In `backend/app/schemas/email.py`, add `folder` as the last field in `EmailSummary`:

```python
class EmailSummary(BaseModel):
    id: str
    subject: str
    sender_name: str
    sender_email: str
    preview: str
    received_at: datetime
    is_read: bool
    folder: str | None = None
```

- [ ] **Step 2: Verify no breakage**

Run: `cd backend && python -m pytest tests/test_api_emails.py -v`

Expected: All existing tests pass. The new field defaults to `None` so existing code is unaffected.

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/email.py
git commit -m "feat: add folder field to EmailSummary schema"
```

---

### Task 2: Backend API — Support `folder=all` with merge logic

**Files:**
- Modify: `backend/app/api/emails.py:1-67`
- Modify: `backend/tests/test_api_emails.py`

- [ ] **Step 1: Write failing tests**

Add these fixtures and test class to `backend/tests/test_api_emails.py`, after the existing `MOCK_BODY_RESPONSE` dict:

```python
MOCK_LIST_INBOX = {
    "value": [
        {
            "id": "msg-inbox-1",
            "subject": "Inbox Email",
            "from": {"emailAddress": {"name": "Alice", "address": "alice@test.com"}},
            "bodyPreview": "Hello from inbox",
            "receivedDateTime": "2026-05-23T12:00:00Z",
            "isRead": False,
        },
    ]
}

MOCK_LIST_JUNK = {
    "value": [
        {
            "id": "msg-junk-1",
            "subject": "Junk Email",
            "from": {"emailAddress": {"name": "Spammer", "address": "spam@test.com"}},
            "bodyPreview": "Buy now!",
            "receivedDateTime": "2026-05-23T14:00:00Z",
            "isRead": True,
        },
    ]
}
```

Add this test class at the end of the file:

```python
class TestEmailListAllFolder:
    @patch("app.api.emails.GraphClient")
    async def test_list_all_merges_and_sorts(self, MockGraph, client: AsyncClient):
        mid = await _import_one(client)
        instance = MockGraph.return_value

        async def fake_list(cid, rt, mid_str, **kwargs):
            f = kwargs.get("folder", "inbox")
            if f == "inbox":
                return MOCK_LIST_INBOX
            elif f == "junk":
                return MOCK_LIST_JUNK
            raise ValueError(f"unexpected folder: {f}")

        instance.list_emails = AsyncMock(side_effect=fake_list)

        resp = await client.get(f"/api/mailboxes/{mid}/emails?folder=all")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        # Junk (14:00) is newer than inbox (12:00)
        assert data[0]["id"] == "msg-junk-1"
        assert data[0]["folder"] == "junk"
        assert data[1]["id"] == "msg-inbox-1"
        assert data[1]["folder"] == "inbox"

    @patch("app.api.emails.GraphClient")
    async def test_single_folder_has_null_folder_field(self, MockGraph, client: AsyncClient):
        mid = await _import_one(client)
        instance = MockGraph.return_value
        instance.list_emails = AsyncMock(return_value=MOCK_LIST_RESPONSE)

        resp = await client.get(f"/api/mailboxes/{mid}/emails?folder=inbox")
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["folder"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_api_emails.py::TestEmailListAllFolder -v`

Expected: FAIL — `folder=all` is not handled yet; the API passes `"all"` straight to GraphClient which falls back to Inbox, and `folder` field won't be set.

- [ ] **Step 3: Implement merge logic in API layer**

Replace the entire `list_emails` endpoint function in `backend/app/api/emails.py` with:

```python
import asyncio

# ... existing imports stay ...

@router.get("/{mailbox_id}/emails", response_model=list[EmailSummary])
async def list_emails(
    mailbox_id: UUID,
    folder: str = Query("inbox"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    crypto: CryptoService = Depends(get_crypto),
    redis=Depends(get_redis),
):
    mailbox, client_id, refresh_token = await _get_mailbox_creds(mailbox_id, db, crypto)
    graph = GraphClient(redis)

    try:
        if folder == "all":
            inbox_data, junk_data = await asyncio.gather(
                graph.list_emails(
                    client_id, refresh_token, str(mailbox_id),
                    folder="inbox", page=page, page_size=page_size, search=search,
                ),
                graph.list_emails(
                    client_id, refresh_token, str(mailbox_id),
                    folder="junk", page=page, page_size=page_size, search=search,
                ),
            )
            inbox_msgs = [
                {**msg, "_folder": "inbox"} for msg in inbox_data.get("value", [])
            ]
            junk_msgs = [
                {**msg, "_folder": "junk"} for msg in junk_data.get("value", [])
            ]
            all_msgs = sorted(
                inbox_msgs + junk_msgs,
                key=lambda m: m["receivedDateTime"],
                reverse=True,
            )[:page_size]
        else:
            data = await graph.list_emails(
                client_id, refresh_token, str(mailbox_id),
                folder=folder, page=page, page_size=page_size, search=search,
            )
            all_msgs = data.get("value", [])
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error(
            f"Graph API list_emails failed for mailbox {mailbox_id}: {type(exc).__name__}: {exc}",
            exc_info=True,
        )
        raise HTTPException(status_code=502, detail=f"Graph API 调用失败: {exc}")

    is_all = folder == "all"
    emails = []
    for msg in all_msgs:
        sender = msg.get("from", {}).get("emailAddress", {})
        emails.append(EmailSummary(
            id=msg["id"],
            subject=msg.get("subject", ""),
            sender_name=sender.get("name", ""),
            sender_email=sender.get("address", ""),
            preview=msg.get("bodyPreview", ""),
            received_at=msg["receivedDateTime"],
            is_read=msg.get("isRead", False),
            folder=msg.get("_folder") if is_all else None,
        ))

    return emails
```

- [ ] **Step 4: Run all email tests**

Run: `cd backend && python -m pytest tests/test_api_emails.py -v`

Expected: All 4 tests pass (2 existing + 2 new).

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/emails.py backend/tests/test_api_emails.py
git commit -m "feat: support folder=all with merged inbox+junk in email list API"
```

---

### Task 3: Frontend — Add "全部" tab and junk source tag

**Files:**
- Modify: `frontend/src/types/index.ts:34-42`
- Modify: `frontend/src/components/EmailViewer.tsx`

- [ ] **Step 1: Add `folder` field to frontend `EmailSummary` type**

In `frontend/src/types/index.ts`, add `folder` to `EmailSummary`:

```typescript
export interface EmailSummary {
  id: string;
  subject: string;
  sender_name: string;
  sender_email: string;
  preview: string;
  received_at: string;
  is_read: boolean;
  folder?: string;
}
```

- [ ] **Step 2: Add `Tag` import in EmailViewer**

In `frontend/src/components/EmailViewer.tsx`, update the antd import (line 2) from:

```typescript
import { Modal, Tabs, Input, Button, List, Spin, Empty, Typography } from 'antd';
```

to:

```typescript
import { Modal, Tabs, Input, Button, List, Spin, Empty, Typography, Tag } from 'antd';
```

- [ ] **Step 3: Change default folder to `'all'`**

Change line 17 from:

```typescript
const [folder, setFolder] = useState<string>('inbox');
```

to:

```typescript
const [folder, setFolder] = useState<string>('all');
```

- [ ] **Step 4: Add "全部" tab as first item**

Change the Tabs items (lines 56-59) from:

```typescript
items={[
  { key: 'inbox', label: '收件箱' },
  { key: 'junk', label: '垃圾箱' },
]}
```

to:

```typescript
items={[
  { key: 'all', label: '全部' },
  { key: 'inbox', label: '收件箱' },
  { key: 'junk', label: '垃圾箱' },
]}
```

- [ ] **Step 5: Add junk source tag in email list item**

In the email list item rendering, change the sender name div (lines 91-97) from:

```typescript
<div style={{
  fontWeight: item.is_read ? 'normal' : 600,
  fontSize: 13, marginBottom: 2,
  whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
}}>
  {item.sender_name || item.sender_email}
</div>
```

to:

```typescript
<div style={{
  fontWeight: item.is_read ? 'normal' : 600,
  fontSize: 13, marginBottom: 2,
  whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
  display: 'flex', alignItems: 'center', gap: 4,
}}>
  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>
    {item.sender_name || item.sender_email}
  </span>
  {item.folder === 'junk' && (
    <Tag color="red" style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px', flexShrink: 0 }}>
      垃圾箱
    </Tag>
  )}
</div>
```

- [ ] **Step 6: Verify in browser**

Run the dev server: `cd frontend && npm run dev`

Open the app, click a mailbox's email viewer:
1. "全部" tab appears first and is selected by default
2. Emails from both inbox and junk appear, sorted newest first
3. Junk-sourced emails show a red "垃圾箱" tag next to sender name
4. Switch to "收件箱" — only inbox emails, no folder tag
5. Switch to "垃圾箱" — only junk emails, no folder tag
6. Search works on all three tabs
7. Refresh button works on all three tabs

- [ ] **Step 7: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/components/EmailViewer.tsx
git commit -m "feat: add All tab with junk source tagging in email viewer"
```
