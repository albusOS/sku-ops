import React from "react";

function isNumeric(text) {
  if (!text) return false;
  const s = String(text).trim();
  return /^[$%]?[\d,]+\.?\d*[%]?$/.test(s) || /^-?\$?[\d,]+\.?\d*$/.test(s);
}

const mdComponents = {
  table: ({ children }) => (
    <div className="overflow-x-auto my-2.5 rounded-lg border border-border/60">
      <table className="min-w-full text-xs">{children}</table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="bg-muted/60 border-b border-border/60">{children}</thead>
  ),
  tbody: ({ children }) => (
    <tbody className="divide-y divide-border/30 [&>tr:nth-child(even)]:bg-muted/20">
      {children}
    </tbody>
  ),
  th: ({ children }) => (
    <th className="px-2.5 py-1.5 text-left font-medium text-muted-foreground text-[10px] uppercase tracking-wider whitespace-nowrap">
      {children}
    </th>
  ),
  td: ({ children }) => {
    const numeric = isNumeric(children);
    return (
      <td
        className={`px-2.5 py-1.5 whitespace-nowrap ${numeric ? "text-right font-mono tabular-nums text-foreground" : "text-foreground/90"}`}
      >
        {children}
      </td>
    );
  },
  p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed text-[15px]">{children}</p>,
  strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
  ul: ({ children }) => (
    <ul className="mb-2 space-y-1 pl-5 list-disc marker:text-muted-foreground">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="mb-2 space-y-1 pl-5 list-decimal marker:text-muted-foreground">{children}</ol>
  ),
  li: ({ children }) => (
    <li className="text-foreground/90 leading-relaxed text-[15px]">{children}</li>
  ),
  h1: ({ children }) => (
    <h1 className="font-bold text-foreground text-base mb-1.5 mt-3 first:mt-0">{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 className="font-semibold text-foreground text-[15px] mb-1.5 mt-3 first:mt-0">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="font-medium text-foreground text-sm mb-1 mt-2.5 first:mt-0">{children}</h3>
  ),
  pre: ({ children }) => (
    <pre className="my-2.5 p-3 bg-sidebar/80 rounded-lg overflow-x-auto text-xs text-foreground/80 font-mono leading-relaxed border border-border/40">
      {children}
    </pre>
  ),
  code: ({ className, children }) =>
    className ? (
      <code className={className}>{children}</code>
    ) : (
      <code className="px-1 py-0.5 bg-muted/80 rounded text-xs font-mono text-accent">
        {children}
      </code>
    ),
  hr: () => <hr className="my-3 border-border/40" />,
  blockquote: ({ children }) => (
    <blockquote className="border-l-2 border-accent/60 pl-3 my-2.5 text-muted-foreground text-sm">
      {children}
    </blockquote>
  ),
};

export { isNumeric, mdComponents };
