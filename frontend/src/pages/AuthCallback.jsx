import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";

const STATUS = {
  LOADING: "loading",
  SUCCESS: "success",
  ERROR: "error",
};

/**
 * Auth callback page for email confirmation links.
 *
 * With implicit flow + detectSessionInUrl, the Supabase client in AuthContext
 * automatically extracts tokens from the URL hash and fires onAuthStateChange.
 * This page just observes the resulting auth state and shows the right UI.
 */
export default function AuthCallback() {
  const navigate = useNavigate();
  const { user, loading } = useAuth();
  const [status, setStatus] = useState(STATUS.LOADING);
  const [errorMessage, setErrorMessage] = useState("");
  const errorChecked = useRef(false);

  useEffect(() => {
    if (errorChecked.current) return;
    errorChecked.current = true;

    const hash = window.location.hash;
    const params = new URLSearchParams(hash.replace(/^#/, ""));
    const hashError = params.get("error");
    const hashErrorDesc = params.get("error_description");

    const url = new URL(window.location.href);
    const queryError = url.searchParams.get("error");
    const queryErrorDesc = url.searchParams.get("error_description");

    const error = hashError || queryError;
    const desc = hashErrorDesc || queryErrorDesc;

    if (error) {
      const msg = desc ? decodeURIComponent(desc.replace(/\+/g, " ")) : error;
      setErrorMessage(msg);
      setStatus(STATUS.ERROR);
    }
  }, []);

  useEffect(() => {
    if (status !== STATUS.LOADING) return;

    if (user) {
      setStatus(STATUS.SUCCESS);
      return;
    }

    if (!loading && !user) {
      setErrorMessage(
        "Could not verify your email. The link may have expired, or the dev server wasn't running when you clicked it.",
      );
      setStatus(STATUS.ERROR);
    }
  }, [user, loading, status]);

  const handleContinue = () => {
    navigate("/", { replace: true });
  };

  const handleBackToLogin = () => {
    navigate("/login", { replace: true });
  };

  if (status === STATUS.SUCCESS) {
    return (
      <div
        className="min-h-screen flex flex-col items-center justify-center gap-4 bg-background p-6"
        data-testid="auth-callback-success"
      >
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/15">
          <CheckCircle2 className="h-8 w-8 text-emerald-500" aria-hidden />
        </div>
        <h1 className="text-xl font-semibold text-foreground">Email verified</h1>
        <p className="text-muted-foreground text-center max-w-sm">
          Your account has been confirmed. You can now access the app.
        </p>
        <Button
          onClick={handleContinue}
          className="mt-2 px-6"
          data-testid="auth-callback-continue"
        >
          Continue to app
        </Button>
      </div>
    );
  }

  if (status === STATUS.ERROR) {
    return (
      <div
        className="min-h-screen flex flex-col items-center justify-center gap-4 bg-background p-6"
        data-testid="auth-callback-error"
      >
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-destructive/15">
          <AlertCircle className="h-8 w-8 text-destructive" aria-hidden />
        </div>
        <h1 className="text-xl font-semibold text-foreground">Verification failed</h1>
        <p
          className="text-muted-foreground text-center max-w-sm"
          data-testid="auth-callback-error-message"
        >
          {errorMessage}
        </p>
        <Button
          onClick={handleBackToLogin}
          variant="outline"
          className="mt-2"
          data-testid="auth-callback-back"
        >
          Back to sign in
        </Button>
      </div>
    );
  }

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center gap-3 bg-background p-6"
      data-testid="auth-callback-loading"
    >
      <Loader2 className="h-8 w-8 animate-spin text-accent" aria-hidden />
      <p className="text-foreground font-medium">Confirming your email…</p>
      <p className="text-sm text-muted-foreground text-center max-w-md">
        If this hangs, ensure the frontend dev server is running before you open the email link.
      </p>
    </div>
  );
}
