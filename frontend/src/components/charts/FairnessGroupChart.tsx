import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export default function FairnessGroupChart({ groupMetrics }: { groupMetrics: Record<string, Record<string, number>> }) {
  const data = Object.entries(groupMetrics).map(([group, metrics]) => ({
    group,
    'Selection Rate': metrics.selection_rate,
    'True Positive Rate': metrics.true_positive_rate,
    'False Positive Rate': metrics.false_positive_rate,
  }));

  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart data={data}>
        <XAxis dataKey="group" />
        <YAxis domain={[0, 1]} tickFormatter={(value) => `${Math.round(value * 100)}%`} label={{ value: 'Rate (%)', angle: -90, position: 'insideLeft' }} />
        <Tooltip />
        <Legend />
        <Bar dataKey="Selection Rate" fill="var(--accent)" />
        <Bar dataKey="True Positive Rate" fill="var(--approved)" />
        <Bar dataKey="False Positive Rate" fill="var(--rejected)" />
      </BarChart>
    </ResponsiveContainer>
  );
}
