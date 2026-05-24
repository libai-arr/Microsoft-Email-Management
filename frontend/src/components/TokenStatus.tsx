import { Badge } from 'antd';

const STATUS_MAP = {
  normal: { status: 'success' as const, text: '正常' },
  checking: { status: 'processing' as const, text: '检测中' },
  expired: { status: 'error' as const, text: '失效' },
};

export default function TokenStatus({ status }: { status: 'normal' | 'checking' | 'expired' }) {
  const config = STATUS_MAP[status] || STATUS_MAP.normal;
  return <Badge status={config.status} text={config.text} />;
}
