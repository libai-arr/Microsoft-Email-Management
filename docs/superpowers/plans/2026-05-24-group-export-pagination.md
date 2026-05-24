# Group Creation, Export Format & Pagination Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add inline group creation in the batch modal, change export to txt with `----` delimiter, and default pagination to 100/page.

**Architecture:** Three independent changes touching the same frontend page (`MailboxList.tsx`) and one backend file (`api/mailboxes.py`), plus the `GroupSelect` component. No new files needed.

**Tech Stack:** React + Ant Design (frontend), FastAPI + SQLAlchemy (backend), pytest + httpx (tests)

---

### Task 1: Backend — Change export format to txt with `----` separator

**Files:**
- Modify: `backend/app/api/mailboxes.py:105-145`
- Modify: `backend/tests/test_api_mailboxes.py:107-118`

- [ ] **Step 1: Update the export test to expect txt format**

Replace the existing `TestMailboxExport` class in `backend/tests/test_api_mailboxes.py`:

```python
class TestMailboxExport:
    async def test_export_txt_format(self, client: AsyncClient):
        await _import_sample(client, 2)
        resp = await client.post(
            "/api/mailboxes/export",
            json={"include_all": True},
        )
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]
        assert "mailboxes.txt" in resp.headers["content-disposition"]
        lines = resp.text.strip().split("\n")
        assert len(lines) == 2  # no header, just 2 data rows
        parts = lines[0].split("----")
        assert len(parts) == 4
        assert parts[0] == "user0@outlook.com"
        assert parts[1] == "pass0"
        assert parts[2] == "cid0"
        assert parts[3] == "rt0"

    async def test_export_selected_ids(self, client: AsyncClient):
        await _import_sample(client, 3)
        listing = await client.get("/api/mailboxes")
        first_id = listing.json()["items"][0]["id"]
        resp = await client.post(
            "/api/mailboxes/export",
            json={"ids": [first_id], "include_all": False},
        )
        assert resp.status_code == 200
        lines = resp.text.strip().split("\n")
        assert len(lines) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_api_mailboxes.py::TestMailboxExport -v`
Expected: FAIL — still produces CSV with header

- [ ] **Step 3: Implement the txt export in the backend**

Replace the `export_mailboxes` function in `backend/app/api/mailboxes.py` (lines 105-145):

```python
@router.post("/export")
async def export_mailboxes(
    body: MailboxExportRequest,
    db: AsyncSession = Depends(get_db),
    crypto: CryptoService = Depends(get_crypto),
    ip: str = Depends(get_client_ip),
):
    stmt = select(Mailbox)
    if not body.include_all and body.ids:
        stmt = stmt.where(Mailbox.id.in_(body.ids))
    stmt = stmt.order_by(Mailbox.created_at)

    rows = (await db.execute(stmt)).scalars().all()

    await log_audit(
        db, "batch_export", len(rows),
        detail={"format": "txt"},
        ip_address=ip,
    )
    await db.commit()

    lines = []
    for m in rows:
        email = m.email
        password = crypto.decrypt(m.password_encrypted)
        client_id = crypto.decrypt(m.client_id_encrypted)
        refresh_token = crypto.decrypt(m.refresh_token_encrypted)
        lines.append(f"{email}----{password}----{client_id}----{refresh_token}")

    content = "\n".join(lines)
    return StreamingResponse(
        iter([content]),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=mailboxes.txt"},
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_api_mailboxes.py::TestMailboxExport -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/mailboxes.py backend/tests/test_api_mailboxes.py
git commit -m "feat: change export format from CSV to txt with ---- separator"
```

---

### Task 2: Backend — Increase page_size default and max

**Files:**
- Modify: `backend/app/api/mailboxes.py:29`
- Modify: `backend/tests/test_api_mailboxes.py:22-27`

- [ ] **Step 1: Add a test for page_size=200**

Add this test method to `TestMailboxList` in `backend/tests/test_api_mailboxes.py`:

```python
    async def test_list_allows_page_size_200(self, client: AsyncClient):
        await _import_sample(client, 1)
        resp = await client.get("/api/mailboxes?page=1&page_size=200")
        assert resp.status_code == 200
        assert resp.json()["page_size"] == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_api_mailboxes.py::TestMailboxList::test_list_allows_page_size_200 -v`
Expected: FAIL — 422 validation error, `page_size` max is 100

- [ ] **Step 3: Update the page_size parameter**

In `backend/app/api/mailboxes.py`, change line 29:

From:
```python
    page_size: int = Query(10, ge=1, le=100),
```

To:
```python
    page_size: int = Query(100, ge=1, le=200),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_api_mailboxes.py::TestMailboxList -v`
