import { useState, useEffect, useMemo } from 'react';
import { Modal, Tabs, Input, Button, List, Spin, Empty, Typography, Tag } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { useEmails } from '@/hooks/useEmails';
import type { EmailSummary } from '@/types';
import dayjs from 'dayjs';

interface Props {
  open: boolean;
  mailboxId: string;
  email: string;
  onClose: () => void;
}

export default function EmailViewer({ open, mailboxId, email, onClose }: Props) {
  const { emails, detail, loading, fetchList, fetchDetail } = useEmails(mailboxId);
  const [folder, setFolder] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    if (open && mailboxId) {
      fetchList({ folder });
      setSelectedId(null);
    }
  }, [open, mailboxId, folder]);

  const filteredEmails = useMemo(() => {
    if (!search) return emails;
    const q = search.toLowerCase();
    return emails.filter(
      e => e.sender_name.toLowerCase().includes(q) || e.subject.toLowerCase().includes(q)
    );
  }, [emails, search]);

  const handleSelect = (msg: EmailSummary) => {
    setSelectedId(msg.id);
    fetchDetail(msg.id);
  };
  return (
    <Modal
      title={`邮件列表 — ${email}`}
      open={open}
      onCancel={onClose}
      width="90vw"
      style={{ top: '5vh' }}
      styles={{ body: { height: '75vh', padding: 0, display: 'flex', overflow: 'hidden' } }}
      footer={null}
    >
      {/* Left Panel */}
      <div style={{ width: 340, borderRight: '1px solid #f0f0f0', display: 'flex', flexDirection: 'column' }}>
        <Tabs
          activeKey={folder}
          onChange={setFolder}
          style={{ padding: '0 12px' }}
          items={[
            { key: 'all', label: '全部' },
            { key: 'inbox', label: '收件箱' },
            { key: 'junk', label: '垃圾箱' },
          ]}
        />
        <div style={{ display: 'flex', gap: 6, padding: '0 12px 8px' }}>
          <Input.Search
            placeholder="搜索发件人、主题..."
            size="small"
            value={search}
            onChange={e => setSearch(e.target.value)}
            allowClear
          />
          <Button
            size="small"
            icon={<ReloadOutlined />}
            onClick={() => fetchList({ folder })}
            loading={loading}
          />
        </div>
        <div style={{ flex: 1, overflow: 'auto' }}>
          <Spin spinning={loading}>
            <List
              dataSource={filteredEmails}
              renderItem={(item) => (
                <List.Item
                  onClick={() => handleSelect(item)}
                  style={{
                    padding: '10px 14px',
                    cursor: 'pointer',
                    background: selectedId === item.id ? '#e6f7ff' : undefined,
                    borderLeft: selectedId === item.id ? '3px solid #1890ff' : '3px solid transparent',
                  }}
                >
                  <div style={{ width: '100%' }}>
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
                    <div style={{
                      fontSize: 12, color: '#555', marginBottom: 2,
                      whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                    }}>
                      {item.subject}
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#999' }}>
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
                        {item.preview}
                      </span>
                      <span style={{ flexShrink: 0, marginLeft: 8 }}>
                        {dayjs(item.received_at).format('MM-DD HH:mm')}
                      </span>
                    </div>
                  </div>
                </List.Item>
              )}
            />
          </Spin>
        </div>
      </div>

      {/* Right Panel */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {!detail ? (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Empty description="请从左侧选择一封邮件查看" />
          </div>
        ) : (
          <>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid #f0f0f0' }}>
              <Typography.Title level={4} style={{ marginBottom: 8 }}>
                {detail.subject}
              </Typography.Title>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13 }}>
                <div style={{
                  width: 32, height: 32, borderRadius: '50%', background: '#1890ff',
                  color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontWeight: 600, flexShrink: 0,
                }}>
                  {detail.sender_name?.[0]?.toUpperCase() || '?'}
                </div>
                <div>
                  <div style={{ fontWeight: 500 }}>{detail.sender_name}</div>
                  <div style={{ fontSize: 11, color: '#999' }}>{detail.sender_email}</div>
                </div>
                <div style={{ marginLeft: 'auto', fontSize: 11, color: '#999' }}>
                  {dayjs(detail.received_at).format('YYYY-MM-DD HH:mm:ss')}
                </div>
              </div>
            </div>
            <div style={{ flex: 1, overflow: 'auto' }}>
              <iframe
                srcDoc={detail.body_html}
                sandbox="allow-same-origin"
                style={{ width: '100%', height: '100%', border: 'none' }}
                title="email body"
              />
            </div>
          </>
        )}
      </div>
    </Modal>
  );
}
