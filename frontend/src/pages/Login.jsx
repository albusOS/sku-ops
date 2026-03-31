import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ShieldCheck, HardHat } from "lucide-react";
import { AuthLayout } from "@/components/AuthLayout";
import { ArchExplorer } from "@/components/ArchExplorer";

const ROLE_CONFIG = {
  admin: {
    title: "Admin / Warehouse",
    icon: ShieldCheck,
    accentClass: "bg-accent/15 text-accent",
  },
  contractor: {
    title: "Contractor",
    icon: HardHat,
    accentClass: "bg-emerald-500/15 text-emerald-400",
  },
};

const Login = () => {
  const [role, setRole] = useState("admin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const { user, login } = useAuth();
  const navigate = useNavigate();

  const { title, icon: Icon, accentClass } = ROLE_CONFIG[role];

  // Redirect when already logged in (e.g. session restored)
  if (user) {
    return <Navigate to="/" replace />;
  }

  const handleLogin = async (emailValue, passwordValue) => {
    setLoading(true);
    try {
      await login(emailValue, passwordValue);
      toast.success("Welcome back!");
      // Defer navigation so React commits the auth state before ProtectedRoute renders
      queueMicrotask(() => navigate("/"));
    } catch (error) {
      toast.error(error.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!email || !password) {
      toast.error("Please fill in all fields");
      return;
    }
    void handleLogin(email, password);
  };

  return (
    <AuthLayout testId="login-page" wide>
      <div className="max-w-md mx-auto w-full">
        <div className="bg-surface rounded-2xl p-8 shadow-soft-lg border border-border/70 backdrop-blur-sm flex flex-col">
          <Tabs value={role} onValueChange={setRole} className="w-full">
            <TabsList className="grid w-full grid-cols-2 h-10 mb-6">
              <TabsTrigger value="admin" className="text-xs sm:text-sm" data-testid="login-role-admin">
                Admin / Warehouse
              </TabsTrigger>
              <TabsTrigger value="contractor" className="text-xs sm:text-sm" data-testid="login-role-contractor">
                Contractor
              </TabsTrigger>
            </TabsList>
          </Tabs>

          <div className="flex items-center gap-3 mb-6">
            <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${accentClass}`}>
              <Icon className="w-5 h-5" />
            </div>
            <h2 className="text-base font-semibold text-foreground">{title}</h2>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 flex-1">
            <div>
              <Label
                htmlFor="login-email"
                className="text-muted-foreground font-medium text-sm"
              >
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
              <Label
                htmlFor="login-password"
                className="text-muted-foreground font-medium text-sm"
              >
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
              disabled={loading}
              className="w-full btn-primary h-11 text-sm mt-2"
              data-testid="login-submit-btn"
            >
              {loading ? "Signing in…" : "Sign in"}
            </Button>
          </form>
        </div>
      </div>
      <ArchExplorer />
    </AuthLayout>
  );
};

export default Login;
