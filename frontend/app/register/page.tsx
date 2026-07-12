import { AuthForm } from "@/components/auth/auth-form";
import { PageTransition } from "@/components/motion/page-transition";

export default function RegisterPage() {
  return (
    <PageTransition>
      <AuthForm mode="register" />
    </PageTransition>
  );
}
