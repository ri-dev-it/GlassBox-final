import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { PartialDependenceCurve } from '../../types';

export default function PartialDependenceChart({ curve }: { curve: PartialDependenceCurve }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={curve.points} margin={{ left: 8, right: 18, top: 8 }}>
        <XAxis dataKey="value" tick={{ fontSize: 11 }} />
        <YAxis domain={[0, 1]} tickFormatter={(value) => `${Math.round(value * 100)}%`} tick={{ fontSize: 11 }} />
        <Tooltip formatter={(value: number) => `${(value * 100).toFixed(1)}%`} />
        <Line type="monotone" dataKey="approval_probability" stroke="#0d3b70" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}