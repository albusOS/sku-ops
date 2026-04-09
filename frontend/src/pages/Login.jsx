import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ArrowLeft, ShieldCheck, HardHat, Mail } from "lucide-react";
import { AuthLayout } from "@/components/AuthLayout";
import { ArchExplorer } from "@/components/ArchExplorer";
import { ROLES } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { getSupabase } from "@/lib/supabase";

const DEFAULT_INBUCKET_ORIGIN = "http://127.0.0.1:54324";

function readInbucketOrigin() {
  const raw = import.meta.env.VITE_INBUCKET_URL;
  if (typeof raw === "string" && raw.trim().length > 0) {
    return raw.replace(/\/$/, "");
  }
  return DEFAULT_INBUCKET_ORIGIN;
}

const ROLE_CONFIG = {
  admin: {
    title: "Admin / Warehouse",
    icon: ShieldCheck,
    accentClass: "bg-accent/15 text-accent",
    role: ROLES.ADMIN,
  },
  contractor: {
    title: "Contractor",
    icon: HardHat,
    accentClass: "bg-emerald-500/15 text-emerald-400",
    role: ROLES.CONTRACTOR,
  },
};

function readExpectedAdminSignupCode() {
  const expectedRaw = import.meta.env.VITE_ADMIN_LOGIN_CODE;
  return typeof expectedRaw === "string" && expectedRaw.length > 0 ? expectedRaw : "1234";
}

