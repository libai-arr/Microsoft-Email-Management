import { useState } from 'react';
import { Modal, Tabs, Input, Upload, Button, Alert, Popconfirm, message, Typography } from 'antd';
import { InboxOutlined } from '@ant-design/icons';
import { parseImportText } from '@/utils/importParser';
import { mailboxesApi } from '@/services/api';
import type { ParseError } from '@/utils/importParser';

const { TextArea } = Input;
const { Dragger } = Upload;

interface Props {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function ImportModal({ open, onClose, onSuccess }: Props) {
  const [text, setText] = useState('');
  const [errors, setErrors] = useState<ParseError[]>([]);
  const [loading, setLoading] = useState(false);

  const handleImport = async (mode: 'append' | 'overwrite') => {
    const result = parseImportText(text);
    if (result.errors.length > 0) {
      setErrors(result.errors);
      return;
    }
    if (result.valid.length === 0) {
      message.warning('没有可导入的数据');
      return;
    }

    setLoading(true);
    try {
      const resp = await mailboxesApi.import(result.valid, mode);
      message.success(`成功导入 ${resp.imported} 条，跳过 ${resp.skipped} 条`);
      setText('');
      setErrors([]);
      onSuccess();
      onClose();
    } finally {
      setLoading(false);
    }
  };

  const handleFileRead = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      setText(e.target?.result as string || '');
      setErrors([]);
    };
    reader.readAsText(file);
    return false;
  };

  const footer = (
    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
      <Button onClick={onClose}>取消</Button>
      <Button type="primary" loading={loading} onClick={() => handleImport('append')}>
        追加导入
      </Button>
      <Popconfirm
        title="确认覆盖导入？"
        description="这将清空所有现有邮箱数据，不可撤销！"
        onConfirm={() => handleImport('overwrite')}
        okText="确认覆盖"
        okButtonProps={{ danger: true }}
      >
        <Button danger loading={loading}>覆盖导入</Button>
      </Popconfirm>
    </div>
  );

  return (
    <Modal
      title="导入邮箱账户"
      open={open}
      onCancel={onClose}
      width={700}
      footer={footer}
    >
      <div style={{
        background: '#f6f8fa', border: '1px solid #e8e8e8',
        borderRadius: 8, padding: '10px 14px', marginBottom: 12, fontSize: 12,
      }}>
        <Typography.Text type="secondary">支持格式：</Typography.Text>
        <br />
        <code>格式 A：邮箱地址 密码 Client_ID 刷新令牌（空格/Tab 分隔）</code>
        <br />
        <code>格式 B：邮箱地址----密码----Client_ID----刷新令牌（四连减号分隔）</code>
      </div>

      <Tabs
        items={[
          {
            key: 'text',
            label: '文本录入',
            children: (
              <TextArea
                rows={10}
                value={text}
                onChange={e => { setText(e.target.value); setErrors([]); }}
                placeholder="每行一条记录，支持混合格式 A 和 B..."
                style={{ fontFamily: 'monospace' }}
              />
            ),
          },
          {
            key: 'file',
            label: '文件上传',
            children: (
              <Dragger
                accept=".txt,.csv"
                showUploadList={false}
                beforeUpload={handleFileRead}
              >
                <p className="ant-upload-drag-icon"><InboxOutlined /></p>
                <p>点击或拖拽文件到此区域上传</p>
                <p className="ant-upload-hint">支持 .txt / .csv 文件</p>
              </Dragger>
            ),
          },
        ]}
      />

      {errors.length > 0 && (
        <Alert
          type="error"
          style={{ marginTop: 12 }}
          message={`校验失败 — ${errors.length} 行数据不合规`}
          description={
            <ul style={{ margin: 0, paddingLeft: 16, fontSize: 12 }}>
              {errors.map(e => (
                <li key={e.line_number}>
                  第 {e.line_number} 行：{e.reason} — "{e.content}"
                </li>
              ))}
            </ul>
          }
        />
      )}
    </Modal>
  );
}
