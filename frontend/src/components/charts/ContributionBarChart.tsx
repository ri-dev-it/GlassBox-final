import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import type { Contribution } from '../../types';

export default function ContributionBarChart({ contributions }: { contributions: Contribution[] }) {
  const data = [...contributions]
    .slice(0, 8)
    .sort((a, b) => a.contribution - b.contribution)
    .map((c) => ({ name: c.label, value: c.contribution }));

  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart data={data} layout="vertical" margin={{ left: 40, right: 20 }}>
        <XAxis type="number" name="Model contribution" label={{ value: 'Model contribution (signed)', position: 'insideBottom', offset: -2 }} />
        <YAxis type="category" dataKey="name" width={180} tick={{ fontSize: 12 }} />
        <Tooltip formatter={(v: number) => v.toFixed(4)} />
        <Bar dataKey="value">
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.value >= 0 ? 'var(--approved)' : 'var(--rejected)'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