const Login = () => {
  const [roleTab, setRoleTab] = useState("admin");
  const [mode, setMode] = useState("signin");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [adminCode, setAdminCode] = useState("");
  const [adminSignupUnlocked, setAdminSignupUnlocked] = useState(false);
  const [loading, setLoading] = useState(false);
  const [pendingConfirmEmail, setPendingConfirmEmail] = useState(null);
  const [confirmInstructionsOpen, setConfirmInstructionsOpen] = useState(false);
  const [signupOtp, setSignupOtp] = useState("");
  const [confirmBusy, setConfirmBusy] = useState(false);
  const { user, login, register, refreshSessionAndProfile } = useAuth();
  const navigate = useNavigate();

  const { title, icon: Icon, accentClass, role } = ROLE_CONFIG[roleTab];
  const showAdminSignupGate =
    mode === "signup" && role === ROLES.ADMIN && !adminSignupUnlocked;

  if (user) {
    return <Navigate to="/" replace />;
  }

  const handleLogin = async (emailValue, passwordValue) => {
    setLoading(true);
    try {
      await login(emailValue, passwordValue);
      toast.success("Welcome back!");
      queueMicrotask(() => navigate("/"));
    } catch (error) {
      toast.error(error.response?.data?.detail || error.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  const tryUnlockAdminSignup = () => {
    if (!adminCode.trim()) {
      toast.error("Admin sign-up code is required");
      return;
    }
    if (adminCode !== readExpectedAdminSignupCode()) {
      toast.error("Invalid admin sign-up code");
      return;
    }
    setAdminSignupUnlocked(true);
  };

  const handleSignup = async () => {
    if (role === ROLES.ADMIN && !adminSignupUnlocked) {
      toast.error("Enter and verify the admin sign-up code first");
      return;
    }
    if (!email || !password || !name.trim()) {
      toast.error("Please fill in all fields");
      return;
    }
    if (role === ROLES.ADMIN) {
      if (!adminCode) {
        toast.error("Admin sign-up code is required");
        return;
      }
      if (adminCode !== readExpectedAdminSignupCode()) {
        toast.error("Invalid admin sign-up code");
        return;
      }
    }
    setLoading(true);
    try {
      const profile = await register(email, password, name.trim(), role);
      if (profile) {
        toast.success("Welcome!");
        queueMicrotask(() => navigate("/"));
      } else {
        setPendingConfirmEmail(email);
        setConfirmInstructionsOpen(true);
        setSignupOtp("");
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || error.message || "Sign up failed");
    } finally {
      setLoading(false);
    }
  };

  const exitSignupToSignIn = () => {
    setMode("signin");
    setPendingConfirmEmail(null);
    setConfirmInstructionsOpen(false);
    setSignupOtp("");
    setAdminSignupUnlocked(false);
    setAdminCode("");
  };

  const emailRedirectTo =
    typeof window !== "undefined" ? `${window.location.origin}/auth/callback` : "";

  const handleResendConfirmation = async () => {
    if (!pendingConfirmEmail) return;
    setConfirmBusy(true);
    try {
      const sb = await getSupabase();
      const { error } = await sb.auth.resend({
        type: "signup",
        email: pendingConfirmEmail,
        ...(emailRedirectTo ? { options: { emailRedirectTo } } : {}),
      });
      if (error) throw error;
      toast.success("Confirmation email sent again.");
    } catch (e) {
      const code = e?.code ?? e?.status;
      if (code === "over_email_send_rate_limit" || e?.status === 429) {
        toast.error(
          "Email rate limit hit (local default was very strict). Restart Supabase after raising email_sent in supabase/config.toml under [auth.rate_limit], or wait an hour.",
        );
      } else {
        toast.error(e?.message || String(e) || "Could not resend email");
      }
    } finally {
      setConfirmBusy(false);
    }
  };

  const handleVerifySignupOtp = async () => {
    if (!pendingConfirmEmail || !signupOtp.trim()) {
      toast.error("Enter the code from your email");
      return;
    }
    setConfirmBusy(true);
    try {
      const sb = await getSupabase();
      const { error } = await sb.auth.verifyOtp({
        email: pendingConfirmEmail,
        token: signupOtp.trim(),
        type: "signup",
      });
      if (error) throw error;
      await refreshSessionAndProfile();
      toast.success("Email confirmed. Welcome!");
      setPendingConfirmEmail(null);
      setConfirmInstructionsOpen(false);
      setSignupOtp("");
      queueMicrotask(() => navigate("/"));
    } catch (e) {
      toast.error(e?.message || "Invalid or expired code");
    } finally {
      setConfirmBusy(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (mode === "signin") {
      if (!email || !password) {
        toast.error("Please fill in all fields");
        return;
      }
      void handleLogin(email, password);
      return;
    }
    void handleSignup();
  };

  return (
    <AuthLayout testId="login-page" wide>
      <div className="max-w-md mx-auto w-full">
        <div className="bg-surface rounded-2xl p-8 shadow-soft-lg border border-border/70 backdrop-blur-sm flex flex-col">
          <div className="grid w-full grid-cols-2 gap-1 h-10 mb-6 rounded-lg bg-muted p-1 text-muted-foreground">
            <button
              type="button"
              data-testid="login-role-admin"
              data-state={roleTab === "admin" ? "active" : "inactive"}
              className={cn(
                "inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-xs sm:text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                roleTab === "admin" ? "bg-background text-foreground shadow" : "",
              )}
              onClick={() => {
                setRoleTab("admin");
                if (mode === "signup") {
                  setAdminSignupUnlocked(false);
                  setAdminCode("");
                }
              }}
            >
              Admin / Warehouse
            </button>
            <button
              type="button"
              data-testid="login-role-contractor"
              data-state={roleTab === "contractor" ? "active" : "inactive"}
              className={cn(
                "inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-xs sm:text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                roleTab === "contractor" ? "bg-background text-foreground shadow" : "",
              )}
              onClick={() => setRoleTab("contractor")}
            >
              Contractor
            </button>
          </div>

          <div className="flex items-center gap-3 mb-6">
            <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${accentClass}`}>
              <Icon className="w-5 h-5" />
            </div>
            <h2 className="text-base font-semibold text-foreground">{title}</h2>
          </div>

          <form
            data-testid="login-form"
            onSubmit={handleSubmit}
            className="space-y-4 flex-1"
          >
            <div className="relative">
              {showAdminSignupGate && (
                <div
                  className="absolute inset-0 z-10 flex items-start justify-center rounded-xl border border-border/40 bg-background/55 px-4 pb-5 pt-3 shadow-sm backdrop-blur-md backdrop-saturate-150"
                  data-testid="signup-admin-gate-overlay"
                >
                  <div className="mx-auto w-full max-w-xs space-y-3">
                    <button
                      type="button"
                      className="-ml-1.5 inline-flex items-center gap-1.5 rounded-md px-1.5 py-1 text-sm text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground"
                      data-testid="signup-admin-gate-back"
                      aria-label="Back to sign in"
                      onClick={exitSignupToSignIn}
                    >
                      <ArrowLeft className="h-4 w-4 shrink-0" aria-hidden />
                      Back
                    </button>
                    <p className="text-sm leading-relaxed text-muted-foreground">
                      Admin registration requires an invite code. Verify it here before entering your
                      details.
                    </p>
                    <div>
                      <Label
                        htmlFor="signup-admin-code"
                        className="text-muted-foreground font-medium text-sm"
                      >
                        Admin sign-up code
                      </Label>
                      <Input
                        id="signup-admin-code"
                        type="password"
                        value={adminCode}
                        onChange={(e) => setAdminCode(e.target.value)}
                        className="input-field mt-2 bg-background/80"
                        data-testid="signup-admin-code-input"
                        autoComplete="off"
                      />
                    </div>
                    <Button
                      type="button"
                      variant={adminCode.trim() ? "default" : "secondary"}
                      className={cn("w-full", adminCode.trim() && "btn-primary")}
                      data-testid="signup-admin-unlock-btn"
                      onClick={tryUnlockAdminSignup}
                    >
                      Continue
                    </Button>
                  </div>
                </div>
              )}
              <div
                className={cn(
                  "space-y-4",
                  showAdminSignupGate && "pointer-events-none select-none opacity-[0.38]",
                )}
                aria-hidden={showAdminSignupGate}
              >
                {mode === "signup" && !showAdminSignupGate && (
                  <div>
                    <Label htmlFor="signup-name" className="text-muted-foreground font-medium text-sm">
                      Name
                    </Label>
                    <Input
                      id="signup-name"
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="input-field mt-2"
                      data-testid="signup-name-input"
                    />
                  </div>
                )}
                <div>
                  <Label htmlFor="login-email" className="text-muted-foreground font-medium text-sm">
                    Email
                  </Label>
                  <Input
                    id="login-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@company.com"
                    className="input-field mt-2"
                    data-testid="login-email-input"
                  />
                </div>
                <div>
                  <Label htmlFor="login-password" className="text-muted-foreground font-medium text-sm">
                    Password
                  </Label>
                  <Input
                    id="login-password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="input-field mt-2"
                    data-testid="login-password-input"
                  />
                </div>
                <Button
                  type="submit"
                  disabled={
                    loading ||
                    (mode === "signup" && role === ROLES.ADMIN && !adminSignupUnlocked)
                  }
                  className="w-full btn-primary h-11 text-sm mt-2"
                  data-testid="login-submit-btn"
                >
                  {loading ? "Please wait…" : mode === "signin" ? "Sign in" : "Sign up"}
                </Button>
                <div className="text-center text-sm">
                  <button
                    type="button"
                    className="text-accent hover:underline"
                    data-testid="login-mode-toggle"
                    onClick={() => {
                      if (mode === "signin") {
                        setMode("signup");
                        setPendingConfirmEmail(null);
                        setConfirmInstructionsOpen(false);
                        setSignupOtp("");
                        setAdminSignupUnlocked(false);
                        setAdminCode("");
                      } else {
                        exitSignupToSignIn();
                      }
                    }}
                  >
                    {mode === "signin" ? "Sign up" : "Sign in"}
                  </button>
                </div>
                {pendingConfirmEmail && !confirmInstructionsOpen && (
                  <button
                    type="button"
                    className="w-full text-sm text-accent hover:underline text-center font-medium"
                    data-testid="signup-email-hint-reopen"
                    onClick={() => setConfirmInstructionsOpen(true)}
                  >
                    Confirmation sent to {pendingConfirmEmail} - open instructions
                  </button>
                )}
              </div>
            </div>
          </form>
        </div>
      </div>

      <Dialog
        open={Boolean(pendingConfirmEmail) && confirmInstructionsOpen}
        onOpenChange={(open) => {
          if (!pendingConfirmEmail) return;
          setConfirmInstructionsOpen(open);
        }}
      >
        <DialogContent className="sm:max-w-md border-border bg-surface shadow-soft-lg">
          <DialogHeader>
            <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-accent/15 text-accent">
              <Mail className="h-6 w-6" aria-hidden />
            </div>
            <DialogTitle className="text-center text-lg">Confirm your email</DialogTitle>
            <DialogDescription
              className="text-center text-foreground/90 text-base pt-1"
              data-testid="signup-email-hint"
            >
              We sent a link to <span className="font-medium text-foreground">{pendingConfirmEmail}</span>
              . Use it to activate your account, then you can sign in.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 text-sm">
            <div className="rounded-lg border border-border/80 bg-muted/40 px-3 py-2.5 text-muted-foreground">
              <p className="font-medium text-foreground/90 mb-1">Local dev</p>
              <ul className="list-disc pl-4 space-y-1">
                <li>Keep the app running (Vite on port 3000) before you click the email link.</li>
                <li>
                  Links open{" "}
                  <code className="text-xs bg-background/80 px-1 rounded">/auth/callback</code> so the
                  session is saved in this browser.
                </li>
              </ul>
            </div>
            <div className="flex flex-wrap gap-2 justify-center">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="text-accent border-accent/40"
                asChild
              >
                <a href={readInbucketOrigin()} target="_blank" rel="noreferrer">
                  Open mail (Inbucket)
                </a>
              </Button>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                disabled={confirmBusy || !pendingConfirmEmail}
                onClick={() => void handleResendConfirmation()}
                data-testid="signup-resend-email"
              >
                Resend email
              </Button>
            </div>
            <div className="space-y-2 pt-1 border-t border-border/60">
              <Label htmlFor="signup-otp" className="text-muted-foreground">
                Code from email (optional)
              </Label>
              <Input
                id="signup-otp"
                inputMode="numeric"
                autoComplete="one-time-code"
                placeholder="6-digit code if your template includes one"
                value={signupOtp}
                onChange={(e) => setSignupOtp(e.target.value)}
                className="input-field"
                data-testid="signup-otp-input"
              />
              <Button
                type="button"
                className="w-full"
                variant="default"
                disabled={confirmBusy || !signupOtp.trim()}
                onClick={() => void handleVerifySignupOtp()}
                data-testid="signup-verify-otp"
              >
                Verify with code
              </Button>
            </div>
          </div>
          <DialogFooter className="sm:justify-center">
            <Button type="button" variant="ghost" onClick={() => setConfirmInstructionsOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ArchExplorer />
    </AuthLayout>
  );
};

export default Login;
