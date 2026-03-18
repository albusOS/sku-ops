import { useState, useRef, useEffect } from "react";
import { Check, ChevronsUpDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { useUnitsOfMeasure } from "@/hooks/useUnitsOfMeasure";

/**
 * Searchable unit-of-measure picker. Suggests from the DB-backed units list
 * but also accepts arbitrary typed values (for units not yet in the system).
 */
export function UnitCombobox({ value, onValueChange, disabled, className, placeholder }) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const triggerRef = useRef(null);
  const { data: units = [] } = useUnitsOfMeasure();

  const displayValue = value || "each";

  useEffect(() => {
    if (!open) setSearch("");
  }, [open]);

  const filtered = units.filter(
    (u) =>
      u.code.toLowerCase().includes(search.toLowerCase()) ||
      u.name.toLowerCase().includes(search.toLowerCase()),
  );

  const searchIsNewUnit =
    search.trim() && !units.some((u) => u.code === search.trim().toLowerCase());

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
          <span className="truncate">{displayValue}</span>
          <ChevronsUpDown className="ml-2 h-3.5 w-3.5 shrink-0 opacity-50" />
        </button>
      </PopoverTrigger>
      <PopoverContent
        className="p-0"
        style={{ width: triggerRef.current?.offsetWidth || 200 }}
        align="start"
      >
        <Command shouldFilter={false}>
          <CommandInput
            placeholder={placeholder || "Search units..."}
            value={search}
            onValueChange={setSearch}
          />
          <CommandList>
            <CommandEmpty>
              {search.trim() ? (
                <button
                  className="w-full text-left px-2 py-1.5 text-sm hover:bg-accent rounded-sm"
                  onClick={() => {
                    onValueChange(search.trim().toLowerCase());
                    setOpen(false);
                  }}
                >
                  Use &ldquo;{search.trim().toLowerCase()}&rdquo;
                </button>
              ) : (
                "No units found"
              )}
            </CommandEmpty>
            <CommandGroup>
              {filtered.map((u) => (
                <CommandItem
                  key={u.id}
                  value={u.code}
                  onSelect={() => {
                    onValueChange(u.code);
                    setOpen(false);
                  }}
                >
                  <Check
                    className={cn(
                      "mr-2 h-3.5 w-3.5",
                      value === u.code ? "opacity-100" : "opacity-0",
                    )}
                  />
                  <span className="font-medium">{u.name}</span>
                  <span className="ml-auto text-xs text-muted-foreground">{u.family}</span>
                </CommandItem>
              ))}
              {searchIsNewUnit && filtered.length > 0 && (
                <CommandItem
                  value={`__custom_${search}`}
                  onSelect={() => {
                    onValueChange(search.trim().toLowerCase());
                    setOpen(false);
                  }}
                >
                  <span className="text-muted-foreground">
                    Use &ldquo;{search.trim().toLowerCase()}&rdquo;
                  </span>
                </CommandItem>
              )}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
