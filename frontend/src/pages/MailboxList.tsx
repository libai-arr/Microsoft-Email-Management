import { useState, useEffect, useCallback, useRef } from 'react';
import { Table, Button, Input, Select, Space, Popconfirm, message, Tooltip } from 'antd';
import {
  PlusOutlined, DownloadOutlined, TagOutlined, DeleteOutlined,
  EyeOutlined, CopyOutlined, EyeInvisibleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useMailboxes } from '@/hooks/useMailboxes';
import { useTokenStatus } from '@/hooks/useTokenStatus';
import { groupsApi, mailboxesApi } from '@/services/api';
import { copyToClipboard } from '@/utils/clipboard';
import type { Mailbox, Group } from '@/types';
import TokenStatusComp from '@/components/TokenStatus';
import GroupTag from '@/components/GroupTag';
import BatchCopyMenu from '@/components/BatchCopyMenu';
import GroupSelect from '@/components/GroupSelect';
import ImportModal from '@/components/ImportModal';
import EmailViewer from '@/components/EmailViewer';

export default function MailboxList() {
  const { data, loading, fetch } = useMailboxes();
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [search, setSearch] = useState('');
  const [groupFilter, setGroupFilter] = useState<string | undefined>();
  const [groups, setGroups] = useState<Group[]>([]);
  const [showImport, setShowImport] = useState(false);
  const [showGroupSelect, setShowGroupSelect] = useState(false);
  const [visiblePasswords, setVisiblePasswords] = useState<Set<string>>(new Set());
  const [passwordCache, setPasswordCache] = useState<Record<string, string>>({});
  const [emailViewer, setEmailViewer] = useState<{ id: string; email: string } | null>(null);

  const pageRef = useRef({ page: 1, page_size: 100 });

  const loadData = useCallback(() => {
    fetch({
      page: pageRef.current.page,
      page_size: pageRef.current.page_size,
      search: search || undefined,
      group_id: groupFilter,
    });
  }, [fetch, search, groupFilter]);

  useEffect(() => { loadData(); }, [loadData]);
  useEffect(() => { groupsApi.list().then(setGroups); }, []);

  useTokenStatus(
    data.items.map(m => m.id),
    (statuses) => {
      const changed = statuses.some(s => {
        const item = data.items.find(m => m.id === s.id);
        return item && item.token_status !== s.status;
      });
      if (changed) loadData();
    },
  );

  const handleDelete = async (id: string) => {
    await mailboxesApi.delete(id);
    message.success('已删除');
    loadData();
  };

  const handleBatchDelete = async () => {
    await mailboxesApi.batchDelete(selectedRowKeys);
    message.success(`已删除 ${selectedRowKeys.length} 条`);
    setSelectedRowKeys([]);
    loadData();
  };

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

  const togglePassword = async (id: string) => {
    if (visiblePasswords.has(id)) {
      setVisiblePasswords(prev => { const s = new Set(prev); s.delete(id); return s; });
    } else {
      if (!passwordCache[id]) {
        const result = await mailboxesApi.batchCopy([id], 'password');
        setPasswordCache(prev => ({ ...prev, [id]: result.text }));
      }
      setVisiblePasswords(prev => new Set(prev).add(id));
    }
  };

  const columns: ColumnsType<Mailbox> = [
    {
      title: '#',
      width: 50,
      render: (_v, _r, i) => (data.page - 1) * data.page_size + i + 1,
    },
    {
      title: '邮箱地址',
      dataIndex: 'email',
      render: (email: string) => (
        <Space>
          <span>{email}</span>
          <Tooltip title="复制">
            <CopyOutlined style={{ color: '#999', cursor: 'pointer' }} onClick={() => copyToClipboard(email)} />
          </Tooltip>
        </Space>
      ),
    },
    {
      title: '密码',
      width: 160,
      render: (_v, record) => (
        <Space>
          <span style={{ fontFamily: 'monospace' }}>
            {visiblePasswords.has(record.id) ? (passwordCache[record.id] || '...') : '••••••'}
          </span>
          <Tooltip title={visiblePasswords.has(record.id) ? '隐藏' : '显示'}>
            {visiblePasswords.has(record.id) ?
              <EyeInvisibleOutlined style={{ cursor: 'pointer' }} onClick={() => togglePassword(record.id)} /> :
              <EyeOutlined style={{ cursor: 'pointer' }} onClick={() => togglePassword(record.id)} />
            }
          </Tooltip>
          <Tooltip title="复制">
            <CopyOutlined
              style={{ color: '#999', cursor: 'pointer' }}
              onClick={async () => {
                const result = await mailboxesApi.batchCopy([record.id], 'password');
                await copyToClipboard(result.text);
              }}
            />
          </Tooltip>
        </Space>
      ),
    },
    {
      title: '分组',
      dataIndex: 'group_name',
      width: 120,
      render: (name: string | null) => <GroupTag name={name} />,
    },
    {
      title: '令牌状态',
      dataIndex: 'token_status',
      width: 100,
      render: (status: Mailbox['token_status']) => <TokenStatusComp status={status} />,
    },
    {
      title: '通道',
      dataIndex: 'channel',
      width: 70,
      render: (ch: string) => (
        <span style={{
          padding: '1px 6px', borderRadius: 3, fontSize: 11, fontWeight: 600,
          background: '#f6ffed', color: '#52c41a', border: '1px solid #b7eb8f',
        }}>
          {ch}
        </span>
      ),
    },
    {
      title: '操作',
      width: 140,
      render: (_v, record) => (
        <Space>
          <a onClick={() => setEmailViewer({ id: record.id, email: record.email })}>查看</a>
          <Popconfirm title="确认删除？" onConfirm={() => handleDelete(record.id)}>
            <a style={{ color: '#ff4d4f' }}>删除</a>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* Toolbar */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setShowImport(true)}>
          导入邮箱
        </Button>
        <Button icon={<DownloadOutlined />} onClick={handleExport}>导出备份</Button>
        <BatchCopyMenu selectedIds={selectedRowKeys} />
        <Button icon={<TagOutlined />} onClick={() => setShowGroupSelect(true)}>
          批量设置分组
        </Button>
        <Popconfirm
          title={`确认删除 ${selectedRowKeys.length} 个邮箱？`}
          onConfirm={handleBatchDelete}
          disabled={selectedRowKeys.length === 0}
        >
          <Button danger icon={<DeleteOutlined />} disabled={selectedRowKeys.length === 0}>
            批量删除
          </Button>
        </Popconfirm>

        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
          <Select
            style={{ width: 140 }}
            placeholder="全部分组"
            allowClear
            onChange={(v) => { setGroupFilter(v); pageRef.current.page = 1; }}
            options={groups.map(g => ({ label: g.name, value: g.id }))}
          />
          <Input.Search
            placeholder="搜索邮箱地址..."
            style={{ width: 220 }}
            allowClear
            onSearch={(v) => { setSearch(v); pageRef.current.page = 1; }}
          />
        </div>
      </div>

      {/* Data Grid */}
      <Table<Mailbox>
        columns={columns}
        dataSource={data.items}
        rowKey="id"
        loading={loading}
        rowSelection={{
          selectedRowKeys,
          onChange: (keys) => setSelectedRowKeys(keys as string[]),
        }}
        pagination={{
          current: data.page,
          pageSize: data.page_size,
          total: data.total,
          showSizeChanger: true,
          pageSizeOptions: ['50', '100', '200'],
          showTotal: (total) => `共 ${total} 条 · 已选 ${selectedRowKeys.length} 条`,
          onChange: (page, pageSize) => {
            pageRef.current = { page, page_size: pageSize };
            loadData();
          },
        }}
      />

      {/* Modals */}
      <ImportModal open={showImport} onClose={() => setShowImport(false)} onSuccess={loadData} />
      <GroupSelect
        open={showGroupSelect}
        selectedIds={selectedRowKeys}
        onClose={() => setShowGroupSelect(false)}
        onSuccess={() => { setSelectedRowKeys([]); loadData(); }}
      />
      {emailViewer && (
        <EmailViewer
          open={!!emailViewer}
          mailboxId={emailViewer.id}
          email={emailViewer.email}
          onClose={() => setEmailViewer(null)}
        />
      )}
    </div>
  );
}
