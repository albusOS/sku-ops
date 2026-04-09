import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ArrowLeft, ShieldCheck, HardHat } from "lucide-react";
import { AuthLayout } from "@/components/AuthLayout";
import { ArchExplorer } from "@/components/ArchExplorer";
import { ROLES } from "@/lib/constants";
import { cn } from "@/lib/utils";

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
  const [signupMessage, setSignupMessage] = useState("");
  const { user, login, register } = useAuth();
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
        setSignupMessage("Check your email to confirm your account, then sign in.");
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || error.message || "Sign up failed");
    } finally {
      setLoading(false);
    }
  };

  const exitSignupToSignIn = () => {
    setMode("signin");
    setSignupMessage("");
    setAdminSignupUnlocked(false);
    setAdminCode("");
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
                        setSignupMessage("");
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
                {signupMessage && (
                  <p
                    className="text-sm text-muted-foreground text-center"
                    data-testid="signup-email-hint"
                  >
                    {signupMessage}
                  </p>
                )}
              </div>
            </div>
          </form>
        </div>
      </div>
      <ArchExplorer />
    </AuthLayout>
  );
};

export default Login;
