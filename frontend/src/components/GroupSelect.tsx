import { useState, useEffect } from 'react';
import { Modal, Select, message } from 'antd';
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

  useEffect(() => {
    if (open) {
      groupsApi.list().then(setGroups);
    }
  }, [open]);

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
        onChange={setGroupId}
        options={groups.map(g => ({ label: g.name, value: g.id }))}
      />
    </Modal>
  );
}
