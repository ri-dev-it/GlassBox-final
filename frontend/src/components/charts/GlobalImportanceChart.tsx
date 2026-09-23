import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import type { GlobalShapEntry } from '../../types';

export default function GlobalImportanceChart({ data }: { data: GlobalShapEntry[] }) {
  const chartData = [...data].slice(0, 10).reverse().map((d) => ({ name: d.label, value: d.mean_abs_shap }));
  return (
    <ResponsiveContainer width="100%" height={360}>
      <BarChart data={chartData} layout="vertical" margin={{ left: 40, right: 20 }}>
        <XAxis type="number" />
        <YAxis type="category" dataKey="name" width={180} tick={{ fontSize: 12 }} />
        <Tooltip formatter={(v: number) => v.toFixed(4)} />
        <Bar dataKey="value" fill="var(--accent)" />
      </BarChart>
    </ResponsiveContainer>
  );
}
