import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Wrench, UserPlus } from "lucide-react";

const Register = () => {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name || !email || !password) {
      toast.error("Please fill in all fields");
      return;
    }
    if (password !== confirmPassword) {
      toast.error("Passwords do not match");
      return;
    }
    if (password.length < 6) {
      toast.error("Password must be at least 6 characters");
      return;
    }

    setLoading(true);
    try {
      await register(email, password, name);
      toast.success("Account created successfully!");
      navigate("/");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4" data-testid="register-page">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-orange-500 rounded-sm mx-auto flex items-center justify-center mb-4 shadow-hard">
            <Wrench className="w-10 h-10 text-white" />
          </div>
          <h1 className="font-heading font-bold text-3xl text-white uppercase tracking-wider">
            SKU Central
          </h1>
          <p className="text-slate-400 mt-2">Hardware Store Management System</p>
        </div>

        {/* Register Form */}
        <div className="bg-white border-2 border-slate-200 rounded-md p-8 shadow-hard">
          <h2 className="font-heading font-bold text-2xl text-slate-900 uppercase tracking-wider mb-6">
            Create Account
          </h2>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <Label htmlFor="name" className="text-slate-700 font-semibold uppercase text-sm tracking-wide">
                Full Name
              </Label>
              <Input
                id="name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="John Doe"
                className="input-workshop mt-2"
                data-testid="register-name-input"
              />
            </div>

            <div>
              <Label htmlFor="email" className="text-slate-700 font-semibold uppercase text-sm tracking-wide">
                Email
              </Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="input-workshop mt-2"
                data-testid="register-email-input"
              />
            </div>

            <div>
              <Label htmlFor="password" className="text-slate-700 font-semibold uppercase text-sm tracking-wide">
                Password
              </Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="input-workshop mt-2"
                data-testid="register-password-input"
              />
            </div>

            <div>
              <Label htmlFor="confirmPassword" className="text-slate-700 font-semibold uppercase text-sm tracking-wide">
                Confirm Password
              </Label>
              <Input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                className="input-workshop mt-2"
                data-testid="register-confirm-password-input"
              />
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="w-full btn-primary h-12 text-base"
              data-testid="register-submit-btn"
            >
              <UserPlus className="w-5 h-5 mr-2" />
              {loading ? "Creating Account..." : "Create Account"}
            </Button>
          </form>

          <p className="text-center mt-6 text-slate-600">
            Already have an account?{" "}
            <Link
              to="/login"
              className="text-orange-500 font-semibold hover:underline"
              data-testid="login-link"
            >
              Sign In
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Register;
