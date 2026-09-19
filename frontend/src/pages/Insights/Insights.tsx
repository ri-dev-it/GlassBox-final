import { useEffect, useState } from 'react';
import { Brain, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';
import { explanationApi } from '../../services/api';
import type { PartialDependenceCurve } from '../../types';
import PartialDependenceChart from '../../components/charts/PartialDependenceChart';

export default function Insights() {
	const [curves, setCurves] = useState<PartialDependenceCurve[]>([]);
	const [selectedFeature, setSelectedFeature] = useState('');

	useEffect(() => {
		explanationApi.partialDependence().then((result) => {
			setCurves(result);
			setSelectedFeature(result[0]?.feature ?? '');
		}).catch(() => undefined);
	}, []);

	const selectedCurve = curves.find((curve) => curve.feature === selectedFeature);
	return <div className="mx-auto max-w-3xl"><p className="text-sm font-medium text-sky-700">Explainable AI</p><h1 className="mt-1 text-3xl font-bold text-[#102a4c]">AI Insights</h1><div className="mt-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"><div className="flex gap-4"><span className="rounded-xl bg-sky-50 p-3 text-sky-700"><Brain /></span><div><h2 className="font-semibold text-slate-800">Individual prediction explanations</h2><p className="mt-1 text-sm leading-6 text-slate-500">Every submitted application is explained using actual SHAP and LIME contributions from the saved model. Rejected applications can also include a DiCE what-if simulation.</p></div></div><div className="mt-6 rounded-lg bg-slate-50 p-4 text-sm text-slate-600"><Sparkles className="mr-2 inline text-sky-600" size={16} />Select an application from your history to review its model probability, AI risk score, feature importance, and model-based improvement scenarios.</div><Link to="/history" className="mt-5 inline-flex rounded-lg bg-[#0d3b70] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#092e57]">View application history</Link></div>{selectedCurve && <section className="mt-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-sm font-medium text-sky-700">Model behavior</p><h2 className="mt-1 text-lg font-semibold text-slate-800">Partial dependence</h2></div><select value={selectedFeature} onChange={(event) => setSelectedFeature(event.target.value)} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700">{curves.map((curve) => <option key={curve.feature} value={curve.feature}>{curve.label}</option>)}</select></div><PartialDependenceChart curve={selectedCurve} /><p className="text-xs text-slate-500">Average predicted approval probability as this feature changes across the reference applicants. This describes model behavior, not causation.</p></section>}</div>;
}
