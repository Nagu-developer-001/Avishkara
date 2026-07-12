"use client";

import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";

import { ProfileSkeleton } from "@/components/loading/page-skeletons";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import Lightning from "@/components/ui/lightning";
import { SportIcon } from "@/components/ui/sport-icon";
import { getApiErrorMessage, isApiErrorStatus } from "@/lib/api-error";
import { getAthleteProfile, updateAthleteProfile } from "@/services/profile";
import type { AthleteProfile as AthleteProfileData } from "@/types/athlete";

const EMPTY_PROFILE: AthleteProfileData = {
  name: "",
  age: 18,
  gender: "",
  state: "",
  sport: "",
  experience: 0,
};

export function AthleteProfile() {
  const [profile, setProfile] = useState<AthleteProfileData>(EMPTY_PROFILE);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    getAthleteProfile()
      .then((data) => {
        if (active) setProfile(data);
      })
      .catch((requestError) => {
        if (!active) return;
        if (isApiErrorStatus(requestError, 404)) {
          setProfile(EMPTY_PROFILE);
        } else {
          setError(getApiErrorMessage(requestError));
        }
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const { name, value, type } = event.target;
    setProfile((current) => ({
      ...current,
      [name]: type === "number" ? Number(value) : value,
    }));
    setSuccess(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    setIsSaving(true);

    try {
      const updated = await updateAthleteProfile(profile);
      setProfile(updated);
      setSuccess("Profile updated successfully.");
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) {
    return <ProfileSkeleton />;
  }

  const initials = profile.name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "AT";
  const completedFields = [
    profile.name,
    profile.age,
    profile.gender,
    profile.state,
    profile.sport,
    profile.experience || profile.experience === 0,
  ].filter(Boolean).length;
  const completion = Math.round((completedFields / 6) * 100);

  return (
    <div className="relative isolate">
      <div className="pointer-events-none absolute -right-28 -top-32 z-0 hidden h-[620px] w-[54%] overflow-hidden opacity-25 mix-blend-screen [mask-image:radial-gradient(ellipse_at_top_right,black,transparent_72%)] lg:block">
        <Lightning hue={205} xOffset={-0.35} speed={0.35} intensity={0.45} size={1.12} />
      </div>

      <div className="content-grid relative z-10 xl:grid-cols-[0.72fr_1.28fr]">
      <Card className="main-action-card relative bg-gradient-to-br from-primary/[0.16] via-card/[0.92] to-accent/[0.09] xl:sticky xl:top-10 xl:h-fit">
        <div className="absolute -right-20 -top-20 h-56 w-56 rounded-full border-[36px] border-primary/[0.055]" />
        <CardContent className="relative p-7 sm:p-8">
          <div className="flex items-start justify-between">
            <div className="relative">
              <div className="absolute inset-0 rounded-[2rem] bg-primary/30 blur-2xl" />
              <div className="relative grid h-24 w-24 place-items-center rounded-[2rem] border border-primary/30 bg-gradient-to-br from-primary to-accent text-3xl font-black text-primary-foreground shadow-glow">
                {initials}
              </div>
              <span className="absolute -bottom-1 -right-1 grid h-7 w-7 place-items-center rounded-full border-4 border-card bg-primary text-primary-foreground"><SportIcon name="check" className="h-3.5 w-3.5" /></span>
            </div>
            <span className="rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-[0.65rem] font-black uppercase tracking-[0.18em] text-primary">Athlete</span>
          </div>

          <div className="mt-7">
            <p className="text-2xl font-black tracking-[-0.04em]">{profile.name || "Your athlete name"}</p>
            <p className="mt-2 flex items-center gap-2 text-sm text-muted-foreground"><SportIcon name="activity" className="h-4 w-4 text-accent" />{profile.sport || "Sport not selected"}</p>
          </div>

          <div className="mt-7 grid grid-cols-3 gap-2">
            {[
              ["Age", profile.age || "—"],
              ["Experience", `${profile.experience || 0} yr`],
              ["State", profile.state || "—"],
            ].map(([label, value]) => (
              <div key={label} className="rounded-xl border border-border/70 bg-card/[0.42] p-3">
                <p className="text-[0.6rem] font-bold uppercase tracking-wider text-muted-foreground">{label}</p>
                <p className="mt-1 truncate text-sm font-bold">{value}</p>
              </div>
            ))}
          </div>

          <div className="mt-7 border-t border-border/70 pt-6">
            <div className="flex items-center justify-between text-xs"><span className="font-semibold text-muted-foreground">Profile completion</span><span className="font-black text-primary">{completion}%</span></div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-card/[0.55]"><div className="h-full rounded-full bg-gradient-to-r from-primary to-accent transition-all" style={{ width: `${completion}%` }} /></div>
            <p className="mt-3 text-xs leading-5 text-muted-foreground">Complete athlete details improve the context attached to every performance assessment.</p>
          </div>
        </CardContent>
      </Card>

      <Card className="main-action-card">
        <CardHeader className="section-card-header">
          <div className="flex items-center gap-3">
            <span className="grid h-11 w-11 place-items-center rounded-xl bg-accent/10 text-accent"><SportIcon name="profile" className="h-5 w-5" /></span>
            <div><CardTitle>Edit personal details</CardTitle><CardDescription className="mt-1">Information used across your athlete workspace.</CardDescription></div>
          </div>
        </CardHeader>
        <CardContent className="p-6 lg:p-8">
          <form className="grid gap-x-6 gap-y-7 sm:grid-cols-2" onSubmit={handleSubmit}>
          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="name" className="metric-label">Full name</Label>
            <Input id="name" name="name" value={profile.name} onChange={handleChange} required />
          </div>

          <div className="space-y-2">
            <Label htmlFor="age" className="metric-label">Age</Label>
            <Input id="age" name="age" type="number" min={5} max={100} value={profile.age} onChange={handleChange} required />
          </div>

          <div className="space-y-2">
            <Label htmlFor="gender" className="metric-label">Gender</Label>
            <Input id="gender" name="gender" value={profile.gender} onChange={handleChange} required />
          </div>

          <div className="space-y-2">
            <Label htmlFor="state" className="metric-label">State</Label>
            <Input id="state" name="state" value={profile.state} onChange={handleChange} required />
          </div>

          <div className="space-y-2">
            <Label htmlFor="sport" className="metric-label">Primary sport</Label>
            <Input id="sport" name="sport" value={profile.sport} onChange={handleChange} required />
          </div>

          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="experience" className="metric-label">Experience (years)</Label>
            <Input id="experience" name="experience" type="number" min={0} max={80} value={profile.experience} onChange={handleChange} required />
          </div>

          {error && (
            <p role="alert" className="rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-300 sm:col-span-2">
              {error}
            </p>
          )}
          {success && (
            <p role="status" className="rounded-xl border border-primary/20 bg-primary/10 px-3 py-2 text-sm text-primary sm:col-span-2">
              {success}
            </p>
          )}

          <div className="flex justify-end border-t border-border/70 pt-6 sm:col-span-2">
            <Button type="submit" size="lg" className="w-full sm:w-auto" disabled={isSaving}>
              {isSaving ? "Saving..." : "Save profile"}
            </Button>
          </div>
        </form>
      </CardContent>
      </Card>
      </div>
    </div>
  );
}
