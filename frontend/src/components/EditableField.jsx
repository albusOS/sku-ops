import { useState, useEffect, useRef } from "react";
import { Input } from "@/components/ui/input";
import { Pencil, Check } from "lucide-react";
import { useUpdateProduct } from "@/hooks/useProducts";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/api-client";

export function EditableField({
  label,
  value,
  field,
  productId,
  type = "text",
  prefix,
  mono,
  onSaved,
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const inputRef = useRef(null);
  const updateMutation = useUpdateProduct();

  useEffect(() => {
    setDraft(value);
    setEditing(false);
  }, [value, productId]);

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  const save = () => {
    const parsed = type === "number" ? parseFloat(draft) : draft;
    if (type === "number" && (isNaN(parsed) || parsed < 0)) {
      toast.error(`${label} must be a valid number`);
      setDraft(value);
      setEditing(false);
      return;
    }
    if (parsed === value) {
      setEditing(false);
      return;
    }
    updateMutation.mutate(
      { id: productId, data: { [field]: parsed } },
      {
        onSuccess: () => {
          toast.success(`${label} updated`);
          setEditing(false);
          onSaved?.();
        },
        onError: (err) => {
          toast.error(getErrorMessage(err));
          setDraft(value);
          setEditing(false);
        },
      },
    );
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") save();
    if (e.key === "Escape") {
      setDraft(value);
      setEditing(false);
    }
  };

  if (editing) {
    return (
      <div>
        <p className="text-xs text-muted-foreground mb-1">{label}</p>
        <div className="flex items-center gap-1.5">
          {prefix && <span className="text-sm text-muted-foreground">{prefix}</span>}
          <Input
            ref={inputRef}
            type={type}
            step={type === "number" ? "0.01" : undefined}
            value={draft ?? ""}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={save}
            onKeyDown={handleKeyDown}
            className="h-8 text-sm font-mono"
            disabled={updateMutation.isPending}
          />
          <button
            onClick={save}
            className="p-1 rounded text-success hover:bg-success/10 transition-colors shrink-0"
          >
            <Check className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    );
  }

  const display =
    type === "number" && value != null
      ? `${prefix || ""}${Number(value).toFixed(2)}`
      : value || "—";

  return (
    <div
      className="group cursor-pointer rounded-md px-1 -mx-1 py-0.5 hover:bg-muted/60 transition-colors"
      onClick={() => setEditing(true)}
    >
      <p className="text-xs text-muted-foreground flex items-center gap-1">
        {label}
        <Pencil className="w-2.5 h-2.5 opacity-0 group-hover:opacity-100 transition-opacity" />
      </p>
      <p className={`text-sm text-foreground mt-0.5 ${mono ? "font-mono tabular-nums" : ""}`}>
        {display}
      </p>
    </div>
  );
}

export function ReadField({ label, value, mono }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={`text-sm text-foreground mt-0.5 ${mono ? "font-mono tabular-nums" : ""}`}>
        {value || "—"}
      </p>
    </div>
  );
}
