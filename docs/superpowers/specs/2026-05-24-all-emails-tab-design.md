# All Emails Tab Design

## Overview

Add an "全部" (All) tab to the email viewer that shows merged emails from Inbox and JunkEmail folders, sorted by most recent first. The tab appears to the left of the existing "收件箱" and "垃圾箱" tabs. Emails from JunkEmail are marked with a tag in the "全部" view.

## Requirements

1. Add "全部" tab as the first tab (leftmost), followed by "收件箱" and "垃圾箱"
2. "全部" tab shows emails from both Inbox and JunkEmail, merged and sorted by `receivedDateTime desc`
3. In "全部" tab, emails originating from JunkEmail display a red "垃圾箱" tag next to the sender name
4. Inbox-originating emails in the "全部" tab have no source tag (inbox is the default/expected source)
5. All three tabs sort emails by most recent first (already implemented for inbox/junk)
6. Default active tab on open is "全部"

## Backend Changes

### Schema: `backend/app/schemas/email.py`

Add optional `folder` field to `EmailSummary`:

```python
class EmailSummary(BaseModel):
    id: str
    subject: str
    sender_name: str
    sender_email: str
    preview: str
    received_at: datetime
    is_read: bool
    folder: str | None = None  # "inbox" or "junk", populated only when folder=all
```

### Graph Client: `backend/app/services/graph_client.py`

Modify `list_emails` to handle `folder="all"`:

- When `folder="all"`:
  - Use `asyncio.gather` to concurrently fetch from both Inbox and JunkEmail
  - Each sub-request uses the same `page_size` and `skip` parameters
  - Tag each message with its source folder (`"inbox"` or `"junk"`)
  - Merge both result sets, sort by `receivedDateTime desc`
  - Return the first `page_size` items
  - Return value includes a `_folder` key on each message dict for the API layer to read
- When `folder` is `"inbox"` or `"junk"`: behavior unchanged

### API: `backend/app/api/emails.py`

- `folder` query parameter accepts `"all"`, `"inbox"`, or `"junk"` (default: `"inbox"`)
- When `folder="all"`, read the `_folder` key from each message dict to populate `EmailSummary.folder`
- When `folder` is `"inbox"` or `"junk"`, `EmailSummary.folder` remains `None`

## Frontend Changes

### Type: `frontend/src/types/index.ts`

Add optional `folder` field to `EmailSummary`:

```typescript
export interface EmailSummary {
  id: string;
  subject: string;
  sender_name: string;
  sender_email: string;
  preview: string;
  received_at: string;
  is_read: boolean;
  folder?: string;  // "inbox" or "junk", present only in "all" tab
}
```

### Component: `frontend/src/components/EmailViewer.tsx`

1. Change `folder` initial state from `'inbox'` to `'all'`
2. Update Tabs items to include "全部" as the first tab:
   ```typescript
   items={[
     { key: 'all', label: '全部' },
     { key: 'inbox', label: '收件箱' },
     { key: 'junk', label: '垃圾箱' },
   ]}
   ```
3. In the email list item rendering, when `item.folder === 'junk'`, show a red Ant Design `<Tag>` with text "垃圾箱" next to the sender name
4. Import `Tag` from `antd`

### No changes needed

- `frontend/src/hooks/useEmails.ts` — `folder` param already passed through
- `frontend/src/services/api.ts` — `folder` param already passed through
- Sorting — already `receivedDateTime desc` on backend
- Search — works the same, applied to each sub-request in "all" mode

## Pagination Note

For the "all" tab, each sub-folder request uses the same `page` and `page_size` parameters. The merged result takes the top `page_size` items. This is an approximation — deep pagination may not be perfectly accurate if one folder has significantly more emails than the other. This is acceptable because the current UI does not expose pagination controls (loads a single page of 20).
