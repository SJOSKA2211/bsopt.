"use client";

import { motion } from "framer-motion";
import { 
  TrendingUp, 
  Activity, 
  AlertTriangle, 
  Layers, 
  Database,
  ArrowUpRight,
  Monitor
} from "lucide-react";
import PricingCalculator from "@/components/PricingCalculator";

interface KpiCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: string;
  trendColor?: string;
  colorClass: string;
}

function KpiCard({ title, value, icon, trend, trendColor, colorClass }: KpiCardProps) {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.02 }}
      className="glass p-6 rounded-2xl relative overflow-hidden group"
    >
      <div className={`absolute top-0 right-0 w-24 h-24 blur-3xl opacity-10 transition-opacity group-hover:opacity-20 ${colorClass}`} />
      
      <div className="flex justify-between items-start mb-4">
        <div className={`p-3 rounded-xl bg-opacity-10 ${colorClass} text-white`}>
          {icon}
        </div>
        {trend && (
          <div className={`flex items-center text-xs font-medium ${trendColor}`}>
            {trend} <ArrowUpRight className="ml-1 w-3 h-3" />
          </div>
        )}
      </div>
      
      <div>
        <p className="text-slate-400 text-sm font-medium mb-1">{title}</p>
        <h3 className="text-3xl font-bold tracking-tight text-white">{value}</h3>
      </div>
    </motion.div>
  );
}

export default function Dashboard() {
  return (
    <div className="min-h-screen bg-[#050505] text-slate-200">
      {/* Sidebar (Small icons for now) */}
      <aside className="fixed left-0 top-0 bottom-0 w-20 glass flex flex-col items-center py-8 space-y-8 z-50">
        <div className="w-12 h-12 bg-blue-600 rounded-2xl flex items-center justify-center shadow-lg shadow-blue-500/20">
          <Monitor className="w-6 h-6 text-white" />
        </div>
        <div className="flex-1 space-y-6">
          <Activity className="w-6 h-6 text-slate-500 hover:text-blue-400 cursor-pointer transition-colors" />
          <Layers className="w-6 h-6 text-slate-500 hover:text-blue-400 cursor-pointer transition-colors" />
          <Database className="w-6 h-6 text-slate-500 hover:text-blue-400 cursor-pointer transition-colors" />
        </div>
      </aside>

      {/* Main Content */}
      <main className="pl-28 pr-8 py-8 space-y-8">
        {/* Header */}
        <header className="flex justify-between items-end">
          <div>
            <h1 className="text-4xl font-bold text-white tracking-tight">System Overview</h1>
            <p className="text-slate-400 mt-2">Real-time options research & numerical method stability monitoring.</p>
          </div>
          <div className="flex items-center space-x-3 text-xs glass px-4 py-2 rounded-full border-blue-500/20 text-blue-400">
            <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
            LIVE INFRASTRUCTURE
          </div>
        </header>

        {/* KPI Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <KpiCard 
            title="Total Experiments" 
            value="1,284" 
            icon={<Layers className="w-6 h-6" />} 
            trend="+12% vs last month"
            trendColor="text-emerald-400"
            colorClass="bg-blue-500"
          />
          <KpiCard 
            title="Active Option Sets" 
            value="842" 
            icon={<Database className="w-6 h-6" />} 
            trend="+5.4%"
            trendColor="text-emerald-400"
            colorClass="bg-emerald-500"
          />
          <KpiCard 
            title="Drift Alerts" 
            value="3" 
            icon={<AlertTriangle className="w-6 h-6" />} 
            trend="Critical priority"
            trendColor="text-amber-400"
            colorClass="bg-amber-500"
          />
          <KpiCard 
            title="Data Throughput" 
            value="1.4M" 
            icon={<Activity className="w-6 h-6" />} 
            trend="Stable"
            trendColor="text-slate-400"
            colorClass="bg-purple-500"
          />
        </div>

        {/* Pricing Calculator Section */}
        <section>
          <div className="flex items-center space-x-2 mb-6">
            <h2 className="text-2xl font-bold text-white">Cross-Method Validator</h2>
            <div className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/20 text-blue-400 border border-blue-500/20">REAL-TIME</div>
          </div>
          <PricingCalculator />
        </section>

        {/* Bottom Section */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
           <div className="lg:col-span-2 glass rounded-3xl p-8 min-h-[300px]">
             <h2 className="text-xl font-semibold text-white mb-6">Error Convergence</h2>
             <div className="h-48 w-full flex items-center justify-center text-slate-700 font-mono text-sm">
                [ CONVERGENCE_PLOT_READY_FOR_RECHARTS ]
             </div>
           </div>
           
           <div className="glass rounded-3xl p-8">
             <h2 className="text-xl font-semibold text-white mb-6">Active Task Queue</h2>
             <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="flex items-center space-x-4 p-4 rounded-xl bg-white/5 border border-white/10 group hover:border-blue-500/50 transition-colors">
                    <div className="w-2 h-2 rounded-full bg-emerald-500" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-white">Ray Scraper Task #{i+1024}</p>
                      <div className="flex items-center mt-1">
                        <div className="w-full bg-white/5 h-1 rounded-full mr-2">
                           <div className="w-2/3 h-full bg-blue-500" />
                        </div>
                        <span className="text-[10px] text-slate-500">67%</span>
                      </div>
                    </div>
                  </div>
                ))}
             </div>
           </div>
        </div>
      </main>
    </div>
  );
}
