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
