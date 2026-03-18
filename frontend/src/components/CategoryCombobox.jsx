import { useState, useRef, useEffect } from "react";
import { Check, ChevronsUpDown, Plus, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { useDepartments, useCreateDepartment } from "@/hooks/useDepartments";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/api-client";

/**
 * Searchable category picker with inline creation.
 * Searches existing departments; when no match, offers "+ Create <typed text>".
 * Creating opens an inline form for the required 3-char code + optional description.
 */
export function CategoryCombobox({ value, onValueChange, disabled, className }) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [creating, setCreating] = useState(null);
  const [newCode, setNewCode] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const triggerRef = useRef(null);
  const codeInputRef = useRef(null);

  const { data: departments = [] } = useDepartments();
  const createMutation = useCreateDepartment();

  const selected = departments.find((d) => d.id === value);
  const displayValue = selected ? `${selected.code} — ${selected.name}` : "Select category";

  useEffect(() => {
    if (!open) {
      setSearch("");
      setCreating(null);
      setNewCode("");
      setNewDesc("");
    }
  }, [open]);

  useEffect(() => {
    if (creating && codeInputRef.current) {
      codeInputRef.current.focus();
    }
  }, [creating]);

  const filtered = departments.filter(
    (d) =>
      d.name.toLowerCase().includes(search.toLowerCase()) ||
      d.code.toLowerCase().includes(search.toLowerCase()),
  );

  const exactMatch = departments.some((d) => d.name.toLowerCase() === search.trim().toLowerCase());
  const showCreate = search.trim().length > 0 && !exactMatch;

  const handleStartCreate = (name) => {
    setCreating(name);
    const code = name
      .replace(/[^a-zA-Z]/g, "")
      .slice(0, 3)
      .toUpperCase();
    setNewCode(code);
    setNewDesc("");
  };

  const handleCreate = async () => {
    if (!creating) return;
    const code = newCode.trim().toUpperCase();
    if (code.length < 2 || code.length > 3) {
      toast.error("Category code must be 2-3 characters");
      return;
    }
    try {
      const created = await createMutation.mutateAsync({
        name: creating.trim(),
        code,
        description: newDesc.trim(),
      });
      toast.success(`Category "${creating.trim()}" created`);
      onValueChange(created.id);
      setOpen(false);
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  };

  if (creating) {
    return (
      <Popover open={true} onOpenChange={setOpen}>
        <PopoverTrigger asChild disabled={disabled}>
          <button
            ref={triggerRef}
            role="combobox"
            className={cn(
              "flex h-9 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
              className,
            )}
          >
            <span className="truncate text-muted-foreground">Creating: {creating}</span>
            <ChevronsUpDown className="ml-2 h-3.5 w-3.5 shrink-0 opacity-50" />
          </button>
        </PopoverTrigger>
        <PopoverContent
          className="p-0"
          style={{ width: Math.max(triggerRef.current?.offsetWidth || 260, 260) }}
          align="start"
        >
          <div className="p-3 space-y-3">
            <p className="text-sm font-medium">
              New category: <span className="text-accent">{creating}</span>
            </p>
            <div>
              <Label className="text-xs text-muted-foreground">Code (2-3 chars) *</Label>
              <Input
                ref={codeInputRef}
                value={newCode}
                onChange={(e) => setNewCode(e.target.value.replace(/[^a-zA-Z]/g, "").slice(0, 3))}
                placeholder="e.g. ELE"
                className="h-8 text-sm font-mono uppercase mt-1"
                maxLength={3}
                onKeyDown={(e) => e.key === "Enter" && handleCreate()}
              />
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">Description</Label>
              <Input
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
                placeholder="Optional"
                className="h-8 text-sm mt-1"
                onKeyDown={(e) => e.key === "Enter" && handleCreate()}
              />
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                className="flex-1 h-8 text-xs"
                onClick={() => setCreating(null)}
                disabled={createMutation.isPending}
              >
                Back
              </Button>
              <Button
                size="sm"
                className="flex-1 h-8 text-xs"
                onClick={handleCreate}
                disabled={createMutation.isPending || newCode.trim().length < 2}
              >
                {createMutation.isPending ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" />
                ) : (
                  <Plus className="w-3.5 h-3.5 mr-1" />
                )}
                Create
              </Button>
            </div>
          </div>
        </PopoverContent>
      </Popover>
    );
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild disabled={disabled}>
        <button
          ref={triggerRef}
          role="combobox"
          aria-expanded={open}
          className={cn(
            "flex h-9 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
            className,
          )}
        >
          <span className={cn("truncate", !selected && "text-muted-foreground")}>
            {displayValue}
          </span>
          <ChevronsUpDown className="ml-2 h-3.5 w-3.5 shrink-0 opacity-50" />
        </button>
      </PopoverTrigger>
      <PopoverContent
        className="p-0"
        style={{ width: Math.max(triggerRef.current?.offsetWidth || 200, 200) }}
        align="start"
      >
        <Command shouldFilter={false}>
          <CommandInput
            placeholder="Search categories..."
            value={search}
            onValueChange={setSearch}
          />
          <CommandList>
            <CommandEmpty>No categories found</CommandEmpty>
            <CommandGroup>
              {filtered.map((dept) => (
                <CommandItem
                  key={dept.id}
                  value={dept.id}
                  onSelect={() => {
                    onValueChange(dept.id);
                    setOpen(false);
                  }}
                >
                  <Check
                    className={cn(
                      "mr-2 h-3.5 w-3.5 shrink-0",
                      value === dept.id ? "opacity-100" : "opacity-0",
                    )}
                  />
                  <span className="font-mono text-xs font-medium mr-1.5">{dept.code}</span>
                  <span className="truncate">{dept.name}</span>
                </CommandItem>
              ))}
            </CommandGroup>
            {showCreate && (
              <>
                <CommandSeparator />
                <CommandGroup>
                  <CommandItem
                    value={`__create_${search}`}
                    onSelect={() => handleStartCreate(search.trim())}
                    className="text-accent"
                  >
                    <Plus className="mr-2 h-3.5 w-3.5" />
                    Create &ldquo;{search.trim()}&rdquo;
                  </CommandItem>
                </CommandGroup>
              </>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
