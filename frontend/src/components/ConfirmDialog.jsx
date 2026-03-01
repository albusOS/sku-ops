import { useState } from "react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { buttonVariants } from "@/components/ui/button";

/**
 * Reusable confirmation dialog. Replaces window.confirm with styled AlertDialog.
 * @param {boolean} open - Controlled open state
 * @param {function} onOpenChange - Called with (open: boolean)
 * @param {string} title - Dialog title
 * @param {string} description - Dialog description
 * @param {string} confirmLabel - Confirm button text (default "Delete")
 * @param {string} cancelLabel - Cancel button text (default "Cancel")
 * @param {function} onConfirm - Async callback when user confirms; dialog closes on success
 * @param {"danger"|"default"} variant - "danger" for destructive actions (red button)
 */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Delete",
  cancelLabel = "Cancel",
  onConfirm,
  variant = "default",
}) {
  const [loading, setLoading] = useState(false);

  const handleConfirm = async () => {
    if (!onConfirm) {
      onOpenChange(false);
      return;
    }
    setLoading(true);
    try {
      await onConfirm();
      onOpenChange(false);
    } catch {
      // Caller handles error via toast; keep dialog open for retry
    } finally {
      setLoading(false);
    }
  };

  const confirmVariant = variant === "danger" ? "destructive" : "default";

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={loading}>{cancelLabel}</AlertDialogCancel>
          <AlertDialogAction
            onClick={(e) => {
              e.preventDefault();
              handleConfirm();
            }}
            disabled={loading}
            className={confirmVariant === "destructive" ? buttonVariants({ variant: "destructive" }) : undefined}
          >
            {loading ? "..." : confirmLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
