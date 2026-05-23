import { Layout, Typography } from 'antd';
import { MailOutlined } from '@ant-design/icons';
import MailboxList from './pages/MailboxList';

const { Header, Content } = Layout;

export default function App() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <MailOutlined style={{ fontSize: 20, color: '#1890ff' }} />
        <Typography.Text strong style={{ color: '#fff', fontSize: 16 }}>
          多邮箱管理系统
        </Typography.Text>
      </Header>
      <Content style={{ padding: 24 }}>
        <MailboxList />
      </Content>
    </Layout>
  );
}
