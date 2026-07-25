import type { AccountV1 } from "@relief/contracts";
import { Card, CardContent, CardHeader, CardTitle } from "@relief/design-system";
import { formatDateTime, formatCents } from "@/lib/format";

/** Section 21.2. */
export function BalanceSummary({ accounts }: { accounts: AccountV1[] }) {
  const total = accounts.reduce((sum, account) => sum + account.current_balance_cents, 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Balance</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <p className="font-mono text-2xl font-semibold tabular-nums text-foreground">{formatCents(total)}</p>
        <ul className="flex flex-col gap-1">
          {accounts.map((account) => (
            <li key={account.account_id} className="flex items-center justify-between text-sm text-muted-foreground">
              <span>{account.display_name}</span>
              <span className="font-mono tabular-nums">{formatCents(account.current_balance_cents)}</span>
            </li>
          ))}
        </ul>
        {accounts[0] && (
          <p className="text-xs text-muted-foreground">Updated {formatDateTime(accounts[0].balance_updated_at)}</p>
        )}
      </CardContent>
    </Card>
  );
}
