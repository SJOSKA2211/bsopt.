"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Calculator, Play, RefreshCcw, CheckCircle2 } from "lucide-react";
import axios from "axios";

const API_BASE = "http://localhost:8000/api/v1";

export default function PricingCalculator() {
  const [params, setParams] = useState({
    underlying_price: 100,
    strike_price: 100,
    time_to_maturity: 1.0,
    volatility: 0.2,
    risk_free_rate: 0.05,
    option_type: "call",
  });

  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any[]>([]);

  const handleCalculate = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE}/pricing/`, params);
      setResults(response.data.results);
    } catch (error) {
      console.error("Calculation failed", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Input Controls */}
        <div className="lg:col-span-1 space-y-4">
          <div className="glass p-6 rounded-2xl space-y-4">
            <h3 className="text-lg font-semibold flex items-center">
              <Calculator className="mr-2 w-5 h-5 text-blue-500" />
              Parameters
            </h3>
            
            <div className="space-y-3">
              {[
                { label: "Underlying Price", key: "underlying_price", step: 1 },
                { label: "Strike Price", key: "strike_price", step: 1 },
                { label: "Volatility (σ)", key: "volatility", step: 0.01 },
                { label: "Risk Free Rate (r)", key: "risk_free_rate", step: 0.01 },
                { label: "Time to Maturity (T)", key: "time_to_maturity", step: 0.1 },
              ].map((input) => (
                <div key={input.key}>
                  <label className="text-xs text-slate-400 block mb-1">{input.label}</label>
                  <input 
                    type="number"
                    step={input.step}
                    value={(params as any)[input.key]}
                    onChange={(e) => setParams({ ...params, [input.key]: parseFloat(e.target.value) })}
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                  />
                </div>
              ))}
              
              <div>
                <label className="text-xs text-slate-400 block mb-1">Option Type</label>
                <div className="flex bg-white/5 p-1 rounded-lg border border-white/10">
                  {["call", "put"].map((t) => (
                    <button
                      key={t}
                      onClick={() => setParams({ ...params, option_type: t })}
                      className={`flex-1 py-1 text-xs rounded-md transition-all ${
                        params.option_type === t ? "bg-blue-500 text-white shadow-lg" : "text-slate-400 hover:text-white"
                      }`}
                    >
                      {t.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <button 
              onClick={handleCalculate}
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 py-3 rounded-xl font-semibold flex items-center justify-center transition-all group"
            >
              {loading ? (
                <RefreshCcw className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2 fill-current group-hover:scale-110 transition-transform" />
                  Compute All Methods
                </>
              )}
            </button>
          </div>
        </div>

        {/* Results Grid */}
        <div className="lg:col-span-2">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <AnimatePresence mode="popLayout">
              {results.length > 0 ? (
                results.map((res, idx) => (
                  <motion.div
                    key={res.method_type}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: idx * 0.05 }}
                    className="glass p-4 rounded-xl border-l-4 border-blue-500"
                  >
                    <div className="flex justify-between items-start">
                      <p className="text-xs text-slate-400 font-mono uppercase tracking-widest">{res.method_type.replace(/_/g, ' ')}</p>
                      {res.converged && <CheckCircle2 className="w-3 h-3 text-emerald-500" />}
                    </div>
                    <div className="mt-2 flex items-baseline justify-between">
                      <h4 className="text-2xl font-bold text-white">${res.computed_price.toFixed(4)}</h4>
                      <p className={`text-[10px] font-medium ${res.mape < 0.1 ? 'text-emerald-400' : 'text-amber-400'}`}>
                        MAPE: {res.mape.toFixed(4)}%
                      </p>
                    </div>
                    <div className="mt-3 w-full bg-white/5 h-1 rounded-full overflow-hidden">
                      <motion.div 
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.min(100, 100 - res.mape * 10)}%` }}
                        className="h-full bg-blue-500"
                      />
                    </div>
                  </motion.div>
                ))
              ) : (
                <div className="col-span-2 h-full min-h-[300px] flex flex-col items-center justify-center text-slate-600 border-2 border-dashed border-white/5 rounded-3xl">
                  <Calculator className="w-12 h-12 mb-4 opacity-20" />
                  <p>Adjust parameters and click compute to see results</p>
                </div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
}
