'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabaseClient';
import {
  Wallet,
  DollarSign,
  PlusCircle,
  ListFilter,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react';

export default function DashboardPage() {
  const router = useRouter();

  const [loading, setLoading] = useState(true);

  // Métricas do Patrimônio
  const [patrimonioTotal, setPatrimonioTotal] = useState(0);
  const [totalInvestido, setTotalInvestido] = useState(0);
  const [rentabilidadeBrutaVal, setRentabilidadeBrutaVal] = useState(0);
  const [rentabilidadeBrutaPct, setRentabilidadeBrutaPct] = useState(0);

  // Métricas de Proventos
  const [proventosMesAtual, setProventosMesAtual] = useState(0);
  const [proventos12MesesTotal, setProventos12MesesTotal] = useState(0);
  const [proventos12MesesMedia, setProventos12MesesMedia] = useState(0);

  useEffect(() => {
    fetchDashboardMetrics();
  }, []);

  async function fetchDashboardMetrics() {
    setLoading(true);
    try {
      // 1. TRANSAÇÕES (Patrimônio e Investido)
      const { data: txData, error: txError } = await supabase
        .from('transactions')
        .select('transaction_type, quantity, unit_price, total_amount, total_amount_brl');
  
      if (txError) throw txError;
  
      let invested = 0;
      if (txData && txData.length > 0) {
        txData.forEach((t) => {
          const valBrl = Number(t.total_amount_brl || t.total_amount) || 0;
          
          if (t.transaction_type === 'BUY' || t.transaction_type === 'COMPRA') {
            invested += valBrl;
          } else if (t.transaction_type === 'SELL' || t.transaction_type === 'VENDA') {
            invested -= valBrl;
          }
        });
      }
  
      setTotalInvestido(invested);
      setPatrimonioTotal(invested);
  
      const profitVal = 0; // Pode ser ajustado via cotação atual das posições
      setRentabilidadeBrutaVal(profitVal);
      setRentabilidadeBrutaPct(0);
  
      // 2. PROVENTOS (Tabela public.dividends)
      const now = new Date();
      const currentYearMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  
      const date12MonthsAgo = new Date();
      date12MonthsAgo.setMonth(now.getMonth() - 12);
      const str12MonthsAgo = date12MonthsAgo.toISOString().slice(0, 10);
  
      const { data: divData, error: divError } = await supabase
        .from('dividends')
        .select('date, gross_per_share, shares_held, total_received, currency')
        .gte('date', str12MonthsAgo);
  
      if (divError) throw divError;
  
      let currentMonthVal = 0;
      let total12m = 0;
      const usdRate = 5.20; // Cotação base para conversão USD -> BRL (pode ser dinâmica)
  
      if (divData && divData.length > 0) {
        divData.forEach((d) => {
          // Se total_received estiver preenchido, usa ele; senão calcula: gross_per_share * shares_held
          const gross = Number(d.gross_per_share) || 0;
          const shares = Number(d.shares_held) || 0;
          let amount = Number(d.total_received) || (gross * shares);
  
          // Se o provento for em USD, converte para BRL
          if (d.currency === 'USD') {
            amount = amount * usdRate;
          }
  
          total12m += amount;
  
          // Filtra os recebidos no mês corrente (YYYY-MM)
          if (d.date && String(d.date).startsWith(currentYearMonth)) {
            currentMonthVal += amount;
          }
        });
      }
  
      setProventosMesAtual(currentMonthVal);
      setProventos12MesesTotal(total12m);
      setProventos12MesesMedia(total12m > 0 ? total12m / 12 : 0);
  
    } catch (err) {
      console.error('Erro ao buscar métricas do Dashboard:', err);
    } finally {
      setLoading(false);
    }
  }

  const isProfit = rentabilidadeBrutaVal >= 0;

  return (
    <div className="bg-[#090d16] min-h-screen text-slate-100 font-sans p-4 md:p-8">
      <div className="max-w-7xl mx-auto space-y-6">

        {/* BARRA SUPERIOR */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
          <div>
            <h1 className="text-xl font-black text-white tracking-tight">Dashboard Financeiro</h1>
            <p className="text-xs text-slate-400">Resumo do seu patrimônio e fluxo de proventos</p>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => router.push('/transactions')}
              className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold px-3.5 py-2 rounded-xl border border-slate-700 transition"
            >
              <ListFilter className="w-4 h-4 text-blue-400" /> Ver Lançamentos
            </button>

            <button
              type="button"
              onClick={() => router.push('/transactions/new')}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold px-3.5 py-2 rounded-xl transition shadow-lg shadow-blue-600/20"
            >
              <PlusCircle className="w-4 h-4" /> Novo Lançamento
            </button>
          </div>
        </div>

        {/* CARDS RESUMO COMPACTOS (1 LINHA COM 2 CARDS) */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

          {/* CARD 1: PATRIMÔNIO */}
          <div className="bg-[#111827] p-4 rounded-2xl border border-slate-800 shadow-xl flex flex-col justify-between space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-blue-500/10 text-blue-400 rounded-lg border border-blue-500/20">
                  <Wallet className="w-4 h-4" />
                </div>
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Patrimônio Total</span>
              </div>
              <span className="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded-md font-semibold">
                Consolidado
              </span>
            </div>

            <div>
              <p className="text-2xl font-black text-white tracking-tight">
                {loading ? (
                  <span className="text-slate-600 animate-pulse">R$ ---</span>
                ) : (
                  `R$ ${patrimonioTotal.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                )}
              </p>
            </div>

            <div className="pt-2 border-t border-slate-800/80 grid grid-cols-2 gap-2 text-xs">
              <div>
                <p className="text-[10px] text-slate-500 uppercase font-semibold">Total Investido</p>
                <p className="font-bold text-slate-300 mt-0.5">
                  R$ {totalInvestido.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </p>
              </div>

              <div>
                <p className="text-[10px] text-slate-500 uppercase font-semibold">Rentabilidade Bruta</p>
                <div className={`flex items-center gap-1 font-bold mt-0.5 ${isProfit ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {isProfit ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                  <span>
                    R$ {Math.abs(rentabilidadeBrutaVal).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                  <span className="text-[10px] opacity-80">
                    ({rentabilidadeBrutaPct >= 0 ? '+' : ''}{rentabilidadeBrutaPct.toFixed(2)}%)
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* CARD 2: PROVENTOS */}
          <div className="bg-[#111827] p-4 rounded-2xl border border-slate-800 shadow-xl flex flex-col justify-between space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-lg border border-emerald-500/20">
                  <DollarSign className="w-4 h-4" />
                </div>
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Proventos (Mês Atual)</span>
              </div>
              <span className="text-[10px] bg-emerald-950 text-emerald-400 border border-emerald-800/50 px-2 py-0.5 rounded-md font-semibold">
                A Receber / Recebido
              </span>
            </div>

            <div>
              <p className="text-2xl font-black text-emerald-400 tracking-tight">
                {loading ? (
                  <span className="text-slate-600 animate-pulse">R$ ---</span>
                ) : (
                  `R$ ${proventosMesAtual.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                )}
              </p>
            </div>

            <div className="pt-2 border-t border-slate-800/80 grid grid-cols-2 gap-2 text-xs">
              <div>
                <p className="text-[10px] text-slate-500 uppercase font-semibold">Total (Últimos 12m)</p>
                <p className="font-bold text-slate-300 mt-0.5">
                  R$ {proventos12MesesTotal.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </p>
              </div>

              <div>
                <p className="text-[10px] text-slate-500 uppercase font-semibold">Média Mensal (12m)</p>
                <p className="font-bold text-slate-300 mt-0.5">
                  R$ {proventos12MesesMedia.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </p>
              </div>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}