Expected: PASS (all list tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/mailboxes.py backend/tests/test_api_mailboxes.py
git commit -m "feat: default page_size to 100, allow up to 200"
```

---

### Task 3: Frontend — Update pagination defaults

**Files:**
- Modify: `frontend/src/pages/MailboxList.tsx:32,233-234`

- [ ] **Step 1: Change pageRef default**

In `frontend/src/pages/MailboxList.tsx`, change line 32:

From:
```typescript
  const pageRef = useRef({ page: 1, page_size: 10 });
```

To:
```typescript
  const pageRef = useRef({ page: 1, page_size: 100 });
```

- [ ] **Step 2: Change pageSizeOptions**

In the same file, change the pagination config (around line 233):

From:
```typescript
          pageSizeOptions: ['10', '20', '50'],
```

To:
```typescript
          pageSizeOptions: ['50', '100', '200'],
```

- [ ] **Step 3: Verify in browser**

Run dev server, open the page, confirm:
- Table shows up to 100 rows by default
- Page size selector shows options: 50, 100, 200

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/MailboxList.tsx
git commit -m "feat: default to 100 items per page, options 50/100/200"
```

---

### Task 4: Frontend — Update export to download .txt

**Files:**
- Modify: `frontend/src/pages/MailboxList.tsx:70-82`

- [ ] **Step 1: Update handleExport function**

In `frontend/src/pages/MailboxList.tsx`, replace the `handleExport` function:

From:
```typescript
  const handleExport = async () => {
    const resp = await mailboxesApi.export({
      ids: selectedRowKeys.length > 0 ? selectedRowKeys : undefined,
      format: 'csv',
      include_all: selectedRowKeys.length === 0,
    });
    const url = URL.createObjectURL(new Blob([resp.data]));
    const a = document.createElement('a');
    a.href = url;
    a.download = 'mailboxes.csv';
    a.click();
    URL.revokeObjectURL(url);
  };
```

To:
```typescript
  const handleExport = async () => {
    const resp = await mailboxesApi.export({
      ids: selectedRowKeys.length > 0 ? selectedRowKeys : undefined,
      format: 'txt',
      include_all: selectedRowKeys.length === 0,
    });
    const url = URL.createObjectURL(new Blob([resp.data]));
    const a = document.createElement('a');
    a.href = url;
    a.download = 'mailboxes.txt';
    a.click();
    URL.revokeObjectURL(url);
  };
```

- [ ] **Step 2: Verify in browser**

Click "导出备份", confirm:
- Downloaded file is named `mailboxes.txt`
- Content is lines of `email----password----client_id----refresh_token`
- No CSV headers

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/MailboxList.tsx
git commit -m "feat: export downloads as .txt matching import format"
```

---

### Task 5: Frontend — Add inline group creation to GroupSelect

**Files:**
- Modify: `frontend/src/components/GroupSelect.tsx`

- [ ] **Step 1: Rewrite GroupSelect with dropdownRender**

Replace the entire content of `frontend/src/components/GroupSelect.tsx`:

```typescript
import { useState, useEffect, useRef } from 'react';
import { Modal, Select, message, Input, Button, Divider, Space } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { groupsApi, mailboxesApi } from '@/services/api';
import type { Group } from '@/types';

interface Props {
  open: boolean;
  selectedIds: string[];
  onClose: () => void;
  onSuccess: () => void;
}

export default function GroupSelect({ open, selectedIds, onClose, onSuccess }: Props) {
  const [groups, setGroups] = useState<Group[]>([]);
  const [groupId, setGroupId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');
  const [creating, setCreating] = useState(false);
  const inputRef = useRef<any>(null);

  useEffect(() => {
    if (open) {
      groupsApi.list().then(setGroups);
      setGroupId(null);
      setNewGroupName('');
    }
  }, [open]);

  const handleCreateGroup = async () => {
    const name = newGroupName.trim();
    if (!name) return;
    setCreating(true);
    try {
      const created = await groupsApi.create({ name });
      setGroups(prev => [...prev, created]);
      setGroupId(created.id);
      setNewGroupName('');
      message.success(`分组「${name}」已创建`);
    } catch (err: any) {
      if (err?.response?.status === 409) {
        message.error('分组名称已存在');
      } else {
        message.error('创建失败');
      }
    } finally {
      setCreating(false);
    }
  };

  const handleOk = async () => {
    setLoading(true);
    try {
      await mailboxesApi.batchSetGroup(selectedIds, groupId);
      message.success(`已更新 ${selectedIds.length} 个邮箱的分组`);
      onSuccess();
      onClose();
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="批量设置分组"
      open={open}
      onOk={handleOk}
      onCancel={onClose}
      confirmLoading={loading}
    >
      <Select
        style={{ width: '100%' }}
        placeholder="选择分组"
        allowClear
        value={groupId}
        onChange={setGroupId}
        options={groups.map(g => ({ label: g.name, value: g.id }))}
        dropdownRender={(menu) => (
          <>
            {menu}
            <Divider style={{ margin: '8px 0' }} />
            <Space style={{ padding: '0 8px 4px' }}>
              <Input
                placeholder="新分组名称"
                ref={inputRef}
                value={newGroupName}
                onChange={(e) => setNewGroupName(e.target.value)}
                onKeyDown={(e) => e.stopPropagation()}
                onPressEnter={handleCreateGroup}
              />
              <Button
                type="text"
                icon={<PlusOutlined />}
                loading={creating}
                onClick={handleCreateGroup}
              >
                添加
              </Button>
            </Space>
          </>
        )}
      />
    </Modal>
  );
}
```

- [ ] **Step 2: Verify in browser**

1. Select some mailboxes, click "批量设置分组"
2. Open the dropdown — see existing groups
3. Type a new group name in the bottom input, click "添加"
4. Verify: new group appears in list and is auto-selected
5. Try creating a duplicate name — verify error toast "分组名称已存在"
6. Click OK — verify mailboxes are assigned to the new group

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/GroupSelect.tsx
git commit -m "feat: add inline group creation in batch group select modal"
```

---

### Task 6: Remove unused csv import from backend

**Files:**
- Modify: `backend/app/api/mailboxes.py:1-2`

- [ ] **Step 1: Remove unused imports**

In `backend/app/api/mailboxes.py`, remove the `csv` and `io` imports at the top (lines 1-2) since they are no longer used:

From:
```python
import csv
import io
from uuid import UUID
```

To:
```python
from uuid import UUID
```

- [ ] **Step 2: Run all backend tests**

Run: `cd backend && python -m pytest -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/mailboxes.py
git commit -m "refactor: remove unused csv/io imports"
```
