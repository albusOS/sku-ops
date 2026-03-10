import { useState, useMemo } from "react";
import { Check, ChevronsUpDown, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { useProductGroups } from "@/hooks/useProducts";

/**
 * Combobox for selecting or creating a product group.
 * Shows existing groups with variant counts; allows typing a new name.
 *
 * @param {string}   value      Current group name (or "")
 * @param {function} onChange   (groupName: string) => void
 * @param {string}   className  Additional classes for the trigger
 * @param {boolean}  compact    Tighter styling
 * @param {boolean}  disabled   Read-only
 */
export function GroupCombobox({ value, onChange, className, compact, disabled }) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const { data: groups = [] } = useProductGroups();

  const filtered = useMemo(() => {
    if (!search.trim()) return groups;
    const q = search.toLowerCase();
    return groups.filter((g) => g.product_group.toLowerCase().includes(q));
  }, [groups, search]);

  const exactMatch = groups.some(
    (g) => g.product_group.toLowerCase() === search.trim().toLowerCase()
  );

  const handleSelect = (groupName) => {
    onChange(groupName);
    setOpen(false);
    setSearch("");
  };

  const handleClear = (e) => {
    e.stopPropagation();
    onChange("");
  };

  const triggerCls = compact
    ? "input-field h-9 text-sm w-full justify-between"
    : "input-workshop mt-2 w-full justify-between";

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          disabled={disabled}
          className={cn(triggerCls, "font-normal", className)}
        >
          <span className={cn("truncate", !value && "text-muted-foreground")}>
            {value || (compact ? "Group" : "Select or create group")}
          </span>
          <div className="flex items-center gap-1 ml-auto shrink-0">
            {value && !disabled && (
              <X
                className="h-3.5 w-3.5 text-muted-foreground hover:text-foreground cursor-pointer"
                onClick={handleClear}
              />
            )}
            <ChevronsUpDown className="h-3.5 w-3.5 text-muted-foreground" />
          </div>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[300px] p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput
            placeholder="Search or type new group…"
            value={search}
            onValueChange={setSearch}
          />
          <CommandList>
            <CommandEmpty>
              {search.trim() ? (
                <button
                  className="w-full text-left px-2 py-1.5 text-sm hover:bg-accent rounded-sm cursor-pointer"
                  onClick={() => handleSelect(search.trim())}
                >
                  Create &ldquo;{search.trim()}&rdquo;
                </button>
              ) : (
                "No groups yet"
              )}
            </CommandEmpty>
            <CommandGroup>
              {filtered.map((g) => (
                <CommandItem
                  key={g.product_group}
                  value={g.product_group}
                  onSelect={() => handleSelect(g.product_group)}
                >
                  <Check
                    className={cn(
                      "mr-2 h-4 w-4",
                      value === g.product_group ? "opacity-100" : "opacity-0"
                    )}
                  />
                  <div className="flex-1 min-w-0">
                    <span className="truncate block">{g.product_group}</span>
                    <span className="text-xs text-muted-foreground">
                      {g.product_count} product{g.product_count !== 1 ? "s" : ""}
                      {" · "}qty {Math.round(g.total_quantity)}
                    </span>
                  </div>
                </CommandItem>
              ))}
              {search.trim() && !exactMatch && filtered.length > 0 && (
                <CommandItem
                  value={`__create__${search.trim()}`}
                  onSelect={() => handleSelect(search.trim())}
                >
                  <span className="text-accent">+ Create &ldquo;{search.trim()}&rdquo;</span>
                </CommandItem>
              )}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
