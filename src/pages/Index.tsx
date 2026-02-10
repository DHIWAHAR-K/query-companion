import { useAuth } from "@/contexts/AuthContext";
import { ChatProvider } from "@/contexts/ChatContext";
import AppLayout from "@/components/layout/AppLayout";
import Login from "./Login";

export default function Index() {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) return <Login />;

  return (
    <ChatProvider>
      <AppLayout />
    </ChatProvider>
  );
}
