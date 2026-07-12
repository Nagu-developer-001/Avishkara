import { AuthForm } from "@/components/auth/auth-form";
import { PageTransition } from "@/components/motion/page-transition";

export default function LoginPage() {
  return (
    <PageTransition>
      <AuthForm mode="login" />
    </PageTransition>
  );
}
