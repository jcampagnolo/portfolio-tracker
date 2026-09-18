'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabaseClient';
import {
  ArrowLeft,
  PlusCircle,
  Filter,
  Trash2,
  TrendingUp,
  TrendingDown,
  DollarSign,
  ListFilter,
  Calendar,
  XCircle,
  Pencil,
  X,
  AlertCircle,
  CheckCircle,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
} from 'lucide-react';

type SortField =
  | 'trade_date'
  | 'transaction_type'
  | 'ticker'
  | 'wallet'
  | 'broker'
  | 'quantity'
  | 'unit_price'
  | 'total_amount'
  | 'exchange_rate_to_brl'
  | 'total_amount_brl';

type SortDirection = 'asc' | 'desc';

export default function TransactionsListPage() {
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [transactions, setTransactions] = useState<any[]>([]);

  // Abas de categorias macro
  const [activeTab, setActiveTab] = useState<'ALL' | 'EQUITY' | 'FIXED_INCOME' | 'FUNDS'>('ALL');

  // Estados de Ordenação
  const [sortField, setSortField] = useState<SortField>('trade_date');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  // Listas de apoio
  const [wallets, setWallets] = useState<any[]>([]);
  const [brokers, setBrokers] = useState<any[]>([]);
  const [currencies, setCurrencies] = useState<any[]>([]);
  const [assets, setAssets] = useState<any[]>([]);

  // Filtros selecionados
  const [filterWallet, setFilterWallet] = useState<string>('');
  const [filterBroker, setFilterBroker] = useState<string>('');
  const [filterType, setFilterType] = useState<string>('');
  const [filterCurrency, setFilterCurrency] = useState<string>('');
  const [filterTicker, setFilterTicker] = useState<string>('');
  const [filterStartDate, setFilterStartDate] = useState<string>('');
  const [filterEndDate, setFilterEndDate] = useState<string>('');

  // Estados do Modal de Edição
  const [editingItem, setEditingItem] = useState<any | null>(null);
  const [editLoading, setEditLoading] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [editSuccess, setEditSuccess] = useState<string | null>(null);

  const [editWalletId, setEditWalletId] = useState<number | string>('');
  const [editBrokerId, setEditBrokerId] = useState<number | string>('');
  const [editAssetId, setEditAssetId] = useState<number | string>('');
  const [editType, setEditType] = useState<'BUY' | 'SELL'>('BUY');
  const [editQuantity, setEditQuantity] = useState('');
  const [editUnitPrice, setEditUnitPrice] = useState('');
  const [editCurrencyId, setEditCurrencyId] = useState<number | string>('');
  const [editExchangeRate, setEditExchangeRate] = useState('1.00');
  const [editTradeDate, setEditTradeDate] = useState('');
  const [editNotes, setEditNotes] = useState('');

  const isEditBRL = Number(editCurrencyId) === 1;

  useEffect(() => {
    fetchAuxiliaryData();
  }, []);

  useEffect(() => {
    fetchTransactions();
  }, [filterWallet, filterBroker, filterType, filterCurrency, filterTicker, filterStartDate, filterEndDate]);

  async function fetchAuxiliaryData() {
    try {
      const [wRes, bRes, cRes, aRes] = await Promise.all([
        supabase.from('wallets').select('id, name').order('name'),
        supabase.from('brokers').select('id, name').order('name'),
        supabase.from('currencies').select('id, code, name').order('code'),
        supabase.from('assets').select('id, ticker, name, currency_id').eq('is_active', true).order('ticker'),
      ]);

      if (wRes.data) setWallets(wRes.data);
      if (bRes.data) setBrokers(bRes.data);
      if (cRes.data) setCurrencies(cRes.data);
      if (aRes.data) setAssets(aRes.data);
    } catch (err) {
      console.error('Erro ao buscar dados auxiliares:', err);
    }
  }

  async function fetchTransactions() {
    setLoading(true);
    try {
      let query = supabase
        .from('transactions')
        .select(`
          id,
          wallet_id,
          asset_id,
          broker_id,
          currency_id,
          trade_date,
          settlement_date,
          transaction_type,
          quantity,
          unit_price,
          total_amount,
          exchange_rate_to_brl,
          total_amount_brl,
          notes,
          source,
          wallets(name),
          brokers(name),
          assets(id, ticker, name, category_id, asset_categories(name)),
          currencies(id, code, symbol)
        `)
        .order('trade_date', { ascending: false })
        .order('id', { ascending: false });

      if (filterWallet) query = query.eq('wallet_id', Number(filterWallet));
      if (filterBroker) query = query.eq('broker_id', Number(filterBroker));
      if (filterType) query = query.eq('transaction_type', filterType);
      if (filterCurrency) query = query.eq('currency_id', Number(filterCurrency));
      if (filterStartDate) query = query.gte('trade_date', filterStartDate);
      if (filterEndDate) query = query.lte('trade_date', filterEndDate);

      const { data, error } = await query;

      if (error) throw error;

      let filteredData = data || [];

      if (filterTicker.trim()) {
        const term = filterTicker.trim().toLowerCase();
        filteredData = filteredData.filter((t) =>
          t.assets?.ticker?.toLowerCase().includes(term) ||
          t.assets?.name?.toLowerCase().includes(term)
        );
      }

      setTransactions(filteredData);
    } catch (err) {
      console.error('Erro ao buscar transações:', err);
    } finally {
      setLoading(false);
    }
  }

  function clearFilters() {
    setFilterWallet('');
    setFilterBroker('');
    setFilterType('');
    setFilterCurrency('');
    setFilterTicker('');
    setFilterStartDate('');
    setFilterEndDate('');
  }

  async function handleDelete(id: number) {
    if (!confirm('Deseja realmente apagar esta transação?')) return;

    try {
      const { error } = await supabase.from('transactions').delete().eq('id', id);
      if (error) throw error;
      setTransactions((prev) => prev.filter((item) => item.id !== id));
    } catch (err: any) {
      alert(`Erro ao excluir: ${err.message}`);
    }
  }

  function handleOpenEdit(item: any) {
    setEditingItem(item);
    setEditError(null);
    setEditSuccess(null);

    setEditWalletId(item.wallet_id || '');
    setEditBrokerId(item.broker_id || '');
    setEditAssetId(item.asset_id || '');
    setEditType(item.transaction_type || 'BUY');
    setEditQuantity(String(item.quantity || ''));
    setEditUnitPrice(String(item.unit_price || ''));
    setEditCurrencyId(item.currency_id || '');
    setEditExchangeRate(String(item.exchange_rate_to_brl || '1.00'));
    setEditTradeDate(item.trade_date || '');
    setEditNotes(item.notes || '');
  }

  function handleEditAssetChange(val: string) {
    setEditAssetId(val);
    const selectedAsset = assets.find((a) => String(a.id) === val);
    if (selectedAsset?.currency_id) {
      setEditCurrencyId(selectedAsset.currency_id);
      if (Number(selectedAsset.currency_id) === 1) {
        setEditExchangeRate('1.00');
      }
    }
  }

  function handleEditCurrencyChange(val: string) {
    setEditCurrencyId(val);
    if (Number(val) === 1) {
      setEditExchangeRate('1.00');
    }
  }

  async function handleSaveEdit(e: React.FormEvent) {
    e.preventDefault();
    setEditError(null);
    setEditSuccess(null);

    if (!editWalletId || !editBrokerId || !editAssetId || !editQuantity || !editUnitPrice || !editCurrencyId || !editTradeDate) {
      setEditError('Preencha todos os campos obrigatórios (*).');
      return;
    }

    setEditLoading(true);

    try {
      const qty = Number(editQuantity) || 0;
      const price = Number(editUnitPrice) || 0;
      const rate = isEditBRL ? 1 : (Number(editExchangeRate) || 1);
      const total = qty * price;
      const totalBrl = total * rate;

      const { error } = await supabase
        .from('transactions')
        .update({
          wallet_id: Number(editWalletId),
          asset_id: Number(editAssetId),
          broker_id: Number(editBrokerId),
          transaction_type: editType,
          trade_date: editTradeDate,
          quantity: qty,
          unit_price: price,
          total_amount: total,
          currency_id: Number(editCurrencyId),
          exchange_rate_to_brl: isEditBRL ? 1 : rate,
          total_amount_brl: isEditBRL ? total : totalBrl,
          notes: editNotes.trim() || null,
        })
        .eq('id', editingItem.id);

      if (error) throw error;

      setEditSuccess('Lançamento atualizado com sucesso!');
      await fetchTransactions();

      setTimeout(() => {
        setEditingItem(null);
      }, 1000);
    } catch (err: any) {
      setEditError(err.message || 'Erro ao atualizar o lançamento.');
    } finally {
      setEditLoading(false);
    }
  }

  // MANIPULADOR DA ORDENAÇÃO
  function handleSort(field: SortField) {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  }

  // RENDEREIZADOR DE ÍCONE DE ORDENAÇÃO
  function renderSortIcon(field: SortField) {
    if (sortField !== field) {
      return <ArrowUpDown className="w-3 h-3 text-slate-600 group-hover:text-slate-400 transition" />;
    }
    return sortDirection === 'asc' ? (
      <ArrowUp className="w-3.5 h-3.5 text-blue-400" />
    ) : (
      <ArrowDown className="w-3.5 h-3.5 text-blue-400" />
    );
  }

  // FILTRAGEM E ORDENAÇÃO PROCESSADOS VIA USEMEMO
  const processedTransactions = useMemo(() => {
    // 1. Filtrar por Aba
    const filtered = transactions.filter((t) => {
      if (activeTab === 'ALL') return true;

      const categoryName = (t.assets?.asset_categories?.name || '').toLowerCase();

      if (activeTab === 'FIXED_INCOME') {
        return categoryName.includes('fixa') || categoryName.includes('tesouro') || categoryName.includes('cdb');
      }

      if (activeTab === 'FUNDS') {
        return categoryName.includes('fundo') || categoryName.includes('fiagro') || categoryName.includes('fii');
      }

      if (activeTab === 'EQUITY') {
        return (
          categoryName.includes('ação') ||
          categoryName.includes('acoes') ||
          categoryName.includes('etf') ||
          categoryName.includes('cripto') ||
          categoryName.includes('bdr') ||
          (!categoryName.includes('fixa') && !categoryName.includes('fundo'))
        );
      }

      return true;
    });

    // 2. Ordenar
    return filtered.sort((a, b) => {
      let valA: any;
      let valB: any;

      switch (sortField) {
        case 'trade_date':
          valA = a.trade_date ? new Date(a.trade_date).getTime() : 0;
          valB = b.trade_date ? new Date(b.trade_date).getTime() : 0;
          break;
        case 'transaction_type':
          valA = a.transaction_type || '';
          valB = b.transaction_type || '';
          break;
        case 'ticker':
          valA = a.assets?.ticker || '';
          valB = b.assets?.ticker || '';
          break;
        case 'wallet':
          valA = a.wallets?.name || '';
          valB = b.wallets?.name || '';
          break;
        case 'broker':
          valA = a.brokers?.name || '';
          valB = b.brokers?.name || '';
          break;
        case 'quantity':
          valA = Number(a.quantity) || 0;
          valB = Number(b.quantity) || 0;
          break;
        case 'unit_price':
          valA = Number(a.unit_price) || 0;
          valB = Number(b.unit_price) || 0;
          break;
        case 'total_amount':
          valA = Number(a.total_amount) || 0;
          valB = Number(b.total_amount) || 0;
          break;
        case 'exchange_rate_to_brl':
          valA = Number(a.exchange_rate_to_brl) || 1;
          valB = Number(b.exchange_rate_to_brl) || 1;
          break;
        case 'total_amount_brl':
          valA = Number(a.total_amount_brl || a.total_amount) || 0;
          valB = Number(b.total_amount_brl || b.total_amount) || 0;
          break;
        default:
          valA = 0;
          valB = 0;
      }

      if (valA < valB) return sortDirection === 'asc' ? -1 : 1;
      if (valA > valB) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }, [transactions, activeTab, sortField, sortDirection]);

  // CÁLCULOS DOS CARDS
  const totalAmountBrl = processedTransactions.reduce((acc, t) => acc + (Number(t.total_amount_brl) || 0), 0);
  const totalBuyBrl = processedTransactions
    .filter((t) => t.transaction_type === 'BUY')
    .reduce((acc, t) => acc + (Number(t.total_amount_brl) || 0), 0);
  const totalSellBrl = processedTransactions
    .filter((t) => t.transaction_type === 'SELL')
    .reduce((acc, t) => acc + (Number(t.total_amount_brl) || 0), 0);

  return (
    <div className="bg-[#090d16] min-h-screen text-slate-100 font-sans p-4 md:p-8">
      <div className="max-w-7xl mx-auto space-y-6">

        {/* TOP BAR */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <button
            type="button"
            onClick={() => router.push('/')}
            className="flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-white transition"
          >
            <ArrowLeft className="w-4 h-4" /> Voltar ao Dashboard
          </button>

          <button
            type="button"
            onClick={() => router.push('/transactions/new')}
            className="flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold px-4 py-2.5 rounded-xl transition shadow-lg shadow-blue-600/20"
          >
            <PlusCircle className="w-4 h-4" /> Novo Lançamento
          </button>
        </div>

        {/* CABEÇALHO */}
        <div className="bg-[#111827] p-6 rounded-2xl border border-slate-800 shadow-xl flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-blue-500/10 text-blue-400 rounded-xl border border-blue-500/20">
              <ListFilter className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-extrabold text-white">Extrato Analítico de Lançamentos</h1>
              <p className="text-xs text-slate-400">Gerencie e edite suas operações de compra e venda</p>
            </div>
          </div>

          {/* NAVEGAÇÃO ENTRE ABAS */}
          <div className="flex bg-[#0b0f19] p-1 rounded-xl border border-slate-800">
            <button
              type="button"
              onClick={() => setActiveTab('ALL')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                activeTab === 'ALL' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              Todos
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('EQUITY')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                activeTab === 'EQUITY' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              Renda Variável
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('FIXED_INCOME')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                activeTab === 'FIXED_INCOME' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              Renda Fixa
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('FUNDS')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                activeTab === 'FUNDS' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              Fundos
            </button>
          </div>
        </div>

        {/* CARDS RESUMO */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-[#111827] p-4 rounded-xl border border-slate-800 flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Total em Operações</p>
              <p className="text-lg font-black text-white mt-1">
                R$ {totalAmountBrl.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </p>
            </div>
            <div className="p-2.5 bg-blue-500/10 text-blue-400 rounded-lg">
              <DollarSign className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-[#111827] p-4 rounded-xl border border-slate-800 flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Total de Compras</p>
              <p className="text-lg font-black text-emerald-400 mt-1">
                R$ {totalBuyBrl.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </p>
            </div>
            <div className="p-2.5 bg-emerald-500/10 text-emerald-400 rounded-lg">
              <TrendingUp className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-[#111827] p-4 rounded-xl border border-slate-800 flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Total de Vendas</p>
              <p className="text-lg font-black text-rose-400 mt-1">
                R$ {totalSellBrl.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </p>
            </div>
            <div className="p-2.5 bg-rose-500/10 text-rose-400 rounded-lg">
              <TrendingDown className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-[#111827] p-4 rounded-xl border border-slate-800 flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Qtd. de Lançamentos</p>
              <p className="text-lg font-black text-slate-200 mt-1">{processedTransactions.length}</p>
            </div>
            <div className="p-2.5 bg-purple-500/10 text-purple-400 rounded-lg">
              <Calendar className="w-5 h-5" />
            </div>
          </div>
        </div>

        {/* BLOCO DE FILTROS */}
        <div className="bg-[#111827] p-5 rounded-2xl border border-slate-800 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-300 uppercase tracking-wider">
              <Filter className="w-4 h-4 text-blue-400" /> Filtros Avançados
            </div>
            <button
              type="button"
              onClick={clearFilters}
              className="text-xs text-slate-400 hover:text-rose-400 flex items-center gap-1 transition"
            >
              <XCircle className="w-3.5 h-3.5" /> Limpar Filtros
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
            <div>
              <label className="block text-[10px] font-bold uppercase text-slate-400 mb-1">Ticker</label>
              <input
                type="text"
                placeholder="Ex: PETR4"
                value={filterTicker}
                onChange={(e) => setFilterTicker(e.target.value)}
                className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500 uppercase"
              />
            </div>

            <div>
              <label className="block text-[10px] font-bold uppercase text-slate-400 mb-1">Operação</label>
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
              >
                <option value="">Todas</option>
                <option value="BUY">Compra</option>
                <option value="SELL">Venda</option>
              </select>
            </div>

            <div>
              <label className="block text-[10px] font-bold uppercase text-slate-400 mb-1">Carteira</label>
              <select
                value={filterWallet}
                onChange={(e) => setFilterWallet(e.target.value)}
                className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
              >
                <option value="">Todas</option>
                {wallets.map((w) => (
                  <option key={w.id} value={w.id}>{w.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[10px] font-bold uppercase text-slate-400 mb-1">Corretora</label>
              <select
                value={filterBroker}
                onChange={(e) => setFilterBroker(e.target.value)}
                className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
              >
                <option value="">Todas</option>
                {brokers.map((b) => (
                  <option key={b.id} value={b.id}>{b.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[10px] font-bold uppercase text-slate-400 mb-1">Moeda</label>
              <select
                value={filterCurrency}
                onChange={(e) => setFilterCurrency(e.target.value)}
                className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
              >
                <option value="">Todas</option>
                {currencies.map((c) => (
                  <option key={c.id} value={c.id}>{c.code || c.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[10px] font-bold uppercase text-slate-400 mb-1">De</label>
              <input
                type="date"
                value={filterStartDate}
                onChange={(e) => setFilterStartDate(e.target.value)}
                className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-[10px] font-bold uppercase text-slate-400 mb-1">Até</label>
              <input
                type="date"
                value={filterEndDate}
                onChange={(e) => setFilterEndDate(e.target.value)}
                className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>
        </div>

        {/* TABELA DE REGISTROS COM ORDENAÇÃO NOS CABEÇALHOS */}
        <div className="bg-[#111827] rounded-2xl border border-slate-800 shadow-xl overflow-hidden">
          {loading ? (
            <div className="p-12 text-center text-slate-400 text-xs font-semibold">
              Carregando lançamentos...
            </div>
          ) : processedTransactions.length === 0 ? (
            <div className="p-12 text-center text-slate-400 text-xs font-semibold">
              Nenhum lançamento encontrado nesta categoria ou filtro.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 bg-[#0b0f19]/80 text-[10px] font-bold text-slate-400 uppercase tracking-wider select-none">
                    
                    <th
                      onClick={() => handleSort('trade_date')}
                      className="p-4 cursor-pointer hover:text-white transition group"
                    >
                      <div className="flex items-center gap-1.5">
                        Data Negócio {renderSortIcon('trade_date')}
                      </div>
                    </th>

                    <th
                      onClick={() => handleSort('transaction_type')}
                      className="p-4 cursor-pointer hover:text-white transition group"
                    >
                      <div className="flex items-center gap-1.5">
                        Tipo {renderSortIcon('transaction_type')}
                      </div>
                    </th>

                    <th
                      onClick={() => handleSort('ticker')}
                      className="p-4 cursor-pointer hover:text-white transition group"
                    >
                      <div className="flex items-center gap-1.5">
                        Ativo {renderSortIcon('ticker')}
                      </div>
                    </th>

                    <th
                      onClick={() => handleSort('wallet')}
                      className="p-4 cursor-pointer hover:text-white transition group"
                    >
                      <div className="flex items-center gap-1.5">
                        Carteira {renderSortIcon('wallet')}
                      </div>
                    </th>

                    <th
                      onClick={() => handleSort('broker')}
                      className="p-4 cursor-pointer hover:text-white transition group"
                    >
                      <div className="flex items-center gap-1.5">
                        Corretora {renderSortIcon('broker')}
                      </div>
                    </th>

                    <th
                      onClick={() => handleSort('quantity')}
                      className="p-4 cursor-pointer hover:text-white transition group text-right"
                    >
                      <div className="flex items-center justify-end gap-1.5">
                        Qtd. {renderSortIcon('quantity')}
                      </div>
                    </th>

                    <th
                      onClick={() => handleSort('unit_price')}
                      className="p-4 cursor-pointer hover:text-white transition group text-right"
                    >
                      <div className="flex items-center justify-end gap-1.5">
                        Preço Unit. {renderSortIcon('unit_price')}
                      </div>
                    </th>

                    <th
                      onClick={() => handleSort('total_amount')}
                      className="p-4 cursor-pointer hover:text-white transition group text-right"
                    >
                      <div className="flex items-center justify-end gap-1.5">
                        Total (Moeda) {renderSortIcon('total_amount')}
                      </div>
                    </th>

                    <th
                      onClick={() => handleSort('exchange_rate_to_brl')}
                      className="p-4 cursor-pointer hover:text-white transition group text-right"
                    >
                      <div className="flex items-center justify-end gap-1.5">
                        Câmbio {renderSortIcon('exchange_rate_to_brl')}
                      </div>
                    </th>

                    <th
                      onClick={() => handleSort('total_amount_brl')}
                      className="p-4 cursor-pointer hover:text-white transition group text-right"
                    >
                      <div className="flex items-center justify-end gap-1.5">
                        Total (BRL) {renderSortIcon('total_amount_brl')}
                      </div>
                    </th>

                    <th className="p-4 text-center">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-xs">
                  {processedTransactions.map((t) => {
                    const isBuy = t.transaction_type === 'BUY';
                    const currencySymbol = t.currencies?.symbol || t.currencies?.code || '$';

                    return (
                      <tr key={t.id} className="hover:bg-slate-900/40 transition">
                        <td className="p-4 text-slate-300 whitespace-nowrap">
                          {t.trade_date ? new Date(t.trade_date + 'T00:00:00').toLocaleDateString('pt-BR') : '-'}
                        </td>

                        <td className="p-4 whitespace-nowrap">
                          <span
                            className={`px-2.5 py-1 rounded-md text-[10px] font-bold border ${
                              isBuy
                                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                                : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                            }`}
                          >
                            {isBuy ? 'COMPRA' : 'VENDA'}
                          </span>
                        </td>

                        <td className="p-4 font-bold text-white whitespace-nowrap">
                          {t.assets?.ticker || 'N/A'}
                        </td>

                        <td className="p-4 text-slate-300 whitespace-nowrap">
                          {t.wallets?.name || 'N/A'}
                        </td>

                        <td className="p-4 text-slate-300 whitespace-nowrap">
                          {t.brokers?.name || 'N/A'}
                        </td>

                        <td className="p-4 text-right font-medium text-slate-200 whitespace-nowrap">
                          {Number(t.quantity).toLocaleString('pt-BR', { maximumFractionDigits: 8 })}
                        </td>

                        <td className="p-4 text-right font-medium text-slate-200 whitespace-nowrap">
                          {currencySymbol} {Number(t.unit_price).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
                        </td>

                        <td className="p-4 text-right font-semibold text-slate-100 whitespace-nowrap">
                          {currencySymbol} {Number(t.total_amount).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </td>

                        <td className="p-4 text-right text-slate-400 whitespace-nowrap">
                          {t.exchange_rate_to_brl ? Number(t.exchange_rate_to_brl).toFixed(4) : '1.0000'}
                        </td>

                        <td className="p-4 text-right font-bold text-emerald-400 whitespace-nowrap">
                          R$ {Number(t.total_amount_brl || t.total_amount).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </td>

                        <td className="p-4 text-center whitespace-nowrap flex items-center justify-center gap-1">
                          <button
                            type="button"
                            onClick={() => handleOpenEdit(t)}
                            className="p-1.5 text-slate-400 hover:text-blue-400 hover:bg-blue-500/10 rounded-lg transition"
                            title="Editar Lançamento"
                          >
                            <Pencil className="w-4 h-4" />
                          </button>

                          <button
                            type="button"
                            onClick={() => handleDelete(t.id)}
                            className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition"
                            title="Apagar Lançamento"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

      </div>

      {/* MODAL EDIÇÃO */}
      {editingItem && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 w-full max-w-xl shadow-2xl space-y-4">
            
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Pencil className="w-5 h-5 text-blue-400" />
                <h3 className="font-bold text-white text-base">Editar Lançamento #{editingItem.id}</h3>
              </div>
              <button
                type="button"
                onClick={() => setEditingItem(null)}
                className="text-slate-400 hover:text-white transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {editError && (
              <div className="p-3 bg-rose-950/80 border border-rose-800 text-rose-300 text-xs rounded-xl flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{editError}</span>
              </div>
            )}

            {editSuccess && (
              <div className="p-3 bg-emerald-950/80 border border-emerald-800 text-emerald-300 text-xs rounded-xl flex items-center gap-2">
                <CheckCircle className="w-4 h-4 flex-shrink-0" />
                <span>{editSuccess}</span>
              </div>
            )}

            <form onSubmit={handleSaveEdit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase text-slate-400 mb-2">Tipo de Operação</label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setEditType('BUY')}
                    className={`py-2 rounded-xl font-bold text-xs transition border ${
                      editType === 'BUY'
                        ? 'bg-emerald-600 text-white border-emerald-500'
                        : 'bg-slate-900 text-slate-400 border-slate-800'
                    }`}
                  >
                    COMPRA
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditType('SELL')}
                    className={`py-2 rounded-xl font-bold text-xs transition border ${
                      editType === 'SELL'
                        ? 'bg-rose-600 text-white border-rose-500'
                        : 'bg-slate-900 text-slate-400 border-slate-800'
                    }`}
                  >
                    VENDA
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold uppercase text-slate-400 mb-1">Carteira *</label>
                  <select
                    value={editWalletId}
                    onChange={(e) => setEditWalletId(e.target.value)}
                    className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                    required
                  >
                    {wallets.map((w) => (
                      <option key={w.id} value={w.id}>{w.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase text-slate-400 mb-1">Corretora *</label>
                  <select
                    value={editBrokerId}
                    onChange={(e) => setEditBrokerId(e.target.value)}
                    className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                    required
                  >
                    {brokers.map((b) => (
                      <option key={b.id} value={b.id}>{b.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold uppercase text-slate-400 mb-1">Ativo *</label>
                  <select
                    value={editAssetId}
                    onChange={(e) => handleEditAssetChange(e.target.value)}
                    className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                    required
                  >
                    {assets.map((a) => (
                      <option key={a.id} value={a.id}>{a.ticker} - {a.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase text-slate-400 mb-1">Moeda *</label>
                  <select
                    value={editCurrencyId}
                    onChange={(e) => handleEditCurrencyChange(e.target.value)}
                    className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                    required
                  >
                    {currencies.map((c) => (
                      <option key={c.id} value={c.id}>{c.code || c.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-semibold uppercase text-slate-400 mb-1">Qtd. *</label>
                  <input
                    type="number"
                    step="any"
                    value={editQuantity}
                    onChange={(e) => setEditQuantity(e.target.value)}
                    className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase text-slate-400 mb-1">Preço Unit. *</label>
                  <input
                    type="number"
                    step="any"
                    value={editUnitPrice}
                    onChange={(e) => setEditUnitPrice(e.target.value)}
                    className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                    required
                  />
                </div>

                {!isEditBRL && (
                  <div>
                    <label className="block text-xs font-semibold uppercase text-slate-400 mb-1">Câmbio (BRL)</label>
                    <input
                      type="number"
                      step="any"
                      value={editExchangeRate}
                      onChange={(e) => setEditExchangeRate(e.target.value)}
                      className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                    />
                  </div>
                )}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold uppercase text-slate-400 mb-1">Data *</label>
                  <input
                    type="date"
                    value={editTradeDate}
                    onChange={(e) => setEditTradeDate(e.target.value)}
                    className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase text-slate-400 mb-1">Observações</label>
                  <input
                    type="text"
                    value={editNotes}
                    onChange={(e) => setEditNotes(e.target.value)}
                    className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setEditingItem(null)}
                  className="w-1/2 bg-slate-800 text-slate-300 font-bold py-2.5 rounded-xl border border-slate-700 text-xs"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={editLoading}
                  className="w-1/2 bg-blue-600 hover:bg-blue-500 text-white font-bold py-2.5 rounded-xl text-xs disabled:opacity-50"
                >
                  {editLoading ? 'Salvando...' : 'Salvar Alterações'}
                </button>
              </div>
            </form>

          </div>
        </div>
      )}

    </div>
  );
}