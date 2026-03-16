/**
 * Renders a data_table block inline in the chat panel.
 * Schema: { type: "data_table", title, columns: string[], rows: string[][] }
 */
function isNumeric(text) {
  if (!text) return false;
  const s = String(text).trim();
  return /^[$%]?[\d,]+\.?\d*[%]?$/.test(s) || /^-?\$?[\d,]+\.?\d*$/.test(s);
}

export function DataTable({ block }) {
  const { title, columns = [], rows = [] } = block;
  if (!columns.length || !rows.length) return null;

  return (
    <div className="my-2">
      {title && (
        <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-muted-foreground mb-1.5">
          {title}
        </p>
      )}
      <div className="overflow-x-auto rounded-lg border border-border/60">
        <table className="min-w-full text-xs">
          <thead className="bg-muted/60 border-b border-border/60">
            <tr>
              {columns.map((col, i) => (
                <th
                  key={i}
                  className="px-2.5 py-1.5 text-left font-medium text-muted-foreground text-[10px] uppercase tracking-wider whitespace-nowrap"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border/30 [&>tr:nth-child(even)]:bg-muted/20">
            {rows.slice(0, 20).map((row, ri) => (
              <tr key={ri}>
                {row.map((cell, ci) => (
                  <td
                    key={ci}
                    className={`px-2.5 py-1.5 whitespace-nowrap ${
                      isNumeric(cell)
                        ? "text-right font-mono tabular-nums text-foreground"
                        : "text-foreground/90"
                    }`}
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length > 20 && (
        <p className="text-[10px] text-muted-foreground mt-1">Showing 20 of {rows.length} rows</p>
      )}
    </div>
  );
}
