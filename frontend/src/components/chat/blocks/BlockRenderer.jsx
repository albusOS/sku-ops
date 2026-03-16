import { StatGroup } from "./StatGroup";
import { DataTable } from "./DataTable";
import { InlineChart } from "./InlineChart";

/**
 * Renders a list of structured blocks from the agent response.
 * Delegates to the appropriate block component based on type.
 */
export function BlockRenderer({ blocks }) {
  if (!blocks?.length) return null;

  return (
    <div className="mt-2 space-y-1">
      {blocks.map((block, i) => {
        switch (block.type) {
          case "stat_group":
            return <StatGroup key={i} block={block} />;
          case "data_table":
            return <DataTable key={i} block={block} />;
          case "chart":
            return <InlineChart key={i} block={block} />;
          default:
            return null;
        }
      })}
    </div>
  );
}
