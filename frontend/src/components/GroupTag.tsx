import { Tag } from 'antd';

const COLORS = ['blue', 'green', 'orange', 'purple', 'cyan', 'magenta', 'gold', 'lime'];

function hashColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = ((hash << 5) - hash + name.charCodeAt(i)) | 0;
  }
  return COLORS[Math.abs(hash) % COLORS.length];
}

export default function GroupTag({ name }: { name: string | null }) {
  if (!name) return <Tag>默认分组</Tag>;
  return <Tag color={hashColor(name)}>{name}</Tag>;
}
