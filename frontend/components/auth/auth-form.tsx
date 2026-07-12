"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AppLogo } from "@/components/brand/app-logo";
import { useAuth } from "@/hooks/use-auth";
import { getApiErrorMessage } from "@/lib/api-error";
import { SportsBackdrop } from "@/components/ui/sports-backdrop";
import { ThemeSwitcher } from "@/components/theme/theme-switcher";

type AuthFormProps = {
  mode: "login" | "register";
};

export function AuthForm({ mode }: AuthFormProps) {
  const isLogin = mode === "login";
  const { login, register } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const data = new FormData(event.currentTarget);
    if (!isLogin) {
      const confirmPassword = String(data.get("confirmPassword") ?? "");
      if (password !== confirmPassword) {
        setError("Passwords do not match.");
        return;
      }
    }

    setIsSubmitting(true);
    try {
      if (isLogin) {
        await login({ email, password }, "athlete");
      } else {
        await register({
          name: String(data.get("name") ?? ""),
          email,
          password,
        });
      }
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
      setIsSubmitting(false);
    }
  }

  return (
    <main className="page-transition relative grid min-h-screen overflow-hidden lg:grid-cols-[1.15fr_0.85fr]">
      <div className="fixed right-4 top-4 z-[70] sm:right-6 sm:top-6">
        <ThemeSwitcher compact />
      </div>
      <section className="relative hidden overflow-hidden border-r border-white/[0.07] bg-[#070b12] p-12 text-white lg:flex lg:flex-col lg:justify-between xl:p-20">
        <SportsBackdrop overlayClassName="bg-gradient-to-r from-[#04080f]/95 via-[#04080f]/65 to-[#04080f]/35" />
        <div className="sport-grid absolute inset-0 opacity-30" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#050810]/90 via-transparent to-[#050810]/35" />
        <div className="absolute -left-32 top-1/3 h-96 w-96 rounded-full bg-primary/10 blur-[120px]" />
        <AppLogo className="relative text-white" size="hero" />

        <div className="relative max-w-2xl">
          <p className="eyebrow">Movement decoded</p>
          <h1 className="mt-5 text-5xl font-black leading-[1.02] tracking-[-0.06em] text-white xl:text-7xl">See the athlete<br />inside every <span className="text-primary">frame.</span></h1>
          <p className="mt-7 max-w-xl text-base leading-8 text-slate-300">Explainable pose analysis, phase-aware biomechanics, and transparent performance benchmarks for the next generation of athletes.</p>
        </div>

        <div className="relative grid grid-cols-3 gap-4">
          {["RUN", "JUMP", "BOWL"].map((sport, index) => <div key={sport} className="border-l border-primary/30 pl-4"><p className="text-xs font-black tracking-[0.2em] text-primary">0{index + 1}</p><p className="mt-1 text-sm font-bold text-white">{sport}</p></div>)}
        </div>
      </section>

      <section className="relative flex items-center justify-center px-5 py-12 sm:px-10">
        <div className="absolute right-0 top-0 h-72 w-72 bg-accent/[0.06] blur-[100px]" />
        <div className="relative w-full max-w-md space-y-7">
          <div className="lg:hidden">
            <AppLogo size="compact" />
          </div>
          <div>
            <p className="eyebrow">{isLogin ? "Athlete access" : "Join the performance lab"}</p>
            <h2 className="mt-3 text-3xl font-black tracking-[-0.04em]">{isLogin ? "Welcome back" : "Create your account"}</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">{isLogin ? "Sign in to continue your performance journey." : "Start building your explainable athlete profile."}</p>
          </div>

          <Card className="border-white/[0.1] bg-white/[0.035]">
          <CardHeader>
            <CardTitle className="text-base">Secure account</CardTitle>
            <CardDescription>Your performance data stays linked to your athlete identity.</CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleSubmit}>
              {!isLogin && (
                <div className="space-y-2">
                  <Label htmlFor="name">Full name</Label>
                  <Input id="name" name="name" autoComplete="name" required />
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  placeholder="athlete@example.com"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete={isLogin ? "current-password" : "new-password"}
                  minLength={8}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                />
              </div>

              {!isLogin && (
                <div className="space-y-2">
                  <Label htmlFor="confirm-password">Confirm password</Label>
                  <Input
                    id="confirm-password"
                    name="confirmPassword"
                    type="password"
                    autoComplete="new-password"
                    minLength={8}
                    required
                  />
                </div>
              )}

              {error && (
                <p role="alert" className="rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-300">
                  {error}
                </p>
              )}

              {isLogin && (
                <button
                  type="button"
                  onClick={() => {
                    setEmail("athlete@demo.com");
                    setPassword("Demo@2026");
                    setError(null);
                  }}
                  className="w-full rounded-xl border border-accent/20 bg-accent/[0.06] px-4 py-3 text-sm font-bold text-accent transition hover:bg-accent/[0.1]"
                >
                  Use Athlete Demo Account
                </button>
              )}

              <Button
                type="submit"
                className="w-full"
                size="lg"
                disabled={isSubmitting}
              >
                {isSubmitting
                  ? "Please wait..."
                  : isLogin
                    ? "Sign in"
                    : "Create account"}
              </Button>
            </form>
          </CardContent>
          <CardFooter className="justify-center border-t border-white/[0.06] pt-5 text-sm text-muted-foreground">
            {isLogin ? "New to Avishkara?" : "Already registered?"}
            <Button variant="outline" asChild className="ml-3">
              <Link href={isLogin ? "/register" : "/login"}>
                {isLogin ? "Register" : "Sign in"}
              </Link>
            </Button>
          </CardFooter>
          </Card>
        </div>
      </section>
    </main>
  );
}
