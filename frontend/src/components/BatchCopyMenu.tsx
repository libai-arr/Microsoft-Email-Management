import { Dropdown, Button, message } from 'antd';
import { CopyOutlined, DownOutlined } from '@ant-design/icons';
import { mailboxesApi } from '@/services/api';
import { copyToClipboard } from '@/utils/clipboard';

interface Props {
  selectedIds: string[];
}

export default function BatchCopyMenu({ selectedIds }: Props) {
  const handleCopy = async (type: 'email' | 'password' | 'combined') => {
    if (selectedIds.length === 0) {
      message.warning('请先选择邮箱');
      return;
    }
    const result = await mailboxesApi.batchCopy(selectedIds, type);
    await copyToClipboard(result.text);
  };

  const items = [
    { key: 'email', label: '批量复制账号', onClick: () => handleCopy('email') },
    { key: 'password', label: '批量复制密码', onClick: () => handleCopy('password') },
    { key: 'combined', label: '批量复制账号----密码', onClick: () => handleCopy('combined') },
  ];

  return (
    <Dropdown menu={{ items }} trigger={['click']}>
      <Button icon={<CopyOutlined />}>
        批量复制 <DownOutlined />
      </Button>
    </Dropdown>
  );
}
