'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabaseClient';
import { ArrowLeft, PlusCircle, CheckCircle, AlertCircle, X, Building2 } from 'lucide-react';

export default function NewTransactionPage() {
  const router = useRouter();
  
  const [loading, setLoading] = useState(false);
  
  // Listas de apoio trazidas do banco
  const [assets, setAssets] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [currencies, setCurrencies] = useState<any[]>([]);
  const [wallets, setWallets] = useState<any[]>([]);
  const [brokers, setBrokers] = useState<any[]>([]);

  const [selectedCategoryFilter, setSelectedCategoryFilter] = useState<string>('ALL');
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Modal para cadastrar novo ativo
  const [isAssetModalOpen, setIsAssetModalOpen] = useState(false);
  const [modalLoading, setModalLoading] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);
  const [newTicker, setNewTicker] = useState('');
  const [newName, setNewName] = useState('');
  const [newCategoryId, setNewCategoryId] = useState<number | string>('');
  const [newCurrencyId, setNewCurrencyId] = useState<number | string>('');

  // Campos do formulário de transação
  const [walletId, setWalletId] = useState<number | string>('');
  const [brokerId, setBrokerId] = useState<number | string>('');
  const [assetId, setAssetId] = useState<number | string>('');
  const [transactionType, setTransactionType] = useState<'BUY' | 'SELL'>('BUY');
  const [quantity, setQuantity] = useState('');
  const [unitPrice, setUnitPrice] = useState('');
  const [currencyId, setCurrencyId] = useState<number | string>('');
  const [exchangeRate, setExchangeRate] = useState('1.00');
  const [tradeDate, setTradeDate] = useState(new Date().toISOString().split('T')[0]);
  const [settlementDate, setSettlementDate] = useState('');
  const [notes, setNotes] = useState('');

  const isBRL = Number(currencyId) === 1;

  useEffect(() => {
    fetchAuxiliaryData();
  }, []);

  async function fetchAuxiliaryData() {
    await Promise.all([
      fetchAssets(),
      fetchCategories(),
      fetchCurrencies(),
      fetchWallets(),
      fetchBrokers(),
    ]);
  }

  async function fetchAssets() {
    try {
      const { data, error } = await supabase
        .from('assets')
        .select('id, ticker, name, category_id, currency_id, asset_categories(id, name), currencies(id, name, code)')
        .eq('is_active', true)
        .order('ticker', { ascending: true });

      if (error) throw error;
      if (data) setAssets(data);
    } catch (err) {
      console.error('Erro ao carregar ativos:', err);
    }
  }

  async function fetchCategories() {
    try {
      const { data, error } = await supabase
        .from('asset_categories')
        .select('id, name')
        .order('name', { ascending: true });

      if (error) throw error;
      if (data) {
        setCategories(data);
        if (data.length > 0) setNewCategoryId(data[0].id);
      }
    } catch (err) {
      console.error('Erro ao carregar categorias:', err);
    }
  }

  async function fetchCurrencies() {
    try {
      const { data, error } = await supabase
        .from('currencies')
        .select('id, name, code')
        .order('code', { ascending: true });

      if (error) throw error;
      if (data) {
        setCurrencies(data);
        if (data.length > 0) setNewCurrencyId(data[0].id);
      }
    } catch (err) {
      console.error('Erro ao carregar moedas:', err);
    }
  }

  async function fetchWallets() {
    try {
      const { data, error } = await supabase
        .from('wallets')
        .select('id, name')
        .order('name', { ascending: true });

      if (error) throw error;
      if (data) {
        setWallets(data);
        if (data.length > 0) setWalletId(data[0].id);
      }
    } catch (err) {
      console.error('Erro ao carregar carteiras:', err);
    }
  }

  async function fetchBrokers() {
    try {
      const { data, error } = await supabase
        .from('brokers')
        .select('id, name')
        .order('name', { ascending: true });

      if (error) throw error;
      if (data) {
        setBrokers(data);
        if (data.length > 0) setBrokerId(data[0].id);
      }
    } catch (err) {
      console.error('Erro ao carregar corretoras:', err);
    }
  }

  function handleSelectAsset(val: string) {
    if (val === 'NEW_ASSET') {
      setModalError(null);
      setIsAssetModalOpen(true);
      setAssetId('');
    } else {
      setAssetId(val);
      // Sincroniza a moeda padrão da transação com a moeda do ativo selecionado
      const selectedAsset = assets.find((a) => String(a.id) === val);
      if (selectedAsset?.currency_id) {
        setCurrencyId(selectedAsset.currency_id);
        if (Number(selectedAsset.currency_id) === 1) {
          setExchangeRate('1.00');
        }
      }
    }
  }

  function handleCurrencyChange(val: string) {
    setCurrencyId(val);
    if (Number(val) === 1) {
      setExchangeRate('1.00');
    }
  }

  async function handleCreateAssetSubmit(e: React.FormEvent) {
    e.preventDefault();
    e.stopPropagation();
    setModalError(null);

    if (!newTicker.trim()) return setModalError('O Ticker é obrigatório.');
    if (!newCategoryId) return setModalError('Selecione uma Categoria.');
    if (!newCurrencyId) return setModalError('Selecione uma Moeda.');

    setModalLoading(true);

    try {
      const formattedTicker = newTicker.toUpperCase().trim();
      const formattedName = newName.trim() || formattedTicker;

      const { data, error } = await supabase
        .from('assets')
        .insert([
          {
            ticker: formattedTicker,
            name: formattedName,
            category_id: Number(newCategoryId),
            currency_id: Number(newCurrencyId),
            is_active: true,
          },
        ])
        .select();

      if (error) {
        setModalError(`Erro no Supabase: ${error.message}`);
        return;
      }

      if (data && data.length > 0) {
        setAssetId(data[0].id);
        setCurrencyId(data[0].currency_id);
        if (Number(data[0].currency_id) === 1) {
          setExchangeRate('1.00');
        }
      }

      await fetchAssets();
      setNewTicker('');
      setNewName('');
      setIsAssetModalOpen(false);
      setMessage({ type: 'success', text: `Ativo ${formattedTicker} cadastrado com sucesso!` });
    } catch (err: any) {
      setModalError(`Erro inesperado: ${err.message || 'Falha ao salvar'}`);
    } finally {
      setModalLoading(false);
    }
  }

  // Cálculos de totais
  const numericQty = Number(quantity) || 0;
  const numericPrice = Number(unitPrice) || 0;
  const numericRate = isBRL ? 1 : (Number(exchangeRate) || 1);
  const totalAmount = numericQty * numericPrice;
  const totalAmountBrl = totalAmount * numericRate;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setMessage(null);

    if (!walletId || !brokerId || !assetId || !quantity || !unitPrice || !currencyId || !tradeDate) {
      setMessage({ type: 'error', text: 'Preencha todos os campos obrigatórios (*).' });
      return;
    }

    setLoading(true);

    try {
      const { error } = await supabase.from('transactions').insert([
        {
          wallet_id: Number(walletId),
          asset_id: Number(assetId),
          broker_id: Number(brokerId),
          transaction_type: transactionType,
          trade_date: tradeDate,
          settlement_date: settlementDate || null,
          quantity: numericQty,
          unit_price: numericPrice,
          total_amount: totalAmount,
          currency_id: Number(currencyId),
          exchange_rate_to_brl: isBRL ? 1 : numericRate,
          total_amount_brl: isBRL ? totalAmount : totalAmountBrl,
          notes: notes.trim() || null,
          source: 'manual',
        },
      ]);

      if (error) throw error;

      setMessage({ type: 'success', text: 'Lançamento registrado com sucesso!' });
      setQuantity('');
      setUnitPrice('');
      setNotes('');

      setTimeout(() => {
        router.push('/');
      }, 1500);

    } catch (err: any) {
      console.error('Erro ao salvar transação:', err);
      setMessage({ type: 'error', text: err.message || 'Erro ao salvar o lançamento.' });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-[#090d16] min-h-screen text-slate-100 font-sans p-4 md:p-8">
      <div className="max-w-3xl mx-auto space-y-6">
        
        {/* VOLTAR */}
        <button
          type="button"
          onClick={() => router.push('/')}
          className="flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-white transition"
        >
          <ArrowLeft className="w-4 h-4" /> Voltar para o Dashboard
        </button>

        {/* CABEÇALHO */}
        <div className="bg-[#111827] p-6 rounded-2xl border border-slate-800 shadow-xl flex items-center gap-3">
          <div className="p-3 bg-blue-500/10 text-blue-400 rounded-xl border border-blue-500/20">
            <PlusCircle className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-extrabold text-white">Novo Lançamento</h1>
            <p className="text-xs text-slate-400">Registre compras ou vendas na sua carteira de investimentos</p>
          </div>
        </div>

        {/* FEEDBACK */}
        {message && (
          <div
            className={`p-4 rounded-xl border text-xs font-semibold flex items-center gap-2 ${
              message.type === 'success'
                ? 'bg-emerald-950/60 border-emerald-800 text-emerald-400'
                : 'bg-rose-950/60 border-rose-800 text-rose-400'
            }`}
          >
            {message.type === 'success' ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
            {message.text}
          </div>
        )}

        {/* FORMULÁRIO */}
        <form onSubmit={handleSubmit} className="bg-[#111827] p-6 rounded-2xl border border-slate-800 shadow-xl space-y-5">
          
          {/* TIPO DE OPERAÇÃO */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
              Tipo de Operação *
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setTransactionType('BUY')}
                className={`py-2.5 rounded-xl font-bold text-xs transition border ${
                  transactionType === 'BUY'
                    ? 'bg-emerald-600 text-white border-emerald-500 shadow-md shadow-emerald-600/20'
                    : 'bg-slate-900 text-slate-400 border-slate-800 hover:bg-slate-800'
                }`}
              >
                COMPRA
              </button>
              <button
                type="button"
                onClick={() => setTransactionType('SELL')}
                className={`py-2.5 rounded-xl font-bold text-xs transition border ${
                  transactionType === 'SELL'
                    ? 'bg-rose-600 text-white border-rose-500 shadow-md shadow-rose-600/20'
                    : 'bg-slate-900 text-slate-400 border-slate-800 hover:bg-slate-800'
                }`}
              >
                VENDA
              </button>
            </div>
          </div>

          {/* CARTEIRA E CORRETORA */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                Carteira *
              </label>
              <select
                value={walletId}
                onChange={(e) => setWalletId(e.target.value)}
                className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-blue-500"
                required
              >
                <option value="">Selecione a carteira...</option>
                {wallets.map((w) => (
                  <option key={w.id} value={w.id}>{w.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                Corretora *
              </label>
              <select
                value={brokerId}
                onChange={(e) => setBrokerId(e.target.value)}
                className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-blue-500"
                required
              >
                <option value="">Selecione a corretora...</option>
                {brokers.map((b) => (
                  <option key={b.id} value={b.id}>{b.name}</option>
                ))}
              </select>
            </div>
          </div>

          {/* SELETOR DE ATIVO + FILTRO RÁPIDO */}
          <div>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400">
                Ativo / Ticker *
              </label>

              <div className="flex flex-wrap gap-1">
                <button
                  type="button"
                  onClick={() => setSelectedCategoryFilter('ALL')}
                  className={`px-2 py-1 text-[10px] font-bold rounded-lg border transition ${
                    selectedCategoryFilter === 'ALL'
                      ? 'bg-blue-600 text-white border-blue-500'
                      : 'bg-slate-900 text-slate-400 border-slate-800 hover:bg-slate-800'
                  }`}
                >
                  Todos
                </button>

                {categories.map((cat) => (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => setSelectedCategoryFilter(String(cat.id))}
                    className={`px-2 py-1 text-[10px] font-bold rounded-lg border transition ${
                      selectedCategoryFilter === String(cat.id)
                        ? 'bg-blue-600 text-white border-blue-500'
                        : 'bg-slate-900 text-slate-400 border-slate-800 hover:bg-slate-800'
                    }`}
                  >
                    {cat.name}
                  </button>
                ))}
              </div>
            </div>

            <select
              value={assetId}
              onChange={(e) => handleSelectAsset(e.target.value)}
              className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-blue-500 transition"
              required
            >
              <option value="">Selecione um ativo...</option>
              <option value="NEW_ASSET" className="font-bold text-blue-400 bg-slate-900">
                + Cadastrar Novo Ativo...
              </option>

              {assets
                .filter((asset) => {
                  if (selectedCategoryFilter === 'ALL') return true;
                  return String(asset.category_id) === selectedCategoryFilter;
                })
                .map((asset) => (
                  <option key={asset.id} value={asset.id}>
                    {asset.ticker} ({asset.asset_categories?.name || 'Não Localizado'})
                  </option>
                ))}
            </select>
          </div>

          {/* QUANTIDADE, PREÇO E MOEDA */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                Quantidade *
              </label>
              <input
                type="number"
                step="any"
                placeholder="Ex: 100"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-blue-500"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                Preço Unitário *
              </label>
              <input
                type="number"
                step="any"
                placeholder="Ex: 35.50"
                value={unitPrice}
                onChange={(e) => setUnitPrice(e.target.value)}
                className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-blue-500"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                Moeda *
              </label>
              <select
                value={currencyId}
                onChange={(e) => handleCurrencyChange(e.target.value)}
                className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-blue-500"
                required
              >
                <option value="">Selecione...</option>
                {currencies.map((curr) => (
                  <option key={curr.id} value={curr.id}>
                    {curr.code || curr.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* CÂMBIO E VALORES CALCULADOS */}
          <div className={`grid grid-cols-1 ${isBRL ? 'sm:grid-cols-1' : 'sm:grid-cols-3'} gap-4`}>
            {!isBRL && (
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                  Taxa Câmbio (para BRL)
                </label>
                <input
                  type="number"
                  step="any"
                  placeholder="Ex: 5.25"
                  value={exchangeRate}
                  onChange={(e) => setExchangeRate(e.target.value)}
                  className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-blue-500"
                />
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                Total {isBRL ? '(R$)' : '(Moeda Origem)'}
              </label>
              <div className="w-full bg-[#0b0f19]/60 border border-slate-800/80 rounded-xl px-4 py-3 text-sm font-bold text-white flex items-center h-[46px]">
                {totalAmount.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
              </div>
            </div>

            {!isBRL && (
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                  Total em BRL
                </label>
                <div className="w-full bg-[#0b0f19]/60 border border-slate-800/80 rounded-xl px-4 py-3 text-sm font-bold text-emerald-400 flex items-center h-[46px]">
                  R$ {totalAmountBrl.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
              </div>
            )}
          </div>

          {/* DATAS */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                Data do Negócio (Trade) *
              </label>
              <input
                type="date"
                value={tradeDate}
                onChange={(e) => setTradeDate(e.target.value)}
                className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-blue-500"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                Data de Liquidação (Opcional)
              </label>
              <input
                type="date"
                value={settlementDate}
                onChange={(e) => setSettlementDate(e.target.value)}
                className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          {/* NOTAS / OBSERVAÇÕES */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
              Observações (Opcional)
            </label>
            <textarea
              rows={2}
              placeholder="Ex: Ordem limite executada parcialmente..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* BOTÕES */}
          <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
            <button
              type="button"
              onClick={() => router.push('/')}
              className="w-full sm:w-1/2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold py-3.5 rounded-xl transition border border-slate-700 text-sm"
            >
              Cancelar
            </button>
            
            <button
              type="submit"
              disabled={loading}
              className="w-full sm:w-1/2 bg-blue-600 hover:bg-blue-500 text-white font-bold py-3.5 rounded-xl transition shadow-lg shadow-blue-600/20 disabled:opacity-50 text-sm"
            >
              {loading ? 'Salvando...' : 'Confirmar Lançamento'}
            </button>
          </div>
        </form>

      </div>

      {/* MODAL CADASTRAR NOVO ATIVO */}
      {isAssetModalOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 w-full max-w-md shadow-2xl space-y-4">
            
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Building2 className="w-5 h-5 text-blue-400" />
                <h3 className="font-bold text-white text-base">Cadastrar Novo Ativo</h3>
              </div>
              <button
                type="button"
                onClick={() => setIsAssetModalOpen(false)}
                className="text-slate-400 hover:text-white transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {modalError && (
              <div className="p-3 bg-rose-950/80 border border-rose-800 text-rose-300 text-xs rounded-xl flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{modalError}</span>
              </div>
            )}

            <form onSubmit={handleCreateAssetSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  Ticker / Código *
                </label>
                <input
                  type="text"
                  placeholder="Ex: PETR4, IVVB11, BTC"
                  value={newTicker}
                  onChange={(e) => setNewTicker(e.target.value)}
                  className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500 uppercase"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  Nome da Empresa / Ativo (Opcional)
                </label>
                <input
                  type="text"
                  placeholder="Ex: Petrobras PN"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  Categoria *
                </label>
                <select
                  value={newCategoryId}
                  onChange={(e) => setNewCategoryId(e.target.value)}
                  className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500"
                  required
                >
                  <option value="">Selecione a categoria...</option>
                  {categories.map((cat) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  Moeda *
                </label>
                <select
                  value={newCurrencyId}
                  onChange={(e) => setNewCurrencyId(e.target.value)}
                  className="w-full bg-[#0b0f19] border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500"
                  required
                >
                  <option value="">Selecione a moeda...</option>
                  {currencies.map((curr) => (
                    <option key={curr.id} value={curr.id}>
                      {curr.code ? `${curr.code} - ${curr.name}` : curr.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsAssetModalOpen(false)}
                  className="w-1/2 bg-slate-800 text-slate-300 font-bold py-2.5 rounded-xl border border-slate-700 text-xs"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={modalLoading}
                  className="w-1/2 bg-blue-600 hover:bg-blue-500 text-white font-bold py-2.5 rounded-xl text-xs disabled:opacity-50"
                >
                  {modalLoading ? 'Salvando...' : 'Salvar Ativo'}
                </button>
              </div>
            </form>

          </div>
        </div>
      )}

    </div>
  );
}