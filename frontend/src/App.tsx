import { useEffect, useState } from 'react';
import { Button, Card, Input, Layout, Spin, Typography, message } from 'antd';
import MailboxList from './pages/MailboxList';
import { authApi } from './services/api';

const { Header, Content } = Layout;

export default function App() {
  const [password, setPassword] = useState('');
  const [ready, setReady] = useState(false);
  const [unlocked, setUnlocked] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const check = async () => {
      try {
        const result = await authApi.status();
        setUnlocked(result.unlocked);
      } catch {
        setUnlocked(false);
      } finally {
        setReady(true);
      }
    };

    check();

    const handleUnauthorized = () => {
      setUnlocked(false);
      setPassword('');
      message.warning('访问会话已失效，请重新输入密码');
    };

    window.addEventListener('app:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('app:unauthorized', handleUnauthorized);
  }, []);

  const handleUnlock = async () => {
    if (!password.trim()) {
      message.warning('请输入访问密码');
      return;
    }

    setSubmitting(true);
    try {
      await authApi.unlock(password);
      setUnlocked(true);
      setPassword('');
      message.success('验证成功');
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '访问密码错误');
    } finally {
      setSubmitting(false);
    }
  };

  const handleLogout = async () => {
    await authApi.logout();
    setUnlocked(false);
    setPassword('');
  };

  if (!ready) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!unlocked) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f5f7fb', padding: '16px 12px' }}>
        <Card style={{ width: 420, maxWidth: '100%' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
            <img
              src="/logo.png"
              alt="logo"
              style={{ width: 32, height: 32, objectFit: 'contain' }}
            />
            <div>
              <Typography.Title level={4} style={{ margin: 0 }}>
                Microsoft
              </Typography.Title>
              <Typography.Text type="secondary">
                请输入访问密码后继续
              </Typography.Text>
            </div>
          </div>
          <Input.Password
            size="large"
            placeholder="访问密码"
            value={password}
            onChange={e => setPassword(e.target.value)}
            onPressEnter={handleUnlock}
          />
          <Button
            type="primary"
            size="large"
            block
            loading={submitting}
            onClick={handleUnlock}
            style={{ marginTop: 16 }}
          >
            进入系统
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap', height: 'auto', minHeight: 64, padding: '12px 16px' }}>
        <img
          src="/logo.png"
          alt="logo"
          style={{ width: 28, height: 28, objectFit: 'contain' }}
        />
        <Typography.Text strong style={{ color: '#fff', fontSize: 18, fontFamily: 'sans-serif' }}>
          Microsoft
        </Typography.Text>
        <Button type="link" onClick={handleLogout} style={{ marginLeft: 'auto', color: '#fff', paddingInline: 0 }}>
          退出
        </Button>
      </Header>
      <Content style={{ padding: '12px' }}>
        <MailboxList />
      </Content>
    </Layout>
  );
}
